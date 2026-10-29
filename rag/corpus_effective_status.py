# -*- coding: utf-8 -*-
"""Normalize legal-document effective status from chunk metadata."""
from __future__ import annotations

import re
from typing import Any

_REPEALED_MARKERS = frozenset(
    {
        "REPEALED",
        "EXPIRED",
        "HET_HIEU_LUC",
        "HẾT_HIỆU_LỰC",
        "HET HIEU LUC",
        "Hết hiệu lực",
    }
)

_HISTORICAL_QUERY_MARKERS = (
    "hết hiệu lực",
    "het hieu luc",
    "đã bị thay thế",
    "da bi thay the",
    "trước ngày",
    "nghị định 12",
    "nd 12",
    "12/2022",
    "so sánh với",
    "lịch sử",
)


def normalized_status(meta: dict[str, Any] | None) -> str:
    if not meta:
        return ""
    raw = meta.get("status") or meta.get("document_status") or ""
    if not isinstance(raw, str):
        return str(raw).upper()
    s = raw.strip()
    if not s:
        return ""
    upper = s.upper()
    if upper in {"CURRENT", "PARTIALLY_EFFECTIVE", "REPEALED", "EXPIRED"}:
        return upper
    if any(m in s for m in ("Hết hiệu lực", "HẾT HIỆU LỰC", "het hieu luc")):
        return "REPEALED"
    if "một phần" in s.lower() or "PARTIALLY" in upper:
        return "PARTIALLY_EFFECTIVE"
    if "còn hiệu lực" in s.lower() or "hiệu lực" in s.lower():
        return "CURRENT"
    return upper


def is_repealed_chunk(meta: dict[str, Any] | None) -> bool:
    st = normalized_status(meta)
    return st in _REPEALED_MARKERS or st == "REPEALED"


def query_allows_repealed_sources(query: str) -> bool:
    q = re.sub(r"\s+", " ", (query or "").lower()).strip()
    return any(m in q for m in _HISTORICAL_QUERY_MARKERS)


def demote_repealed_candidates(
    candidates: list[dict[str, Any]],
    query: str,
    *,
    demotion_factor: float = 0.12,
) -> list[dict[str, Any]]:
    """Push REPEALED chunks down unless the user explicitly asks about superseded law."""
    if query_allows_repealed_sources(query):
        return candidates
    adjusted: list[dict[str, Any]] = []
    for item in candidates:
        meta = item.get("metadata") or {}
        if is_repealed_chunk(meta if isinstance(meta, dict) else {}):
            copy = dict(item)
            base = float(copy.get("score") or copy.get("rrf_score") or 0.0)
            copy["score"] = base * demotion_factor
            if "rrf_score" in copy:
                copy["rrf_score"] = float(copy["rrf_score"]) * demotion_factor
            adjusted.append(copy)
        else:
            adjusted.append(item)
    adjusted.sort(key=lambda x: float(x.get("score") or x.get("rrf_score") or 0.0), reverse=True)
    return adjusted
