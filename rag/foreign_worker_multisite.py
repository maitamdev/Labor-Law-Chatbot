"""Clause-grounded answer for a foreign worker assigned across provinces.

Article 4(1) of Decree 219/2025 places competence at the employer's head-office
province. Article 4(2) only permits delegation and does not establish that rule.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

MULTISITE_EVIDENCE_IDS = ("ND_219_2025#d4-k1",)


def is_multisite_filing_question(question: str) -> bool:
    text = unicodedata.normalize("NFC", question).lower()
    foreign_worker = "người nước ngoài" in text or "lao động nước ngoài" in text
    many_places = bool(re.search(r"nhiều\s+(?:tỉnh|thành phố|địa phương)", text))
    filing = any(term in text for term in ("hồ sơ", "nộp", "thẩm quyền", "cơ quan nào", "tỉnh nào"))
    notification = any(term in text for term in ("thông báo", "bao lâu", "mấy ngày", "trước bao nhiêu"))
    return foreign_worker and many_places and filing and not notification


def grounded_answer(question: str, available_chunk_ids: Iterable[str]) -> str | None:
    if not is_multisite_filing_question(question):
        return None
    if not set(MULTISITE_EVIDENCE_IDS).issubset(set(available_chunk_ids)):
        return None
    return (
        "Nếu một người lao động nước ngoài làm việc cho cùng một người sử dụng lao động "
        "tại nhiều tỉnh/thành phố, UBND cấp tỉnh nơi người sử dụng lao động đặt trụ sở "
        "chính có thẩm quyền cấp, cấp lại, gia hạn hoặc thu hồi giấy phép lao động và "
        "giấy xác nhận không thuộc diện cấp giấy phép lao động. Đây là quy tắc tại "
        "khoản 1 Điều 4 Nghị định 219/2025/NĐ-CP. Vì vậy không thể tùy ý chọn một "
        "tỉnh bất kỳ để cơ quan tỉnh đó giải quyết hồ sơ. Khi nộp, doanh nghiệp cần "
        "theo kênh tiếp nhận được công bố cho thủ tục tương ứng tại địa phương có "
        "thẩm quyền; quy định về thẩm quyền không tự nó thay thế hướng dẫn về cách nộp."
    )
