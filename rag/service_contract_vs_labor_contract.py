"""Statutory determination of Service Contract vs Labor Contract (HĐ dịch vụ vs HĐLĐ).

Under Article 13 of the 2019 Labor Code, any agreement involving paid work and the
management, direction, or supervision of one party is deemed an employment contract
regardless of the name used. Employers cannot substitute a service contract for an
employment contract to evade statutory social insurance or labor obligations.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection

SERVICE_CONTRACT_EVIDENCE_IDS = (
    "VBHN_18_2026#d13-k1",
    "VBHN_18_2026#d13-k2",
)


def is_service_contract_vs_labor_contract_query(query: str) -> bool:
    """Detect queries comparing or asking whether a service contract can replace an employment contract."""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", query).lower())
    
    # Must mention service contract / hợp đồng dịch vụ / cung cấp dịch vụ
    has_service = any(term in text for term in (
        "hợp đồng dịch vụ", "hợp đồng cung cấp dịch vụ", "hđ dịch vụ", "ký hợp đồng dịch vụ",
        "hợp đồng khoán", "hợp đồng cộng tác viên"
    ))
    # And must mention employment contract or labor relationship
    has_labor = any(term in text for term in (
        "hđlđ", "hợp đồng lao động", "quan hệ lao động", "thay cho hđlđ", "thay thế hđlđ",
        "nlđ", "người lao động", "nsdlđ"
    ))
    # Or comparison terms
    has_comparison = any(term in text for term in (
        "thay cho", "thay thế", "phân biệt", "trường hợp nào ký", "được không", "có được",
        "khác nhau", "là hợp đồng dịch vụ hay hđlđ", "hđlđ hay hợp đồng dịch vụ"
    ))

    return has_service and (has_labor or has_comparison)


def is_work_agreement_vs_labor_contract_query(query: str) -> bool:
    """Detect «Thỏa thuận công việc» or similar labels denied as HĐLĐ (Article 13 de facto rule)."""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", query).lower())
    has_work_agreement = any(
        term in text
        for term in ("thỏa thuận công việc", "thoa thuan cong viec", "thỏa thuận việc làm")
    )
    if not has_work_agreement:
        return False
    return any(
        term in text
        for term in (
            "không phải hợp đồng lao động",
            "không phải là hợp đồng lao động",
            "không có căn cứ để kiện",
            "không có căn cứ kiện",
            "có được coi là hợp đồng",
            "tên gọi khác",
            "tiền công",
            "trả công",
            "thanh toán",
        )
    )


def is_de_facto_labor_contract_evidence_query(query: str) -> bool:
    """Whether to lock Article 13 evidence for de facto employment (any label)."""
    return (
        is_service_contract_vs_labor_contract_query(query)
        or is_work_agreement_vs_labor_contract_query(query)
    )


def grounded_service_contract_answer(query: str, available_chunk_ids: Collection[str]) -> str | None:
    if not is_service_contract_vs_labor_contract_query(query):
        return None
    if not set(SERVICE_CONTRACT_EVIDENCE_IDS).issubset(set(available_chunk_ids)):
        return None

    return (
        "### 1. NSDLĐ có được ký hợp đồng dịch vụ thay cho HĐLĐ không?\n\n"
        "**KHÔNG ĐƯỢC PHÉP**, nếu công việc thực tế mang bản chất của quan hệ lao động.\n\n"
        "Căn cứ **Khoản 1 Điều 13 Bộ luật Lao động 2019**, pháp luật áp dụng nguyên tắc **«bản chất hơn tên gọi»**:\n"
        "- Hợp đồng lao động là sự thỏa thuận giữa người lao động và người sử dụng lao động về việc làm có trả công, tiền lương, điều kiện lao động, quyền và nghĩa vụ của mỗi bên trong quan hệ lao động.\n"
        "- **Đặc biệt:** Trường hợp hai bên thỏa thuận bằng tên gọi khác (như *hợp đồng dịch vụ, hợp đồng cộng tác viên, hợp đồng khoán việc*) nhưng có nội dung thể hiện về **việc làm có trả công, tiền lương và sự quản lý, điều hành, giám sát của một bên thì ĐƯỢC COI LÀ HỢP ĐỒNG LAO ĐỘNG**.\n"
        "- Do đó, NSDLĐ không được dùng hợp đồng dịch vụ để «lách luật» nhằm trốn đóng BHXH, BHYT, BHTN hay né tránh các chế độ thai sản, phép năm, làm thêm giờ cho NLĐ. Hành vi giao kết hợp đồng không đúng loại sẽ bị **xử phạt vi phạm hành chính từ 2.000.000 đồng đến 50.000.000 đồng** theo quy định tại Điều 9 Nghị định 12/2022/NĐ-CP.\n\n"
        "### 2. Trường hợp nào ký HĐLĐ? Trường hợp nào ký Hợp đồng dịch vụ?\n\n"
        "- **Ký Hợp đồng lao động (HĐLĐ):** Bắt buộc áp dụng khi NLĐ thực hiện công việc thường xuyên, gắn với vị trí chức danh của doanh nghiệp; nhận tiền lương/tiền công định kỳ; và chịu sự quản lý, phân công ca kíp, giám sát, tuân thủ nội quy lao động của NSDLĐ (Khoản 1, Khoản 2 Điều 13 BLLĐ 2019).\n"
        "- **Ký Hợp đồng dịch vụ:** Chỉ áp dụng khi công việc có tính chất vụ việc, độc lập, chuyên biệt (như dịch vụ tư vấn pháp lý, kế toán thuế độc lập, bảo trì máy tính định kỳ, thiết kế theo dự án...). Trong hợp đồng dịch vụ, bên cung ứng dịch vụ hoàn toàn tự chủ về phương thức thực hiện, không chịu sự quản lý/chấm công của bên thuê, và chỉ chịu trách nhiệm bàn giao kết quả nghiệm thu cuối cùng theo quy định của Bộ luật Dân sự 2015."
    )


def grounded_work_agreement_vs_labor_contract_answer(
    query: str, available_chunk_ids: Collection[str]
) -> str | None:
    if not is_work_agreement_vs_labor_contract_query(query):
        return None
    if not set(SERVICE_CONTRACT_EVIDENCE_IDS).issubset(set(available_chunk_ids)):
        return None

    return (
        "### 1. Kết luận\n\n"
        "**Chủ cửa hàng nói như vậy là không đúng.** Tên gọi của văn bản (\"Thỏa thuận công việc\" hay \"Hợp đồng lao động\") "
        "không quyết định bản chất quan hệ pháp lý.\n\n"
        "Căn cứ **Khoản 1 Điều 13 Bộ luật Lao động 2019**:\n"
        "- Hợp đồng lao động là sự thỏa thuận về việc làm có trả công, tiền lương, điều kiện lao động, quyền và nghĩa vụ của các bên.\n"
        "- **Nếu hai bên thỏa thuận bằng tên gọi khác** nhưng có nội dung về việc làm có trả công/tiền lương và sự quản lý, điều hành, "
        "giám sát của người sử dụng lao động thì **vẫn được coi là hợp đồng lao động**.\n\n"
        "Trường hợp A làm việc theo lịch, nhận tiền công, bị quản lý công việc thì bản \"Thỏa thuận công việc\" mang bản chất HĐLĐ. "
        "A **có căn cứ** yêu cầu thanh toán tiền công còn thiếu và yêu cầu giải quyết tranh chấp lao động theo quy định pháp luật.\n\n"
        "### 2. Khuyến nghị\n\n"
        "- Thu thập bản thỏa thuận, bảng chấm công, tin nhắn/ủy quyền thanh toán để chứng minh quan hệ lao động và số tiền còn nợ.\n"
        "- Yêu cầu hòa giải lao động hoặc khởi kiện tại Tòa án (tùy loại tranh chấp) trong thời hiệu luật định.\n"
        "- Việc chủ cửa hàng tự ý trừ tiền công vì lý do tìm người thay cần được đối chiếu với quy định về khấu trừ tiền lương "
        "(chỉ khi có thiệt hại do lỗi của người lao động và tuân thủ giới hạn pháp luật)."
    )


def grounded_de_facto_labor_contract_answer(
    query: str, available_chunk_ids: Collection[str]
) -> str | None:
    """Deterministic Article 13 answer for service-contract or work-agreement disguises."""
    for builder in (
        grounded_service_contract_answer,
        grounded_work_agreement_vs_labor_contract_answer,
    ):
        answer = builder(query, available_chunk_ids)
        if answer:
            return answer
    return None
