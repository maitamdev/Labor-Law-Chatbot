# -*- coding: utf-8 -*-
"""Compact grounded prompts for the local Ollama model.

Legal rules belong in retrieved evidence and deterministic validators, not in a
30K-character system prompt. Keeping this module compact materially reduces
prompt-evaluation latency on consumer GPUs and avoids context truncation.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional


SYSTEM_PROMPT = """Bạn là VietLabor AI, trợ lý tra cứu pháp luật lao động Việt Nam.

NGUYÊN TẮC BẮT BUỘC:
1. Chỉ sử dụng dữ kiện người dùng và các khối [E1], [E2]... trong LEGAL_CONTEXT. Không dùng trí nhớ để bịa điều luật, số tiền, thời hạn hoặc ngoại lệ.
2. Mỗi kết luận phải gắn evidence_ids hợp lệ. Không viết chunk_id nội bộ. Không viện dẫn Điều/Khoản/Điểm không có trong LEGAL_CONTEXT. TUYỆT ĐỐI KHÔNG dùng mã [E1], [E2] thay cho danh từ trong câu (ví dụ: cấm viết "đòi lại [E1] và [E2]", "phạt theo [E1]"). Phải viết trọn vẹn ngữ nghĩa câu tiếng Việt, ví dụ: "đòi lại số tiền lương bị khấu trừ theo Điều 102 [E1]".
3. PHƯƠNG PHÁP SUY LUẬN PHÁP LÝ (IRAC):
   - Bước 1 (Issue): Xác định vấn đề pháp lý cần giải quyết.
   - Bước 2 (Rule & Exceptions): Xác định quy phạm điều chỉnh. LUÔN phân biệt Quy tắc chung (General Rule) và Quy phạm ngoại lệ (Exceptions/Conditions). Ví dụ: quyền đơn phương có quy tắc phải báo trước (Khoản 1) nhưng có ngoại lệ không cần báo trước khi doanh nghiệp vi phạm hoặc bố trí sai việc (Khoản 2).
   - Bước 3 (Application): Đối chiếu tình tiết thực tế vào các điều kiện. Nếu tình tiết thỏa mãn quy phạm ngoại lệ, BẮT BUỘC áp dụng ngoại lệ, không áp đặt máy móc quy tắc chung.
   - Bước 4 (Conclusion): Đưa ra kết luận pháp lý dứt khoát, logic và hướng xử lý quyền lợi thực tế.
4. Với nhiều vấn đề, trả đúng một finding cho mỗi issue_id. Finding chỉ được dùng bằng chứng ghi “Nhóm căn cứ độc quyền” của chính issue_id đó.
5. Nếu cổng căn cứ đánh dấu FAIL/INCOMPLETE, ghi đúng: “Chưa đủ căn cứ trong cơ sở dữ liệu để kết luận vấn đề này.” Không suy diễn.
6. Dùng chính xác số liệu và DATE_INTERVAL do backend cung cấp. Phân biệt tiền lương, thưởng, trợ cấp và bồi thường.
7. Viết tiếng Việt rõ ràng, mạch lạc, trực diện, không emoji, không lặp ý. Với câu hỏi nhiều vấn đề, bài tư vấn (answer) dùng tiêu đề Markdown “### ...” tương ứng từng vấn đề. Không chèn từ khóa kỹ thuật như "Finding:" hoặc "issue_1" vào nội dung bài tư vấn answer. TUYỆT ĐỐI KHÔNG mở đầu bằng các câu máy móc như: "Bài tư vấn pháp lý cho câu hỏi...", "Dựa trên LEGAL_CONTEXT...", "Trong LEGAL_CONTEXT...", "Dưới đây là...". TUYỆT ĐỐI KHÔNG sử dụng từ "LEGAL_CONTEXT", "context", "prompt" trong bài viết; hãy đi thẳng vào phân tích và giải quyết vấn đề một cách tự nhiên.
8. answer phải là bài tư vấn pháp lý chuyên sâu, chi tiết và đầy đủ:
   - Nêu kết luận pháp lý dứt khoát cho câu hỏi.
   - Giải thích bản chất quy định pháp luật điều chỉnh (nghĩa vụ của người sử dụng lao động, giới hạn, quyền và ngoại lệ luật định).
   - Đối chiếu cụ thể với tình huống của người dùng để chỉ ra tính hợp pháp hoặc sai phạm thực tế.
   - Nêu rõ chế tài xử phạt hành chính và biện pháp khắc phục hậu quả (buộc trả đủ tiền lương, tiền lãi, bồi thường...).
   - Chỉ dẫn cụ thể từng bước xử lý quyền lợi thực tế cho người lao động (quyền đơn phương chấm dứt HĐLĐ không cần báo trước, quy trình khiếu nại tới cơ quan quản lý lao động, khởi kiện ra Tòa án...).
   - Không chép nguyên văn điều luật dài dòng, mà phân tích rõ ràng, dễ hiểu và có giá trị thực tiễn cao.

CHỈ TRẢ VỀ MỘT JSON HỢP LỆ, KHÔNG CÓ VĂN BẢN NGOÀI JSON.
Các khóa bắt buộc: answer (bài tư vấn Markdown hoàn chỉnh), findings (mảng kết quả theo từng issue_id), needs_clarification, clarification_question, out_of_scope. Mỗi finding gồm issue_id, issue, conclusion và evidence_ids.

Để JSON không lỗi, không dùng dấu ngoặc kép thẳng bên trong giá trị chuỗi; dùng dấu ngoặc kép tiếng Việt hoặc diễn đạt lại."""


def build_user_prompt(
    query: str,
    context_str: str,
    history_summary: str = "Không có lịch sử trước đó.",
    needs_clarification_hint: bool = False,
    clarification_reason_hint: str = "",
    decomposed_issues: Optional[List[Any]] = None,
    calculation_result: Optional[Any] = None,
    case_analysis: Optional[Any] = None,
    evidence_completeness: Optional[Any] = None,
) -> str:
    """Build a compact turn prompt containing only query-specific material."""
    parts = [
        "[LỊCH SỬ NGẮN]",
        history_summary or "Không có.",
        "",
        "[LEGAL_CONTEXT]",
        context_str,
        "",
        "[CÂU HỎI]",
        query,
    ]

    if case_analysis is not None:
        parts.extend(["", case_analysis.to_prompt_block()])

    if evidence_completeness is not None:
        parts.extend(["", evidence_completeness.to_prompt_block()])

    if decomposed_issues and len(decomposed_issues) > 1:
        parts.extend(["", "[DANH SÁCH VẤN ĐỀ BẮT BUỘC TRẢ LỜI]"])
        for index, issue in enumerate(decomposed_issues, 1):
            issue_id = getattr(issue, "issue_id", f"issue_{index}")
            issue_text = getattr(issue, "raw_issue_text", str(issue))
            parts.append(f"- {issue_id}: {issue_text}")
        parts.append(
            "Tạo đúng một finding cho mỗi issue_id theo đúng thứ tự. "
            "Trong answer, BẮT BUỘC trình bày theo cấu trúc Markdown rõ ràng với tiêu đề (### ...) tương ứng từng vấn đề, không viết dồn thành một đoạn văn duy nhất. Mỗi đề mục chỉ dùng [E...] thuộc issue_id tương ứng."
        )

        ownership: dict[str, list[str]] = {}
        for evidence_id, issue_id in re.findall(
            r"\[(E\d+)\]\s*\nNhóm căn cứ độc quyền:\s*(issue_\d+)",
            context_str,
        ):
            ownership.setdefault(issue_id, []).append(evidence_id)
        if ownership:
            parts.append("- Bản đồ căn cứ được phép dùng:")
            for issue in decomposed_issues:
                issue_id = str(getattr(issue, "issue_id", ""))
                allowed = ", ".join(ownership.get(issue_id, [])) or "không có"
                parts.append(f"  + {issue_id}: chỉ {allowed}")

    if calculation_result is not None:
        parts.extend([
            "",
            "[KẾT QUẢ TÍNH TOÁN ĐÃ KHÓA]",
            f"- Chế độ: {getattr(calculation_result, 'benefit_type', '')}",
            f"- Căn cứ: {getattr(calculation_result, 'legal_basis', '')}",
            f"- Công thức: {getattr(calculation_result, 'formula_description', '')}",
            f"- Tổng tiền: {getattr(calculation_result, 'total_amount', 0):,.0f} VNĐ",
            *[f"- {line}" for line in getattr(calculation_result, "breakdown", [])],
            "Phải dùng đúng kết quả trên, không tự tính lại.",
        ])

    issue_texts = " ".join(
        str(getattr(issue, "raw_issue_text", "")) for issue in (decomposed_issues or [])
    ).lower()
    if any(term in issue_texts for term in ["chậm trả lương", "chậm lương", "nợ lương"]):
        parts.extend([
            "",
            "[KIỂM SOÁT PHÂN TÍCH CHẬM LƯƠNG]",
            "Mốc tối đa 30 ngày không phải thời gian được tự do chậm trả. Chỉ áp dụng khi có bất khả kháng và người sử dụng lao động đã tìm mọi biện pháp khắc phục. Khó khăn tài chính đơn thuần chưa chứng minh đủ hai điều kiện này. Nếu chậm từ 15 ngày, phải phân tích khoản đền bù tiền lãi. Không được viết hai kết luận mâu thuẫn trong cùng vấn đề.",
        ])
    if any(term in issue_texts for term in ["trừ thưởng", "cắt thưởng", "không xét thưởng"]):
        parts.extend([
            "",
            "[KIỂM SOÁT PHÂN TÍCH THƯỞNG]",
            "Không đồng nhất thưởng với tiền lương. Tách quyền từ chối làm thêm khi chưa đồng ý khỏi việc hưởng thưởng. "
            "Nếu chưa có hợp đồng, thỏa ước hoặc quy chế thưởng, trong cả answer và finding đều cấm kết luận tuyệt đối rằng việc cắt/không xét thưởng là hợp pháp hoặc trái pháp luật; chỉ được nêu các nhánh điều kiện cần kiểm tra.",
        ])

    if needs_clarification_hint and clarification_reason_hint:
        parts.extend([
            "",
            "[DỮ KIỆN CÓ THỂ CẦN LÀM RÕ]",
            clarification_reason_hint,
            "Chỉ đặt needs_clarification=true nếu không thể phân tích có điều kiện từ dữ liệu hiện có.",
        ])

    parts.extend([
        "",
        "[YÊU CẦU CUỐI]",
        "- Bài tư vấn (answer) cần phân tích chi tiết, thấu đáo và khai thác tối đa dữ liệu pháp luật được cung cấp: kết luận dứt khoát, giải thích cặn kẽ căn cứ, đối chiếu tình tiết thực tế, nêu chế tài và hướng dẫn cụ thể quyền lợi/các bước người dùng nên làm. Độ dài khuyến nghị: 250–450 từ (với câu hỏi nhiều vấn đề: 150–250 từ cho mỗi vấn đề). Trình bày khoa học với các đề mục Markdown (###).",
        "- Đi thẳng vào nội dung tư vấn, KHÔNG dùng câu mở đầu rập khuôn (ví dụ: cấm viết 'Bài tư vấn pháp lý cho câu hỏi...'). KHÔNG nhắc đến từ 'LEGAL_CONTEXT' trong bài viết.",
        "- finding phải có issue_id, conclusion đủ ý (khoảng 40–90 từ) và evidence_ids.",
        "- Chỉ xuất JSON hợp lệ theo schema hệ thống.",
    ])
    return "\n".join(parts)
