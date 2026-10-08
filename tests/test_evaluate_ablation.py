# -*- coding: utf-8 -*-
"""Unit tests for the pure metric helpers of scripts/evaluate_ablation.py."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "evaluate_ablation", Path(__file__).resolve().parent.parent / "scripts" / "evaluate_ablation.py",
)
ab = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ab)


def _chunk(cid, doc=None, art=None):
    meta = {"doc_id": doc, "article_number": art} if doc else {}
    return {"chunk_id": cid, "metadata": meta}


def test_article_from_chunk_id():
    assert ab.article_from_chunk_id("VBHN_18_2026#d25-k1") == ("VBHN_18_2026", "25")
    assert ab.article_from_chunk_id("ND_12_2022#preamble") is None


def test_gold_articles_prefers_chunk_ids_and_handles_ambiguity():
    item = {"relevant_chunk_ids": ["VBHN_18_2026#d25", "VBHN_18_2026#d25-k1"], "relevant_articles": ["99"]}
    assert ab.gold_articles(item) == {("VBHN_18_2026", "25")}
    assert ab.gold_articles({"relevant_documents": ["A"], "relevant_articles": ["1", "2"]}) == {("A", "1"), ("A", "2")}
    assert ab.gold_articles({"relevant_documents": ["A", "B"], "relevant_articles": ["1"]}) == set()


def test_score_query_metrics():
    retrieved = [
        _chunk("X#d1", "X", "1"),
        _chunk("VBHN_18_2026#d25-k2", "VBHN_18_2026", "25"),
        _chunk("Y#d9"),
    ]
    gold = {("VBHN_18_2026", "25"), ("VBHN_18_2026", "26")}
    s = ab.score_query(retrieved, gold, ["VBHN_18_2026#d25", "VBHN_18_2026#d26"], ks=[1, 3])
    assert s["hit@1"] == 0.0 and s["hit@3"] == 1.0
    assert s["recall@3"] == pytest.approx(0.5)
    assert s["mrr@3"] == pytest.approx(0.5)
    assert s["chunk_recall@3"] == pytest.approx(0.5)


def test_run_ablation_skips_out_of_scope_and_renders_report():
    gold = [
        {"question_id": "Q1", "question": "thử việc", "relevant_chunk_ids": ["A#d1"], "query_type": "semantic"},
        {"question_id": "Q2", "question": "python", "relevant_chunk_ids": [], "query_type": "out_of_scope"},
    ]
    results = ab.run_ablation(gold, {"bm25": lambda q, k: [_chunk("A#d1-k1", "A", "1")]}, ks=[5])
    assert results["bm25"]["n"] == 1
    assert results["bm25"]["metrics"]["hit@5"] == 1.0
    report = ab.render_markdown(results, {"dense": "N/A - test"}, ks=[5], n_total=2)
    assert "| bm25 |" in report and "| dense | N/A" in report
