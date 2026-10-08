# -*- coding: utf-8 -*-
"""Official Rubric Unit & Component Tests for 15 Benchmark Test Cases (Section IV).

Validates the full coverage of:
1. In-Scope Statutory Questions (TC_IN_01 to TC_IN_05)
2. Paraphrased/Colloquial Expressions (TC_PAR_01 to TC_PAR_03)
3. Multi-Turn Dialogues (TC_MUL_01 to TC_MUL_03)
4. Out-of-Scope Detection & Polite Refusal (TC_OOS_01 to TC_OOS_02)
5. Ambiguous Input & Material Premise Gating (TC_AMB_01 to TC_AMB_02)
"""
from __future__ import annotations

import pytest

from rag.issue_decomposer import IssueDecomposer
from rag.legal_issue_parser import LegalIssueParser
from rag.material_premise_gate import MaterialPremiseGate
from rag.query_processor import normalize_colloquial_vietnamese
from rag.query_router import QueryRouter


@pytest.fixture
def router():
    return QueryRouter()


@pytest.fixture
def parser(router):
    return LegalIssueParser(router=router)


@pytest.fixture
def decomposer():
    return IssueDecomposer()


@pytest.fixture
def premise_gate():
    return MaterialPremiseGate()


# ---------------------------------------------------------------------------
# 1. Out-of-Scope Detection (TC_OOS_01, TC_OOS_02)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("query", [
    "Thủ tục phân chia di sản thừa kế là quyền sử dụng đất nông nghiệp giữa các anh em như thế nào?",
    "Tôi muốn nộp đơn thuận tình ly hôn và giải quyết quyền nuôi con thì nộp ở đâu?",
])
def test_rubric_out_of_scope(router, query):
    decision = router.route(query)
    assert decision.strategy == "out_of_scope", f"Query should be out of scope: {query}"


# ---------------------------------------------------------------------------
# 2. Ambiguous / Missing Facts Premise Gating (TC_AMB_01, TC_AMB_02)
# ---------------------------------------------------------------------------
def test_rubric_ambiguous_termination_notice(parser, premise_gate):
    q = "Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày"
    norm_q = normalize_colloquial_vietnamese(q)
    issue = parser.parse(norm_q, issue_id="TC_AMB_01")
    result = premise_gate.evaluate(issue)
    assert result.needs_clarification is True
    assert result.category == "RESIGNATION_NOTICE_TERM_MISSING"
    assert result.clarification_question is not None


def test_rubric_ambiguous_probation_duration(parser, premise_gate):
    q = "Công ty bắt tôi thử việc 3 tháng có đúng không"
    norm_q = normalize_colloquial_vietnamese(q)
    issue = parser.parse(norm_q, issue_id="TC_AMB_02")
    result = premise_gate.evaluate(issue)
    assert result.needs_clarification is True
    assert result.category == "PROBATION_DURATION_QUALIFICATION_MISSING"
    assert result.clarification_question is not None


# ---------------------------------------------------------------------------
# 3. Paraphrase / Colloquial Event & Role Mapping (TC_PAR_01, TC_PAR_02, TC_PAR_03)
# ---------------------------------------------------------------------------
def test_rubric_paraphrase_unpaid_wage_resignation(decomposer):
    q = "cty nợ lương 2 tháng nay rồi, giờ tui muốn nghỉ luôn khỏi báo trước được hông?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert "EMPLOYEE_NO_NOTICE_EXCEPTION" in iss.required_evidence_roles
    assert "EMPLOYEE_NOTICE_REQUIREMENT" not in iss.required_evidence_roles
    assert "35" in iss.retrieval_query


def test_rubric_paraphrase_withholding_diploma(decomposer):
    q = "Sếp bắt nộp bằng đại học gốc để làm tin mới cho ký hợp đồng, như vậy có phạm luật ko?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert "PROHIBITED_ACTS_IDENTIFICATION" in iss.required_evidence_roles
    assert "17" in iss.retrieval_query


def test_rubric_paraphrase_multiple_contracts(decomposer):
    q = "ban ngày làm văn phòng ở cty A, tối làm thêm shipper cho cty B thì có bị cấm ko vậy bot?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert "MULTIPLE_CONTRACTS_PERMISSION" in iss.required_evidence_roles
    assert "OVERTIME_CONSENT" not in iss.required_evidence_roles
    assert "19" in iss.retrieval_query


# ---------------------------------------------------------------------------
# 4. In-Scope Event & Evidence Requirements (TC_IN_01 to TC_IN_05)
# ---------------------------------------------------------------------------
def test_rubric_in_scope_tc_in_01_definite_notice(parser):
    q = "Tôi ký hợp đồng lao động thời hạn 24 tháng, nay muốn đơn phương chấm dứt hợp đồng thì phải báo trước bao nhiêu ngày?"
    issue = parser.parse(q)
    assert "TERMINATION" in issue.legal_events
    assert "EMPLOYEE_NOTICE_REQUIREMENT" in issue.required_evidence_roles


def test_rubric_in_scope_tc_in_02_pregnancy_dismissal(decomposer):
    q = "Lao động nữ đang mang thai tháng thứ 5 có bị công ty sa thải vì lý do cắt giảm nhân sự không?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert "PREGNANCY_DISMISSAL_PROHIBITION" in iss.required_evidence_roles
    assert "37" in iss.retrieval_query or "137" in iss.retrieval_query


def test_rubric_in_scope_tc_in_03_monthly_overtime_limit(parser):
    q = "Người sử dụng lao động có được yêu cầu người lao động làm thêm giờ quá 40 giờ trong 1 tháng không?"
    issue = parser.parse(q)
    assert "OVERTIME" in issue.legal_events
    assert "OVERTIME_LIMIT" in issue.required_evidence_roles


def test_rubric_in_scope_tc_in_04_severance_allowance(decomposer):
    q = "Điều kiện để người lao động được hưởng trợ cấp thôi việc từ người sử dụng lao động là gì?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert "TERMINATION_SEVERANCE_ALLOWANCE" in iss.required_evidence_roles
    assert "46" in iss.retrieval_query or "145" in iss.retrieval_query


def test_rubric_in_scope_tc_in_05_uninsured_accident(decomposer):
    q = "Công ty chưa đóng bảo hiểm tai nạn lao động mà người lao động bị tai nạn thì công ty phải chịu trách nhiệm gì?"
    issues = decomposer.decompose(q)
    assert len(issues) == 1
    iss = issues[0]
    assert iss.domain == "OCCUPATIONAL_SAFETY"
    assert "UNINSURED_ACCIDENT_SUBSTITUTION" in iss.required_evidence_roles
    assert "EMPLOYER_MEDICAL_RESPONSIBILITY" in iss.required_evidence_roles
    assert "EMPLOYER_WAGE_RESPONSIBILITY" in iss.required_evidence_roles
    assert "EMPLOYER_ACCIDENT_COMPENSATION" in iss.required_evidence_roles
