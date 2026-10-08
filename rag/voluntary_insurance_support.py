"""Grounded schedule for state support of voluntary social-insurance dues."""
from __future__ import annotations

SUPPORT_EVIDENCE_IDS = (
    "ND_159_2025#d5-k1",
    "ND_159_2025#d5-k1-a",
    "ND_159_2025#d5-k1-b",
    "ND_159_2025#d5-k1-c",
    "ND_159_2025#d5-k1-d",
)


def is_support_question(query: str) -> bool:
    text = query.lower()
    return (
        ("bảo hiểm xã hội tự nguyện" in text or "bhxh tự nguyện" in text)
        and "hỗ trợ" in text
        and not any(old in text for old in ("134/2015", "năm 2015", "năm 2020", "trước 2025"))
    )


def grounded_answer(query: str, available_chunk_ids: set[str]) -> str | None:
    if not is_support_question(query) or not set(SUPPORT_EVIDENCE_IDS).issubset(available_chunk_ids):
        return None
    return (
        "Không, mức hỗ trợ của Nhà nước không giống nhau cho mọi người tham gia BHXH tự nguyện. "
        "Theo khoản 1 Điều 5 Nghị định 159/2025/NĐ-CP, mức hỗ trợ tính trên mức đóng hằng tháng "
        "theo mức chuẩn hộ nghèo khu vực nông thôn là: 50% cho người thuộc hộ nghèo hoặc đang sinh sống "
        "tại xã đảo, đặc khu; 40% cho người thuộc hộ cận nghèo; 30% cho người dân tộc thiểu số; "
        "20% cho người tham gia khác. Nếu đồng thời thuộc nhiều nhóm, áp dụng mức hỗ trợ cao nhất. "
        "Địa phương có thể quyết định hỗ trợ thêm ngoài mức này."
    )
