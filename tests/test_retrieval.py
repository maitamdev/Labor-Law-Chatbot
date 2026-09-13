# -*- coding: utf-8 -*-
"""
VietLabor AI - Retrieval Engine Unit Tests
Tests:
- Corpus fingerprint determinism & versioning
- Structure-aware retrieval text formatting
- BM25 legal entity preservation (Điều, Khoản, doc numbers, %, monetary figures)
- BM25 indexing, persistence, and top-k monotonicity
- Embedding dimension consistency (1024-dim BGE-M3)
- Hybrid Reciprocal Rank Fusion (RRF) logic
- Metadata preservation & roundtrip
- Gold retrieval dataset integrity & stratification
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from rag.embeddings import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_MODEL_NAME,
    LocalBGEEmbeddings,
    compute_corpus_fingerprint,
    format_retrieval_text,
)
from rag.bm25_retriever import BM25Retriever, tokenize_legal_vietnamese
from rag.hybrid_retriever import HybridRetriever
from rag.vectorstore import clean_metadata_for_chroma

CORPUS_PATH = Path("data/processed/legal_documents.jsonl")
GOLD_PATH = Path("data/evaluation/retrieval_gold.json")


class DummyBM25Retriever:
    """Mock BM25 retriever for deterministic unit testing of RRF fusion."""
    def retrieve(self, query: str, top_k: int = 5):
        return [
            {"chunk_id": "chunk_A", "score": 10.0, "content": "Doc A", "metadata": {}},
            {"chunk_id": "chunk_B", "score": 8.0, "content": "Doc B", "metadata": {}},
            {"chunk_id": "chunk_C", "score": 5.0, "content": "Doc C", "metadata": {}},
        ][:top_k]


class DummyDenseRetriever:
    """Mock Dense retriever for deterministic unit testing of RRF fusion."""
    def retrieve(self, query: str, top_k: int = 5, where=None):
        return [
            {"chunk_id": "chunk_B", "score": 0.95, "content": "Doc B", "metadata": {}},
            {"chunk_id": "chunk_A", "score": 0.85, "content": "Doc A", "metadata": {}},
            {"chunk_id": "chunk_D", "score": 0.70, "content": "Doc D", "metadata": {}},
        ][:top_k]


def test_corpus_fingerprint_deterministic():
    """Verifies SHA256 fingerprinting is deterministic and sensitive to model/config changes."""
    fp1 = compute_corpus_fingerprint(CORPUS_PATH, model_name=DEFAULT_MODEL_NAME)
    fp2 = compute_corpus_fingerprint(CORPUS_PATH, model_name=DEFAULT_MODEL_NAME)
    assert fp1 == fp2, "Fingerprint should be strictly deterministic"
    assert len(fp1) == 64, "Fingerprint must be a 64-character hexadecimal SHA256 string"

    fp_other = compute_corpus_fingerprint(CORPUS_PATH, model_name="other-model")
    assert fp1 != fp_other, "Changing embedding model must produce a different fingerprint"


def test_format_retrieval_text():
    """Verifies hierarchical legal headers format correctly and exclude raw technical metadata."""
    sample_chunk = {
        "chunk_id": "VBHN_18_2026#d25-k1",
        "doc_title": "Bộ luật Lao động",
        "chapter": "III",
        "article_number": 25,
        "article_title": "Thời gian thử việc",
        "clause_number": 1,
        "point": "a",
        "content": "Không quá 180 ngày đối với công việc của người quản lý doanh nghiệp.",
        "text_source_url": "https://congbao.chinhphu.vn/van-ban/test.htm",
        "extraction_timestamp": "2026-09-11T10:00:00Z",
    }

    formatted = format_retrieval_text(sample_chunk)

    assert "Văn bản: Bộ luật Lao động" in formatted
    assert "Chương: III" in formatted
    assert "Điều 25: Thời gian thử việc" in formatted
    assert "Khoản 1" in formatted
    assert "Điểm a" in formatted
    assert "Nội dung: Không quá 180 ngày" in formatted

    # Strict check: technical noise must NOT be present
    assert "https://" not in formatted
    assert "congbao.chinhphu.vn" not in formatted
    assert "2026-09-11" not in formatted


def test_bm25_tokenize_preserves_legal_entities():
    """Verifies tokenizer preserves document codes, Điều/Khoản, %, and monetary numbers."""
    text = (
        "Theo Điều 25 khoản 1 Nghị định số 145/2020/NĐ-CP và Nghị định 293/2025/NĐ-CP, "
        "mức lương 5.310.000 đồng, phụ cấp 150% tiền lương."
    )

    tokens = tokenize_legal_vietnamese(text, mode="segmented")

    # Document numbers preserved
    assert "145/2020/nđ-cp" in tokens
    assert "293/2025/nđ-cp" in tokens

    # Article and clause preserved with dual matching tokens
    assert "điều_25" in tokens
    assert "khoản_1" in tokens
    assert "điều" in tokens
    assert "25" in tokens

    # Monetary and percentage entities preserved
    assert "5.310.000" in tokens
    assert "150%" in tokens


def test_bm25_indexing_and_persistence():
    """Verifies BM25 index loads, retrieves valid chunks, and matches expected legal articles."""
    retriever = BM25Retriever()
    retriever.load_index()

    # Query exact document number
    res_doc = retriever.retrieve("145/2020/NĐ-CP", top_k=3)
    assert len(res_doc) > 0
    assert any("145/2020/NĐ-CP" in r["metadata"].get("document_no", "") for r in res_doc)

    # Query exact article
    res_art = retriever.retrieve("Điều 25 thời gian thử việc", top_k=3)
    assert len(res_art) > 0
    assert any(str(r["metadata"].get("article_number")) == "25" for r in res_art)


def test_bm25_top_k_monotonicity():
    """Verifies top-k retrieval returns descending scores."""
    retriever = BM25Retriever()
    results = retriever.retrieve("tiền lương thử việc", top_k=5)
    assert len(results) <= 5
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "BM25 scores must be in descending order"


def test_embedding_dimension():
    """Verifies dense embedding model produces exactly 1024-dimensional vectors."""
    embeddings = LocalBGEEmbeddings()
    assert embeddings.dimension == DEFAULT_EMBEDDING_DIM
    vec = embeddings.embed_query("Thử việc tối đa bao nhiêu ngày?")
    assert len(vec) == 1024
    assert isinstance(vec[0], float)


def test_hybrid_rrf_scoring():
    """Verifies Reciprocal Rank Fusion calculation and candidate fusion."""
    mock_bm25 = DummyBM25Retriever()
    mock_dense = DummyDenseRetriever()

    hybrid = HybridRetriever(
        bm25_retriever=mock_bm25,  # type: ignore
        dense_retriever=mock_dense,  # type: ignore
        rrf_k=60,
    )

    results = hybrid.retrieve("query test", top_k=4)

    # Chunk B is rank 2 in BM25 (1/62) and rank 1 in Dense (1/61)
    # RRF(B) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.032522
    # Chunk A is rank 1 in BM25 (1/61) and rank 2 in Dense (1/62)
    # RRF(A) = 1/61 + 1/62 = 0.032522
    # Both A and B must be in top 2 (higher than C and D which only appear in one list)
    top2_ids = {results[0]["chunk_id"], results[1]["chunk_id"]}
    assert top2_ids == {"chunk_A", "chunk_B"}

    # Results must have all provenance fields
    for r in results:
        assert "chunk_id" in r
        assert "score" in r
        assert "bm25_rank" in r
        assert "dense_rank" in r


def test_metadata_roundtrip_cleaning():
    """Verifies Chroma metadata sanitizer strips None and retains all required legal keys."""
    raw_chunk = {
        "chunk_id": "VBHN_18_2026#d25-k1",
        "doc_id": "VBHN_18_2026",
        "doc_title": "Bộ luật Lao động",
        "document_no": "18/VBHN-VPQH",
        "document_type": "Văn bản hợp nhất",
        "issuer": "Văn phòng Quốc hội",
        "part": None,
        "chapter": "III",
        "section": None,
        "article_number": 25,
        "article_title": "Thời gian thử việc",
        "clause_number": 1,
        "point": None,
        "source_file": "01_18_VBHN_VPQH_2026.pdf",
        "source_page_start": 12,
        "source_page_end": 12,
        "official_source": "https://congbao.chinhphu.vn/van-ban/18.htm",
        "signer": "Lê Quang Mạnh",
        "effective_from": "2026-02-12",
        "status": "Còn hiệu lực",
        "content": "Nội dung thử việc",
    }

    cleaned = clean_metadata_for_chroma(raw_chunk)

    for k, v in cleaned.items():
        assert isinstance(v, (str, int, float, bool)), f"Field {k} has illegal type {type(v)}"
        assert v is not None

    assert cleaned["chunk_id"] == "VBHN_18_2026#d25-k1"
    assert cleaned["article_number"] == "25"
    assert cleaned["clause_number"] == "1"
    assert cleaned["point"] == ""  # None cleanly converted to empty string
    assert cleaned["source_page_start"] == 12


def test_gold_dataset_integrity():
    """Verifies gold evaluation dataset meets or exceeds all Phase 4 specifications."""
    assert GOLD_PATH.exists(), f"Gold dataset missing at {GOLD_PATH}"
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold = json.load(f)

    # Must have at least 100 questions (actually 155)
    assert len(gold) >= 100, f"Expected at least 100 gold questions, found {len(gold)}"

    valid_topics = {
        "probation", "contract", "termination", "wage", "overtime",
        "working_hours", "leave", "discipline", "penalties", "safety", "out_of_scope"
    }
    valid_query_types = {
        "semantic", "exact_reference", "paraphrase", "short", "long",
        "colloquial", "numeric", "cross_reference", "ambiguous", "out_of_scope"
    }

    seen_ids = set()
    topic_counts = {}
    type_counts = {}

    for q in gold:
        qid = q["question_id"]
        assert qid not in seen_ids, f"Duplicate question_id: {qid}"
        seen_ids.add(qid)

        assert q["question"].strip(), f"Empty question text in {qid}"
        topic = q["topic"]
        assert topic in valid_topics, f"Invalid topic '{topic}' in {qid}"
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

        qt = q["query_type"]
        assert qt in valid_query_types, f"Invalid query_type '{qt}' in {qid}"
        type_counts[qt] = type_counts.get(qt, 0) + 1

        if topic != "out_of_scope":
            assert len(q["relevant_articles"]) > 0, f"In-scope query {qid} must have relevant_articles"

    # Verify coverage across major topics
    assert topic_counts.get("probation", 0) >= 10
    assert topic_counts.get("contract", 0) >= 15
    assert topic_counts.get("termination", 0) >= 15
    assert topic_counts.get("wage", 0) >= 15
    assert topic_counts.get("overtime", 0) >= 10
    assert topic_counts.get("leave", 0) >= 10
    assert topic_counts.get("discipline", 0) >= 10
    assert topic_counts.get("out_of_scope", 0) >= 5
