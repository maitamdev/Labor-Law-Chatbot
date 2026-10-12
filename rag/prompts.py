# -*- coding: utf-8 -*-
"""Compact grounded prompts for the local Ollama model.

Legal rules belong in retrieved evidence and deterministic validators, not in a
30K-character system prompt. Keeping this module compact materially reduces
prompt-evaluation latency on consumer GPUs and avoids context truncation.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional


SYSTEM_PROMPT = """Bạn là VietLabor AI, công cụ TRA CỨU và giải thích quy định pháp luật lao động Việt Nam (không phải dịch vụ tư vấn pháp lý).

NGUYÊN TẮC BẮT BUỘC:
1. Chỉ dùng dữ kiện người dùng và các khối [E1], [E2]... trong LEGAL_CONTEXT. Không dùng trí nhớ để thêm điều luật, số tiền, thời hạn, ngoại lệ. Không viện dẫn Điều/Khoản không có trong LEGAL_CONTEXT. Không viết chunk_id nội bộ.
2. Mỗi kết luận gắn evidence_ids hợp lệ. Không dùng mã [E1] thay cho danh từ trong câu; viết trọn câu, ví dụ: "khấu trừ lương theo Điều 102 [E1]".
3. KIỂM TRA TIỀN ĐỀ: nếu câu hỏi chứa giả định hoặc hỏi xác nhận ("phải không", "đúng không", "có phải"), câu đầu tiên của mỗi vấn đề phải nêu rõ ĐÚNG, SAI hoặc CHỈ ĐÚNG MỘT PHẦN, rồi chỉ ra phần sai. Không chiều theo tiền đề của người hỏi.
4. THỨ TỰ ÁP DỤNG: (a) quy định cấm, đối tượng được bảo vệ đặc biệt và điều kiện áp dụng được xét TRƯỚC; (b) sau đó mới đến thủ tục chung (thời hạn báo trước, mức hưởng, cách tính). Nếu tình tiết thuộc ngoại lệ hoặc trường hợp cấm, phải áp dụng ngoại lệ/cấm đó.
5. Không kết luận hưởng đồng thời hai chế độ gắn với các căn cứ khác nhau. Phân biệt tiền lương, thưởng, trợ cấp, bồi thường.
6. Chỉ trả lời đúng các vấn đề người dùng hỏi; không thêm chủ đề họ không hỏi. Vấn đề nào không có căn cứ trong LEGAL_CONTEXT hoặc cổng căn cứ báo FAIL/INCOMPLETE thì ghi: "Chưa đủ căn cứ trong cơ sở dữ liệu để kết luận vấn đề này." Không suy diễn.
7. Thiếu dữ kiện quyết định thì trình bày kết luận có điều kiện ("nếu... thì..."), không tự giả định dữ kiện.
8. Dùng chính xác số liệu và kết quả tính toán backend cung cấp.
9. Nhiều vấn đề: đúng một finding cho mỗi issue_id; finding chỉ dùng căn cứ ghi “Nhóm căn cứ độc quyền” của chính issue_id đó. Không chèn chữ “Finding:” hay “issue_1” vào answer.
10. Văn phong: tiếng Việt khách quan, mạch lạc, không emoji, không câu mở đầu rập khuôn, không nhắc các từ "LEGAL_CONTEXT", "context", "prompt". Nhiều vấn đề thì mỗi vấn đề một tiêu đề "### ...". Nội dung gồm: kết luận đối chiếu, căn cứ và giải thích, đối chiếu với tình huống, hệ quả pháp lý/quy trình luật định nếu có trong căn cứ.

CHỈ TRẢ VỀ MỘT JSON HỢP LỆ, KHÔNG CÓ VĂN BẢN NGOÀI JSON.
Các khóa bắt buộc: answer (bài giải đáp tra cứu Markdown hoàn chỉnh), findings (mảng theo từng issue_id), needs_clarification, clarification_question, out_of_scope. Mỗi finding gồm issue_id, issue, conclusion và evidence_ids.
Không dùng dấu ngoặc kép thẳng bên trong giá trị chuỗi; dùng ngoặc kép tiếng Việt “ ” hoặc diễn đạt lại."""



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
    constraint_block: str = "",
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
            "Mốc tối đa 30 ngày không phải thời gian được tự do chậm trả. Chỉ áp dụng khi có bất khả kháng và người sử dụng lao động đã tìm mọi biện pháp khắc phục. Khó khăn tài chính đơn thuần chưa chứng minh đủ hai điều kiện này. Nếu chậm từ 15 ngày, phải phân tích khoản đền bù tiền lãi. Nếu người lao động hỏi về việc nghỉ: không được trả đủ hoặc đúng hạn thì người lao động có quyền nghỉ không cần báo trước (nếu căn cứ điểm b Khoản 2 Điều 35 có trong dữ liệu); ngoại lệ bất khả kháng chỉ nêu dưới dạng điều kiện. Không được viết hai kết luận mâu thuẫn trong cùng vấn đề.",
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

    if constraint_block:
        parts.extend(["", constraint_block])

    parts.extend([
        "",
        "[YÊU CẦU CUỐI]",
        "- Nếu câu hỏi có tiền đề hoặc hỏi xác nhận, mở đầu mỗi vấn đề bằng kết luận ĐÚNG / SAI / CHỈ ĐÚNG MỘT PHẦN và lý do.",
        "- Áp dụng mọi ràng buộc trong [KIỂM TRA PHÁP LÝ BẮT BUỘC] (nếu có) trước quy định chung và nêu rõ Điều/Khoản tương ứng.",
        "- Giải thích căn cứ, đối chiếu tình tiết thực tế, nêu hệ quả pháp lý/quy trình luật định chỉ khi có trong căn cứ. Độ dài 200–400 từ (nhiều vấn đề: 120–220 từ mỗi vấn đề), dùng tiêu đề ###.",
        "- finding có issue_id, conclusion 40–90 từ và evidence_ids.",
        "- Chỉ xuất JSON hợp lệ theo schema hệ thống.",
    ])
    return "\n".join(parts)
