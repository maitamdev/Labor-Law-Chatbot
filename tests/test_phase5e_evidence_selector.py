# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5E Unit & Regression Tests
Validates:
1. Sibling Point selection (e.g. Điều 107k2 Điểm a vs b vs c)
2. Sibling Clause selection (e.g. Điều 102 Khoản 1 vs Khoản 2)
3. Number/threshold discrimination (e.g. Điều 97 Khoản 1 vs Khoản 4: delay > 15 days)
4. Substantive vs sanction intent (e.g. BLLĐ Điều 17 vs NĐ 12 Điều 9)
5. Probation vs ordinary employment termination (e.g. Điều 27 vs Điều 35)
6. Hazardous vs especially hazardous category (e.g. Điều 113k1b 14 days vs Điều 113k1c 16 days)
7. Actor matching (Employer Điều 36 vs Employee Điều 35)
8. Evidence confidence margin & ambiguity handling
9. Evidence locking
10. Backend citation ownership in OutputValidator
"""
from __future__ import annotations

import pytest

from rag.evidence_selector import EvidenceSelector, ScoredEvidence
from rag.legal_issue_parser import LegalIssue, LegalIssueParser
from rag.output_validator import LegalAnswer, OutputValidator
from rag.query_router import QueryRouter


@pytest.fixture
def parser():
    return LegalIssueParser(router=QueryRouter())


@pytest.fixture
def selector():
    return EvidenceSelector()


@pytest.fixture
def validator():
    return OutputValidator()


def test_sibling_clause_selection_d102(parser, selector):
    """Test Clause 1 (substantive deduction rule) is preferred over Clause 2 (trade union discussion)."""
    q = "Công ty có được tự ý trừ lương của người lao động không?"
    issue = parser.parse(q)

    cand_k1 = {
        "chunk_id": "VBHN_18_2026#d102-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 102,
        "clause_number": 1,
        "point": None,
        "article_title": "Khấu trừ tiền lương",
        "content": "Người sử dụng lao động chỉ được khấu trừ tiền lương của người lao động để bồi thường thiệt hại do làm hư hỏng dụng cụ, thiết bị, tài sản...",
    }
    cand_k2 = {
        "chunk_id": "VBHN_18_2026#d102-k2",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 102,
        "clause_number": 2,
        "point": None,
        "article_title": "Khấu trừ tiền lương",
        "content": "Người lao động có quyền được biết lý do khấu trừ tiền lương của mình và việc khấu trừ phải thảo luận với ban chấp hành công đoàn cơ sở...",
    }

    res = selector.select_evidence(issue, [cand_k2, cand_k1])
    assert len(res.locked_evidence_blocks) >= 1
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d102-k1"
    assert res.locked_evidence_blocks[0].total_score > res.all_scored_candidates[1].total_score


def test_number_and_threshold_discrimination_d97(parser, selector):
    """Test delay > 15 days selects Clause 4 (delay compensation) over Clause 1 (general wage payment periods)."""
    q = "Người lao động bị chậm trả lương trên 15 ngày có được nhận thêm tiền lãi đền bù không?"
    issue = parser.parse(q)

    assert 15 in issue.numbers
    assert "delay_over_15_days" in issue.qualifiers

    cand_k1 = {
        "chunk_id": "VBHN_18_2026#d97-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 97,
        "clause_number": 1,
        "point": None,
        "article_title": "Kỳ hạn trả lương",
        "content": "Người lao động hưởng lương theo giờ, ngày, tuần thì được trả lương sau giờ, ngày, tuần làm việc hoặc được trả gộp do hai bên thỏa thuận...",
    }
    cand_k4 = {
        "chunk_id": "VBHN_18_2026#d97-k4",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 97,
        "clause_number": 4,
        "point": None,
        "article_title": "Kỳ hạn trả lương",
        "content": "Trường hợp vì lý do bất khả kháng mà người sử dụng lao động đã tìm mọi biện pháp khắc phục nhưng không thể trả lương đúng hạn thì không được chậm quá 30 ngày; nếu trả lương chậm từ 15 ngày trở lên thì phải đền bù cho người lao động một khoản tiền ít nhất bằng số tiền lãi...",
    }

    res = selector.select_evidence(issue, [cand_k1, cand_k4])
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d97-k4"
    assert res.locked_evidence_blocks[0].numeric_score > 0


def test_sibling_point_selection_overtime(parser, selector):
    """Test overtime in a single day favors Point b / locks daily limit points."""
    q = "Làm thêm giờ trong một ngày thì bị giới hạn tối đa bao nhiêu giờ?"
    issue = parser.parse(q)

    assert "temporal_limit_day" in issue.qualifiers

    cand_pt_a = {
        "chunk_id": "VBHN_18_2026#d107-k2-a",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 107,
        "clause_number": 2,
        "point": "a",
        "article_title": "Làm thêm giờ",
        "content": "Phải được sự đồng ý của người lao động...",
    }
    cand_pt_b = {
        "chunk_id": "VBHN_18_2026#d107-k2-b",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 107,
        "clause_number": 2,
        "point": "b",
        "article_title": "Làm thêm giờ",
        "content": "Bảo đảm số giờ làm thêm của người lao động không quá 50% số giờ làm việc bình thường trong 01 ngày; trường hợp áp dụng quy định thời giờ làm việc bình thường theo tuần thì tổng số giờ làm việc bình thường và số giờ làm thêm không quá 12 giờ trong 01 ngày; không quá 40 giờ trong 01 tháng...",
    }
    cand_pt_c = {
        "chunk_id": "VBHN_18_2026#d107-k2-c",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 107,
        "clause_number": 2,
        "point": "c",
        "article_title": "Làm thêm giờ",
        "content": "Bảo đảm số giờ làm thêm của người lao động không quá 200 giờ trong 01 năm...",
    }

    res = selector.select_evidence(issue, [cand_pt_a, cand_pt_c, cand_pt_b])
    locked_cids = res.selected_chunk_ids
    # Point b must be selected and locked
    assert "VBHN_18_2026#d107-k2-b" in locked_cids


def test_substantive_vs_sanction_deposit(parser, selector):
    """Test deposit legality query prioritizes BLLĐ Điều 17k2 over NĐ 12 sanction fines."""
    q = "Công ty bắt đặt cọc 5 triệu đồng để được nhận vào làm việc có hợp pháp không?"
    issue = parser.parse(q)

    cand_blld_17_2 = {
        "chunk_id": "VBHN_18_2026#d17-k2",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 17,
        "clause_number": 2,
        "point": None,
        "article_title": "Hành vi người sử dụng lao động không được làm khi giao kết, thực hiện hợp đồng lao động",
        "content": "Yêu cầu người lao động phải thực hiện biện pháp bảo đảm bằng tiền hoặc tài sản khác cho việc thực hiện hợp đồng lao động.",
    }
    cand_nd12_sanction = {
        "chunk_id": "ND_12_2022#d9-k2",
        "doc_id": "ND_12_2022",
        "document_no": "12/2022/NĐ-CP",
        "article_number": 9,
        "clause_number": 2,
        "point": None,
        "article_title": "Vi phạm quy định về giao kết hợp đồng lao động",
        "content": "Phạt tiền từ 20.000.000 đồng đến 25.000.000 đồng đối với người sử dụng lao động có một trong các hành vi sau đây: Yêu cầu người lao động nộp tiền hoặc tài sản khác để bảo đảm thực hiện hợp đồng lao động...",
    }

    res = selector.select_evidence(issue, [cand_nd12_sanction, cand_blld_17_2])
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d17-k2"
    assert res.locked_evidence_blocks[0].doc_id == "VBHN_18_2026"


def test_probation_vs_employment_termination(parser, selector):
    """Test probation cancellation prefers Điều 27k2 over ordinary termination Điều 35."""
    q = "Trong thời gian thử việc, tôi muốn hủy bỏ thỏa thuận thử việc thì có cần báo trước không?"
    issue = parser.parse(q)

    assert issue.topic == "probation"
    assert "probation_cancellation" in issue.qualifiers

    cand_d27 = {
        "chunk_id": "VBHN_18_2026#d27-k2",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 27,
        "clause_number": 2,
        "point": None,
        "article_title": "Hủy bỏ thỏa thuận thử việc",
        "content": "Trong thời gian thử việc, mỗi bên có quyền hủy bỏ hợp đồng thử việc hoặc thỏa thuận thử việc mà không cần báo trước và không phải bồi thường.",
    }
    cand_d35 = {
        "chunk_id": "VBHN_18_2026#d35-k1-b",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 35,
        "clause_number": 1,
        "point": "b",
        "article_title": "Quyền đơn phương chấm dứt hợp đồng lao động của người lao động",
        "content": "Ít nhất 30 ngày nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng...",
    }

    res = selector.select_evidence(issue, [cand_d35, cand_d27])
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d27-k2"
    assert res.locked_evidence_blocks[0].total_score > 10.0


def test_hazardous_vs_especially_hazardous_category(parser, selector):
    """Test 'nặng nhọc, độc hại' selects 14 days (Point b) over 'đặc biệt nặng nhọc' 16 days (Point c)."""
    q = "Người làm công việc nặng nhọc, độc hại, nguy hiểm được nghỉ bao nhiêu ngày phép hàng năm?"
    issue = parser.parse(q)

    assert "category_hazardous_normal" in issue.qualifiers
    assert "category_especially_hazardous" not in issue.qualifiers

    cand_pt_b = {
        "chunk_id": "VBHN_18_2026#d113-k1-b",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 113,
        "clause_number": 1,
        "point": "b",
        "article_title": "Nghỉ hằng năm",
        "content": "14 ngày làm việc đối với người lao động làm nghề, công việc nặng nhọc, độc hại, nguy hiểm...",
    }
    cand_pt_c = {
        "chunk_id": "VBHN_18_2026#d113-k1-c",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 113,
        "clause_number": 1,
        "point": "c",
        "article_title": "Nghỉ hằng năm",
        "content": "16 ngày làm việc đối với người lao động làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm...",
    }

    res = selector.select_evidence(issue, [cand_pt_c, cand_pt_b])
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d113-k1-b"
    assert res.locked_evidence_blocks[0].point == "b"


def test_actor_matching_employer(parser, selector):
    """Test employer unilateral termination query matches Điều 36 over Điều 35."""
    q = "Người sử dụng lao động muốn đơn phương chấm dứt hợp đồng lao động thì phải báo trước bao nhiêu ngày?"
    issue = parser.parse(q)

    assert issue.actor in ["employer", "EMPLOYER"]

    cand_d35 = {
        "chunk_id": "VBHN_18_2026#d35-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 35,
        "clause_number": 1,
        "point": None,
        "article_title": "Quyền đơn phương chấm dứt hợp đồng lao động của người lao động",
        "content": "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước...",
    }
    cand_d36 = {
        "chunk_id": "VBHN_18_2026#d36-k2",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 36,
        "clause_number": 2,
        "point": None,
        "article_title": "Quyền đơn phương chấm dứt hợp đồng lao động của người sử dụng lao động",
        "content": "Khi đơn phương chấm dứt hợp đồng lao động trong các trường hợp quy định... người sử dụng lao động phải báo trước...",
    }

    res = selector.select_evidence(issue, [cand_d35, cand_d36])
    assert res.locked_evidence_blocks[0].chunk_id == "VBHN_18_2026#d36-k2"
    assert res.locked_evidence_blocks[0].actor_score > 0


def test_evidence_confidence_margin():
    """Test that candidates from different articles with close scores trigger ambiguity margin flag."""
    selector = EvidenceSelector(min_margin_threshold=0.6)
    dummy_issue = LegalIssue(
        raw_query="câu hỏi chung",
        issue_id="I1",
        topic="other",
        actor="general",
        intent="general",
    )
    cand1 = {
        "chunk_id": "VBHN_18_2026#d1-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 1,
        "clause_number": 1,
        "point": None,
        "article_title": "Tiêu đề 1",
        "content": "Nội dung chung chung về lao động...",
    }
    cand2 = {
        "chunk_id": "VBHN_18_2026#d2-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 2,
        "clause_number": 1,
        "point": None,
        "article_title": "Tiêu đề 2",
        "content": "Nội dung chung chung về lao động...",
    }

    res = selector.select_evidence(dummy_issue, [cand1, cand2])
    assert res.is_ambiguous is True


def test_backend_citation_ownership(validator):
    """Test that locked_chunk_ids strictly dictates valid citations even if LLM emitted wrong tokens."""
    # Suppose LLM output cites E1 (wrong) and hallucinates
    llm_answer = LegalAnswer(
        answer="Theo quy định, người lao động được đền bù tiền lãi [E1].",
        evidence_ids=["E1"],  # LLM picked E1
        findings=[],
        abstain=False,
    )

    registry = {
        "VBHN_18_2026#d97-k1": {
            "chunk_id": "VBHN_18_2026#d97-k1",
            "document_no": "18/VBHN-VPQH",
            "article_number": 97,
            "clause_number": 1,
            "content": "Kỳ hạn trả lương chung...",
        },
        "VBHN_18_2026#d97-k4": {
            "chunk_id": "VBHN_18_2026#d97-k4",
            "document_no": "18/VBHN-VPQH",
            "article_number": 97,
            "clause_number": 4,
            "content": "Chậm trả từ 15 ngày trở lên phải đền bù tiền lãi...",
        },
    }

    # Backend locked chunk ID is d97-k4!
    locked_cids = ["VBHN_18_2026#d97-k4"]

    validated = validator.validate_and_format(
        legal_answer=llm_answer,
        available_chunk_ids={"VBHN_18_2026#d97-k1", "VBHN_18_2026#d97-k4"},
        chunk_registry=registry,
        locked_chunk_ids=locked_cids,
    )

    # Validated response must strictly cite the backend-locked chunk ID!
    assert validated.cited_chunk_ids == ["VBHN_18_2026#d97-k4"]
    assert "Điều 97" in validated.formatted_citations
    assert "Khoản 4" in validated.formatted_citations
    assert "Khoản 1" not in validated.formatted_citations
    assert "Khoản 1 Điều 97" not in validated.formatted_citations
