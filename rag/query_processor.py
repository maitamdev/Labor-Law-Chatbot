# -*- coding: utf-8 -*-
"""
VietLabor AI - Safe Query Normalization
Provides deterministic, non-destructive normalization for Vietnamese user queries.
Applies Unicode NFC normalization, collapses redundant whitespace, and cleans
trailing punctuation while preserving legal syntax (slashes, hyphens, percent signs).
Strictly NO LLM rewriting and NO hard-coded query-to-law mapping.
"""
from __future__ import annotations

import re
import unicodedata


def normalize_query(query: str) -> str:
    """Normalizes query text safely and deterministically.
    
    Operations:
    1. Unicode NFC normalization (standard Vietnamese representation).
    2. Whitespace collapse: tabs, newlines, and multiple spaces -> single space.
    3. Trimming leading/trailing whitespace and non-syntactic edge punctuation (?, !, ., ;).
    4. Preserves legal syntax: e.g. '145/2020/NĐ-CP', 'Điều 25', '150%'.
    
    Args:
        query: Raw user query string.
        
    Returns:
        Cleaned, normalized query string.
    """
    if not query or not isinstance(query, str):
        return ""

    # 1. Unicode NFC normalization
    norm = unicodedata.normalize("NFC", query)

    # 2. Collapse internal whitespace (tabs, consecutive spaces, carriage returns)
    norm = re.sub(r"[\s\u200b\u200e\u200f\ufeff]+", " ", norm).strip()

    # 3. Strip trailing conversational punctuation while preserving legal syntax
    # e.g. "Công ty quỵt lương???" -> "Công ty quỵt lương"
    # But leave "145/2020/NĐ-CP" intact.
    norm = re.sub(r"[\s?!.,;:\'\"`~]+$", "", norm)
    norm = re.sub(r"^[\s?!.,;:\'\"`~]+", "", norm)

    return norm.strip()


def normalize_colloquial_vietnamese(query: str) -> str:
    """Standardizes colloquial Vietnamese abbreviations and expressions for RAG intent parsing.
    
    Preserves meaning while standardizing slang, shortcuts, and informal jargon.
    Does NOT modify legal article numbers or official codes.
    """
    text = normalize_query(query)
    if not text:
        return ""

    # Specific phrase replacements (order matters)
    phrase_map = [
        (r"\bđuổi ngang\b", "đơn phương chấm dứt hợp đồng lao động không báo trước"),
        (r"\bcho nghỉ ngang\b", "đơn phương chấm dứt hợp đồng lao động không báo trước"),
        (r"\bnghỉ ngang\b", "nghỉ việc không báo trước"),
        (r"\b(ko|không)\s+có\s+lương\b", "không được trả tiền lương"),
        (r"\blương\s+0\s*đồng\b", "không được trả tiền lương"),
        (r"\b(ko|không)\s+có\s+đồng\s+nào\b", "không được trả tiền lương"),
        (r"\blàm\s+8\s*tiếng\b", "làm việc 8 giờ một ngày"),
        (r"\blàm\s+8h\b", "làm việc 8 giờ một ngày"),
        (r"\b8h/ngày\b", "8 giờ một ngày"),
        (r"\blàm\s+thử\s+không\s+lương\b", "làm việc không được trả lương"),
    ]
    for pattern, replacement in phrase_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Word-boundary abbreviations
    word_map = [
        (r"\bko\b", "không"),
        (r"\bk0\b", "không"),
        (r"\bkhg\b", "không"),
        (r"\bcty\b", "công ty"),
        (r"\bct\b", "công ty"),
        (r"\bnld\b", "người lao động"),
        (r"\bnlđ\b", "người lao động"),
        (r"\bnsdld\b", "người sử dụng lao động"),
        (r"\bnsdlđ\b", "người sử dụng lao động"),
        (r"\bhđlđ\b", "hợp đồng lao động"),
        (r"\bhdld\b", "hợp đồng lao động"),
        (r"\bhđ\b", "hợp đồng"),
        (r"\bhd\b", "hợp đồng"),
        (r"\br\b", "rồi"),
        (r"\brùi\b", "rồi"),
        (r"\bdc\b", "được"),
        (r"\bđc\b", "được"),
        (r"\bbhxh\b", "bảo hiểm xã hội"),
        (r"\bbhtn\b", "bảo hiểm thất nghiệp"),
        (r"\bctv\b", "cộng tác viên"),
    ]
    for pattern, replacement in word_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Clean double spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_scenario_or_legal_consultation(query: str, raw_query: str = "") -> bool:
    """Determines whether a query is a real-world scenario, case study, or legal consultation.

    Real-world scenarios / consultations contain factual narratives, named personas,
    workplace descriptions, chronological events, or multi-question consultations.
    Such queries MUST NEVER be interrupted by premature premise clarification gates;
    instead, the system must provide comprehensive consultation covering applicable legal branches.

    Returns True if the query represents a scenario/consultation, False if it is a brief ambiguous query.
    """
    if not query and not raw_query:
        return False

    raw_text = raw_query.strip() if raw_query else query.strip()
    norm = unicodedata.normalize("NFC", raw_text)
    words = norm.split()
    word_count = len(words)
    char_count = len(norm)

    # 1. Clear length criteria: Queries with >= 25 words & >= 130 chars (or >= 160 chars) are detailed factual inquiries
    if (word_count >= 25 and char_count >= 130) or char_count >= 160:
        return True

    # 2. Structural inquiry markers (e.g. "Hỏi:", "Câu hỏi:", "Vấn đề 1", "1. ... 2. ...")
    if re.search(r"(?i)\b(hỏi\s*:|câu\s*hỏi\s*:|vấn\s*đề\s*\d+|thứ\s*nhất|thứ\s*hai)", norm):
        return True

    # 3. Multi-question criteria: Multiple question marks or multiple interrogative clauses
    if norm.count("?") >= 2:
        return True

    interrogative_matches = len(re.findall(
        r"(?i)\b(như\s*thế\s*nào|như\s*nào|có\s*đúng\s*không|có\s*được\s*không|xử\s*lý\s*như\s*thế\s*nào|xử\s*lý\s*ra\s*sao|có\s*quyền|trách\s*nhiệm\s*như\s*nào|phải\s*làm\s*gì)\b",
        norm,
    ))
    if interrogative_matches >= 2:
        return True

    # 4. Named personas or demographic profiles with specific narrative names (case-sensitive)
    persona_match = re.search(r"\b(?:[Aa]nh|[Cc]hị|[Ôô]ng|[Bb]à|[Cc]ô|[Cc]hú|[Bb]ác)\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+)*)", raw_text)
    if persona_match:
        name_first_word = persona_match.group(1).split()[0].lower()
        if name_first_word not in ["cho", "em", "ơi", "nào", "gì", "chị", "tôi", "bắt", "muốn", "nghĩ"]:
            return True

    if re.search(
        r"(?i)\b(người\s+dân\s+tộc|công\s+nhân\s+(?:vận\s+hành|bốc\s+xếp|may|xây\s+dựng)|lao\s+động\s+nữ\s+(?:mang\s+thai|nuôi\s+con))\b",
        norm,
    ):
        return True

    # 5. Narrative workplace incident keywords in context (e.g. "trong quá trình làm việc", "nguy cơ sạt lở", "bị trượt ngã")
    incident_patterns = [
        r"(?i)\btrong\s+quá\s+trình\s+làm\s+việc\b",
        r"(?i)\bkhi\s+đang\s+làm\s+việc\b",
        r"(?i)\bnguy\s+cơ\s+(?:sạt\s+lở|tai\s+nạn|nguy\s+hiểm)\b",
        r"(?i)\btừ\s+chối\s+(?:tiếp\s+tục\s+)?làm\s+việc\b",
        r"(?i)\b(trượt\s+ngã|gãy\s+chân|gãy\s+tay)\b",
        r"(?i)\b(chậm\s+trả\s+lương|nợ\s+lương)\s+(?:từ\s+)?\d+",
        r"(?i)\bkhông\s+thông\s+báo\s+rõ\s+lý\s+do\b",
    ]
    for pat in incident_patterns:
        if re.search(pat, norm):
            return True

    return False


