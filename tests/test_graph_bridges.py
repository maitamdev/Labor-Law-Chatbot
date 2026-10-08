# -*- coding: utf-8 -*-
"""Graph statutory bridges must reference real, non-repealed articles of the corpus."""
from __future__ import annotations

import json
from collections import defaultdict

from config.settings import PRODUCTION_CORPUS_PATH
from graph.schema import DEFAULT_STATUTORY_BRIDGES, LegalRelationType


def _corpus_index():
    articles = defaultdict(set)
    status = {}
    for line in PRODUCTION_CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        doc_id = row.get("doc_id")
        status.setdefault(doc_id, str(row.get("status") or "").upper())
        try:
            articles[doc_id].add(int(str(row.get("article_number") or "").strip()))
        except ValueError:
            continue
    return articles, status


def test_bridges_reference_existing_articles():
    articles, _ = _corpus_index()
    for bridge in DEFAULT_STATUTORY_BRIDGES:
        for side in ("source", "target"):
            doc_id = bridge[f"{side}_doc_id"]
            art = bridge[f"{side}_article"]
            assert art in articles.get(doc_id, set()), f"{doc_id} Điều {art} not in corpus ({bridge['description']})"


def test_bridges_never_use_repealed_documents():
    _, status = _corpus_index()
    for bridge in DEFAULT_STATUTORY_BRIDGES:
        for side in ("source", "target"):
            assert status.get(bridge[f"{side}_doc_id"]) != "REPEALED", bridge["description"]


def test_bridge_relation_types_are_known():
    allowed = {LegalRelationType.GUIDES, LegalRelationType.PENALIZES}
    assert all(b["rel_type"] in allowed for b in DEFAULT_STATUTORY_BRIDGES)


def test_graph_expansion_skips_repealed_chunks():
    from rag.hybrid_graph_retriever import HybridGraphRetriever

    class _Graph:
        def is_available(self):
            return True

        def expand_related_chunks(self, seeds, limit=40):
            return [
                {"chunk_id": "OLD#d1", "doc_id": "OLD", "article_number": 1,
                 "seed_doc_id": "VBHN_18_2026", "seed_article": 97, "relation": "PENALIZES"},
                {"chunk_id": "NEW#d2", "doc_id": "NEW", "article_number": 2,
                 "seed_doc_id": "VBHN_18_2026", "seed_article": 97, "relation": "PENALIZES"},
            ]

    class _BM25:
        def get_chunk(self, cid, score=0.0):
            status = "REPEALED" if cid.startswith("OLD") else "CURRENT"
            return {"chunk_id": cid, "score": score, "content": cid, "metadata": {"status": status}}

    retriever = object.__new__(HybridGraphRetriever)
    retriever.graph_retriever = _Graph()
    retriever.bm25_retriever = _BM25()
    retriever.max_graph_chunks = 6
    retriever.max_chunks_per_related_article = 3
    retriever.graph_weight = 1.15
    retriever.use_reranker = False
    retriever.reranker = None
    base = [{"chunk_id": "VBHN_18_2026#d97", "score": 1.0,
             "metadata": {"doc_id": "VBHN_18_2026", "article_number": "97"}}]

    import rag.hybrid_retriever as hr
    original = hr.HybridRetriever.retrieve
    hr.HybridRetriever.retrieve = lambda self, **kw: [dict(c) for c in base]
    try:
        out = retriever.retrieve("chậm trả lương bị phạt thế nào", top_k=5)
    finally:
        hr.HybridRetriever.retrieve = original
    ids = [c["chunk_id"] for c in out]
    assert "NEW#d2" in ids and "OLD#d1" not in ids
