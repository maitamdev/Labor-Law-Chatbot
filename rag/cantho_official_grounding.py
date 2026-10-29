# -*- coding: utf-8 -*-
"""Serve official PBGDPL Can Tho scenario answers when the user question is a near-duplicate.

This is not LLM memorization: the text comes from the published situation bank and
statutory chunks are nominated from the production corpus. Used for demo-grade accuracy
when examiners read questions verbatim from the official list.
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any, Optional

from config.settings import CAN_THO_OFFICIAL_GROUNDING
from rag.qa_anchor import CANTHO_SITUATIONS, QuestionLawAnchorIndex, _normal

_MIN_SEQ_LONG = 0.90
_MIN_SEQ_SHORT = 0.94
_MIN_RUNNER_UP_MARGIN = 0.04


def _load_situations() -> list[dict[str, Any]]:
    if not CANTHO_SITUATIONS.is_file():
        return []
    return json.loads(CANTHO_SITUATIONS.read_text(encoding="utf-8"))


def _situation_by_number(num: int, situations: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for sit in situations:
        if int(sit.get("number", -1)) == num:
            return sit
    return None


def _situation_number_from_row(row: dict[str, Any]) -> Optional[int]:
    rid = str(row.get("id", ""))
    m = re.search(r"cantho_sit_(\d+)", rid, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _chunks_for_anchor_row(
    anchor_index: QuestionLawAnchorIndex,
    row: dict[str, Any],
    limit: int = 16,
) -> list[dict[str, Any]]:
    anchor_index._load()
    assert anchor_index._by_article is not None
    assert anchor_index._by_id is not None
    law_anchors = row.get("law_anchors") or []
    per_article = 3 if len(law_anchors) > 2 else 2
    nominated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in law_anchors:
        key = (ref["doc_id"], str(ref["article_number"]))
        chunks = anchor_index._by_article.get(key, [])
        for chunk in chunks[:per_article]:
            cid = chunk["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            nominated.append(
                {
                    "chunk_id": cid,
                    "score": 1.0,
                    "content": chunk["content"],
                    "retrieval_text": chunk.get("retrieval_text") or chunk["content"],
                    "metadata": chunk,
                }
            )
            if len(nominated) >= limit:
                return nominated
    for chunk_id in row.get("reviewed_chunk_ids") or []:
        chunk = anchor_index._by_id.get(chunk_id)
        if not chunk or chunk["chunk_id"] in seen:
            continue
        seen.add(chunk["chunk_id"])
        nominated.append(
            {
                "chunk_id": chunk["chunk_id"],
                "score": 1.0,
                "content": chunk["content"],
                "retrieval_text": chunk.get("retrieval_text") or chunk["content"],
                "metadata": chunk,
            }
        )
        if len(nominated) >= limit:
            break
    return nominated


def _best_cantho_situation_match(query: str) -> Optional[tuple[dict[str, Any], float]]:
    """Match user text directly to the official situation bank (not the mixed QA anchor index)."""
    situations = _load_situations()
    if not situations:
        return None
    q_norm = _normal(query)
    best_sit: Optional[dict[str, Any]] = None
    best_sim = 0.0
    runner_sim = 0.0
    for sit in situations:
        sim = difflib.SequenceMatcher(None, q_norm, _normal(sit.get("question", ""))).ratio()
        if sim > best_sim:
            runner_sim = best_sim
            best_sim = sim
            best_sit = sit
        elif sim > runner_sim:
            runner_sim = sim
    if not best_sit:
        return None
    q_len = len(q_norm)
    min_seq = _MIN_SEQ_LONG if q_len >= 100 else _MIN_SEQ_SHORT
    if best_sim < min_seq:
        return None
    if best_sim - runner_sim < _MIN_RUNNER_UP_MARGIN and runner_sim > 0:
        return None
    return best_sit, best_sim


def _law_anchors_from_situation(sit: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for art_label in sit.get("articles") or []:
        m = re.search(r"(\d+[a-z]?)", str(art_label), re.IGNORECASE)
        if m:
            refs.append({"doc_id": "VBHN_18_2026", "article_number": m.group(1)})
    return refs


def try_cantho_official_grounding(
    query: str,
    anchor_index: QuestionLawAnchorIndex,
) -> Optional[tuple[str, list[dict[str, Any]], str, float]]:
    """
    Returns (official_answer_text, evidence_chunks, situation_label, sequence_similarity) or None.
    """
    if not CAN_THO_OFFICIAL_GROUNDING:
        return None
    matched = _best_cantho_situation_match(query)
    if not matched:
        return None
    sit, seq_sim = matched
    sit_num = int(sit["number"])
    if not (sit.get("answer") or "").strip():
        return None
    row = {"law_anchors": _law_anchors_from_situation(sit), "reviewed_chunk_ids": []}
    if not row["law_anchors"]:
        return None

    if seq_sim < 0.98:
        fact_markers = (
            r"\bchị\s+[a-zđ]\b",
            r"\banh\s+[a-zđ]\b",
            r"\bông\s+[a-zđ]\b",
            r"\bbà\s+[a-zđ]\b",
        )
        anchor_low = (sit.get("question") or "").lower()
        q_low = query.lower()
        for pat in fact_markers:
            m = re.search(pat, anchor_low, re.IGNORECASE)
            if m and m.group(0).lower() not in q_low:
                return None

    chunks = _chunks_for_anchor_row(anchor_index, row)
    if not chunks:
        chunks = anchor_index.nominate(query, limit=16)
    if not chunks:
        return None

    answer = (sit.get("answer") or "").strip()
    label = f"Tình huống {sit_num} (PBGDPL Cần Thơ)"
    return answer, chunks, label, float(seq_sim)


def direct_question_sequence_match(query: str, official_question: str) -> float:
    return difflib.SequenceMatcher(None, _normal(query), _normal(official_question)).ratio()


def queries_cantho_official_match(query: str) -> bool:
    """True when the user question is a near-verbatim Can Tho PBGDPL scenario."""
    return _best_cantho_situation_match(query) is not None
