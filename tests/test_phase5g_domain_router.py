# -*- coding: utf-8 -*-
"""
Tests for Phase 5G Domain Router and Issue Decomposer.
Verifies accurate classification of:
- CORE_LABOR
- RETIREMENT (ND 135/2020)
- UNEMPLOYMENT_INSURANCE (Luat Viec Lam 74/2025, ND 374/2025)
- FOREIGN_WORKER (ND 219/2025)
- CROSS_DOMAIN multi-issue decomposition
- Exemption for foreign worker marriage rights
"""
import pytest
from rag.query_router import QueryRouter
from rag.issue_decomposer import IssueDecomposer
from rag.legal_issue_parser import LegalIssueParser


@pytest.fixture
def router():
    return QueryRouter()


@pytest.fixture
def decomposer():
    return IssueDecomposer()


def test_retirement_domain_routing(router):
    queries = [
        "Tuổi nghỉ hưu của nam năm 2026 là bao nhiêu?",
        "Lộ trình tăng tuổi nghỉ hưu của lao động nữ theo Nghị định 135/2020",
        "Tôi làm công việc nặng nhọc có được nghỉ hưu sớm 5 năm không?",
        "Thời điểm hưởng lương hưu được tính từ ngày nào?",
        "Điều 4 Nghị định 135/2020/NĐ-CP",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.domain == "RETIREMENT", f"Failed for query '{q}': got {decision.domain}"


def test_unemployment_insurance_domain_routing(router):
    queries = [
        "Điều kiện hưởng trợ cấp thất nghiệp theo Luật Việc làm 2025",
        "Thời hạn nộp hồ sơ bảo hiểm thất nghiệp là bao lâu?",
        "Mức hưởng trợ cấp thất nghiệp hằng tháng là bao nhiêu phần trăm?",
        "Hồ sơ đề nghị hưởng BHTN gồm những giấy tờ gì theo Nghị định 374/2025?",
        "Điều 61 Luật Việc làm 74/2025",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.domain == "UNEMPLOYMENT_INSURANCE", f"Failed for query '{q}': got {decision.domain}"


def test_foreign_worker_domain_routing(router):
    queries = [
        "Thời hạn tối đa của giấy phép lao động cấp cho người nước ngoài là bao lâu?",
        "Điều kiện để được cấp work permit cho chuyên gia nước ngoài theo Nghị định 219/2025",
        "Các trường hợp miễn giấy phép lao động cho người nước ngoài",
        "Thủ tục cấp giấy phép lao động cho lao động kỹ thuật nước ngoài",
        "Điều 7 Nghị định 219/2025/NĐ-CP",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.domain == "FOREIGN_WORKER", f"Failed for query '{q}': got {decision.domain}"


def test_core_labor_preservation(router):
    queries = [
        "Thời gian thử việc tối đa của nhân viên kinh doanh là bao nhiêu ngày?",
        "Công ty sa thải người lao động trái pháp luật thì phải bồi thường gì?",
        "Mức lương làm thêm giờ ban đêm vào ngày lễ là bao nhiêu %?",
        "Nghỉ phép năm có được hưởng nguyên lương không?",
        "Điều 25 Bộ luật Lao động",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.domain == "CORE_LABOR", f"Failed for query '{q}': got {decision.domain}"


def test_foreign_marriage_exemption(router):
    """Foreign marriage labor rights must be routed to FOREIGN_WORKER, NOT blocked as out-of-scope family law."""
    q = "Chồng tôi là người nước ngoài kết hôn với người Việt Nam đi làm tại Việt Nam có cần giấy phép lao động không?"
    decision = router.route(q)
    assert not decision.is_out_of_scope, f"Should NOT be out-of-scope: {decision.reason}"
    assert decision.domain == "FOREIGN_WORKER", f"Expected FOREIGN_WORKER, got {decision.domain}"


def test_out_of_scope_still_blocked(router):
    queries = [
        "Thủ tục ly hôn đơn phương tại tòa án cần những giấy tờ gì?",
        "Tội lừa đảo chiếm đoạt tài sản bị phạt tù bao nhiêu năm?",
        "Thuế thu nhập doanh nghiệp áp dụng thuế suất bao nhiêu phần trăm?",
    ]
    for q in queries:
        decision = router.route(q)
        assert decision.is_out_of_scope, f"Should be out-of-scope: '{q}'"


def test_cross_domain_decomposition(decomposer):
    q = "Tôi nghỉ việc sau 5 năm thì công ty có phải trả trợ cấp thôi việc không và tôi có được hưởng trợ cấp thất nghiệp không?"
    issues = decomposer.decompose(q)
    assert len(issues) >= 2, f"Expected compound decomposition, got {len(issues)}"
    domains = {iss.domain for iss in issues}
    assert "CORE_LABOR" in domains or "UNEMPLOYMENT_INSURANCE" in domains
