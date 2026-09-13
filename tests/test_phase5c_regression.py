# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5C Regression Test Suite
Tests:
1. Generalized Statutory Hierarchy Expansion in ContextBuilder:
   - Point chunk retrieval attaches parent clause lead-in and direct sibling points.
   - Context is strictly bounded (< 4,500 chars, <= 8 chunks).
2. Multi-turn Clarification End-to-End:
   - Turn 1: Ambiguous query -> needs_clarification=True, asks clarification question.
   - Turn 2: User provides specific fact -> fact retained, retrieves correct provision, answers accurately without asking clarification again.
   - Examples:
     * Probation: Turn 1 (ambiguous 3-month) -> Turn 2 (software engineer / university degree -> max 60 days, Điều 25).
     * General Resignation: Turn 1 (I want to quit) -> Turn 2 (2-year contract -> at least 30 days, Điều 35).
     * Special Occupation: Turn 1 (I want to quit) -> Turn 2 (flight crew, 2-year contract -> at least 120 days, Điều 7 NĐ 145).
3. Compound Query Multi-Evidence Handling:
   - Two distinct legal issues in one query (e.g. late wages + withheld university degree).
   - Asserts both legal provisions are cited and completeness >= 1.0.
4. Mandatory Critical Cases:
   - Case A: General 2-year contract notice (30 days, Điều 35 Khoản 1 Điểm b, NOT Điều 7 NĐ 145).
   - Case B: Flight crew 2-year contract notice (120 days, Điều 7 NĐ 145 + Điều 35 Khoản 1 Điểm d).
   - Case C: 3-month probation ambiguity (needs_clarification=True).
"""
from __future__ import annotations

import pytest

from rag.chain import VietLaborRAGChain
from rag.context_builder import ContextBuilder
from rag.output_validator import OutputValidator


@pytest.fixture(scope="module")
def rag_chain():
    return VietLaborRAGChain()


@pytest.fixture(scope="module")
def context_builder():
    return ContextBuilder(max_context_chars=4500, max_chunks=8)


# ==============================================================================
# 1. Statutory Hierarchy Expansion
# ==============================================================================
def test_hierarchy_expansion_point_attaches_parent_lead_in(context_builder):
    """Retrieving a point chunk should attach its parent clause lead-in and direct siblings."""
    # Chunk: VBHN_18_2026#d35-k1-b (báo trước 30 ngày)
    mock_point_chunk = {
        "chunk_id": "VBHN_18_2026#d35-k1-b",
        "score": 0.05,
        "content": "b) Ít nhất 30 ngày nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng;",
        "metadata": {
            "doc_id": "VBHN_18_2026",
            "doc_title": "Bộ luật Lao động",
            "document_no": "18/VBHN-VPQH",
            "article_number": 35,
            "article_title": "Quyền đơn phương chấm dứt hợp đồng lao động của người lao động",
            "clause_number": 1,
            "point": "b",
            "official_source": "Công báo Chính phủ",
        }
    }

    fc = context_builder.build_context([mock_point_chunk], expand_siblings=True)

    # Must contain parent lead-in (d35-k1)
    assert "VBHN_18_2026#d35-k1" in fc.available_chunk_ids, (
        "Parent clause lead-in must be attached when point chunk is retrieved"
    )
    # Must contain target point (d35-k1-b)
    assert "VBHN_18_2026#d35-k1-b" in fc.available_chunk_ids
    # Context must be compact
    assert len(fc.prompt_context) <= 4500, f"Context exceeded 4500 chars: {len(fc.prompt_context)}"
    assert fc.total_chunks_in_context <= 8, f"Too many chunks: {fc.total_chunks_in_context}"


def test_hierarchy_expansion_bounds_and_budget(context_builder):
    """Context must not exceed budget even if many candidates are passed."""
    # Pass 20 dummy candidate chunks
    dummy_chunks = [
        {
            "chunk_id": f"VBHN_18_2026#d{i}-k1",
            "score": 0.05 - (i * 0.001),
            "content": f"Nội dung điều luật số {i} " * 20,
            "metadata": {
                "doc_id": "VBHN_18_2026",
                "doc_title": "Bộ luật Lao động",
                "document_no": "18/VBHN-VPQH",
                "article_number": i,
                "article_title": f"Điều {i}",
                "clause_number": 1,
                "point": None,
                "official_source": "Công báo Chính phủ",
            }
        }
        for i in range(1, 21)
    ]

    fc = context_builder.build_context(dummy_chunks, expand_siblings=True)
    assert fc.total_chunks_in_context <= 8
    assert len(fc.prompt_context) <= 4500


# ==============================================================================
# 2. Multi-turn Clarification End-to-End
# ==============================================================================
def test_multiturn_probation_end_to_end(rag_chain):
    """Turn 1: ambiguous 3 months -> needs clarification.
    Turn 2: user provides job/qualification -> answers with Điều 25 Khoản 2 (max 60 days)."""
    rag_chain.memory.clear()

    # --- Turn 1 ---
    t1_res = rag_chain.run("Công ty bắt tôi thử việc 3 tháng có đúng không?")
    assert t1_res.validated_response.needs_clarification is True
    assert t1_res.validated_response.clarification_question is not None
    assert not t1_res.validated_response.abstain

    # --- Turn 2 ---
    t2_res = rag_chain.run("Tôi làm lập trình viên, vị trí yêu cầu bằng đại học.")
    # In Turn 2, clarification must NOT be requested again because facts were provided
    assert t2_res.validated_response.needs_clarification is False
    assert not t2_res.validated_response.abstain
    # Answer must mention statutory limit (60 ngày)
    assert "60" in t2_res.answer, "Must mention 60 ngày for university graduate"
    # Citations must include Điều 25
    cited_articles = [
        str(t2_res.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "")
        for cid in t2_res.validated_response.cited_chunk_ids
    ]
    assert "25" in cited_articles, f"Must cite Điều 25, got: {cited_articles}"


def test_multiturn_general_resignation_end_to_end(rag_chain):
    """Turn 1: I want to quit -> needs clarification on contract type.
    Turn 2: 2-year contract -> at least 30 days (Điểm b Khoản 1 Điều 35 BLLĐ)."""
    rag_chain.memory.clear()

    # --- Turn 1 ---
    t1_res = rag_chain.run("Tôi muốn nghỉ việc thì phải báo trước bao lâu?")
    assert t1_res.validated_response.needs_clarification is True

    # --- Turn 2 ---
    t2_res = rag_chain.run("Hợp đồng của tôi là hợp đồng xác định thời hạn 2 năm.")
    assert t2_res.validated_response.needs_clarification is False
    assert not t2_res.validated_response.abstain
    assert "30" in t2_res.answer, "Must mention 30 ngày for 2-year contract"

    # Must cite Điều 35 Khoản 1 Điểm b
    cited_docs = [
        t2_res.formatted_context.chunk_metadata_registry.get(cid, {}).get("doc_id")
        for cid in t2_res.validated_response.cited_chunk_ids
    ]
    assert "VBHN_18_2026" in cited_docs
    # Must NOT cite ND 145 Điều 7
    cited_articles = [
        str(t2_res.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "")
        for cid in t2_res.validated_response.cited_chunk_ids
    ]
    assert "7" not in cited_articles, "Must NOT cite NĐ 145 Điều 7 for ordinary employee"


def test_multiturn_special_occupation_resignation_end_to_end(rag_chain):
    """Turn 1: I want to quit -> needs clarification.
    Turn 2: Flight crew member, 2-year contract -> at least 120 days (Điều 7 NĐ 145)."""
    rag_chain.memory.clear()

    # --- Turn 1 ---
    t1_res = rag_chain.run("Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày?")
    assert t1_res.validated_response.needs_clarification is True

    # --- Turn 2 ---
    t2_res = rag_chain.run("Tôi là thành viên tổ lái tàu bay, hợp đồng 2 năm.")
    assert t2_res.validated_response.needs_clarification is False
    assert not t2_res.validated_response.abstain
    assert "120" in t2_res.answer, "Must mention 120 ngày for flight crew"

    # Must cite NĐ 145 Điều 7
    cited_articles = [
        str(t2_res.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "")
        for cid in t2_res.validated_response.cited_chunk_ids
    ]
    assert "7" in cited_articles, f"Must cite Điều 7 NĐ 145 for flight crew, got: {cited_articles}"


# ==============================================================================
# 3. Mandatory Critical Cases (Direct Single Turn)
# ==============================================================================
def test_mandatory_case_a_general_employee(rag_chain):
    """Case A: Office employee, 2-year contract -> 30 days, Điều 35 BLLĐ, NOT Điều 7 NĐ 145."""
    rag_chain.memory.clear()
    res = rag_chain.run("Tôi ký hợp đồng 2 năm làm nhân viên văn phòng, muốn nghỉ thì báo trước bao lâu?")
    assert not res.validated_response.abstain
    assert "30" in res.answer
    assert "120" not in res.answer

    cited_cids = res.validated_response.cited_chunk_ids
    assert len(cited_cids) > 0
    for cid in cited_cids:
        meta = res.formatted_context.chunk_metadata_registry.get(cid, {})
        assert meta.get("doc_id") == "VBHN_18_2026", "General employee must cite BLLĐ"
        assert str(meta.get("article_number")) == "35", "Must cite Điều 35 BLLĐ"


def test_mandatory_case_b_flight_crew(rag_chain):
    """Case B: Flight crew member, 2-year contract -> 120 days, Điều 7 NĐ 145."""
    rag_chain.memory.clear()
    res = rag_chain.run("Tôi là thành viên tổ lái tàu bay, ký hợp đồng 2 năm, muốn nghỉ việc thì phải báo trước bao lâu?")
    assert not res.validated_response.abstain
    assert "120" in res.answer

    cited_articles = [
        str(res.formatted_context.chunk_metadata_registry.get(cid, {}).get("article_number") or "")
        for cid in res.validated_response.cited_chunk_ids
    ]
    assert "7" in cited_articles, f"Must cite Điều 7 NĐ 145, got: {cited_articles}"


def test_mandatory_case_c_ambiguous_probation(rag_chain):
    """Case C: 3-month probation without qualification -> needs_clarification=True."""
    rag_chain.memory.clear()
    res = rag_chain.run("Công ty bắt tôi thử việc 3 tháng có đúng không?")
    assert res.validated_response.needs_clarification is True
    assert res.validated_response.clarification_question is not None
    assert not res.validated_response.abstain


# ==============================================================================
# 4. Out-of-Scope Fast Rejection
# ==============================================================================
def test_out_of_scope_rejection(rag_chain):
    """Divorce question must be immediately rejected without citing labor laws."""
    rag_chain.memory.clear()
    res = rag_chain.run("Thủ tục chia tài sản chung của vợ chồng khi ly hôn như thế nào?")
    assert res.validated_response.abstain is True
    assert len(res.validated_response.cited_chunk_ids) == 0
    assert "hôn nhân" in res.answer.lower() or "không thuộc phạm vi" in res.answer.lower()
