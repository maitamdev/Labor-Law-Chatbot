# -*- coding: utf-8 -*-
"""
VietLabor AI - Test Scenario Consultation Anti-Interruption Guardrail
Verifies:
1. Real-world legal scenarios (Chị Nhung, Anh Dơ, Anh Dũng, pregnant worker, deduction dispute)
   are ALWAYS classified as SCENARIOS and NEVER interrupted by MaterialPremiseGate or BenefitCalculator.
2. The pipeline guarantees needs_clarification=False on all complex scenarios.
3. Truly brief, ambiguous queries (Phase 5F tests) still retain their legitimate clarification prompts.
"""
import pytest

from rag.legal_issue_parser import LegalIssueParser
from rag.material_premise_gate import MaterialPremiseGate
from rag.legal_calculator import BenefitCalculator
from rag.query_processor import is_scenario_or_legal_consultation, normalize_colloquial_vietnamese


@pytest.fixture
def parser():
    return LegalIssueParser()


@pytest.fixture
def gate():
    return MaterialPremiseGate()


class TestScenarioDetectionAndGuardrail:
    """Test scenario detector and premise gate bypass."""

    def test_chi_nhung_wage_scenario(self, parser, gate):
        q = (
            "Chị Hoàng Thị Nhung, người dân tộc Dao ở xã PN, làm việc cho doanh nghiệp may gia công xuất khẩu. "
            "Công ty thường xuyên chậm trả lương từ 10-15 ngày và không thông báo rõ lý do. "
            "Hỏi: Pháp luật quy định như nào về kỳ hạn trả lương cho người lao động? "
            "Trường hợp chậm trả lương thì xử lý như thế nào? "
            "Chị Nhung có quyền khiếu nại hay tạm ngừng làm việc khi doanh nghiệp chậm trả lương không?"
        )
        assert is_scenario_or_legal_consultation(q) is True

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="SCENARIO_NHUNG")
        res = gate.evaluate(issue)

        assert res.needs_clarification is False
        assert res.is_sufficient is True
        assert res.category == "SCENARIO_LEGAL_CONSULTATION_SUFFICIENT"

        calc_res = BenefitCalculator.extract_and_calculate(norm_q)
        assert calc_res is None or calc_res.needs_clarification is False

    def test_anh_do_workplace_accident_scenario(self, parser, gate):
        q = (
            "Anh Vàng A Dơ, 25 tuổi, người dân tộc Mông, sau khi học hết lớp 9, anh làm công nhân tại Công ty TNHH Khai thác và Xây dựng A, "
            "chuyên thi công các công trình đường giao thông vùng núi. Công ty ký với anh hợp đồng lao động thời hạn 12 tháng, "
            "công việc là bốc xếp và vận chuyển vật liệu. Tuy nhiên, do ở vùng xa, nhiều lao động dân tộc không hiểu rõ pháp luật nên phần lớn không được đóng bảo hiểm xã hội, bảo hiểm y tế đầy đủ. "
            "Trong quá trình làm việc, ngày 12/5/2025, anh Dơ bị trượt ngã khi đang bốc dỡ đá, dẫn đến gãy chân, phải điều trị hơn 2 tháng "
            "khi anh đề nghị công ty thanh toán tiền bảo hiểm tai nạn lao động, thì mới phát hiện doanh nghiệp chưa đóng bảo hiểm xã hội, bảo hiểm tai nạn cho anh dù hợp đồng đã ký hơn 8 tháng. "
            "Hỏi: Người sử dụng lao động có trách nhiệm như nào trong việc đóng bảo hiểm cho người lao động từ 01 tháng trở lên? "
            "Anh Vàng A Dơ có được hưởng chế độ tai nạn lao động không khi doanh nghiệp trốn đóng bảo hiểm?"
        )
        assert is_scenario_or_legal_consultation(q) is True

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="SCENARIO_DO")
        res = gate.evaluate(issue)

        assert res.needs_clarification is False
        assert res.is_sufficient is True

        # BenefitCalculator must NOT erroneously intercept with incomplete calculation
        calc_res = BenefitCalculator.extract_and_calculate(norm_q)
        assert calc_res is None

    def test_anh_dung_safety_refusal_scenario(self, parser, gate):
        q = (
            "Anh Lò Văn Dũng, người dân tộc Thái là công nhân vận hành máy xúc tại công trình xây dựng đường liên xã do Công ty TNHH Xây dựng Minh Phát thi công. "
            "Công việc của anh chủ yếu là vận hành máy xúc ở khu vực sườn núi, địa hình dốc và dễ sạt lở, nhất là trong mùa mưa. "
            "Ngày 20/9/2025, khi đang làm việc, anh Dũng phát hiện khu vực ta-luy phía trên có nhiều đá và đất bị nứt, có dấu hiệu sắp sạt lở. "
            "Anh báo với tổ trưởng công trình đề nghị tạm dừng thi công và di chuyển máy ra khỏi khu vực nguy hiểm. Tuy nhiên, tổ trưởng vẫn yêu cầu anh tiếp tục làm việc để kịp tiến độ, vì mới mưa nhỏ, chưa sao đâu. "
            "Nhận thấy nguy cơ sạt lở có thể đe dọa trực tiếp đến tính mạng và sức khỏe, anh Dũng kiên quyết từ chối tiếp tục làm việc và rời khỏi khu vực. "
            "Hỏi: Việc anh Dũng từ chối làm việc có đúng pháp luật không? Các quyền của người lao động trong trường hợp này?"
        )
        assert is_scenario_or_legal_consultation(q) is True

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="SCENARIO_DUNG")
        res = gate.evaluate(issue)

        assert res.needs_clarification is False
        assert res.is_sufficient is True

    def test_pregnant_worker_arbitrary_termination(self, parser, gate):
        q = (
            "Chị Mai đang mang thai tháng thứ 7 thì công ty bất ngờ ra quyết định sa thải lấy lý do không đạt năng suất làm việc. "
            "Công ty làm như vậy có đúng luật không và chị Mai có thể làm gì để bảo vệ quyền lợi?"
        )
        assert is_scenario_or_legal_consultation(q) is True

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="SCENARIO_MAI")
        res = gate.evaluate(issue)

        assert res.needs_clarification is False
        assert res.is_sufficient is True

    def test_wage_deduction_and_overtime_dispute(self, parser, gate):
        q = (
            "Công ty tự ý trừ 3 triệu đồng tiền lương của tôi vì làm rơi vỡ linh kiện máy móc nhưng không hề lập biên bản hay thỏa thuận bồi thường. "
            "Đồng thời công ty ép tăng ca 50 giờ trong tháng mà không có sự đồng ý. "
            "Tôi phải khiếu nại ở đâu và công ty bị xử phạt như thế nào?"
        )
        assert is_scenario_or_legal_consultation(q) is True

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="SCENARIO_DEDUCT")
        res = gate.evaluate(issue)

        assert res.needs_clarification is False
        assert res.is_sufficient is True


class TestBriefQueriesRetainClarification:
    """Verify that legitimate short ambiguous queries still trigger clarification."""

    def test_short_internship_clarification(self, parser, gate):
        q = "tôi đi thực tập 7 tháng rồi mà ko có lương"
        assert is_scenario_or_legal_consultation(q) is False

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="BRIEF_01")
        res = gate.evaluate(issue)
        assert res.needs_clarification is True
        assert res.category == "RELATIONSHIP_AMBIGUITY_INTERNSHIP"

    def test_short_probation_duration_clarification(self, parser, gate):
        q = "Công ty bắt tôi thử việc 3 tháng có đúng không"
        assert is_scenario_or_legal_consultation(q) is False

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="BRIEF_02")
        res = gate.evaluate(issue)
        assert res.needs_clarification is True
        assert res.category == "PROBATION_DURATION_QUALIFICATION_MISSING"

    def test_short_resignation_notice_clarification(self, parser, gate):
        q = "Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày"
        assert is_scenario_or_legal_consultation(q) is False

        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="BRIEF_03")
        res = gate.evaluate(issue)
        assert res.needs_clarification is True
        assert res.category == "RESIGNATION_NOTICE_TERM_MISSING"
