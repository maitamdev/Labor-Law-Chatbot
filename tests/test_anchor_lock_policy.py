# -*- coding: utf-8 -*-
"""Generic anchor hard-lock gates — avoid hijacking novel questions."""
from __future__ import annotations

import json

from config.settings import PROJECT_ROOT
from rag.anchor_lock_policy import evaluate_anchor_hard_lock
from rag.qa_anchor import QuestionLawAnchorIndex


def test_exact_cantho_question_can_hard_lock_with_agreeing_retrieval():
    index = QuestionLawAnchorIndex()
    sit_path = PROJECT_ROOT / "data/processed/cantho_legal_situations.json"
    sit1 = next(s for s in json.loads(sit_path.read_text(encoding="utf-8")) if s["number"] == 1)
    q = sit1["question"]
    ranked = index.ranked_question_matches(q, top_n=2)
    assert ranked
    row, score, seq_sim = ranked[0]
    chunks = index.nominate(q, limit=4)
    locked = index.chunks_for_confident_statutory_lock(q, retrieval_candidates=chunks)
    assert seq_sim >= 0.94
    assert locked, "near-duplicate official scenario should lock when retrieval agrees"


def test_different_discipline_question_must_not_hard_lock_cantho():
    index = QuestionLawAnchorIndex()
    q = "Tôi bị công ty sa thải vì nghỉ không phép 3 ngày, có đúng luật không?"
    locked = index.chunks_for_confident_statutory_lock(q, retrieval_candidates=[])
    assert locked == []


def test_short_thoa_thuan_query_must_not_hard_lock_long_cantho_scenario():
    index = QuestionLawAnchorIndex()
    q = (
        "Chủ cửa hàng nói thỏa thuận công việc không phải hợp đồng lao động "
        "nên không trả tiền, đúng không?"
    )
    locked = index.chunks_for_confident_statutory_lock(q, retrieval_candidates=[])
    assert locked == []


def test_contrastive_spec_no_false_locks():
    spec_path = PROJECT_ROOT / "data/evaluation/anchor_lock_contrastive.json"
    cases = json.loads(spec_path.read_text(encoding="utf-8"))
    index = QuestionLawAnchorIndex()
    for case in cases:
        if not case.get("should_hard_lock"):
            assert index.chunks_for_confident_statutory_lock(case["query"]) == [], case["id"]


def test_policy_rejects_retrieval_disagreement():
    row = {
        "question": "X",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "13"}],
        "reviewed_chunk_ids": ["VBHN_18_2026#d13-k1"],
    }
    retrieval = [{"metadata": {"article_number": "35", "doc_id": "VBHN_18_2026"}}]
    long_q = " ".join(["tình huống"] * 30)
    d = evaluate_anchor_hard_lock(
        long_q,
        row,
        match_score=0.95,
        sequence_similarity=0.96,
        runner_up_score=None,
        retrieval_candidates=retrieval,
    )
    assert not d.allow_lock
    assert "retrieval_disagrees" in d.reason
