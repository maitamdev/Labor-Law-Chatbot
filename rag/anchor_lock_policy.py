# -*- coding: utf-8 -*-
"""When to hard-lock evidence from a question-pattern anchor (precision over recall).

Hard-locking bypasses the evidence selector. If we lock on a fuzzy match to one
official scenario, a *different* user question with overlapping words gets the
wrong statutes. This module encodes generic gates that apply to every anchor row
(Can Tho, QA bank, etc.), not per-question scripts.

Training note: do not fine-tune the generator on memorizing scenario→answer pairs.
Prefer (1) retrieval + constraint engine, (2) optional future classifier trained on
contrastive pairs (see data/evaluation/anchor_lock_contrastive.json).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Set


@dataclass(frozen=True)
class AnchorLockDecision:
    allow_lock: bool
    reason: str


def _article_set_from_chunks(chunks: Iterable[dict[str, Any]], limit: int = 12) -> Set[str]:
    arts: Set[str] = set()
    for c in chunks:
        if len(arts) >= limit:
            break
        meta = c.get("metadata") or c
        an = meta.get("article_number")
        if an is not None and str(an).strip():
            arts.add(str(an).strip().lower())
    return arts


def _row_source(row: dict[str, Any]) -> str:
    if row.get("source") == "pbgdpl.cantho.gov.vn" or str(row.get("id", "")).startswith("cantho_sit_"):
        return "cantho"
    if row.get("reviewed_chunk_ids"):
        return "reviewed_bank"
    return "law_anchor_only"


def evaluate_anchor_hard_lock(
    query: str,
    match_row: dict[str, Any],
    match_score: float,
    sequence_similarity: float,
    runner_up_score: Optional[float],
    retrieval_candidates: Optional[list[dict[str, Any]]],
    *,
    min_runner_up_margin: float = 0.05,
) -> AnchorLockDecision:
    """Decide whether a question-pattern match is safe to hard-lock."""
    anchor_arts = {
        str(a["article_number"]).strip().lower()
        for a in (match_row.get("law_anchors") or [])
        if a.get("article_number") is not None
    }
    if not anchor_arts:
        return AnchorLockDecision(False, "no_law_anchors")

    q_norm = re.sub(r"\s+", " ", (query or "").strip())
    if len(q_norm) < 100 and sequence_similarity < 0.97:
        return AnchorLockDecision(False, "short_query_no_hard_lock")

    if runner_up_score is not None and (match_score - runner_up_score) < min_runner_up_margin:
        return AnchorLockDecision(
            False,
            f"ambiguous_match margin={match_score - runner_up_score:.3f}",
        )

    source = _row_source(match_row)
    # Official long scenarios: require near-duplicate wording, not thematic overlap.
    if source == "cantho":
        if sequence_similarity < 0.94:
            return AnchorLockDecision(
                False,
                f"cantho_requires_near_duplicate seq_sim={sequence_similarity:.3f}",
            )
    elif source == "reviewed_bank":
        if sequence_similarity < 0.88:
            return AnchorLockDecision(
                False,
                f"reviewed_bank_low_sim seq_sim={sequence_similarity:.3f}",
            )
    else:
        if sequence_similarity < 0.92:
            return AnchorLockDecision(
                False,
                f"law_anchor_only_high_bar seq_sim={sequence_similarity:.3f}",
            )

    if retrieval_candidates:
        retrieved_arts = _article_set_from_chunks(retrieval_candidates)
        if retrieved_arts and not anchor_arts.intersection(retrieved_arts):
            if source == "cantho" and sequence_similarity >= 0.97:
                pass
            else:
                return AnchorLockDecision(
                    False,
                    "retrieval_disagrees_with_anchor_articles",
                )

    # Material fact drift: anchor question encodes specific actors/facts; user omitted them.
    if source == "cantho" and sequence_similarity < 0.98:
        anchor_q = (match_row.get("question") or "").lower()
        q_low = query.lower()
        fact_markers = (
            r"\bchị\s+[a-zđ]\b",
            r"\banh\s+[a-zđ]\b",
            r"\bông\s+[a-zđ]\b",
            r"\bbà\s+[a-zđ]\b",
            r"\bcông ty\s+[a-z]\b",
        )
        for pat in fact_markers:
            m = re.search(pat, anchor_q, re.IGNORECASE)
            if m and m.group(0).lower() not in q_low:
                return AnchorLockDecision(False, "missing_named_entity_from_anchor")

    return AnchorLockDecision(True, f"ok source={source} seq_sim={sequence_similarity:.3f}")
