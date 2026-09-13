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

