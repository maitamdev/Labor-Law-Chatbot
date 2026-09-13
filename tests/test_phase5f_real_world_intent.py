# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5F Real-World Intent & Ambiguity Hardening Tests
Verifies:
1. Colloquial Vietnamese normalization
2. Generic MaterialPremiseGate evaluation
3. Real-world regression query RW_01 (No premature Điều 46, triggers clarification)
4. Multi-turn conversation state transitions:
   - Internship -> School-program transition (Flow A)
   - Internship -> De facto employment transition (Flow B)
   - Internship -> Probation transition -> Qualification resolution (Flow C)
5. Collaborator / freelancer ambiguity detection
6. Prevention of premature statutory anchoring
"""
import pytest

from rag.chain import ConversationMemory, VietLaborRAGChain
from rag.legal_issue_parser import LegalIssueParser
from rag.material_premise_gate import MaterialPremiseGate
from rag.query_processor import normalize_colloquial_vietnamese, normalize_query


class TestColloquialNormalization:
    """Test colloquial abbreviations and slang normalizations."""

    def test_abbreviations(self):
        assert "công ty" in normalize_colloquial_vietnamese("cty không trả lương")
        assert "không" in normalize_colloquial_vietnamese("em ko có bằng")
        assert "người lao động" in normalize_colloquial_vietnamese("nld có quyền gì")
        assert "hợp đồng lao động" in normalize_colloquial_vietnamese("chưa ký hđlđ")
        assert "cộng tác viên" in normalize_colloquial_vietnamese("làm ctv 3 tháng")

    def test_phrases(self):
        norm = normalize_colloquial_vietnamese("bị đuổi ngang thì dc gì")
        assert "đơn phương chấm dứt hợp đồng lao động không báo trước" in norm
        assert "được" in norm

        norm2 = normalize_colloquial_vietnamese("tôi đi thực tập 7 tháng rồi mà ko có lương")
        assert "không được trả tiền lương" in norm2

        norm3 = normalize_colloquial_vietnamese("làm 8 tiếng mỗi ngày")
        assert "làm việc 8 giờ một ngày" in norm3


class TestMaterialPremiseGate:
    """Tests generic MaterialPremiseGate rules without hardcoding."""

    @pytest.fixture
    def parser(self):
        return LegalIssueParser()

    @pytest.fixture
    def gate(self):
        return MaterialPremiseGate()

    def test_rw_01_internship_ambiguity(self, parser, gate):
        q = "tôi đi thực tập 7 tháng rồi mà ko có lương"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_01")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.is_sufficient is False
        assert res.category == "RELATIONSHIP_AMBIGUITY_INTERNSHIP"
        assert "18/VBHN-VPQH#d46" in res.forbidden_provisions
        assert "VBHN_18_2026#d46" in res.forbidden_provisions
        assert "chương trình của nhà trường" in res.clarification_question
        assert len(res.clarification_options) >= 3

    def test_collaborator_subordination_ambiguity(self, parser, gate):
        q = "công ty bảo em là cộng tác viên nhưng ngày nào cũng chấm công làm 8 tiếng"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_02")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.is_sufficient is False
        assert res.category == "RELATIONSHIP_AMBIGUITY_COLLABORATOR"
        assert "Điều 13" in res.clarification_question

    def test_probation_duration_missing_qualification(self, parser, gate):
        q = "Công ty bắt tôi thử việc 3 tháng có đúng không"
        issue = parser.parse(q, issue_id="AMB_01")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "PROBATION_DURATION_QUALIFICATION_MISSING"
        assert "trình độ chuyên môn" in res.clarification_question

    def test_resignation_notice_missing_contract_term(self, parser, gate):
        q = "Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày"
        issue = parser.parse(q, issue_id="AMB_03")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "RESIGNATION_NOTICE_TERM_MISSING"

    def test_severance_prevention_on_wage_dispute(self, parser, gate):
        q = "Công ty chậm trả lương 2 tháng"
        issue = parser.parse(q, issue_id="IN_TEST")
        res = gate.evaluate(issue)

        assert res.is_sufficient is True
        assert "18/VBHN-VPQH#d46" in res.forbidden_provisions


    def test_informal_arrangement_ambiguity(self, parser, gate):
        q = "công ty nhận em vào làm quen việc 2 tháng không trả tiền"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_04")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "INFORMAL_ARRANGEMENT_AMBIGUITY"
        assert "18/VBHN-VPQH#d46" in res.forbidden_provisions

    def test_unsigned_employment_ambiguity(self, parser, gate):
        q = "em làm ở công ty 6 tháng mà chưa ký hợp đồng có sao k"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_11")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "UNSIGNED_EMPLOYMENT_AMBIGUITY"

    def test_contract_type_ambiguity(self, parser, gate):
        q = "tôi làm thời vụ mà ko biết hợp đồng của tôi thuộc loại gì"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_12")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "CONTRACT_TYPE_AMBIGUITY"

    def test_severance_facts_missing(self, parser, gate):
        q = "chấm dứt hợp đồng có phải trả tiền trợ cấp thôi việc không"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_19")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "SEVERANCE_FACTS_MISSING"

    def test_apprenticeship_ambiguity(self, parser, gate):
        q = "tôi học việc 4 tháng không được đồng nào có đúng không"
        norm_q = normalize_colloquial_vietnamese(q)
        issue = parser.parse(norm_q, issue_id="RW_26")
        res = gate.evaluate(issue)

        assert res.needs_clarification is True
        assert res.category == "APPRENTICESHIP_TRAINING_AMBIGUITY"
        assert "18/VBHN-VPQH#d46" in res.forbidden_provisions


class TestConversationMemoryStateTransitions:
    """Tests multi-turn state accumulation and refinement in ConversationMemory."""

    def test_probation_state_refinement(self):
        mem = ConversationMemory(max_turns=3)
        # Turn 1: initial query
        mem.add_turn("Công ty bắt tôi thử việc 3 tháng có đúng không", "Vui lòng cho biết trình độ của bạn")
        assert mem.accumulated_facts.get("topic") == "thử việc"
        assert not mem.has_clarification_facts()

        # Turn 2: user provides qualification
        mem.add_turn("Tôi có bằng đại học", "Thời gian thử việc tối đa là 60 ngày theo Điều 25")
        assert mem.accumulated_facts.get("qualification") == "cao đẳng trở lên"
        assert mem.has_clarification_facts()

    def test_internship_to_probation_override(self):
        mem = ConversationMemory(max_turns=3)
        # Turn 1: user asks about internship
        mem.add_turn("Em đi thực tập không lương", "Bạn thực tập theo trường hay công ty tuyển?")
        # Turn 2: user clarifies it's actually probation
        mem.add_turn("Thực ra công ty bảo đây là thử việc", "Thử việc ở vị trí nào?")
        assert mem.accumulated_facts.get("relationship_type") == "PROBATION"
        assert mem.accumulated_facts.get("topic") == "thử việc"
        assert "school_program" not in mem.accumulated_facts


class TestVietLaborRAGChainPhase5F:
    """End-to-end regression tests for RW_01 and multi-turn flows."""

    def test_rw_01_regression_behavior(self):
        chain = VietLaborRAGChain()
        chain.memory.clear()
        res = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương", update_memory=False)

        # Must trigger clarification immediately
        assert res.validated_response.needs_clarification is True
        assert not res.validated_response.abstain
        assert len(res.validated_response.cited_chunk_ids) == 0
        # Absolutely NO Điều 46
        assert not any("d46" in cid for cid in res.validated_response.cited_chunk_ids)
        assert not any("Điều 46" in res.validated_response.final_answer for cid in ["d46"])
        # Clarification prompt must inquire about nature of relationship
        assert "chương trình của nhà trường" in res.validated_response.clarification_question
        assert len(res.validated_response.clarification_options) >= 3

    def test_flow_a_school_internship_transition(self):
        chain = VietLaborRAGChain()
        chain.memory.clear()

        # Turn 1: Initial ambiguous query
        res1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
        assert res1.validated_response.needs_clarification is True

        # Turn 2: User clarifies school internship program
        res2 = chain.run("Em thực tập theo chương trình của trường, có giấy giới thiệu và thỏa thuận thực tập.")
        assert res2.validated_response.needs_clarification is False
        assert not any("d46" in cid for cid in res2.validated_response.cited_chunk_ids)

    def test_flow_b_de_facto_employment_transition(self):
        chain = VietLaborRAGChain()
        chain.memory.clear()

        # Turn 1: Initial ambiguous query
        res1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
        assert res1.validated_response.needs_clarification is True

        # Turn 2: User clarifies de facto employment characteristics
        res2 = chain.run("Công ty tự tuyển em, ngày nào em cũng làm 8 tiếng, chấm công và làm việc như nhân viên, không có giấy của trường.")
        assert res2.validated_response.needs_clarification is False
        assert not any("d46" in cid for cid in res2.validated_response.cited_chunk_ids)
        # Should cite Điều 13 Khoản 1 BLLĐ for labor relationship
        cids_joined = " ".join(res2.validated_response.cited_chunk_ids)
        answer_text = res2.validated_response.final_answer
        assert "d13" in cids_joined or "Điều 13" in answer_text or "quan hệ lao động" in answer_text

    def test_flow_c_probation_transition_chain(self):
        chain = VietLaborRAGChain()
        chain.memory.clear()

        # Turn 1: Initial ambiguous query
        res1 = chain.run("tôi đi thực tập 7 tháng rồi mà ko có lương")
        assert res1.validated_response.needs_clarification is True

        # Turn 2: User clarifies this is actually probation before signing contract
        res2 = chain.run("Thực ra công ty bảo đây là thử việc trước khi ký hợp đồng.")
        # Transitions to probation analysis; asks for qualification if needed
        assert res2.validated_response.needs_clarification is True
        assert "trình độ chuyên môn" in res2.validated_response.clarification_question

        # Turn 3: User provides qualification
        res3 = chain.run("Em có bằng đại học kỹ sư phần mềm.")
        assert res3.validated_response.needs_clarification is False
        cids_joined = " ".join(res3.validated_response.cited_chunk_ids)
        answer_text = res3.validated_response.final_answer
        assert "d25" in cids_joined or "d26" in cids_joined or "Điều 25" in answer_text or "Điều 26" in answer_text

