# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H.3 Test Suite
tests/test_phase5h3_legal_event_grounding.py

Validates:
1. RW_TNLD_01 regression failure resolution (Unpaid insurance + Workplace accident)
2. Backend-Owned Citations & CitationSanitizer (phantom citations = 0)
3. Legal Event Model & Multi-Issue Decomposition
4. Required Evidence Roles & Evidence Sufficiency per Issue
5. Semantic Incompatibility Penalties (Accident vs Sickness)
6. 30 Real-World Adversarial Queries (Paraphrases, Colloquial, Negative Tests)
"""
import pytest
from typing import Dict, Any, List

from rag.legal_issue_parser import (
    LegalIssueParser,
    LegalIssue,
    detect_legal_events,
    determine_required_evidence_roles,
)
from rag.issue_decomposer import IssueDecomposer
from rag.evidence_selector import EvidenceSelector, ScoredEvidence
from rag.evidence_mapper import EvidenceMapper, EvidenceBlock, CitationSanitizer, PhantomCitation
from rag.evidence_sufficiency_validator import EvidenceSufficiencyValidator
from rag.output_validator import OutputValidator, ValidatedResponse, LegalAnswer


@pytest.fixture
def parser():
    return LegalIssueParser()


@pytest.fixture
def decomposer():
    return IssueDecomposer()


@pytest.fixture
def selector():
    return EvidenceSelector()


@pytest.fixture
def sufficiency_validator():
    return EvidenceSufficiencyValidator()


@pytest.fixture
def output_validator():
    return OutputValidator()


# =============================================================================
# 1. REPRODUCE FAILURE & RESOLVE: Regression Case RW_TNLD_01
# =============================================================================

def test_rw_tnld_01_regression_resolved(parser, decomposer, selector, sufficiency_validator):
    """RW_TNLD_01: 'Công ty chưa đóng BHXH, tôi bị gãy chân khi đang làm việc'
    Must parse both UNPAID_INSURANCE and OCCUPATIONAL_ACCIDENT.
    Must decompose into at least 2 distinct issues.
    Must select L_84_2015#d38, L_84_2015#d39, VBHN_18_2026#d168.
    Must suppress Điều 26 Luật BHXH (ốm đau).
    """
    query = "Công ty chưa đóng BHXH, tôi bị gãy chân khi đang làm việc"

    # Step 1: Legal Event Detection
    events = detect_legal_events(query)
    assert "UNPAID_INSURANCE" in events, f"Expected UNPAID_INSURANCE in {events}"
    assert "OCCUPATIONAL_ACCIDENT" in events, f"Expected OCCUPATIONAL_ACCIDENT in {events}"
    assert "ORDINARY_SICKNESS" not in events, f"ORDINARY_SICKNESS should not be in {events}"

    # Step 2: Multi-Issue Decomposition
    issues = decomposer.decompose(query)
    assert len(issues) >= 2, f"Expected at least 2 decomposed issues, got {len(issues)}"

    issue_domains = [iss.domain for iss in issues]
    assert "CORE_LABOR" in issue_domains or "SOCIAL_INSURANCE" in issue_domains, "Expected employer insurance obligation issue"
    assert "OCCUPATIONAL_SAFETY" in issue_domains or "OCCUPATIONAL_ACCIDENT_DISEASE" in issue_domains, "Expected occupational accident issue"

    # Step 3: Required Evidence Roles per Issue
    accident_issue = next(iss for iss in issues if iss.domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"])
    assert "EMPLOYER_MEDICAL_RESPONSIBILITY" in accident_issue.required_evidence_roles or "EMPLOYER_ACCIDENT_COMPENSATION" in accident_issue.required_evidence_roles
    assert "UNINSURED_ACCIDENT_SUBSTITUTION" in accident_issue.required_evidence_roles

    # Step 4: Evidence Selection with Semantic Incompatibility Penalty
    mock_candidates = [
        {
            "chunk_id": "L_84_2015#d38-k1",
            "metadata": {
                "doc_id": "L_84_2015",
                "article_number": 38,
                "clause_number": 1,
                "article_title": "Trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp",
                "content": "Kịp thời sơ cứu, cấp cứu cho người lao động bị tai nạn lao động và phải tạm ứng chi phí sơ cứu, cấp cứu và điều trị cho người lao động bị tai nạn lao động",
                "domain": "OCCUPATIONAL_SAFETY",
            },
        },
        {
            "chunk_id": "L_84_2015#d38-k3",
            "metadata": {
                "doc_id": "L_84_2015",
                "article_number": 38,
                "clause_number": 3,
                "article_title": "Trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động",
                "content": "Trả đủ tiền lương cho người lao động bị tai nạn lao động, bệnh nghề nghiệp phải nghỉ việc trong thời gian điều trị, phục hồi chức năng lao động",
                "domain": "OCCUPATIONAL_SAFETY",
            },
        },
        {
            "chunk_id": "L_84_2015#d39-k4",
            "metadata": {
                "doc_id": "L_84_2015",
                "article_number": 39,
                "clause_number": 4,
                "article_title": "Trường hợp người sử dụng lao động không đóng bảo hiểm tai nạn lao động",
                "content": "Nếu người sử dụng lao động không đóng bảo hiểm tai nạn lao động, bệnh nghề nghiệp cho người lao động thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc theo quy định thì ngoài việc phải bồi thường, trợ cấp theo quy định tại Điều 38 của Luật này, người sử dụng lao động phải trả một khoản tiền tương ứng với chế độ bảo hiểm tai nạn lao động, bệnh nghề nghiệp",
                "domain": "OCCUPATIONAL_SAFETY",
            },
        },
        {
            "chunk_id": "VBHN_58_2025#d26-k1",
            "metadata": {
                "doc_id": "VBHN_58_2025",
                "article_number": 26,
                "clause_number": 1,
                "article_title": "Thời gian hưởng chế độ ốm đau",
                "content": "Thời gian tối đa hưởng chế độ ốm đau trong một năm đối với người lao động tính theo ngày làm việc không kể ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần là 30 ngày nếu làm việc trong điều kiện bình thường",
                "domain": "SOCIAL_INSURANCE",
            },
        },
    ]

    parsed_acc = parser.parse(query=accident_issue.retrieval_query, forced_domain="OCCUPATIONAL_SAFETY")
    sel_res = selector.select_evidence(parsed_acc, mock_candidates)

    # Verify locked chunks
    assert "L_84_2015#d38-k1" in sel_res.selected_chunk_ids or "L_84_2015#d38-k3" in sel_res.selected_chunk_ids
    assert "L_84_2015#d39-k4" in sel_res.selected_chunk_ids, "L_84_2015#d39-k4 MUST be locked for uninsured accident"
    assert "VBHN_58_2025#d26-k1" not in sel_res.selected_chunk_ids, "Sickness provision d26 MUST NOT be selected for accident"

    # Step 5: Evidence Sufficiency Gate
    val_res = sufficiency_validator.validate(
        question=query,
        question_specificity=parsed_acc.question_specificity,
        locked_chunks=sel_res.locked_evidence_blocks,
        required_roles=parsed_acc.required_evidence_roles,
    )
    assert val_res.overall_status == "SUPPORTED_AND_SUFFICIENT"
    assert val_res.is_legally_sufficient is True


# =============================================================================
# 2. Backend-Owned Citations & CitationSanitizer Tests
# =============================================================================

def test_citation_sanitizer_eliminates_phantom_articles():
    """Sanitizer must intercept Article numbers not in allowed set and record phantoms."""
    # Simulated Qwen hallucinated output quoting Điều 41 and Điều 111
    raw_llm_text = (
        "Căn cứ Điều 168 Bộ luật Lao động 2019, công ty có nghĩa vụ đóng BHXH bắt buộc. "
        "Ngoài ra, theo Điều 41 Bộ luật Lao động 2019, doanh nghiệp phải bồi thường thiệt hại. "
        "Đồng thời, căn cứ Điều 111 Bộ luật Lao động 2019 về tai nạn lao động..."
    )

    # Allowed articles are ONLY 168, 38, 39
    allowed_articles = {"168", "38", "39"}
    sanitized, phantoms = CitationSanitizer.sanitize(raw_llm_text, allowed_articles)

    # Verification: Phantom references eliminated
    assert "Điều 41" not in sanitized, f"Điều 41 should have been sanitized from: {sanitized}"
    assert "Điều 111" not in sanitized, f"Điều 111 should have been sanitized from: {sanitized}"
    assert "Điều 168" in sanitized, "Allowed Điều 168 must be preserved"
    assert len(phantoms) == 2
    phantom_arts = [p.article_number for p in phantoms]
    assert "41" in phantom_arts
    assert "111" in phantom_arts


def test_evidence_mapper_replaces_tokens_with_canonical_metadata():
    """Backend replaces [E1] with verified statutory citations without hallucinations."""
    mapper = EvidenceMapper()
    blocks = [
        EvidenceBlock(
            evidence_id="E1",
            chunk_id="L_84_2015#d38-k1",
            document_no="84/2015/QH13",
            document_title="Luật An toàn, vệ sinh lao động 2015",
            article_number=38,
            clause_number=1,
            point=None,
            content="Chi phí y tế từ sơ cứu đến điều trị ổn định",
        ),
        EvidenceBlock(
            evidence_id="E2",
            chunk_id="L_84_2015#d39-k4",
            document_no="84/2015/QH13",
            document_title="Luật An toàn, vệ sinh lao động 2015",
            article_number=39,
            clause_number=4,
            point=None,
            content="Chi trả khoản tiền tương ứng với chế độ bảo hiểm tai nạn",
        ),
    ]
    mapper.register_blocks(blocks)

    text_with_tokens = "Theo [E1], công ty phải thanh toán viện phí. Theo [E2], công ty phải trả tiền thay bảo hiểm."
    replaced = mapper.replace_evidence_tokens_in_text(text_with_tokens)

    assert "Khoản 1 Điều 38 Luật An toàn, vệ sinh lao động 2015" in replaced
    assert "Khoản 4 Điều 39 Luật An toàn, vệ sinh lao động 2015" in replaced
    assert "[E1]" not in replaced
    assert "[E2]" not in replaced


# =============================================================================
# 3. Semantic Incompatibility Penalty Tests
# =============================================================================

def test_sickness_chunk_penalized_on_occupational_accident_query(selector, parser):
    """When query is OCCUPATIONAL_ACCIDENT, chunks solely about ORDINARY_SICKNESS get -10.0 penalty."""
    query = "Tôi bị tai nạn lao động ngã giàn giáo thì công ty trả lương thế nào"
    parsed = parser.parse(query)
    assert parsed.legal_event == "OCCUPATIONAL_ACCIDENT"
    assert "ORDINARY_SICKNESS" not in parsed.legal_events

    accident_chunk = {
        "chunk_id": "L_84_2015#d38-k3",
        "metadata": {
            "doc_id": "L_84_2015",
            "article_number": 38,
            "clause_number": 3,
            "article_title": "Trách nhiệm trả đủ tiền lương",
            "content": "Trả đủ tiền lương cho người lao động bị tai nạn lao động trong thời gian điều trị",
            "domain": "OCCUPATIONAL_SAFETY",
        },
    }
    sickness_chunk = {
        "chunk_id": "VBHN_58_2025#d26-k1",
        "metadata": {
            "doc_id": "VBHN_58_2025",
            "article_number": 26,
            "clause_number": 1,
            "article_title": "Thời gian hưởng chế độ ốm đau",
            "content": "Thời gian tối đa hưởng chế độ ốm đau là 30 ngày làm việc",
            "domain": "SOCIAL_INSURANCE",
        },
    }

    scored_acc = selector.score_candidate(parsed, accident_chunk)
    scored_sick = selector.score_candidate(parsed, sickness_chunk)

    assert scored_acc.total_score > scored_sick.total_score + 10.0, (
        f"Accident score {scored_acc.total_score} should dominate sickness score {scored_sick.total_score} by >= 10 points"
    )
    assert scored_sick.topic_score <= -8.0, f"Sickness chunk should receive strong penalty, got {scored_sick.topic_score}"


def test_accident_chunk_penalized_on_ordinary_sickness_query(selector, parser):
    """When query is ORDINARY_SICKNESS, accident chunks get strong penalty."""
    query = "Tôi bị sốt xuất huyết nghỉ ốm 5 ngày có được BHXH chi trả không"
    parsed = parser.parse(query)
    assert parsed.legal_event == "ORDINARY_SICKNESS"
    assert "OCCUPATIONAL_ACCIDENT" not in parsed.legal_events

    sickness_chunk = {
        "chunk_id": "VBHN_58_2025#d25",
        "metadata": {
            "doc_id": "VBHN_58_2025",
            "article_number": 25,
            "article_title": "Điều kiện hưởng chế độ ốm đau",
            "content": "Bị ốm đau, tai nạn mà không phải là tai nạn lao động phải nghỉ việc",
            "domain": "SOCIAL_INSURANCE",
        },
    }
    accident_chunk = {
        "chunk_id": "L_84_2015#d38",
        "metadata": {
            "doc_id": "L_84_2015",
            "article_number": 38,
            "article_title": "Trách nhiệm của NSDLĐ khi bị tai nạn lao động",
            "content": "Sơ cứu cấp cứu và bồi thường tai nạn lao động",
            "domain": "OCCUPATIONAL_SAFETY",
        },
    }

    scored_sick = selector.score_candidate(parsed, sickness_chunk)
    scored_acc = selector.score_candidate(parsed, accident_chunk)

    assert scored_sick.total_score > scored_acc.total_score + 8.0
    assert scored_acc.topic_score <= -8.0


# =============================================================================
# 4. Evidence Sufficiency Gate & Claim-Event Mismatch Tests
# =============================================================================

def test_event_mismatch_detected_when_accident_query_only_has_sickness_evidence(sufficiency_validator):
    """If question is occupational accident but evidence only discusses sickness, status is EVENT_MISMATCH."""
    query = "Tôi bị tai nạn lao động gãy chân khi đang làm việc ở công ty"
    sickness_locked = [
        {
            "chunk_id": "VBHN_58_2025#d26",
            "metadata": {
                "doc_id": "VBHN_58_2025",
                "article_number": 26,
                "article_title": "Thời gian hưởng chế độ ốm đau",
                "content": "Thời gian tối đa hưởng chế độ ốm đau là 30 ngày làm việc",
            },
        }
    ]

    res = sufficiency_validator.validate(
        question=query,
        question_specificity="GENERAL_PRINCIPLE",
        locked_chunks=sickness_locked,
    )
    assert res.overall_status == "EVENT_MISMATCH"
    assert res.is_legally_sufficient is False


def test_missing_uninsured_role_marks_incomplete(sufficiency_validator):
    """If query requires UNINSURED_ACCIDENT_SUBSTITUTION but evidence only has d38 (no d39k4), status is INCOMPLETE."""
    query = "Công ty không đóng bảo hiểm, tôi bị tai nạn lao động thì công ty phải trả gì"
    d38_only = [
        {
            "chunk_id": "L_84_2015#d38",
            "metadata": {
                "doc_id": "L_84_2015",
                "article_number": 38,
                "article_title": "Trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động",
                "content": "Thanh toán viện phí và trả đủ tiền lương trong thời gian điều trị tai nạn lao động",
                "evidence_roles": ["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY"],
            },
        }
    ]
    req_roles = ["EMPLOYER_MEDICAL_RESPONSIBILITY", "UNINSURED_ACCIDENT_SUBSTITUTION"]

    res = sufficiency_validator.validate(
        question=query,
        question_specificity="GENERAL_PRINCIPLE",
        locked_chunks=d38_only,
        required_roles=req_roles,
    )
    assert res.overall_status == "SUPPORTED_BUT_INCOMPLETE"
    assert res.is_legally_sufficient is False
    assert any("UNINSURED_ACCIDENT_SUBSTITUTION" in m for m in res.missing_details)


# =============================================================================
# 5. 30 Real-World Adversarial Queries Suite
# =============================================================================

ADVERSARIAL_30_CASES = [
    # 1-5: Workplace accident + unpaid insurance variants
    {
        "id": "ADV_01",
        "query": "Công ty chưa đóng BHXH, tôi bị gãy chân khi đang làm việc",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    {
        "id": "ADV_02",
        "query": "cty chưa đóng bhxh mà tôi bị tai nạn lúc đang làm",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    {
        "id": "ADV_03",
        "query": "đang làm bị máy kẹp tay mà công ty chưa đóng bảo hiểm",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    {
        "id": "ADV_04",
        "query": "công ty ko đóng bảo hiểm tai nạn thì ai trả tiền",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    {
        "id": "ADV_05",
        "query": "công ty trốn đóng bhxh cho công nhân may bị máy khâu đâm vào tay",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    # 6-10: Hospital costs, wage & fault in accident
    {
        "id": "ADV_06",
        "query": "ngã giàn giáo tại công trình thì công ty phải trả viện phí không",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_07",
        "query": "tiền viện phí tai nạn lao động bảo hiểm y tế chi trả hay công ty trả",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_08",
        "query": "người lao động tự làm đứt tay do vi phạm quy trình thì công ty có bồi thường không",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_09",
        "query": "đang điều trị tai nạn lao động công ty có được trừ lương không",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_10",
        "query": "tai nạn lao động chết người công ty phải bồi thường bao nhiêu tháng lương",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    # 11-15: Commuting accident, occupational disease, impairment
    {
        "id": "ADV_11",
        "query": "bị tai nạn trên đường đi làm về có được công ty bồi thường không",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_12",
        "query": "bị tai nạn giao thông hợp lý từ nơi ở đến nơi làm việc",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_13",
        "query": "bị bệnh bụi phổi sau 5 năm làm việc tại mỏ đá",
        "expected_events": ["OCCUPATIONAL_DISEASE"],
        "min_issues": 1,
    },
    {
        "id": "ADV_14",
        "query": "bị tai nạn lao động suy giảm 10% khả năng lao động thì nhận bao nhiêu tiền",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_15",
        "query": "đang thử việc bị tai nạn lao động công ty có phải bồi thường không",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    # 16-20: Ordinary sickness vs Workplace accident (Disambiguation)
    {
        "id": "ADV_16",
        "query": "bị gãy chân trong ca làm việc thì có phải ốm đau ko",
        "expected_events": ["OCCUPATIONAL_ACCIDENT", "ORDINARY_SICKNESS"],
        "min_issues": 2,
    },
    {
        "id": "ADV_17",
        "query": "nghỉ ốm đau do sốt xuất huyết nằm viện 5 ngày",
        "expected_events": ["ORDINARY_SICKNESS"],
        "min_issues": 1,
    },
    {
        "id": "ADV_18",
        "query": "con nhỏ 2 tuổi bị sốt mẹ nghỉ làm chăm sóc",
        "expected_events": ["ORDINARY_SICKNESS"],
        "min_issues": 1,
    },
    {
        "id": "ADV_19",
        "query": "bị cảm cúm thông thường nghỉ ở nhà 2 ngày có được hưởng tai nạn lao động không",
        "expected_events": ["ORDINARY_SICKNESS", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_20",
        "query": "nghỉ ốm đau dài ngày quá 180 ngày có được hưởng tiếp không",
        "expected_events": ["ORDINARY_SICKNESS"],
        "min_issues": 1,
    },
    # 21-25: Compound cross-domain & termination
    {
        "id": "ADV_21",
        "query": "nghỉ sinh con xong đi làm lại bị sa thải",
        "expected_events": ["MATERNITY", "TERMINATION"],
        "min_issues": 2,
    },
    {
        "id": "ADV_22",
        "query": "vừa bị tai nạn lao động vừa hết hạn hợp đồng",
        "expected_events": ["OCCUPATIONAL_ACCIDENT", "TERMINATION"],
        "min_issues": 1,
    },
    {
        "id": "ADV_23",
        "query": "công ty nợ bhxh 1 năm rồi tôi bị tai nạn xe nâng ở xưởng",
        "expected_events": ["UNPAID_INSURANCE", "OCCUPATIONAL_ACCIDENT"],
        "min_issues": 2,
    },
    {
        "id": "ADV_24",
        "query": "công ty chưa đóng bhxh thì người lao động có quyền khởi kiện không",
        "expected_events": ["UNPAID_INSURANCE"],
        "min_issues": 1,
    },
    {
        "id": "ADV_25",
        "query": "công ty cử đi học nước ngoài về đòi nghỉ việc có phải đền tiền không",
        "expected_events": ["VOCATIONAL_TRAINING"],
        "min_issues": 1,
    },
    # 26-30: Colloquial Vietnamese, Typos & Negative Tests
    {
        "id": "ADV_26",
        "query": "bị máy ép dập ngón tay trong giờ làm việc công ty bảo tự chịu",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_27",
        "query": "bị ngã cầu thang tại trụ sở công ty trong giờ giải lao",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_28",
        "query": "nghỉ dưỡng sức sau khi điều trị tai nạn lao động",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_29",
        "query": "công ty ép người lao động ký cam kết không khiếu nại tai nạn lao động",
        "expected_events": ["OCCUPATIONAL_ACCIDENT"],
        "min_issues": 1,
    },
    {
        "id": "ADV_30",
        "query": "đủ tuổi nghỉ hưu nhưng mới đóng bảo hiểm 10 năm",
        "expected_events": ["RETIREMENT", "INSURANCE_CONTRIBUTION"],
        "min_issues": 2,
    },
]


@pytest.mark.parametrize("case", ADVERSARIAL_30_CASES, ids=lambda c: c["id"])
def test_adversarial_event_detection_and_decomposition(case, parser, decomposer):
    """Evaluates legal event detection accuracy and multi-issue decomposition recall."""
    query = case["query"]
    events = detect_legal_events(query)

    for expected_ev in case["expected_events"]:
        assert expected_ev in events, (
            f"Case {case['id']} query '{query}' missing expected event {expected_ev}. Got: {events}"
        )

    # Multi-issue decomposition check
    issues = decomposer.decompose(query)
    assert len(issues) >= case["min_issues"], (
        f"Case {case['id']} expected at least {case['min_issues']} issues, got {len(issues)}: {[i.raw_issue_text for i in issues]}"
    )
