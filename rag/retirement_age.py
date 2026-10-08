"""Deterministic retirement-age arithmetic grounded in Decree 135/2020.

Only handles ordinary age and the at-most-5/10-year early-age categories in
Article 5. It does not decide pension eligibility or override other statutes.
"""
from __future__ import annotations

import re

AGE_EVIDENCE_IDS = (
    "ND_135_2020#d4-k2",
    "ND_135_2020#d5",
    "ND_135_2020#d5-k5",
    "ND_135_2020#d5-k6",
)


def request_details(query: str) -> tuple[int, str, str] | None:
    text = query.lower()
    if "nghỉ hưu" not in text or not any(word in text for word in ("tuổi thấp hơn", "tuổi nghỉ hưu thấp nhất", "nghỉ hưu sớm", "nghỉ ở tuổi thấp hơn")):
        return None
    year_match = re.search(r"\bnăm\s+(20\d{2})\b", text)
    if not year_match:
        return None
    year = int(year_match.group(1))
    if not 2021 <= year <= 2035:
        return None
    gender = "nữ" if re.search(r"\b(?:lao động nữ|người lao động nữ|phụ nữ)\b", text) else "nam" if re.search(r"\b(?:lao động nam|người lao động nam)\b", text) else ""
    if not gender:
        return None
    special_ten = any(phrase in text for phrase in ("hầm lò", "khai thác than", "81%", "81 %"))
    specific_five = any(phrase in text for phrase in ("nặng nhọc", "đặc biệt khó khăn", "61%", "61 %"))
    category = "ten" if special_ten else "five" if specific_five else "general"
    return year, gender, category


def _age_text(total_months: int) -> str:
    years, months = divmod(total_months, 12)
    return f"{years} tuổi" + (f" {months} tháng" if months else "")


def grounded_answer(query: str, available_chunk_ids: set[str]) -> str | None:
    details = request_details(query)
    if details is None or not set(AGE_EVIDENCE_IDS).issubset(available_chunk_ids):
        return None
    year, gender, category = details
    normal_months = min(62 * 12, 60 * 12 + 3 + (year - 2021) * 3) if gender == "nam" else min(60 * 12, 55 * 12 + 4 + (year - 2021) * 4)
    normal, five, ten = (_age_text(normal_months - offset) for offset in (0, 5 * 12, 10 * 12))
    lead = f"Năm {year}, tuổi nghỉ hưu trong điều kiện lao động bình thường của lao động {gender} là {normal} (khoản 2 Điều 4 Nghị định 135/2020/NĐ-CP). "
    if category == "ten":
        return lead + f"Nếu đáp ứng điều kiện khai thác than trong hầm lò từ đủ 15 năm hoặc suy giảm khả năng lao động từ 81% trở lên theo khoản 5 hoặc khoản 6 Điều 5, có thể nghỉ sớm tối đa 10 năm, tức từ {ten}. Đây là giới hạn theo Nghị định 135; còn phải kiểm tra đầy đủ điều kiện hưởng lương hưu."
    if category == "five":
        return lead + f"Nếu thuộc nhóm được nghỉ sớm tối đa 05 năm theo phần mở đầu Điều 5 và đủ điều kiện riêng của nhóm đó, mốc sớm nhất là {five}. Không áp dụng mốc này cho mọi người lao động."
    return lead + f"Điều 5 có hai mức cần phân biệt: các trường hợp thông thường được nghỉ sớm tối đa 05 năm có mốc {five} nếu đủ điều kiện; riêng người có từ đủ 15 năm khai thác than trong hầm lò hoặc suy giảm khả năng lao động từ 81% trở lên có thể nghỉ sớm tối đa 10 năm, tức {ten}. Vì câu hỏi chưa nêu thuộc nhóm nào, không thể chốt một tuổi cho cá nhân; nếu hỏi mốc thấp nhất trong các nhóm nêu tại Nghị định 135 thì là {ten}."
