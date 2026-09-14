# -*- coding: utf-8 -*-
"""
VietLabor AI - Structured Legal Issue Parser (Phase 5E)
Extracts structured semantic, numeric, categorical, and qualifier representations
from user legal queries to drive deterministic evidence selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set
import unicodedata

from rag.query_router import QueryRouter


@dataclass
class LegalIssue:
    """Structured representation of a discrete legal issue."""
    issue_id: str
    raw_query: str
    topic: str
    actor: str  # "EMPLOYEE" | "EMPLOYER" | "BOTH" | "UNKNOWN"
    intent: str  # "SUBSTANTIVE_RULE" | "SANCTION" | "BOTH" | "CLARIFICATION"
    domain: str = "CORE_LABOR"  # "CORE_LABOR" | "RETIREMENT" | "UNEMPLOYMENT_INSURANCE" | "FOREIGN_WORKER"
    action: Optional[str] = None
    object: Optional[str] = None
    qualifiers: List[str] = field(default_factory=list)
    numbers: List[int] = field(default_factory=list)
    units: List[str] = field(default_factory=list)
    special_conditions: List[str] = field(default_factory=list)

    # Factual state & premise fields (Phase 5F)
    relationship_type: str = "UNKNOWN"  # "EMPLOYMENT" | "PROBATION" | "INTERNSHIP" | "APPRENTICESHIP_TRAINING" | "SERVICE_COLLABORATOR" | "UNKNOWN"
    employment_status: str = "UNKNOWN"  # "ACTUAL_EMPLOYEE" | "TRAINEE" | "INTERN" | "COLLABORATOR" | "UNKNOWN"
    contract_status: str = "UNKNOWN"    # "SIGNED" | "UNSIGNED" | "ORAL" | "UNKNOWN"
    probation_status: str = "UNKNOWN"   # "IN_PROBATION" | "PROBATION_ENDED" | "UNKNOWN"
    internship_status: str = "UNKNOWN"  # "POSSIBLE" | "SCHOOL_PROGRAM" | "COMPANY_DIRECT" | "UNKNOWN"
    payment_issue: bool = False
    material_facts: Dict[str, Any] = field(default_factory=dict)
    missing_material_facts: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "raw_query": self.raw_query,
            "topic": self.topic,
            "domain": self.domain,
            "actor": self.actor,
            "intent": self.intent,
            "action": self.action,
            "object": self.object,
            "qualifiers": self.qualifiers,
            "numbers": self.numbers,
            "units": self.units,
            "special_conditions": self.special_conditions,
            "relationship_type": self.relationship_type,
            "employment_status": self.employment_status,
            "contract_status": self.contract_status,
            "probation_status": self.probation_status,
            "internship_status": self.internship_status,
            "payment_issue": self.payment_issue,
            "material_facts": self.material_facts,
            "missing_material_facts": self.missing_material_facts,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt,
            "clarification_options": self.clarification_options,
        }


class LegalIssueParser:
    """Deterministic parser extracting fine-grained legal qualifiers and numeric thresholds."""

    def __init__(self, router: Optional[QueryRouter] = None):
        self.router = router or QueryRouter()

    def parse(
        self,
        query: str,
        issue_id: str = "I1",
        context_facts: Optional[Dict[str, str]] = None,
    ) -> LegalIssue:
        """Parses a query into a structured LegalIssue."""
        norm_q = unicodedata.normalize("NFC", query).strip()
        q_lower = norm_q.lower()

        # Step 1: Route analysis for high-level actor and intent
        route = self.router.route(norm_q)
        actor = route.actor
        intent = route.legal_intent

        if any(k in q_lower for k in ["công ty đơn phương", "người sử dụng lao động đơn phương", "nsdlđ đơn phương", "doanh nghiệp đơn phương", "công ty muốn sa thải", "công ty có quyền", "công ty"]):
            actor = "EMPLOYER"
        elif any(k in q_lower for k in ["người lao động muốn nghỉ", "người lao động đơn phương", "nld muốn nghỉ", "người lao động"]):
            actor = "EMPLOYEE"

        # Step 2: Extract numeric values and paired units
        numbers: List[int] = []
        units: List[str] = []

        # Find numbers
        num_matches = re.findall(r"\b(\d+)\b", q_lower)
        for m in num_matches:
            try:
                numbers.append(int(m))
            except ValueError:
                pass

        # Find units
        if any(u in q_lower for u in ["ngày", "ngay"]):
            units.append("ngày")
        if any(u in q_lower for u in ["tháng", "thang"]):
            units.append("tháng")
        if any(u in q_lower for u in ["năm", "nam"]):
            units.append("năm")
        if any(u in q_lower for u in ["giờ", "tiếng", "gio"]):
            units.append("giờ")
        if "%" in q_lower or "phần trăm" in q_lower:
            units.append("%")
        if any(u in q_lower for u in ["triệu", "nghìn", "tỷ", "vnd"]) or re.search(r"\b\d+\s*đồng\b", q_lower):
            units.append("đồng")

        # Step 3: Extract domain qualifiers
        topic = "general"
        action = "general"
        obj = "general"
        qualifiers: List[str] = []
        special_conditions: List[str] = []

        # Phase 5G Domain extraction
        issue_domain = getattr(route, "domain", "CORE_LABOR")
        if issue_domain == "CROSS_DOMAIN":
            if any(k in q_lower for k in ["thất nghiệp", "bhtn", "việc làm", "374/2025", "74/2025"]):
                issue_domain = "UNEMPLOYMENT_INSURANCE"
            elif any(k in q_lower for k in ["hưu", "nghỉ hưu", "tuổi hưu", "135/2020"]):
                issue_domain = "RETIREMENT"
            elif any(k in q_lower for k in ["nước ngoài", "work permit", "giấy phép lao động", "219/2025"]):
                issue_domain = "FOREIGN_WORKER"
            else:
                issue_domain = "CORE_LABOR"

        # Retirement Topics
        if issue_domain == "RETIREMENT" or any(k in q_lower for k in ["nghỉ hưu", "tuổi hưu", "hưu trí", "135/2020"]):
            topic = "retirement"
            issue_domain = "RETIREMENT"
            obj = "retirement_age"
            qualifiers.append("retirement")
            if any(k in q_lower for k in ["sớm", "nặng nhọc", "độc hại", "suy giảm"]):
                qualifiers.append("early_retirement")
            if any(k in q_lower for k in ["lộ trình", "năm 20", "bao giờ", "khi nào"]):
                qualifiers.append("retirement_roadmap")

        # Unemployment Insurance Topics
        elif issue_domain == "UNEMPLOYMENT_INSURANCE" or any(k in q_lower for k in ["thất nghiệp", "bhtn", "trợ cấp thất nghiệp"]):
            topic = "unemployment_insurance"
            issue_domain = "UNEMPLOYMENT_INSURANCE"
            obj = "unemployment_allowance"
            qualifiers.append("unemployment_insurance")
            if any(k in q_lower for k in ["hồ sơ", "thủ tục", "nộp"]):
                qualifiers.append("unemployment_dossier")
            if any(k in q_lower for k in ["mức hưởng", "bao nhiêu %", "mấy tháng"]):
                qualifiers.append("unemployment_rate")
            if any(k in q_lower for k in ["điều kiện"]):
                qualifiers.append("unemployment_conditions")

        # Foreign Worker Topics
        elif issue_domain == "FOREIGN_WORKER" or any(k in q_lower for k in ["người nước ngoài", "work permit", "giấy phép lao động", "gplđ", "219/2025"]):
            topic = "foreign_worker"
            issue_domain = "FOREIGN_WORKER"
            obj = "work_permit"
            qualifiers.append("foreign_worker")
            if any(k in q_lower for k in ["miễn", "không thuộc diện", "kết hôn"]):
                qualifiers.append("work_permit_exemption")
            if any(k in q_lower for k in ["thời hạn", "bao lâu", "mấy năm"]):
                qualifiers.append("work_permit_duration")
            if any(k in q_lower for k in ["chuyên gia", "lao động kỹ thuật", "giám đốc"]):
                qualifiers.append("foreign_worker_qualifications")

        # Probation Topics
        elif any(k in q_lower for k in ["thử việc", "thu viec", "hợp đồng thử việc"]):
            topic = "probation"
            qualifiers.append("probation")
            obj = "probation_agreement"
            if any(k in q_lower for k in ["dưới 01 tháng", "dưới 1 tháng"]):
                qualifiers.append("probation_under_1_month_prohibited")
            if any(k in q_lower for k in ["hủy bỏ", "huy bo", "chấm dứt"]):
                action = "probation_cancellation"
                qualifiers.append("probation_cancellation")
            if any(k in q_lower for k in ["không cần báo trước", "không phải báo trước", "khong bao truoc"]):
                qualifiers.append("no_notice_required")
            if any(k in q_lower for k in ["không phải bồi thường", "khong boi thuong"]):
                qualifiers.append("no_compensation")
            if any(k in q_lower for k in ["người quản lý doanh nghiệp", "quản lý doanh nghiệp", "giám đốc"]):
                qualifiers.append("probation_enterprise_manager")
            elif any(k in q_lower for k in ["cao đẳng", "đại học", "kỹ sư", "cử nhân", "chuyên viên"]):
                qualifiers.append("probation_college_degree")
            elif any(k in q_lower for k in ["trung cấp", "công nhân kỹ thuật", "nghiệp vụ"]):
                qualifiers.append("probation_intermediate")
            elif any(k in q_lower for k in ["công việc khác", "lao động phổ thông"]):
                qualifiers.append("probation_other_work")
            if any(k in q_lower for k in ["lương", "tiền lương", "bao nhiêu %", "mức lương"]):
                action = "probation_salary"
                qualifiers.append("probation_salary")
            if any(k in q_lower for k in ["bhxh", "bảo hiểm", "bảo hiểm xã hội"]):
                qualifiers.append("probation_social_insurance")
            if any(k in q_lower for k in ["thông báo", "kết quả", "kết thúc", "kéo dài", "hết thời gian thử việc", "ký hợp đồng"]):
                qualifiers.append("probation_conclusion")

        # Wage and Salary Topics
        if any(k in q_lower for k in ["lương", "luong", "tiền lương"]):
            if topic == "general":
                topic = "salary"
            obj = "salary"

            # Wage deductions (Điều 102)
            if any(k in q_lower for k in ["khấu trừ", "khau tru", "trừ lương", "tru luong"]):
                action = "wage_deduction"
                qualifiers.append("wage_deduction")
                if any(k in q_lower for k in ["mức khấu trừ", "tối đa", "bao nhiêu %", "không quá bao nhiêu"]):
                    qualifiers.append("wage_deduction_limit")
                elif any(k in q_lower for k in ["trường hợp nào", "khi nào", "được khấu trừ không", "có được khấu trừ"]):
                    qualifiers.append("deduction_substantive_grounds")
                if any(k in q_lower for k in ["bồi thường thiệt hại", "hư hỏng", "tai san"]):
                    qualifiers.append("property_damage_compensation")

            # Delayed salary payment & interest (Điều 97)
            if any(k in q_lower for k in ["chậm trả lương", "chậm lương", "cham tra luong", "chậm trả"]):
                action = "delayed_salary"
                qualifiers.append("delayed_salary")
                if any(k in q_lower for k in ["15 ngày", "trên 15 ngày", "từ 15 ngày"]):
                    qualifiers.append("delay_over_15_days")
                if any(k in q_lower for k in ["tiền lãi", "lãi suất", "đền bù"]):
                    qualifiers.append("delayed_interest_compensation")

            # Overtime pay rate (Điều 98)
            if any(k in q_lower for k in ["làm thêm", "tăng ca", "đi làm ngày nghỉ", "làm việc vào ngày", "làm ngày lễ", "làm ngày tết", "làm ngày chủ nhật"]):
                action = "overtime_pay_rate"
                qualifiers.append("overtime_pay_rate")
                if any(k in q_lower for k in ["ngày thường", "ngay thuong"]):
                    qualifiers.append("overtime_normal_day")
                elif any(k in q_lower for k in ["nghỉ hàng tuần", "nghỉ hằng tuần", "cuối tuần", "chủ nhật"]):
                    qualifiers.append("overtime_weekly_rest_day")
                elif any(k in q_lower for k in ["ngày lễ", "ngay le", "tết"]):
                    qualifiers.append("overtime_holiday_tet")

        # Bonus / Tết Bonus (Điều 104)
        if any(k in q_lower for k in ["tiền thưởng", "thưởng tết", "quy chế thưởng", "trả thưởng"]):
            topic = "salary"
            action = "bonus"
            qualifiers.append("bonus_regulation")

        # Public holiday leave (Điều 112)
        if any(k in q_lower for k in ["nghỉ lễ", "nghỉ tết", "ngày lễ, tết", "ngày lễ tết", "bao nhiêu ngày lễ", "bao nhiêu ngày nghỉ lễ"]) and "làm thêm" not in q_lower and "tăng ca" not in q_lower:
            topic = "leave"
            action = "public_holiday_leave"
            qualifiers.append("public_holiday_leave")

        # Normal Working Hours (Điều 105) vs Night work (Điều 106) vs Overtime Limits (Điều 107)
        if any(k in q_lower for k in ["thời giờ làm việc", "giờ làm việc bình thường", "làm việc bình thường"]):
            if "làm thêm" not in q_lower and "tăng ca" not in q_lower:
                topic = "working_hours"
                action = "normal_working_hours"
                qualifiers.append("normal_working_hours")
            if any(k in q_lower for k in ["theo tuần", "trong tuần", "một tuần", "01 tuần"]):
                qualifiers.append("normal_hours_week_limit")
            elif any(k in q_lower for k in ["một ngày", "01 ngày", "trong ngày"]):
                qualifiers.append("normal_hours_day_limit")
            if any(k in q_lower for k in ["rút ngắn", "rut ngan", "giảm giờ", "giam gio", "độc hại", "nặng nhọc"]):
                qualifiers.append("working_hours_reduction")

        if any(k in q_lower for k in ["ban đêm", "giờ làm việc ban đêm", "tính từ mấy giờ"]):
            if any(k in q_lower for k in ["lương", "trả thêm", "%", "bao nhiêu %"]):
                topic = "salary"
                action = "night_work_salary"
                qualifiers.append("night_work_salary_rate")
            else:
                topic = "working_hours"
                action = "night_work_hours"
                qualifiers.append("night_work_hours")

        if any(k in q_lower for k in ["làm thêm", "lam them", "tăng ca", "tang ca", "giờ làm thêm"]) and "overtime_pay_rate" not in qualifiers:
            topic = "overtime"
            action = "overtime_limit"
            qualifiers.append("overtime")
            if any(k in q_lower for k in ["trong một ngày", "trong 01 ngày", "một ngày", "theo ngày", "mỗi ngày"]):
                qualifiers.append("temporal_limit_day")
            if any(k in q_lower for k in ["trong một tháng", "trong 01 tháng", "một tháng", "theo tháng", "mỗi tháng"]):
                qualifiers.append("temporal_limit_month")
            if any(k in q_lower for k in ["trong một năm", "trong 01 năm", "một năm", "theo năm", "mỗi năm"]):
                qualifiers.append("temporal_limit_year")
            if any(k in q_lower for k in ["đồng ý", "ép", "bắt", "ép làm thêm"]):
                qualifiers.append("employee_consent_required")

        # Contract definition & types (Điều 13, 20)
        if any(k in q_lower for k in ["hợp đồng lao động", "hđlđ", "hợp đồng xác định thời hạn", "hợp đồng không xác định"]):
            if topic == "general":
                topic = "contract"
            if any(k in q_lower for k in ["là gì", "khái niệm", "thế nào là"]):
                action = "contract_definition"
                qualifiers.append("contract_definition")
            if any(k in q_lower for k in ["mấy loại", "các loại", "phân loại"]):
                action = "contract_types"
                qualifiers.append("contract_types")
            if any(k in q_lower for k in ["hết hạn", "tiếp tục làm việc", "chuyển thành", "xử lý thế nào"]):
                action = "contract_renewal_clause2"
                qualifiers.append("contract_renewal_clause2")
                qualifiers.append("contract_auto_indefinite_b")

        # Contract duration / term in query
        if any(k in q_lower for k in ["dưới 12 tháng", "dưới 1 năm", "dưới 01 năm", "ít hơn 12 tháng"]):
            qualifiers.append("contract_under_12_months")
        else:
            m_term = re.search(r"(\d+)\s*(năm|tháng)", q_lower)
            if m_term:
                num = int(m_term.group(1))
                unit = m_term.group(2)
                months = num * 12 if unit == "năm" else num
                if months >= 12:
                    qualifiers.append("contract_definite_12_36_months")
                else:
                    qualifiers.append("contract_under_12_months")
        if "không xác định thời hạn" in q_lower or "vô thời hạn" in q_lower:
            qualifiers.append("contract_indefinite")

        # Personal leave with pay (Điều 115)
        if any(k in q_lower for k in ["kết hôn", "lấy vợ", "lấy chồng"]):
            topic = "personal_leave"
            action = "marriage_leave"
            qualifiers.append("marriage_leave_paid")

        # Administrative Sanctions Specifics (Nghị định 12/2022)
        if any(k in q_lower for k in ["12/2022", "nghị định 12", "phạt tiền bao nhiêu", "bị phạt bao nhiêu"]):
            if any(k in q_lower for k in ["văn bằng", "bằng gốc", "giấy tờ", "bản chính"]):
                qualifiers.append("sanction_withholding_diploma")
            if any(k in q_lower for k in ["thử việc quá thời gian", "quá thời gian"]):
                qualifiers.append("sanction_probation_overtime")
            if any(k in q_lower for k in ["phạt tiền", "cắt lương", "thay xử lý kỷ luật", "thay kỷ luật"]):
                qualifiers.append("sanction_monetary_fine_discipline")

        # Post-termination settlement obligation (Điều 48)
        if any(k in q_lower for k in ["chấm dứt hợp đồng", "nghỉ việc", "thôi việc"]) and any(k in q_lower for k in ["thanh toán", "không trả lương", "trả lương tháng cuối", "14 ngày", "bao nhiêu ngày", "trách nhiệm thanh toán"]):
            qualifiers.append("termination_settlement_obligation")

        # Annual leave & Cash-out (Điều 113)
        if any(k in q_lower for k in ["phép năm", "nghỉ hằng năm", "nghỉ phép", "nghi phep", "ngày phép"]):
            topic = "annual_leave"
            obj = "annual_leave"
            if any(k in q_lower for k in ["thôi việc", "nghỉ việc", "mất việc"]) and any(k in q_lower for k in ["chưa nghỉ hết", "chưa nghỉ", "thanh toán"]):
                action = "leave_cashout_on_termination"
                qualifiers.append("leave_cashout_on_termination")

        # Hazard Categorization (Crucial discriminator between 14 vs 16 days, normal hazard vs especially hazardous)
        has_dac_biet = any(k in q_lower for k in ["đặc biệt nặng nhọc", "dac biet nang nhoc", "đặc biệt độc hại", "đặc biệt nguy hiểm"])
        has_nang_nhoc = any(k in q_lower for k in ["nặng nhọc", "nang nhoc", "độc hại", "doc hai", "nguy hiểm"])

        if has_dac_biet:
            qualifiers.append("category_especially_hazardous")
        elif has_nang_nhoc:
            qualifiers.append("category_hazardous_normal")

        # Deposit and Document Withholding (Điều 17 BLLĐ vs NĐ 12)
        if any(k in q_lower for k in ["đặt cọc", "thế chấp", "tiền cọc", "tiền bảo đảm", "giữ bằng", "giữ căn cước", "giấy tờ tùy thân"]):
            topic = "contract"
            action = "prohibited_acts_contract"
            qualifiers.append("prohibited_deposit_or_withholding")
            if any(k in q_lower for k in ["đặt cọc", "thế chấp", "tiền bảo đảm"]):
                qualifiers.append("money_deposit_security")
            if any(k in q_lower for k in ["bằng", "văn bằng", "chứng chỉ", "căn cước", "giấy tờ"]):
                qualifiers.append("original_document_withholding")

        # Special Occupation Resignation (Điều 35k1d + NĐ 145 Điều 7)
        if any(k in q_lower for k in ["tổ lái", "tàu bay", "phi công", "tiếp viên hàng không", "ngành nghề đặc thù"]):
            special_conditions.append("flight_crew")
            qualifiers.append("special_occupation_notice")

        # Maternity & Female employees (Điều 122, 137)
        if any(k in q_lower for k in ["mang thai", "thai sản", "nuôi con dưới 12 tháng"]):
            special_conditions.append("female_maternity")
            qualifiers.append("female_maternity_protection")
            if any(k in q_lower for k in ["tháng thứ 7", "tháng thứ 07", "7 tháng"]):
                qualifiers.append("pregnancy_month_7")
            if any(k in q_lower for k in ["sa thải", "kỷ luật"]):
                qualifiers.append("no_discipline_maternity")

        # Discipline forms & monetary penalties (Điều 124, 127)
        if any(k in q_lower for k in ["hình thức kỷ luật", "kỷ luật lao động"]):
            topic = "discipline"
            qualifiers.append("discipline_forms")
        if any(k in q_lower for k in ["bao nhiêu hình thức", "các hình thức kỷ luật"]):
            qualifiers.append("discipline_forms_enumeration")
        if any(k in q_lower for k in ["nhiều hình thức", "một hành vi", "nguyên tắc xử lý kỷ luật"]):
            qualifiers.append("discipline_principles")
        if any(k in q_lower for k in ["tự ý bỏ việc", "tu y bo viec"]):
            qualifiers.append("job_abandonment_dismissal")
        if any(k in q_lower for k in ["phạt tiền", "trừ lương thay kỷ luật", "cắt lương thay"]):
            topic = "discipline"
            action = "prohibited_monetary_fine"
            qualifiers.append("prohibited_monetary_fine")

        # Step 4: Context facts enrichment
        if context_facts:
            qual = context_facts.get("qualification")
            if qual:
                if any(k in qual.lower() for k in ["cao đẳng", "đại học"]):
                    qualifiers.append("probation_college_degree")
                elif "trung cấp" in qual.lower():
                    qualifiers.append("probation_intermediate")
                elif "quản lý" in qual.lower():
                    qualifiers.append("probation_enterprise_manager")
                elif "công việc khác" in qual.lower() or "phổ thông" in qual.lower():
                    qualifiers.append("probation_other_work")
            term = context_facts.get("contract_term")
            if term:
                term_str = str(term).lower()
                if any(k in term_str for k in ["dưới", "ít hơn"]):
                    qualifiers.append("contract_under_12_months")
                else:
                    m_term = re.search(r"(\d+)\s*(năm|tháng)", term_str)
                    if m_term:
                        num = int(m_term.group(1))
                        unit = m_term.group(2)
                        months = num * 12 if unit == "năm" else num
                        if months >= 12:
                            qualifiers.append("contract_definite_12_36_months")
                        else:
                            qualifiers.append("contract_under_12_months")
                    elif any(k in term_str for k in ["12", "36", "12 tháng", "36 tháng", "2 năm", "1 năm", "3 năm"]):
                        qualifiers.append("contract_definite_12_36_months")
                    elif "không xác định" in term_str:
                        qualifiers.append("contract_indefinite")
            if context_facts.get("special_occupation"):
                special_conditions.append("flight_crew")
                qualifiers.append("special_occupation_notice")

        # Step 5: Generic Factual State Extraction (Phase 5F)
        relationship_type = "UNKNOWN"
        employment_status = "UNKNOWN"
        contract_status = "UNKNOWN"
        probation_status = "UNKNOWN"
        internship_status = "UNKNOWN"
        payment_issue = False
        material_facts: Dict[str, Any] = {}

        # 1. Payment issue detection
        if any(k in q_lower for k in [
            "không được trả", "không có lương", "chậm trả lương", "nợ lương", "quỵt lương",
            "không trả lương", "khấu trừ", "cắt lương", "trừ lương", "0 đồng", "không có đồng nào"
        ]):
            payment_issue = True
            material_facts["has_payment_dispute"] = True

        # 2. Contract status detection
        if any(k in q_lower for k in [
            "chưa ký hợp đồng", "không ký hợp đồng", "không ký giấy tờ", "chưa ký gì",
            "làm không giấy tờ", "không có hợp đồng", "chưa có hợp đồng"
        ]):
            contract_status = "UNSIGNED"
            material_facts["contract_status"] = "UNSIGNED"
        elif any(k in q_lower for k in [
            "đã ký hợp đồng", "hợp đồng xác định thời hạn", "hợp đồng không xác định",
            "ký hợp đồng", "hợp đồng 2 năm", "hợp đồng 1 năm", "hợp đồng 3 năm"
        ]):
            contract_status = "SIGNED"
            material_facts["contract_status"] = "SIGNED"

        # 3. Work duration facts
        m_dur = re.search(r"(\d+)\s*(tháng|năm|tuần|ngày)", q_lower)
        if m_dur:
            material_facts["duration_number"] = int(m_dur.group(1))
            material_facts["duration_unit"] = m_dur.group(2)

        # 4. Actual work characteristics (subordination, hours, management)
        has_subordination = any(k in q_lower for k in [
            "chấm công", "8 tiếng", "8 giờ", "giờ làm cố định", "quản lý", "giao việc",
            "như nhân viên", "kpi", "nội quy", "theo ca"
        ])
        if has_subordination:
            material_facts["has_subordination"] = True

        # 5. Relationship / Arrangement classification
        if any(k in q_lower for k in ["thực tập", "sinh viên thực tập", "thực tập sinh"]):
            internship_status = "POSSIBLE"
            material_facts["claimed_label"] = "internship"
            if any(k in q_lower for k in ["trường", "đại học", "giấy giới thiệu", "thỏa thuận thực tập", "đồ án"]):
                internship_status = "SCHOOL_PROGRAM"
                relationship_type = "INTERNSHIP"
                material_facts["internship_type"] = "SCHOOL_PROGRAM"
            elif has_subordination or (m_dur and int(m_dur.group(1)) >= 3 and m_dur.group(2) == "tháng"):
                internship_status = "COMPANY_DIRECT"
                relationship_type = "UNKNOWN"
                material_facts["internship_type"] = "COMPANY_DIRECT"
            else:
                relationship_type = "UNKNOWN"
        elif any(k in q_lower for k in ["học việc", "tập nghề"]):
            relationship_type = "APPRENTICESHIP_TRAINING"
            employment_status = "TRAINEE"
            material_facts["claimed_label"] = "apprenticeship"
        elif any(k in q_lower for k in ["cộng tác viên", "ctv", "freelance"]):
            material_facts["claimed_label"] = "collaborator"
            if has_subordination:
                relationship_type = "UNKNOWN"
            else:
                relationship_type = "SERVICE_COLLABORATOR"
        elif any(k in q_lower for k in ["thử việc", "làm thử"]):
            probation_status = "IN_PROBATION"
            material_facts["claimed_label"] = "probation"
            if relationship_type == "UNKNOWN":
                relationship_type = "PROBATION"
        elif any(k in q_lower for k in ["nhân viên chính thức", "hợp đồng lao động", "người lao động"]):
            if relationship_type == "UNKNOWN":
                relationship_type = "EMPLOYMENT"
                employment_status = "ACTUAL_EMPLOYEE"

        # 6. Context facts integration (user's explicit answers in subsequent turns)
        if context_facts:
            material_facts.update(context_facts)
            if context_facts.get("school_program") or any(k in str(context_facts).lower() for k in ["trường", "giấy giới thiệu"]):
                internship_status = "SCHOOL_PROGRAM"
                relationship_type = "INTERNSHIP"
            if context_facts.get("de_facto_employee") or any(k in str(context_facts).lower() for k in ["công ty tự tuyển", "như nhân viên", "8 tiếng", "8 giờ"]):
                relationship_type = "EMPLOYMENT"
                employment_status = "ACTUAL_EMPLOYEE"
            if context_facts.get("probation_clarified") or "thử việc" in str(context_facts.get("topic", "")).lower():
                relationship_type = "PROBATION"
                probation_status = "IN_PROBATION"

        return LegalIssue(
            issue_id=issue_id,
            raw_query=norm_q,
            topic=topic,
            domain=issue_domain,
            actor=actor,
            intent=intent,
            action=action,
            object=obj,
            qualifiers=qualifiers,
            numbers=numbers,
            units=units,
            special_conditions=special_conditions,
            relationship_type=relationship_type,
            employment_status=employment_status,
            contract_status=contract_status,
            probation_status=probation_status,
            internship_status=internship_status,
            payment_issue=payment_issue,
            material_facts=material_facts,
        )
