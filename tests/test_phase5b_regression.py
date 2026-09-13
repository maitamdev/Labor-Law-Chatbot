# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5B Regression Test Suite
Tests:
1. Four Probation Groups in Điều 25 Bộ luật Lao động (18/VBHN-VPQH):
   - Người quản lý doanh nghiệp (tối đa 180 ngày) -> Điều 25 Khoản 1
   - Công việc yêu cầu trình độ cao đẳng trở lên (tối đa 60 ngày) -> Điều 25 Khoản 2
   - Công việc yêu cầu trình độ trung cấp, công nhân kỹ thuật, nhân viên nghiệp vụ (tối đa 30 ngày) -> Điều 25 Khoản 3
   - Công việc khác (tối đa 6 ngày làm việc) -> Điều 25 Khoản 4
   Asserts: Gold evidence points to Điều 25 BLLĐ without hardcoding into router.
2. Notice Period Distinction:
   - User A (office staff / general, 2-year contract) -> Điều 35 BLLĐ (báo trước ít nhất 30 ngày)
   - User B (aircraft flight crew, 2-year contract) -> Điều 7 Nghị định 145/2020/NĐ-CP (báo trước ít nhất 120 ngày)
   Asserts: System does NOT cite the same statute for both scenarios.
3. Ambiguous Query Handling:
   - "Công ty bắt tôi thử việc 3 tháng có đúng không?" -> needs_clarification == True
   Asserts: System does not conclude immediately and asks for job position/qualification.
"""
from __future__ import annotations

import pytest

from rag.chain import VietLaborRAGChain
from rag.query_router import QueryRouter


@pytest.fixture(scope="module")
def rag_chain():
    return VietLaborRAGChain()


# ---------------------------------------------------------------------------
# 1. Four Probation Groups under Điều 25 BLLĐ
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query,expected_clause,expected_days_str,group_desc",
    [
        (
            "Người quản lý doanh nghiệp theo Luật Doanh nghiệp thì thời gian thử việc tối đa bao lâu?",
            1,
            "180",
            "Người quản lý doanh nghiệp",
        ),
        (
            "Công việc có chức danh nghề nghiệp cần trình độ cao đẳng trở lên thử việc tối đa bao lâu?",
            2,
            "60",
            "Trình độ cao đẳng trở lên",
        ),
        (
            "Công nhân kỹ thuật, nhân viên nghiệp vụ có trình độ trung cấp thử việc tối đa mấy ngày?",
            3,
            "30",
            "Trình độ trung cấp / công nhân kỹ thuật",
        ),
        (
            "Công việc lao động phổ thông, công việc khác thì thời gian thử việc tối đa là bao nhiêu ngày?",
            4,
            "6",
            "Công việc khác",
        ),
    ],
)
def test_probation_four_groups(rag_chain, query, expected_clause, expected_days_str, group_desc):
    rag_chain.memory.clear()
    res = rag_chain.run(query)

    # Must not be out-of-scope or ungrounded abstain
    assert not res.validated_response.abstain, f"Should not abstain on {group_desc}"

    # Answer must mention the exact statutory duration
    assert expected_days_str in res.answer, f"{group_desc} must mention {expected_days_str} ngày"

    # Statutory citation must be Điều 25 BLLĐ (18/VBHN-VPQH)
    cited_ids = res.validated_response.cited_chunk_ids
    assert len(cited_ids) > 0, f"{group_desc} must cite valid chunks"

    cited_articles = []
    for cid in cited_ids:
        meta = res.formatted_context.chunk_metadata_registry.get(cid, {})
        art = str(meta.get("article_number") or "")
        cited_articles.append(art)

    assert "25" in cited_articles, f"{group_desc} must cite Điều 25 BLLĐ, got articles: {cited_articles}"


# ---------------------------------------------------------------------------
# 2. Ambiguous Query Test: "Công ty bắt tôi thử việc 3 tháng có đúng không?"
# ---------------------------------------------------------------------------
def test_ambiguous_probation_needs_clarification(rag_chain):
    rag_chain.memory.clear()
    query = "Công ty bắt tôi thử việc 3 tháng có đúng không?"
    res = rag_chain.run(query)

    # Must ask for clarification because position/education tier is missing
    assert res.validated_response.needs_clarification is True, (
        "Query without job position must set needs_clarification=True"
    )
    assert res.validated_response.clarification_question is not None
    clarify_q = res.validated_response.clarification_question.lower()
    assert any(k in clarify_q for k in ["vị trí", "công việc", "trình độ", "chuyên môn"]), (
        "Clarification question must ask about job position or qualification"
    )


# ---------------------------------------------------------------------------
# 3. Notice Period Distinction: User A (Office) vs User B (Flight Crew)
# ---------------------------------------------------------------------------
def test_notice_period_distinction_user_a_vs_user_b(rag_chain):
    # User A: Office worker, 2-year contract -> Điều 35 BLLĐ (30 ngày)
    rag_chain.memory.clear()
    query_a = "Tôi ký hợp đồng 2 năm làm nhân viên văn phòng, muốn nghỉ thì báo trước bao lâu?"
    res_a = rag_chain.run(query_a)

    assert not res_a.validated_response.abstain
    assert "30" in res_a.answer, "General office worker with 2-year contract must be at least 30 days"

    # User A must cite Điều 35 BLLĐ (18/VBHN-VPQH), NOT Điều 7 NĐ 145
    cited_ids_a = res_a.validated_response.cited_chunk_ids
    assert any("d35" in cid for cid in cited_ids_a), f"User A must cite Điều 35, got: {cited_ids_a}"
    assert not any("ND_145_2020#d7" in cid for cid in cited_ids_a), "User A must NOT cite Điều 7 NĐ 145"

    # User B: Aircraft flight crew, 2-year contract -> Điều 7 NĐ 145 (120 ngày)
    rag_chain.memory.clear()
    query_b = "Tôi là thành viên tổ lái tàu bay, hợp đồng 2 năm, muốn đơn phương nghỉ thì báo trước bao lâu?"
    res_b = rag_chain.run(query_b)

    assert not res_b.validated_response.abstain
    assert "120" in res_b.answer, "Aircraft flight crew must be at least 120 days"

    # User B must cite Điều 7 NĐ 145
    cited_ids_b = res_b.validated_response.cited_chunk_ids
    assert any("ND_145_2020#d7" in cid for cid in cited_ids_b), (
        f"User B must cite Điều 7 NĐ 145, got: {cited_ids_b}"
    )

    # Verify both do NOT use the same legal basis
    assert set(cited_ids_a) != set(cited_ids_b), "User A and User B must not have identical citations"
