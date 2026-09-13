# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5 Unit & Integration Tests
Tests:
- Query normalization
- Query router (exact-reference routing vs hybrid routing)
- Context builder (deduplication, hierarchical grouping, metadata preservation)
- Output validator (LegalAnswer schema, hallucinated citation rejection, abstention formatting)
- Short-term conversation memory and context resolution
- Local LLM connectivity and mock chain execution
"""
from __future__ import annotations

import json
import pytest

from rag.query_processor import normalize_query
from rag.query_router import QueryRouter, RouteDecision
from rag.context_builder import ContextBuilder, FormattedContext
from rag.output_validator import LegalAnswer, OutputValidator, ValidatedResponse
from rag.chain import ConversationMemory, VietLaborRAGChain
from models.local_llm import check_ollama_health, LocalLLMManager


# ---------------------------------------------------------------------------
# 1. Query Normalization Tests
# ---------------------------------------------------------------------------
def test_normalize_query_whitespace_and_punctuation():
    raw = "   Công ty   quỵt lương của tôi???   "
    norm = normalize_query(raw)
    assert norm == "Công ty quỵt lương của tôi"


def test_normalize_query_preserves_legal_entities():
    raw = "Nghị định 145/2020/NĐ-CP Điều 25 có hiệu lực thế nào???"
    norm = normalize_query(raw)
    assert "145/2020/NĐ-CP" in norm
    assert "Điều 25" in norm
    assert not norm.endswith("?")


def test_normalize_query_unicode_nfc():
    # Decomposed form: e + acute
    decomposed = "Đi\u1ec1u 25 B\u1ed9 lu\u1eadt Lao \u0111\u1ed9ng"
    norm = normalize_query(decomposed)
    assert norm == "Điều 25 Bộ luật Lao động"


# ---------------------------------------------------------------------------
# 2. Query Router Tests
# ---------------------------------------------------------------------------
def test_query_router_exact_article():
    router = QueryRouter()
    decision = router.route("Điều 25 Bộ luật Lao động quy định gì?")
    assert decision.strategy == "exact_reference"
    assert decision.detected_article == 25
    assert "Điều 25" in decision.reason


def test_query_router_exact_clause_and_article():
    router = QueryRouter()
    decision = router.route("Khoản 1 Điều 35 quy định về thời hạn báo trước thế nào?")
    assert decision.strategy == "exact_reference"
    assert decision.detected_article == 35
    assert decision.detected_clause == 1


def test_query_router_exact_document_number():
    router = QueryRouter()
    decision = router.route("Theo 145/2020/NĐ-CP thì phụ cấp lương tính thế nào?")
    assert decision.strategy == "exact_reference"
    assert decision.detected_doc_no == "145/2020/NĐ-CP"


def test_query_router_natural_language_hybrid():
    router = QueryRouter()
    decision = router.route("Tôi bị công ty trừ lương vô cớ thì khiếu nại ở đâu?")
    assert decision.strategy == "hybrid"
    assert decision.detected_article is None
    assert "Hybrid RRF" in decision.reason


# ---------------------------------------------------------------------------
# 3. Context Builder Tests
# ---------------------------------------------------------------------------
def test_context_builder_dedup_and_hierarchy():
    builder = ContextBuilder(max_context_chars=5000)
    mock_chunks = [
        {
            "chunk_id": "VBHN_18_2026#d25_k1",
            "content": "Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày.",
            "metadata": {
                "doc_id": "VBHN_18_2026",
                "doc_title": "Bộ luật Lao động",
                "document_no": "18/VBHN-VPQH",
                "article_number": 25,
                "article_title": "Thời giờ làm việc bình thường",
                "clause_number": 1,
                "official_source": "Công báo Chính phủ",
                "source_page_start": "15",
                "source_page_end": "15",
            },
        },
        # Duplicate chunk ID
        {
            "chunk_id": "VBHN_18_2026#d25_k1",
            "content": "Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày.",
            "metadata": {
                "doc_id": "VBHN_18_2026",
                "article_number": 25,
                "clause_number": 1,
            },
        },
        # Clause 2 of same Article
        {
            "chunk_id": "VBHN_18_2026#d25_k2",
            "content": "Người sử dụng lao động có quyền quy định thời giờ làm việc theo giờ hoặc ngày hoặc tuần.",
            "metadata": {
                "doc_id": "VBHN_18_2026",
                "doc_title": "Bộ luật Lao động",
                "document_no": "18/VBHN-VPQH",
                "article_number": 25,
                "article_title": "Thời giờ làm việc bình thường",
                "clause_number": 2,
                "official_source": "Công báo Chính phủ",
                "source_page_start": "15",
                "source_page_end": "15",
            },
        },
    ]

    context = builder.build_context(mock_chunks)
    assert context.total_chunks_in_context == 2  # Deduplicated from 3 to 2
    assert context.grouped_articles_count == 1  # Both belong to Article 25
    assert "VBHN_18_2026#d25_k1" in context.available_chunk_ids
    assert "VBHN_18_2026#d25_k2" in context.available_chunk_ids
    assert "Thời giờ làm việc bình thường không quá 08 giờ" in context.prompt_context


# ---------------------------------------------------------------------------
# 4. Output Validator Tests
# ---------------------------------------------------------------------------
def test_output_validator_parses_json():
    validator = OutputValidator()
    raw_json = json.dumps({
        "answer": "Thời gian thử việc tối đa là 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ cao đẳng trở lên.",
        "cited_chunk_ids": ["VBHN_18_2026#d25_k1"],
        "needs_clarification": False,
        "clarification_question": None,
        "abstain": False,
        "abstain_reason": None,
    })
    parsed = validator.parse_llm_json(raw_json)
    assert parsed.answer.startswith("Thời gian thử việc tối đa là 60 ngày")
    assert parsed.cited_chunk_ids == ["VBHN_18_2026#d25_k1"]
    assert not parsed.abstain


def test_output_validator_rejects_hallucinated_citations():
    validator = OutputValidator()
    legal_answer = LegalAnswer(
        answer="Theo quy định tại Điều 999 Bộ luật Lao động...",
        cited_chunk_ids=["VBHN_18_2026#d25_k1", "VBHN_18_2026#d999_fake"],
        needs_clarification=False,
        abstain=False,
    )
    available_ids = {"VBHN_18_2026#d25_k1"}
    registry = {
        "VBHN_18_2026#d25_k1": {
            "chunk_id": "VBHN_18_2026#d25_k1",
            "doc_title": "Bộ luật Lao động",
            "document_no": "18/VBHN-VPQH",
            "article_number": 25,
            "clause_number": 1,
            "official_source": "Công báo Chính phủ",
            "source_page": "Trang 15",
        }
    }

    validated = validator.validate_and_format(legal_answer, available_ids, registry)
    assert validated.cited_chunk_ids == ["VBHN_18_2026#d25_k1"]
    assert "VBHN_18_2026#d999_fake" in validated.rejected_chunk_ids
    assert "Điều 25, Khoản 1" in validated.formatted_citations
    assert "Điều 999" not in validated.formatted_citations
    assert not validated.is_fully_grounded  # flagged because a hallucinated citation was rejected


def test_output_validator_handles_abstention():
    validator = OutputValidator()
    legal_answer = LegalAnswer(
        answer="Hệ thống VietLabor AI chỉ hỗ trợ pháp luật lao động, không tư vấn thủ tục ly hôn.",
        cited_chunk_ids=[],
        abstain=True,
        abstain_reason="Out of scope",
    )
    validated = validator.validate_and_format(legal_answer, set(), {})
    assert validated.abstain is True
    assert validated.abstain_reason == "Out of scope"
    assert validated.formatted_citations == ""


# ---------------------------------------------------------------------------
# 5. Conversation Memory Tests
# ---------------------------------------------------------------------------
def test_conversation_memory_sliding_window_and_context():
    memory = ConversationMemory(max_turns=2)
    memory.add_turn("Tôi ký hợp đồng 2 năm.", "Chào bạn, hợp đồng lao động xác định thời hạn 2 năm được điều chỉnh theo BLLĐ.")
    assert "contract_term" in memory.accumulated_facts
    assert memory.accumulated_facts["contract_term"] == "2 năm"

    resolved = memory.resolve_context("Vậy nghỉ việc thì phải báo trước bao nhiêu ngày?")
    assert "hợp đồng 2 năm" in resolved


# ---------------------------------------------------------------------------
# 6. Local Ollama Integration Health Test
# ---------------------------------------------------------------------------
def test_ollama_local_health():
    health = check_ollama_health()
    assert health["online"] is True, f"Ollama local daemon must be running. Error: {health.get('error')}"
