# -*- coding: utf-8 -*-
"""
Tests for Vocational Training and Post-Training Work Commitment / Cost Refund
Validates compliance with congbaochinhphu.vn benchmark.
"""
import pytest
from rag.query_expander import QueryExpander
from rag.legal_issue_parser import LegalIssueParser
from rag.evidence_selector import EvidenceSelector
from rag.context_builder import ContextBuilder
from rag.issue_decomposer import IssueDecomposer


@pytest.fixture
def expander():
    return QueryExpander()


@pytest.fixture
def parser():
    return LegalIssueParser()


@pytest.fixture
def selector():
    return EvidenceSelector()


@pytest.fixture
def context_builder():
    return ContextBuilder()


@pytest.fixture
def decomposer():
    return IssueDecomposer()


def test_query_expander_training_lexicon(expander):
    q1 = "Quy định về đào tạo nâng cao trình độ, kỹ năng nghề nhằm duy trì, chuyển đổi việc làm cho người lao động"
    expanded1 = expander.expand(q1)
    assert "Điều 6 Khoản 2 Điểm c" in expanded1
    assert "Điều 60" in expanded1

    q2 = "Chưa hết cam kết làm việc sau đào tạo mà xin nghỉ việc chuyển sang công ty khác thì xử lý chi phí đào tạo thế nào"
    expanded2 = expander.expand(q2)
    assert "Điều 62" in expanded2
    assert "Điều 40 Khoản 3" in expanded2


def test_legal_issue_parser_training_qualifiers(parser):
    q1 = "Pháp luật lao động quy định như thế nào về việc đào tạo nâng cao trình độ, kỹ năng nghề nhằm duy trì, chuyển đổi nghề nghiệp, việc làm cho người lao động?"
    issue1 = parser.parse(q1)
    assert issue1.topic == "vocational_training"
    assert "employer_training_responsibility" in issue1.qualifiers

    q2 = "Trường hợp sau khi được đào tạo nâng cao tay nghề nhưng chị Luyến lại xin nghỉ và chuyển sang làm cho công ty khác khi chưa hết cam kết làm việc sau đào tạo thì sẽ xử lý như thế nào đối với chi phí công ty đã bỏ ra cử chị đi học?"
    issue2 = parser.parse(q2)
    assert issue2.topic == "vocational_training"
    assert "training_commitment_refund" in issue2.qualifiers


def test_evidence_selector_training_responsibility(parser, selector):
    q = "Trách nhiệm và nghĩa vụ của công ty về đào tạo, đào tạo lại nâng cao tay nghề cho công nhân"
    issue = parser.parse(q)

    cand_d6 = {
        "chunk_id": "VBHN_18_2026#d6-k2-c",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 6,
        "clause_number": 2,
        "point": "c",
        "article_title": "Quyền và nghĩa vụ của người sử dụng lao động",
        "content": "2. Người sử dụng lao động có các nghĩa vụ sau đây:\nc) Đào tạo, đào tạo lại, bồi dưỡng nâng cao trình độ, kỹ năng nghề nhằm duy trì, chuyển đổi nghề nghiệp, việc làm cho người lao động;",
    }
    cand_d60 = {
        "chunk_id": "VBHN_18_2026#d60-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 60,
        "clause_number": 1,
        "point": None,
        "article_title": "Trách nhiệm của người sử dụng lao động về đào tạo, bồi dưỡng, nâng cao trình độ, kỹ năng nghề",
        "content": "1. Người sử dụng lao động xây dựng kế hoạch hằng năm và dành kinh phí cho việc đào tạo, bồi dưỡng, nâng cao trình độ, kỹ năng nghề...",
    }
    cand_nd12 = {
        "chunk_id": "ND_12_2022#d14-k1",
        "doc_id": "ND_12_2022",
        "document_no": "12/2022/NĐ-CP",
        "article_number": 14,
        "clause_number": 1,
        "point": None,
        "article_title": "Vi phạm quy định về đào tạo",
        "content": "Phạt tiền từ 1.000.000 đồng đến 2.000.000 đồng đối với người sử dụng lao động có một trong các hành vi...",
    }

    res = selector.select_evidence(issue, [cand_nd12, cand_d60, cand_d6])
    assert "VBHN_18_2026#d6-k2-c" in res.selected_chunk_ids
    assert "VBHN_18_2026#d60-k1" in res.selected_chunk_ids
    assert "ND_12_2022#d14-k1" not in res.selected_chunk_ids


def test_evidence_selector_training_commitment_refund(parser, selector):
    q = "Chị Luyến xin nghỉ việc sang công ty khác khi chưa hết hạn cam kết làm việc sau đào tạo thì có phải hoàn trả chi phí đào tạo không"
    issue = parser.parse(q)

    cand_d62_k1 = {
        "chunk_id": "VBHN_18_2026#d62-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 62,
        "clause_number": 1,
        "point": None,
        "article_title": "Hợp đồng đào tạo nghề",
        "content": "1. Hai bên phải ký kết hợp đồng đào tạo nghề trong trường hợp người lao động được đào tạo nâng cao trình độ, kỹ năng nghề...",
    }
    cand_d62_k2c = {
        "chunk_id": "VBHN_18_2026#d62-k2-c",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 62,
        "clause_number": 2,
        "point": "c",
        "article_title": "Hợp đồng đào tạo nghề",
        "content": "2. Hợp đồng đào tạo nghề phải có các nội dung chủ yếu sau đây:\nc) Thời hạn cam kết phải làm việc sau khi được đào tạo;",
    }
    cand_d62_k2d = {
        "chunk_id": "VBHN_18_2026#d62-k2-d",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 62,
        "clause_number": 2,
        "point": "d",
        "article_title": "Hợp đồng đào tạo nghề",
        "content": "2. Hợp đồng đào tạo nghề phải có các nội dung chủ yếu sau đây:\nd) Chi phí đào tạo và trách nhiệm hoàn trả chi phí đào tạo;",
    }
    cand_d40_k3 = {
        "chunk_id": "VBHN_18_2026#d40-k3",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 40,
        "clause_number": 3,
        "point": None,
        "article_title": "Nghĩa vụ của người lao động khi đơn phương chấm dứt hợp đồng lao động trái pháp luật",
        "content": "3. Phải hoàn trả cho người sử dụng lao động chi phí đào tạo quy định tại Điều 62 của Bộ luật này.",
    }
    cand_d35 = {
        "chunk_id": "VBHN_18_2026#d35-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 35,
        "clause_number": 1,
        "point": None,
        "article_title": "Quyền đơn phương chấm dứt",
        "content": "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước...",
    }

    res = selector.select_evidence(issue, [cand_d35, cand_d62_k1, cand_d62_k2c, cand_d62_k2d, cand_d40_k3])
    # Must lock Điều 62 and Điều 40 Khoản 3
    assert any("d62" in cid for cid in res.selected_chunk_ids)
    assert "VBHN_18_2026#d40-k3" in res.selected_chunk_ids
    assert "VBHN_18_2026#d35-k1" not in res.selected_chunk_ids


def test_context_builder_statutory_bridges_for_training(context_builder):
    # Case 1: Issue with only d6-k2-c should get d60-k1 and d60-k2 bridged
    cand_d6 = {
        "chunk_id": "VBHN_18_2026#d6-k2-c",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 6,
        "clause_number": 2,
        "point": "c",
        "content": "c) Đào tạo, đào tạo lại, bồi dưỡng nâng cao trình độ, kỹ năng nghề",
    }
    ctx = context_builder.build_context(retrieved_chunks=[cand_d6], enforce_statutory_bridge=True)
    assert "VBHN_18_2026#d6-k2-c" in ctx.available_chunk_ids
    assert "VBHN_18_2026#d60-k1" in ctx.available_chunk_ids
    assert "VBHN_18_2026#d60-k2" in ctx.available_chunk_ids

    # Case 2: Issue with d62 should get full training contract and d40-k3 bridged
    cand_d62 = {
        "chunk_id": "VBHN_18_2026#d62-k3",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 62,
        "clause_number": 3,
        "point": None,
        "content": "Chi phí đào tạo bao gồm các khoản chi có chứng từ hợp lệ...",
    }
    ctx2 = context_builder.build_context(retrieved_chunks=[cand_d62], enforce_statutory_bridge=True)
    assert "VBHN_18_2026#d62-k1" in ctx2.available_chunk_ids
    assert "VBHN_18_2026#d62-k2-c" in ctx2.available_chunk_ids
    assert "VBHN_18_2026#d62-k2-d" in ctx2.available_chunk_ids
    assert "VBHN_18_2026#d40-k3" in ctx2.available_chunk_ids
