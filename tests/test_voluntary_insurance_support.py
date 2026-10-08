from rag.legal_issue_parser import LegalIssueParser
from rag.voluntary_insurance_support import SUPPORT_EVIDENCE_IDS, grounded_answer


QUESTION = (
    "Nhà nước hiện hỗ trợ tiền đóng BHXH tự nguyện cho những nhóm đối tượng nào "
    "và mức hỗ trợ có giống nhau cho tất cả người tham gia không?"
)


def test_voluntary_support_is_not_employer_contribution():
    issue = LegalIssueParser().parse(QUESTION)

    assert "VOLUNTARY_SOCIAL_INSURANCE_SUPPORT" in issue.legal_events
    assert "EMPLOYER_INSURANCE_OBLIGATION" not in issue.required_evidence_roles
    assert set(issue.required_evidence_roles) >= {
        "VOLUNTARY_SUPPORT_50", "VOLUNTARY_SUPPORT_40",
        "VOLUNTARY_SUPPORT_30", "VOLUNTARY_SUPPORT_20",
    }


def test_support_schedule_requires_all_four_official_points():
    assert grounded_answer(QUESTION, set(SUPPORT_EVIDENCE_IDS[:-1])) is None
    answer = grounded_answer(QUESTION, set(SUPPORT_EVIDENCE_IDS))

    assert answer is not None
    assert all(value in answer for value in ("50%", "40%", "30%", "20%"))
