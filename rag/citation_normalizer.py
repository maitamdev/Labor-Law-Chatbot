"""
Statutory citation normalizer for Vietnamese labor law references.
Converts informal or variant citations into canonical format.
"""
import re

CANONICAL_LAW_MAP = {
    r"(?i)bộ\s*luật\s*lao\s*động(\s*(năm\s*)?2019)?": "Bộ luật Lao động 2019",
    r"(?i)bllđ(\s*2019)?": "Bộ luật Lao động 2019",
    r"(?i)nghị\s*định\s*145(/2020(/nđ-cp)?)?": "Nghị định 145/2020/NĐ-CP",
    r"(?i)nghị\s*định\s*12(/2022(/nđ-cp)?)?": "Nghị định 12/2022/NĐ-CP",
    r"(?i)nghị\s*định\s*283(/2026(/nđ-cp)?)?": "Nghị định 283/2026/NĐ-CP",
    r"(?i)thông\s*tư\s*10(/2020(/tt-blđtbxh)?)?": "Thông tư 10/2020/TT-BLĐTBXH",
    r"(?i)luật\s*an\s*toàn(\s*,?\s*vệ\s*sinh)?\s*lao\s*động(\s*2015)?": "Luật An toàn, vệ sinh lao động 2015",
    r"(?i)luật\s*bảo\s*hiểm\s*xã\s*hội(\s*2024)?": "Luật Bảo hiểm xã hội 2024",
}

def normalize_statute_name(text: str) -> str:
    """Normalize statute mentions to official legal titles."""
    normalized = text
    for pattern, canonical in CANONICAL_LAW_MAP.items():
        normalized = re.sub(pattern, canonical, normalized)
    return normalized

def extract_article_and_law(citation: str) -> dict:
    """Parse article number and statute name from citation string."""
    art_match = re.search(r"(?i)điều\s*(\d+)", citation)
    clause_match = re.search(r"(?i)khoản\s*(\d+)", citation)
    point_match = re.search(r"(?i)điểm\s*([a-zđ])", citation)
    
    article = int(art_match.group(1)) if art_match else None
    clause = int(clause_match.group(1)) if clause_match else None
    point = point_match.group(1).lower() if point_match else None
    
    return {
        "article": article,
        "clause": clause,
        "point": point,
        "normalized": normalize_statute_name(citation).strip(),
    }
