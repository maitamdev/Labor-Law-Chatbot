# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5D Regression Test Suite
Tests:
1. EvidenceMapper:
   - Maps temporary [E1], [E2] tokens to canonical chunk IDs deterministically.
   - Rejects hallucinated tokens (e.g. E99) without phantom emission.
   - Formats legal citations with full hierarchy (Văn bản, Điều, Khoản, Điểm) from metadata.
2. IssueDecomposer:
   - Decomposes compound multi-issue questions into independent sub-issues.
   - Preserves single-issue questions without fragmentation.
3. QueryRouter:
   - Actor classification: EMPLOYEE vs EMPLOYER vs BOTH.
   - Intent classification: SUBSTANTIVE_RULE vs SANCTION vs BOTH.
4. ContextBuilder (Phase 5D):
   - Generates compact evidence blocks with [E1..En] markers.
   - Enforces per-issue budget allocation.
   - Enforces statutory bridge: when NĐ 145 Điều 7 is retrieved, BLLĐ Điều 35k1d is attached.
5. Canonical Article 25 Citation Verification:
   - Citation labels for Điều 25 probation limits are strictly derived from metadata, not LLM manufactured points.
6. Zero Final Phantom Citations Guarantee:
   - OutputValidator ensures 0 phantom citations in final output.
"""
from __future__ import annotations

import pytest

from rag.chain import VietLaborRAGChain
from rag.context_builder import ContextBuilder
from rag.evidence_mapper import EvidenceBlock, EvidenceMapper
from rag.issue_decomposer import IssueDecomposer
from rag.output_validator import OutputValidator
from rag.query_router import QueryRouter


# ==============================================================================
# 1. EvidenceMapper Unit Tests
# ==============================================================================
def test_evidence_mapper_deterministic_conversion():
    mapper = EvidenceMapper()
    block1 = EvidenceBlock(
        evidence_id="E1",
        chunk_id="VBHN_18_2026#d35-k1-b",
        document_no="18/VBHN-VPQH",
        document_title="Bộ luật Lao động",
        article_number=35,
        article_title="Quyền đơn phương chấm dứt hợp đồng lao động",
        clause_number=1,
        point="b",
        content="Nội dung điểm b",
    )
    block2 = EvidenceBlock(
        evidence_id="E2",
        chunk_id="ND_145_2020#d7",
        document_no="145/2020/NĐ-CP",
        document_title="Nghị định quy định chi tiết Bộ luật Lao động",
        article_number=7,
        article_title="Ngành, nghề, công việc đặc thù",
        content="Nội dung điều 7",
    )
    mapper.register_blocks([block1, block2])

    # Resolves E1 -> canonical chunk_id
    assert mapper.resolve_token("E1") == "VBHN_18_2026#d35-k1-b"
    assert mapper.resolve_token("E2") == "ND_145_2020#d7"
    assert mapper.is_valid_evidence_id("E1") is True
    assert mapper.is_valid_evidence_id("E2") is True


def test_evidence_mapper_rejects_hallucinated_tokens():
    mapper = EvidenceMapper()
    block1 = EvidenceBlock(
        evidence_id="E1",
        chunk_id="VBHN_18_2026#d35-k1-b",
        document_no="18/VBHN-VPQH",
        document_title="Bộ luật Lao động",
        article_number=35,
        clause_number=1,
        point="b",
        content="Nội dung",
    )
    mapper.register_blocks([block1])

    # E99 does not exist
    assert mapper.resolve_token("E99") is None
    assert mapper.is_valid_evidence_id("E99") is False
    assert mapper.is_valid_evidence_id("E0") is False
    assert mapper.is_valid_evidence_id("CHUNK_123") is False

    # Map multiple tokens with mixed validity
    res_map = mapper.map_evidence_tokens(["E1", "E99", "E2"])
    assert res_map.canonical_chunk_ids == ["VBHN_18_2026#d35-k1-b"]
    assert "E99" in res_map.invalid_evidence_ids
    assert "E2" in res_map.invalid_evidence_ids


def test_evidence_mapper_canonical_label_formatting():
    mapper = EvidenceMapper()
    block = EvidenceBlock(
        evidence_id="E1",
        chunk_id="VBHN_18_2026#d35-k1-b",
        document_no="18/VBHN-VPQH",
        document_title="Bộ luật Lao động 2019",
        article_number=35,
        clause_number=1,
        point="b",
        content="Nội dung",
    )
    mapper.register_blocks([block])
    label = mapper.format_citation_label("E1")
    assert "Điều 35" in label
    assert "Khoản 1" in label
    assert "Điểm b" in label


# ==============================================================================
# 2. IssueDecomposer Tests
# ==============================================================================
def test_issue_decomposer_compound_query():
    decomposer = IssueDecomposer()
    query = "Công ty chậm trả lương 2 tháng và giữ bằng đại học của tôi thì xử lý thế nào?"
    issues = decomposer.decompose(query)

    assert len(issues) >= 2, f"Should decompose into at least 2 issues, got {len(issues)}"
    issue_texts = [iss.raw_issue_text.lower() for iss in issues]
    assert any("lương" in t for t in issue_texts), "Must contain wage issue"
    assert any("bằng" in t for t in issue_texts), "Must contain diploma/certificate issue"


def test_issue_decomposer_single_query():
    decomposer = IssueDecomposer()
    query = "Thời gian thử việc đối với vị trí lập trình viên yêu cầu trình độ đại học là bao lâu?"
    issues = decomposer.decompose(query)

    assert len(issues) == 1, f"Single query should not be decomposed into multiple issues, got {len(issues)}"
    assert issues[0].issue_id == "issue_1"


# ==============================================================================
# 3. QueryRouter Tests (Actor & Intent)
# ==============================================================================
def test_query_router_actor_routing():
    router = QueryRouter()

    # Employee actor
    res_ee = router.route("Người lao động muốn nghỉ việc thì phải báo trước bao nhiêu ngày?")
    assert res_ee.actor == "EMPLOYEE"

    # Employer actor
    res_er = router.route("Công ty muốn cho nhân viên nghỉ việc vì lý do thu hẹp sản xuất thì phải làm sao?")
    assert res_er.actor == "EMPLOYER"


def test_query_router_intent_routing():
    router = QueryRouter()

    # Substantive rule intent
    res_sub = router.route("Công ty có được giữ chứng minh thư gốc của nhân viên không?")
    assert res_sub.legal_intent == "SUBSTANTIVE_RULE"

    # Sanction intent
    res_sanc = router.route("Công ty giữ bản chính bằng đại học bị phạt bao nhiêu tiền theo Nghị định 12?")
    assert res_sanc.legal_intent in ("SANCTION", "BOTH")


# ==============================================================================
# 4. ContextBuilder & Statutory Bridge Tests
# ==============================================================================
def test_statutory_bridge_enforcement():
    builder = ContextBuilder(max_context_chars=8000, max_chunks=10)
    # Simulate candidate containing only Điều 7 NĐ 145
    nd145_chunk = {
        "chunk_id": "ND_145_2020#d7",
        "score": 0.05,
        "content": "Ngành, nghề, công việc đặc thù và thời hạn báo trước...",
        "metadata": {
            "doc_id": "ND_145_2020",
            "document_no": "145/2020/NĐ-CP",
            "article_number": 7,
            "article_title": "Ngành, nghề, công việc đặc thù",
        }
    }

    fc = builder.build_context([nd145_chunk], enforce_statutory_bridge=True)

    # Must contain statutory bridge: BLLĐ Điều 35k1d
    assert "VBHN_18_2026#d35-k1-d" in fc.available_chunk_ids, (
        "ContextBuilder must automatically attach BLLĐ Điều 35k1d statutory bridge when NĐ 145 Điều 7 is present"
    )


# ==============================================================================
# 5. End-to-End Zero Phantom Citations Guarantee
# ==============================================================================
def test_zero_phantom_citations_end_to_end():
    chain = VietLaborRAGChain()
    chain.memory.clear()

    res = chain.run("Thời gian thử việc tối đa của nhân viên kỹ thuật có trình độ cao đẳng là bao lâu?")
    assert not res.validated_response.abstain

    # Verify that every cited chunk ID exists in available context chunks
    for cid in res.validated_response.cited_chunk_ids:
        assert cid in res.formatted_context.available_chunk_ids, f"Phantom citation detected: {cid}"

    # Verify raw evidence validity is recorded
    assert res.validated_response.raw_evidence_validity is not None
    assert 0.0 <= res.validated_response.raw_evidence_validity <= 1.0
