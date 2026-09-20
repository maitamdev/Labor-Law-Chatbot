# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G.3 Unit & Regression Tests
Evidence Precision Hardening:
1. Question Specificity Classification (10 discrete categories)
2. Chunk Rule-Type Classification (DOSSIER, DEADLINE, NUMERIC_THRESHOLD, etc.)
3. Specificity Matching (Decree vs Framework Law on specific questions)
4. Preamble Hard-Suppression (Preambles never beat substantive articles)
5. Delegating Clause Penalty ("theo quy định của Chính phủ" when specific detail asked)
6. Evidence Sufficiency Validator (SUPPORTED_AND_SUFFICIENT, SUPPORTED_BUT_INCOMPLETE, UNSUPPORTED)
"""
from __future__ import annotations

import pytest

from rag.evidence_selector import EvidenceSelector
from rag.evidence_selector import EvidenceSelector
from rag.evidence_sufficiency_validator import (
    EvidenceSufficiencyValidator,
    ValidationResult,
)
from rag.legal_issue_parser import LegalIssueParser
from rag.query_router import QueryRouter


@pytest.fixture
def parser():
    return LegalIssueParser(router=QueryRouter())


@pytest.fixture
def selector():
    return EvidenceSelector()


@pytest.fixture
def validator():
    return EvidenceSufficiencyValidator()


# ==============================================================================
# 1. Question Specificity Classifier Tests
# ==============================================================================
def test_question_specificity_dossier(parser):
    issue = parser.parse("Hồ sơ xin cấp giấy phép lao động cho người nước ngoài gồm những giấy tờ gì?")
    assert issue.question_specificity == "DOSSIER"


def test_question_specificity_deadline(parser):
    issue = parser.parse("Người sử dụng lao động phải nộp hồ sơ xin giấy phép trước bao nhiêu ngày?")
    assert issue.question_specificity == "DEADLINE"


def test_question_specificity_numeric_threshold(parser):
    issue = parser.parse("Năm 2026 lao động nữ nghỉ hưu ở độ tuổi bao nhiêu?")
    assert issue.question_specificity == "NUMERIC_THRESHOLD"


def test_question_specificity_duration(parser):
    issue = parser.parse("Thời hạn tối đa của giấy phép lao động cho người nước ngoài là bao lâu?")
    assert issue.question_specificity == "DURATION"


def test_question_specificity_exemption(parser):
    issue = parser.parse("Chủ sở hữu công ty TNHH một thành viên có được miễn giấy phép lao động không?")
    assert issue.question_specificity == "EXEMPTION"


def test_question_specificity_general_principle(parser):
    issue = parser.parse("Nguyên tắc chung về sử dụng lao động nước ngoài tại Việt Nam?")
    assert issue.question_specificity == "GENERAL_PRINCIPLE"


def test_question_specificity_procedure(parser):
    issue = parser.parse("Trình tự, thủ tục xin cấp giấy phép lao động thực hiện như thế nào?")
    assert issue.question_specificity in ("PROCEDURE", "DOSSIER")


# ==============================================================================
# 2. Chunk Rule-Type Classification Tests
# ==============================================================================
def test_chunk_rule_type_dossier(selector):
    cand = {
        "article_title": "Hồ sơ đề nghị cấp giấy phép lao động",
        "content": "Hồ sơ đề nghị cấp giấy phép lao động gồm: 1. Văn bản đề nghị... 2. Giấy chứng nhận sức khỏe...",
        "chunk_id": "ND_219_2025#d11-k1",
    }
    assert selector._classify_chunk_rule_type(cand["chunk_id"], cand["article_title"], cand["content"]) == "DOSSIER"


def test_chunk_rule_type_deadline(selector):
    cand = {
        "article_title": "Thời hạn và trình tự cấp giấy phép lao động",
        "content": "Trước ít nhất 15 ngày làm việc, người sử dụng lao động phải nộp hồ sơ...",
        "chunk_id": "ND_219_2025#d12-k1",
    }
    assert selector._classify_chunk_rule_type(cand["chunk_id"], cand["article_title"], cand["content"]) == "DEADLINE"


def test_chunk_rule_type_preamble(selector):
    cand = {
        "article_title": "Căn cứ ban hành",
        "content": "Chính phủ ban hành Nghị định quy định chi tiết...",
        "chunk_id": "ND_135_2020#preamble",
    }
    assert selector._classify_chunk_rule_type(cand["chunk_id"], cand["article_title"], cand["content"]) == "PREAMBLE"


# ==============================================================================
# 3. Specificity Matching: Procedural Decree vs General Framework Law
# ==============================================================================
def test_dossier_prefers_procedural_decree(parser, selector):
    """When asking for dossier, NĐ 219 Điều 11 must beat BLLĐ Điều 151 (general conditions)."""
    q = "Hồ sơ xin cấp giấy phép lao động gồm những giấy tờ gì?"
    issue = parser.parse(q)

    cand_framework = {
        "chunk_id": "VBHN_18_2026#d151-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 151,
        "clause_number": 1,
        "article_title": "Điều kiện lao động là công dân nước ngoài làm việc tại Việt Nam",
        "content": "Người lao động nước ngoài làm việc tại Việt Nam phải đáp ứng đủ 18 tuổi, có giấy phép lao động theo quy định của Chính phủ...",
        "score": 0.85,
    }
    cand_decree = {
        "chunk_id": "ND_219_2025#d11-k1",
        "doc_id": "ND_219_2025",
        "document_no": "219/2025/NĐ-CP",
        "article_number": 11,
        "clause_number": 1,
        "article_title": "Hồ sơ đề nghị cấp giấy phép lao động",
        "content": "Hồ sơ đề nghị cấp giấy phép lao động gồm: Văn bản đề nghị của người sử dụng lao động, Giấy chứng nhận sức khỏe...",
        "score": 0.80,  # lower initial score
    }

    res = selector.select_evidence(issue, [cand_framework, cand_decree])
    assert len(res.locked_evidence_blocks) >= 1
    assert res.locked_evidence_blocks[0].chunk_id == "ND_219_2025#d11-k1"
    assert res.locked_evidence_blocks[0].chunk_id != "VBHN_18_2026#d151-k1"


def test_deadline_prefers_procedural_decree(parser, selector):
    """When asking for deadline, NĐ 219 Điều 12 (15 days) must beat BLLĐ Điều 152."""
    q = "Phải nộp hồ sơ xin cấp giấy phép lao động trước bao nhiêu ngày?"
    issue = parser.parse(q)

    cand_framework = {
        "chunk_id": "VBHN_18_2026#d152-k1",
        "doc_id": "VBHN_18_2026",
        "document_no": "18/VBHN-VPQH",
        "article_number": 152,
        "clause_number": 1,
        "article_title": "Điều kiện tuyển dụng, sử dụng lao động nước ngoài",
        "content": "Doanh nghiệp có nhu cầu sử dụng lao động nước ngoài phải giải trình nhu cầu sử dụng...",
        "score": 0.82,
    }
    cand_decree = {
        "chunk_id": "ND_219_2025#d12-k1",
        "doc_id": "ND_219_2025",
        "document_no": "219/2025/NĐ-CP",
        "article_number": 12,
        "clause_number": 1,
        "article_title": "Thời hạn và trình tự cấp giấy phép lao động",
        "content": "Trước ít nhất 15 ngày làm việc kể từ ngày người lao động nước ngoài dự kiến bắt đầu làm việc, người sử dụng lao động phải nộp hồ sơ...",
        "score": 0.78,
    }

    res = selector.select_evidence(issue, [cand_framework, cand_decree])
    assert len(res.locked_evidence_blocks) >= 1
    assert res.locked_evidence_blocks[0].chunk_id == "ND_219_2025#d12-k1"


def test_preamble_is_hard_suppressed(parser, selector):
    """Preambles should never beat substantive articles for non-CURRENT_STATUS questions."""
    q = "Năm 2026 tuổi nghỉ hưu của nữ là bao nhiêu?"
    issue = parser.parse(q)

    cand_preamble = {
        "chunk_id": "ND_135_2020#preamble",
        "doc_id": "ND_135_2020",
        "document_no": "135/2020/NĐ-CP",
        "article_number": 0,
        "article_title": "Căn cứ ban hành Nghị định 135/2020/NĐ-CP",
        "content": "Căn cứ Bộ luật Lao động ngày 20 tháng 11 năm 2019; Theo đề nghị của Bộ trưởng Bộ Lao động - Thương binh và Xã hội...",
        "score": 0.90,
    }
    cand_schedule = {
        "chunk_id": "ND_135_2020#d4-k2",
        "doc_id": "ND_135_2020",
        "document_no": "135/2020/NĐ-CP",
        "article_number": 4,
        "clause_number": 2,
        "article_title": "Tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường",
        "content": "Kể từ năm 2021, tuổi nghỉ hưu của người lao động trong điều kiện lao động bình thường được thực hiện theo lộ trình: Năm 2026 lao động nữ là 57 tuổi...",
        "score": 0.80,
    }

    res = selector.select_evidence(issue, [cand_preamble, cand_schedule])
    assert len(res.locked_evidence_blocks) >= 1
    assert res.locked_evidence_blocks[0].chunk_id == "ND_135_2020#d4-k2"


# ==============================================================================
# 4. Evidence Sufficiency Validator Tests
# ==============================================================================
def test_evidence_sufficiency_supported_and_sufficient(validator):
    q = "Năm 2026 lao động nữ nghỉ hưu ở tuổi bao nhiêu?"
    evidences = [
        {
            "chunk_id": "ND_135_2020#d4-k2",
            "content": "Lộ trình tuổi nghỉ hưu: Năm 2026 lao động nữ nghỉ hưu khi đủ 57 tuổi.",
            "article_title": "Tuổi nghỉ hưu",
        }
    ]
    res = validator.validate(
        question=q,
        question_specificity="NUMERIC_THRESHOLD",
        locked_chunks=evidences,
        answer_text="Năm 2026 lao động nữ nghỉ hưu khi đủ 57 tuổi theo Nghị định 135/2020/NĐ-CP.",
    )
    assert res.overall_status == "SUPPORTED_AND_SUFFICIENT"
    assert res.is_legally_sufficient is True


def test_evidence_sufficiency_supported_but_incomplete(validator):
    q = "Hồ sơ xin cấp giấy phép phải nộp trước bao nhiêu ngày?"
    # Evidence is general framework law that only says "theo quy định của Chính phủ"
    evidences = [
        {
            "chunk_id": "VBHN_18_2026#d151-k1",
            "content": "Người lao động nước ngoài làm việc tại Việt Nam phải có giấy phép lao động do cơ quan nhà nước có thẩm quyền cấp theo quy định của Chính phủ.",
            "article_title": "Điều kiện lao động là công dân nước ngoài",
        }
    ]
    res = validator.validate(
        question=q,
        question_specificity="DEADLINE",
        locked_chunks=evidences,
        answer_text="Hồ sơ xin cấp giấy phép phải nộp trước ít nhất 15 ngày làm việc theo quy định.",
    )
    assert res.overall_status == "SUPPORTED_BUT_INCOMPLETE"
    assert res.is_legally_sufficient is False
    assert len(res.missing_details) >= 1


def test_evidence_sufficiency_unsupported(validator):
    q = "Thời hạn thử việc đối với người quản lý doanh nghiệp là bao lâu?"
    evidences = [
        {
            "chunk_id": "VBHN_18_2026#d112-k1",
            "content": "Người lao động được nghỉ làm việc, hưởng nguyên lương trong những ngày lễ, tết sau đây...",
            "article_title": "Nghỉ lễ, tết",
        }
    ]
    res = validator.validate(
        question=q,
        question_specificity="DURATION",
        locked_chunks=evidences,
        answer_text="Thời gian thử việc tối đa của vị trí giám đốc là 180 ngày.",
    )
    assert res.overall_status == "UNSUPPORTED"
    assert res.is_legally_sufficient is False

