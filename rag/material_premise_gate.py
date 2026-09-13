# -*- coding: utf-8 -*-
"""
VietLabor AI - Material Premise Gate (Phase 5F)
Deterministic gate evaluating whether a query provides sufficient factual premises
to anchor a specific statutory regime. Prevents premature statutory anchoring
and enforces clarification BEFORE retrieval when material legal premises are missing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional

from rag.legal_issue_parser import LegalIssue

logger = logging.getLogger(__name__)


@dataclass
class PremiseGateResult:
    """Outcome of material premise evaluation."""
    is_sufficient: bool
    needs_clarification: bool
    category: str
    missing_facts: List[str] = field(default_factory=list)
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    forbidden_provisions: List[str] = field(default_factory=list)
    reason: Optional[str] = None


class MaterialPremiseGate:
    """Evaluates factual completeness across legal categories before retrieval."""

    def evaluate(
        self,
        issue: LegalIssue,
        context_facts: Optional[Dict[str, Any]] = None,
    ) -> PremiseGateResult:
        """Evaluates whether the legal premise has sufficient factual grounding."""
        facts = context_facts or {}
        q_lower = issue.raw_query.lower()

        # -------------------------------------------------------------
        # CATEGORY 1: Relationship Ambiguity (Internship / Training / De Facto Employee)
        # -------------------------------------------------------------
        is_internship_query = (
            issue.internship_status in ["POSSIBLE", "COMPANY_DIRECT"]
            or "thực tập" in q_lower
            or issue.material_facts.get("claimed_label") == "internship"
        )

        if is_internship_query:
            has_school_fact = (
                bool(facts.get("school_program"))
                or issue.internship_status == "SCHOOL_PROGRAM"
                or (facts.get("relationship_type") == "INTERNSHIP")
                or any(k in q_lower for k in [
                    "theo chương trình của trường", "có giấy giới thiệu của trường",
                    "thỏa thuận với trường", "giấy giới thiệu", "đồ án"
                ])
            )
            has_employee_fact = (
                bool(facts.get("de_facto_employee"))
                or (facts.get("relationship_type") == "EMPLOYMENT")
            )
            has_probation_fact = (
                bool(facts.get("probation_clarified"))
                or (facts.get("relationship_type") == "PROBATION")
                or (facts.get("topic") == "thử việc")
            )

            if not (has_school_fact or has_employee_fact or has_probation_fact):
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="RELATIONSHIP_AMBIGUITY_INTERNSHIP",
                    missing_facts=["internship_program_type", "work_subordination", "wage_agreement"],
                    clarification_question=(
                        "Để xác định chính xác quy định về quyền lợi và tiền lương/phụ cấp thực tập, "
                        "mình cần biết thêm thông tin về trường hợp của bạn:\n"
                        "1. Bạn thực tập theo chương trình của nhà trường (có giấy giới thiệu/thỏa thuận với trường) "
                        "hay do công ty trực tiếp tuyển dụng?\n"
                        "2. Trong thời gian này, bạn có phải làm việc cố định theo ca/giờ, chấm công và thực hiện công việc "
                        "như một nhân viên bình thường không?"
                    ),
                    clarification_options=[
                        "Thực tập theo trường (có giấy giới thiệu)",
                        "Công ty tự tuyển, làm việc như nhân viên",
                        "Thực ra là thử việc trước khi ký HĐ",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Internship relationship nature (school program vs de facto employment vs probation) is unknown",
                )

        # -------------------------------------------------------------
        # CATEGORY 2: Collaborator / Freelancer Ambiguity
        # -------------------------------------------------------------
        is_collaborator_query = (
            issue.material_facts.get("claimed_label") == "collaborator"
            or any(k in q_lower for k in ["cộng tác viên", "ctv", "freelance"])
        )
        if is_collaborator_query:
            has_subordination = (
                issue.material_facts.get("has_subordination", False)
                or any(k in q_lower for k in ["chấm công", "làm 8 tiếng", "làm 8h", "ngồi văn phòng", "cố định"])
            )
            has_clarified = facts.get("collaborator_nature_clarified") or any(k in q_lower for k in ["đã ký hợp đồng dịch vụ", "tự do hoàn toàn"])
            if has_subordination and not has_clarified:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="RELATIONSHIP_AMBIGUITY_COLLABORATOR",
                    missing_facts=["actual_subordination_evidence", "agreement_type"],
                    clarification_question=(
                        "Theo quy định tại Điều 13 Bộ luật Lao động, nếu bạn làm việc có sự quản lý, "
                        "điều hành, giám sát, chấm công và trả công định kỳ thì được coi là quan hệ lao động thực tế. "
                        "Bạn vui lòng cho biết: Công ty có quy định giờ giấc làm việc cố định và quản lý trực tiếp bạn không, "
                        "hay bạn chỉ giao nộp kết quả công việc/sản phẩm?"
                    ),
                    clarification_options=[
                        "Có chấm công, làm việc cố định theo giờ",
                        "Làm việc tự do, chỉ nhận thù lao theo sản phẩm",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Collaborator label with employee-like subordination requires clarification",
                )

        # -------------------------------------------------------------
        # CATEGORY 3: Informal Arrangement Ambiguity (Làm quen việc / Đi làm ké)
        # -------------------------------------------------------------
        informal_signals = ["làm quen việc", "làm quen", "đi làm ké", "làm ké", "làm thử việc không lương", "thử việc miệng"]
        is_informal_arrangement = (
            any(k in q_lower for k in informal_signals)
            or issue.material_facts.get("claimed_label") in ["familiarization", "informal_help"]
        )
        if is_informal_arrangement:
            has_clarified = facts.get("relationship_clarified") or facts.get("relationship_type")
            if not has_clarified:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="INFORMAL_ARRANGEMENT_AMBIGUITY",
                    missing_facts=["agreement_type", "job_qualification_level", "work_subordination"],
                    clarification_question=(
                        "Pháp luật lao động không có chế định 'làm quen việc' hay 'đi làm ké', "
                        "mà chỉ điều chỉnh các quan hệ: Hợp đồng lao động, Thử việc (có trả lương tối thiểu 85%), "
                        "hoặc Tập nghề/học nghề (tối đa 3 tháng và phải trả lương nếu trực tiếp làm việc). "
                        "Để bảo vệ quyền lợi của bạn, bạn vui lòng cho biết:\n"
                        "1. Bạn và công ty có thỏa thuận đây là thử việc, học việc hay làm việc thực tế không?\n"
                        "2. Bạn có người quản lý trực tiếp giao việc, theo dõi giờ giấc làm việc hay không?"
                    ),
                    clarification_options=[
                        "Thực chất là thử việc trước khi ký HĐ",
                        "Được nhận vào học việc / tập nghề",
                        "Tham gia hỗ trợ dự án, không có văn bản",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Informal arrangement label is not a recognized legal relationship",
                )

        # -------------------------------------------------------------
        # CATEGORY 4: Unsigned Employment / Missing Contract Facts
        # -------------------------------------------------------------
        unsigned_signals = [
            "chưa ký hợp đồng", "chưa ký hđlđ", "chưa ký giấy tờ", "chưa ký gì",
            "không ký hợp đồng", "không có hợp đồng", "không ký giấy tờ", "chưa ký gì hết",
        ]
        is_unsigned_query = (
            (issue.contract_status == "UNSIGNED" or any(k in q_lower for k in unsigned_signals))
            and any(k in q_lower for k in ["có sao", "quyền lợi", "được không", "thế nào", "ra sao", "có vi phạm", "bảo vệ"])
            and not any(k in q_lower for k in ["xử phạt", "phạt bao nhiêu", "nghị định 12"])
        )
        if is_unsigned_query:
            has_clarified = facts.get("unsigned_clarified") or facts.get("relationship_clarified")
            if not has_clarified:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="UNSIGNED_EMPLOYMENT_AMBIGUITY",
                    missing_facts=["nature_of_work", "wage_payment_form", "probation_vs_employment"],
                    clarification_question=(
                        "Để xác định chính xác quyền lợi và nghĩa vụ của công ty khi chưa ký hợp đồng bằng văn bản, "
                        "bạn vui lòng cho biết thêm:\n"
                        "1. Bạn và công ty có thỏa thuận miệng về công việc, tiền lương và thời gian làm việc không?\n"
                        "2. Hàng tháng bạn có được trả lương, chấm công và chịu sự quản lý, giám sát trực tiếp không?"
                    ),
                    clarification_options=[
                        "Có thỏa thuận lương, chấm công và nhận lương hàng tháng",
                        "Mới vào làm thử, chưa thỏa thuận cụ thể",
                        "Làm theo việc tự do, không có giờ cố định",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Unsigned employment relationship requires establishing actual labor subordination and wage payment",
                )

        # -------------------------------------------------------------
        # CATEGORY 5: Seasonal / Contract Type Ambiguity
        # -------------------------------------------------------------
        is_seasonal_type_query = (
            any(k in q_lower for k in ["thời vụ", "mùa vụ"])
            and any(k in q_lower for k in ["thuộc loại gì", "loại hợp đồng nào", "là loại gì", "hợp đồng gì", "hợp đồng loại gì"])
        )
        if is_seasonal_type_query:
            has_term = (
                any(k in issue.qualifiers for k in ["contract_indefinite", "contract_definite_12_36_months", "contract_under_12_months"])
                or bool(facts.get("contract_term"))
            )
            if not has_term:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="CONTRACT_TYPE_AMBIGUITY",
                    missing_facts=["contract_duration_type", "agreed_term"],
                    clarification_question=(
                        "Bộ luật Lao động 2019 hiện hành đã bỏ loại 'hợp đồng mùa vụ/thời vụ', "
                        "chỉ còn 02 loại: Hợp đồng xác định thời hạn (tối đa 36 tháng) và Không xác định thời hạn. "
                        "Để xác định công việc thời vụ của bạn thuộc loại hợp đồng nào, bạn vui lòng cho biết "
                        "thời gian công việc mà hai bên đã thỏa thuận:"
                    ),
                    clarification_options=[
                        "Thỏa thuận công việc ngắn hạn dưới 12 tháng",
                        "Thỏa thuận từ 12 đến 36 tháng",
                        "Không thỏa thuận thời hạn cụ thể",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=[],
                    reason="Seasonal work classification depends on agreed duration under Điều 20 BLLĐ 2019",
                )

        # -------------------------------------------------------------
        # CATEGORY 6: Apprenticeship / Vocational Training Ambiguity
        # -------------------------------------------------------------
        is_apprenticeship_query = (
            any(k in q_lower for k in ["học việc", "tập nghề", "học nghề"])
            and any(k in q_lower for k in ["không có lương", "không được đồng nào", "không trả tiền", "không trả lương", "0 đồng", "ko có lương", "không có tiền"])
        )
        if is_apprenticeship_query:
            has_clarified = facts.get("apprenticeship_clarified") or facts.get("direct_labor")
            if not has_clarified:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="APPRENTICESHIP_TRAINING_AMBIGUITY",
                    missing_facts=["training_contract", "work_performance"],
                    clarification_question=(
                        "Theo Điều 61 Bộ luật Lao động, thời hạn tập nghề tối đa không quá 03 tháng và "
                        "nếu người tập nghề trực tiếp tham gia lao động thì phải được trả lương theo thỏa thuận. "
                        "Để xác định việc công ty không trả lương cho bạn có vi phạm hay không, bạn vui lòng cho biết:\n"
                        "1. Trong thời gian học việc, bạn chỉ học lý thuyết/thực hành hay trực tiếp làm ra sản phẩm/doanh thu cho công ty?\n"
                        "2. Hai bên có ký kết hợp đồng đào tạo nghề/tập nghề bằng văn bản không?"
                    ),
                    clarification_options=[
                        "Trực tiếp làm việc, tạo ra sản phẩm/doanh thu cho công ty",
                        "Chỉ quan sát và thực hành học hỏi, không tạo ra sản phẩm",
                        "Có ký hợp đồng đào tạo nghề bằng văn bản",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Legality of unpaid apprenticeship depends on direct labor participation under Điều 61 BLLĐ",
                )

        # -------------------------------------------------------------
        # CATEGORY 7: Probation Duration & Transition (Ambiguous Qualification)
        # -------------------------------------------------------------
        is_sanction_query = (issue.intent == "SANCTION" or any(k in q_lower for k in ["bị phạt", "xử phạt", "phạt bao nhiêu", "nghị định 12"]))
        is_under_1_month = any(k in q_lower for k in ["dưới 01 tháng", "dưới 1 tháng"])
        is_probation = (
            issue.topic == "probation"
            or issue.relationship_type == "PROBATION"
            or facts.get("topic") == "thử việc"
            or facts.get("relationship_type") == "PROBATION"
            or any(k in q_lower for k in ["thử việc 3 tháng", "thử việc 2 tháng", "thử việc 1 tháng"])
        )

        is_probation_duration_query = (
            is_probation
            and not is_sanction_query
            and not is_under_1_month
            and (
                any(k in q_lower for k in ["mấy tháng", "bao lâu", "bao nhiêu ngày", "đúng không", "đúng luật không"])
                or any(k in q_lower for k in ["3 tháng", "2 tháng", "1 tháng", "quá thời gian"])
                or bool(facts.get("probation_clarified"))
                or any(k in q_lower for k in ["thực ra là thử việc", "công ty bảo thử việc", "thử việc trước khi ký", "thử việc 3 tháng"])
            )
            and "probation_salary" not in issue.qualifiers
            and "probation_cancellation" not in issue.qualifiers
        )
        if is_probation_duration_query:
            has_qual = (
                any(k in issue.qualifiers for k in [
                    "probation_enterprise_manager", "probation_college_degree",
                    "probation_intermediate", "probation_other_work"
                ])
                or bool(facts.get("qualification"))
            )
            if not has_qual:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="PROBATION_DURATION_QUALIFICATION_MISSING",
                    missing_facts=["job_qualification_level"],
                    clarification_question=(
                        "Để xác định thời gian thử việc tối đa và tính hợp pháp của tiền lương thử việc theo Điều 25, 26 BLLĐ, "
                        "bạn vui lòng cho biết vị trí công việc của bạn yêu cầu trình độ chuyên môn ở mức nào:"
                    ),
                    clarification_options=[
                        "Người quản lý doanh nghiệp",
                        "Cao đẳng trở lên",
                        "Trung cấp / công nhân kỹ thuật",
                        "Công việc khác",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=["18/VBHN-VPQH#d46", "VBHN_18_2026#d46"],
                    reason="Probation duration strictly depends on job qualification level (Điều 25 BLLĐ)",
                )

        # -------------------------------------------------------------
        # CATEGORY 8: Resignation / Termination Notice Period (Ambiguous Contract Term)
        # -------------------------------------------------------------
        is_no_notice_exception = any(k in q_lower for k in [
            "không cần báo trước", "không phải báo trước", "có cần báo trước",
            "có phải báo trước", "trường hợp nào", "miễn báo trước"
        ])
        is_compensation_query = any(k in q_lower for k in ["bồi thường", "trái pháp luật", "trái luật"])
        is_notice_duration_inquiry = any(k in q_lower for k in [
            "báo trước mấy ngày", "báo trước bao nhiêu ngày", "báo trước bao lâu",
            "cần báo trước bao lâu", "phải báo trước bao lâu", "thời hạn báo trước"
        ])

        is_termination_notice_query = (
            is_notice_duration_inquiry
            and not is_no_notice_exception
            and not is_compensation_query
        )
        if is_termination_notice_query:
            has_term = (
                any(k in issue.qualifiers for k in [
                    "contract_indefinite", "contract_definite_12_36_months",
                    "contract_under_12_months", "special_occupation_notice"
                ])
                or bool(facts.get("contract_term"))
                or bool(facts.get("special_occupation"))
                or any(k in q_lower for k in [
                    "không xác định", "vô thời hạn", "12 tháng", "24 tháng", "36 tháng",
                    "dưới 12 tháng", "1 năm", "2 năm", "3 năm", "thử việc"
                ])
            )
            if not has_term:
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="RESIGNATION_NOTICE_TERM_MISSING",
                    missing_facts=["contract_duration_type", "terminating_party"],
                    clarification_question=(
                        "Thời hạn báo trước khi chấm dứt hợp đồng lao động phụ thuộc vào loại hợp đồng của bạn "
                        "(Điều 35, 36 BLLĐ). Bạn vui lòng cho biết loại hợp đồng lao động đang áp dụng:"
                    ),
                    clarification_options=[
                        "Hợp đồng không xác định thời hạn (báo trước ít nhất 45 ngày)",
                        "Hợp đồng xác định thời hạn 12 - 36 tháng (báo trước ít nhất 30 ngày)",
                        "Hợp đồng xác định thời hạn dưới 12 tháng (báo trước ít nhất 03 ngày làm việc)",
                        "Ngành nghề đặc thù (như tổ lái tàu bay, tiếp viên hàng không)",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=[],
                    reason="Notice period strictly depends on contract duration (Điều 35, 36 BLLĐ)",
                )

        # -------------------------------------------------------------
        # CATEGORY 8B: Resignation without Notice Grounds Missing (Điều 35k2 vs Điều 40 BLLĐ)
        # -------------------------------------------------------------
        is_quit_no_notice = any(k in q_lower for k in [
            "nghỉ ngang", "nghi ngang", "nghỉ việc không báo trước", "nghỉ không báo trước"
        ])
        has_exception_ground = any(k in q_lower for k in [
            "không được trả lương", "không trả đủ lương", "không trả lương", "chậm lương", "nợ lương",
            "ngược đãi", "đánh đập", "nhục mạ", "quấy rối", "mang thai", "ốm đau", "đủ tuổi", "lý do"
        ]) or bool(facts.get("resignation_ground"))
        if is_quit_no_notice and not has_exception_ground:
            return PremiseGateResult(
                is_sufficient=False,
                needs_clarification=True,
                category="RESIGNATION_WITHOUT_NOTICE_GROUNDS_MISSING",
                missing_facts=["resignation_ground"],
                clarification_question=(
                    "Theo Bộ luật Lao động, người lao động chỉ được nghỉ việc không báo trước khi thuộc một trong các trường hợp "
                    "đặc biệt quy định tại Khoản 2 Điều 35 (như bị chậm trả lương, bị ngược đãi, quấy rối tình dục, lao động nữ mang thai...). "
                    "Nếu không thuộc các trường hợp này, việc nghỉ ngang sẽ bị coi là đơn phương chấm dứt hợp đồng trái pháp luật (Điều 39, 40). "
                    "Bạn vui lòng cho biết lý do bạn muốn nghỉ việc không báo trước:"
                ),
                clarification_options=[
                    "Bị công ty chậm trả lương hoặc không trả đủ lương",
                    "Bị người sử dụng lao động ngược đãi, đánh đập, xúc phạm hoặc quấy rối",
                    "Do lý do cá nhân, muốn nghỉ ngay không báo trước",
                    "Lý do khác",
                ],
                forbidden_provisions=[],
                reason="Resignation without notice requires establishing whether statutory exemption grounds under Điều 35k2 apply vs illegal termination under Điều 40",
            )

        # -------------------------------------------------------------
        # CATEGORY 9: Severance Allowance Facts Missing (Điều 46 BLLĐ)
        # -------------------------------------------------------------
        is_severance_general = (
            any(k in q_lower for k in ["trợ cấp thôi việc", "tiền thôi việc"])
            and any(k in q_lower for k in ["có phải trả", "được hưởng không", "có được nhận không", "khi nào được", "điều kiện gì", "có được không", "phải trả không", "có phải trả tiền"])
        )
        if is_severance_general:
            has_duration = (
                any(k in q_lower for k in ["12 tháng", "1 năm", "2 năm", "3 năm", "6 tháng", "dưới 12 tháng"])
                or bool(facts.get("work_duration"))
            )
            has_ground = (
                any(k in q_lower for k in ["hết hạn", "thỏa thuận", "sa thải", "nghỉ hưu", "đơn phương"])
                or bool(facts.get("termination_ground"))
            )
            if not (has_duration and has_ground):
                return PremiseGateResult(
                    is_sufficient=False,
                    needs_clarification=True,
                    category="SEVERANCE_FACTS_MISSING",
                    missing_facts=["employment_duration", "termination_ground"],
                    clarification_question=(
                        "Theo Điều 46 Bộ luật Lao động, trợ cấp thôi việc chỉ áp dụng khi người lao động đã làm việc thường xuyên "
                        "từ đủ 12 tháng trở lên và chấm dứt hợp đồng theo một số trường hợp luật định (hết hạn, thỏa thuận...). "
                        "Để tư vấn chính xác, bạn vui lòng cho biết:\n"
                        "1. Bạn đã làm việc tại công ty được bao lâu (đã đủ 12 tháng chưa)?\n"
                        "2. Lý do hai bên chấm dứt hợp đồng lao động là gì?"
                    ),
                    clarification_options=[
                        "Đã làm việc từ đủ 12 tháng trở lên, hết hạn HĐ hoặc thỏa thuận nghỉ",
                        "Làm việc dưới 12 tháng",
                        "Bị sa thải kỷ luật hoặc tự ý bỏ việc trái luật",
                        "Tôi không rõ",
                    ],
                    forbidden_provisions=[],
                    reason="Severance allowance under Điều 46 requires employment duration >= 12 months and valid termination ground",
                )

        # -------------------------------------------------------------
        # CATEGORY 10: Severance (Điều 46) Protection Gate
        # -------------------------------------------------------------
        forbidden_provisions = []
        is_explicit_severance = any(k in q_lower for k in ["trợ cấp thôi việc", "tiền thôi việc"])
        if not is_explicit_severance:
            # If user didn't explicitly ask for severance allowance, forbid anchoring to Điều 46
            forbidden_provisions.append("18/VBHN-VPQH#d46")
            forbidden_provisions.append("VBHN_18_2026#d46")

        # Sufficient factual grounding
        return PremiseGateResult(
            is_sufficient=True,
            needs_clarification=False,
            category="SUFFICIENT_PREMISE",
            forbidden_provisions=forbidden_provisions,
        )
