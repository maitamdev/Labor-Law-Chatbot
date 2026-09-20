# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H.1 Legal Benefit Calculation Engine
rag/legal_calculator.py

Deterministic calculation engine derived strictly from canonical legal provisions:
1. Chế độ thai sản (Maternity Benefit):
   - Điều 38, 39 Luật BHXH (58/VBHN-VPQH)
2. Chế độ ốm đau (Sickness Benefit):
   - Điều 26, 28 Luật BHXH (58/VBHN-VPQH) & TT 12/2025/TT-BNV
3. BHXH một lần (Lump-sum Social Insurance):
   - Điều 70 Luật BHXH (58/VBHN-VPQH) & Điều 19 NĐ 158/2025/NĐ-CP
4. Chế độ hưu trí (Pension Benefit):
   - Điều 64, 65, 66 Luật BHXH (58/VBHN-VPQH) & Điều 169 Bộ luật Lao động
5. Bồi thường TNLĐ từ người sử dụng lao động (Employer Accident Compensation):
   - Điều 38, 39 Luật ATVSLĐ (84/2015/QH13) & Điều 3 06/VBHN-BNV (2026)
6. Trợ cấp TNLĐ từ Quỹ bảo hiểm TNLĐ-BNN (Insurance Fund Accident Benefit):
   - Điều 48, 49 Luật ATVSLĐ (84/2015/QH13) & 04/VBHN-BNV (2026)
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, List, Optional


# Current statutory reference base salary (mức tham chiếu / mức lương cơ sở hiện hành)
CURRENT_REFERENCE_SALARY = 2_340_000  # VND


@dataclass
class FormulaMetadata:
    """Formal metadata registry for statutory benefit formulas."""
    formula_id: str
    domain: str
    legal_source: str
    article: str
    clause: str
    effective_from: str
    effective_to: Optional[str]
    applicability_conditions: str
    required_inputs: List[str]
    formula: str
    rounding_rule: str


FORMULA_REGISTRY: Dict[str, FormulaMetadata] = {
    "SICKNESS_STANDARD_75": FormulaMetadata(
        formula_id="SICKNESS_STANDARD_75",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 28",
        clause="Khoản 1",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Nghỉ việc do ốm đau thông thường trong giới hạn ngày quy định tại Điều 26",
        required_inputs=["preceding_salary", "sick_days"],
        formula="Tổng tiền = (Tiền lương tháng đóng BHXH liền kề * 75% / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "SICKNESS_LONGTERM_65": FormulaMetadata(
        formula_id="SICKNESS_LONGTERM_65",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 28",
        clause="Khoản 2 Điểm a",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Bệnh dài ngày điều trị quá 180 ngày và có thời gian đóng BHXH từ đủ 30 năm trở lên",
        required_inputs=["preceding_salary", "sick_days", "contribution_years"],
        formula="Tổng tiền = (Tiền lương tháng đóng BHXH liền kề * 65% / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "SICKNESS_LONGTERM_55": FormulaMetadata(
        formula_id="SICKNESS_LONGTERM_55",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 28",
        clause="Khoản 2 Điểm b",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Bệnh dài ngày điều trị quá 180 ngày và có thời gian đóng BHXH từ đủ 15 năm đến dưới 30 năm",
        required_inputs=["preceding_salary", "sick_days", "contribution_years"],
        formula="Tổng tiền = (Tiền lương tháng đóng BHXH liền kề * 55% / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "SICKNESS_LONGTERM_50": FormulaMetadata(
        formula_id="SICKNESS_LONGTERM_50",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 28",
        clause="Khoản 2 Điểm c",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Bệnh dài ngày điều trị quá 180 ngày và có thời gian đóng BHXH dưới 15 năm",
        required_inputs=["preceding_salary", "sick_days", "contribution_years"],
        formula="Tổng tiền = (Tiền lương tháng đóng BHXH liền kề * 50% / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "SICKNESS_ARMED_FORCES_100": FormulaMetadata(
        formula_id="SICKNESS_ARMED_FORCES_100",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 28",
        clause="Khoản 1",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Sĩ quan, quân nhân chuyên nghiệp, công an nhân dân thuộc diện hưởng 100% lương",
        required_inputs=["preceding_salary", "sick_days"],
        formula="Tổng tiền = (Tiền lương tháng đóng BHXH liền kề * 100% / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "MATERNITY_STANDARD": FormulaMetadata(
        formula_id="MATERNITY_STANDARD",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 38, 39",
        clause="Khoản 1 Điều 39 & Điều 38",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Lao động nữ sinh con đóng đủ từ 6 tháng BHXH trong 12 tháng trước sinh",
        required_inputs=["avg_salary_6m", "leave_months", "children_count"],
        formula="Tổng tiền = (100% * Lương BQ 6 tháng * Số tháng nghỉ) + (2.0 * Mức tham chiếu * Số con)",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "MATERNITY_UNDER_6M": FormulaMetadata(
        formula_id="MATERNITY_UNDER_6M",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 39",
        clause="Khoản 1 Điểm a",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Người lao động đóng BHXH chưa đủ 6 tháng (thuộc trường hợp đặc thù theo quy định)",
        required_inputs=["avg_salary_contributed", "leave_months"],
        formula="Trợ cấp thai sản = Lương bình quân các tháng đã đóng * Số tháng nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "MATERNITY_PATERNITY": FormulaMetadata(
        formula_id="MATERNITY_PATERNITY",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 34, 39",
        clause="Khoản 2 Điều 34 & Khoản 1 Điểm b Điều 39",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Lao động nam có vợ sinh con đang tham gia BHXH (nghỉ 5/7/10/14 ngày trong vòng 30 ngày)",
        required_inputs=["avg_salary_6m", "paternity_days"],
        formula="Trợ cấp thai sản nam = (Lương BQ 6 tháng / 24) * Số ngày nghỉ",
        rounding_rule="Làm tròn đến hàng đơn vị VNĐ",
    ),
    "LUMP_SUM_BHXH_STANDARD": FormulaMetadata(
        formula_id="LUMP_SUM_BHXH_STANDARD",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH & NĐ 158/2025/NĐ-CP",
        article="Điều 70 58/VBHN-VPQH & Điều 19 NĐ 158",
        clause="Khoản 2 Điều 70",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Người lao động đủ điều kiện hưởng BHXH một lần theo Khoản 1 Điều 70",
        required_inputs=["avg_salary", "years_before_2014", "years_from_2014"],
        formula="BHXH một lần = Lương BQ * (1.5 * số năm trước 2014 + 2.0 * số năm từ 2014)",
        rounding_rule="Tháng lẻ: 1-6 tháng = 0.5 năm; 7-11 tháng = 1.0 năm",
    ),
    "PENSION_FEMALE_STANDARD": FormulaMetadata(
        formula_id="PENSION_FEMALE_STANDARD",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 64, Điều 66",
        clause="Khoản 1 Điểm a Điều 66",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Lao động nữ đủ tuổi Điều 169 BLLĐ và có đủ từ 15 năm đóng BHXH trở lên",
        required_inputs=["avg_salary", "contribution_years"],
        formula="Tỷ lệ = 45% (15 năm đầu) + 2% * (số năm - 15), tối đa 75%. Lương hưu = Tỷ lệ * Lương BQ",
        rounding_rule="Tỷ lệ tối đa 75%",
    ),
    "PENSION_MALE_STANDARD": FormulaMetadata(
        formula_id="PENSION_MALE_STANDARD",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 64, Điều 66",
        clause="Khoản 1 Điểm b Điều 66",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Lao động nam đủ tuổi Điều 169 BLLĐ và có đủ từ 20 năm đóng BHXH trở lên",
        required_inputs=["avg_salary", "contribution_years"],
        formula="Tỷ lệ = 45% (20 năm đầu) + 2% * (số năm - 20), tối đa 75%. Lương hưu = Tỷ lệ * Lương BQ",
        rounding_rule="Tỷ lệ tối đa 75%",
    ),
    "PENSION_MALE_15_TO_20Y": FormulaMetadata(
        formula_id="PENSION_MALE_15_TO_20Y",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 64, Điều 66",
        clause="Khoản 1 Điểm b Điều 66",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Lao động nam đủ tuổi Điều 169 BLLĐ và có từ đủ 15 năm đến dưới 20 năm đóng BHXH",
        required_inputs=["avg_salary", "contribution_years"],
        formula="Tỷ lệ = 40% (15 năm đầu) + 2.25% * (số năm - 15). Lương hưu = Tỷ lệ * Lương BQ",
        rounding_rule="Tỷ lệ phần trăm làm tròn 2 chữ số thập phân",
    ),
    "PENSION_EARLY_IMPAIRMENT": FormulaMetadata(
        formula_id="PENSION_EARLY_IMPAIRMENT",
        domain="SOCIAL_INSURANCE",
        legal_source="58/VBHN-VPQH (Luật BHXH)",
        article="Điều 65, Điều 66",
        clause="Khoản 2 Điều 66",
        effective_from="2025-07-01",
        effective_to=None,
        applicability_conditions="Nghỉ hưu trước tuổi do suy giảm KNLĐ từ 61% trở lên, có đủ từ 20 năm đóng BHXH",
        required_inputs=["avg_salary", "contribution_years", "years_early"],
        formula="Tỷ lệ sau giảm = Tỷ lệ chuẩn - (2% * số năm nghỉ sớm). Lẻ đến 6 tháng giảm 1%, trên 6 tháng không giảm",
        rounding_rule="Giảm 2%/năm",
    ),
    "EMPLOYER_ACCIDENT_5_TO_10": FormulaMetadata(
        formula_id="EMPLOYER_ACCIDENT_5_TO_10",
        domain="OCCUPATIONAL_SAFETY",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 06/BNV",
        article="Điều 38",
        clause="Khoản 4 Điểm a",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="Suy giảm KNLĐ từ 5% đến 10% do tai nạn lao động thuộc trách nhiệm NSDLĐ",
        required_inputs=["monthly_salary", "impairment_percent"],
        formula="Bồi thường = Ít nhất 1.5 tháng tiền lương hợp đồng",
        rounding_rule="Hệ số cố định 1.5 tháng lương",
    ),
    "EMPLOYER_ACCIDENT_11_TO_80": FormulaMetadata(
        formula_id="EMPLOYER_ACCIDENT_11_TO_80",
        domain="OCCUPATIONAL_SAFETY",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 06/BNV",
        article="Điều 38",
        clause="Khoản 4 Điểm a",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="Suy giảm KNLĐ từ 11% đến 80% do tai nạn lao động thuộc trách nhiệm NSDLĐ",
        required_inputs=["monthly_salary", "impairment_percent"],
        formula="Bồi thường = [1.5 + (Tỷ lệ suy giảm - 10) * 0.4] * Tiền lương tháng",
        rounding_rule="Mỗi 1% tăng thêm cộng 0.4 tháng lương",
    ),
    "EMPLOYER_ACCIDENT_81_PLUS": FormulaMetadata(
        formula_id="EMPLOYER_ACCIDENT_81_PLUS",
        domain="OCCUPATIONAL_SAFETY",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 06/BNV",
        article="Điều 38",
        clause="Khoản 4 Điểm b",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="Suy giảm KNLĐ từ 81% trở lên hoặc chết do TNLĐ thuộc trách nhiệm NSDLĐ",
        required_inputs=["monthly_salary"],
        formula="Bồi thường = Ít nhất 30.0 tháng tiền lương hợp đồng",
        rounding_rule="Hệ số tối thiểu 30 tháng lương",
    ),
    "EMPLOYER_ACCIDENT_FAULT": FormulaMetadata(
        formula_id="EMPLOYER_ACCIDENT_FAULT",
        domain="OCCUPATIONAL_SAFETY",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 06/BNV",
        article="Điều 39",
        clause="Khoản 1",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="TNLĐ xảy ra hoàn toàn do lỗi của chính người lao động",
        required_inputs=["monthly_salary", "impairment_percent"],
        formula="Trợ cấp = Ít nhất 40% của mức bồi thường tương ứng quy định tại Điều 38",
        rounding_rule="Nhân hệ số 0.4 trên mức bồi thường chuẩn",
    ),
    "FUND_ACCIDENT_ONE_TIME": FormulaMetadata(
        formula_id="FUND_ACCIDENT_ONE_TIME",
        domain="OCCUPATIONAL_ACCIDENT_DISEASE",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 04/BNV",
        article="Điều 48",
        clause="Khoản 1 & Khoản 2",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="Suy giảm KNLĐ từ 5% đến 30% do TNLĐ-BNN (chi trả từ Quỹ BH TNLĐ-BNN)",
        required_inputs=["impairment_percent", "reference_salary", "years_insured", "monthly_salary"],
        formula="Trợ cấp = [5.0 + (P - 5) * 0.5] * Mức tham chiếu + [0.5 + (Năm - 1) * 0.3] * Lương đóng BHXH",
        rounding_rule="Chi trả một lần",
    ),
    "FUND_ACCIDENT_MONTHLY": FormulaMetadata(
        formula_id="FUND_ACCIDENT_MONTHLY",
        domain="OCCUPATIONAL_ACCIDENT_DISEASE",
        legal_source="Luật ATVSLĐ 84/2015 & VBHN 04/BNV",
        article="Điều 49",
        clause="Khoản 1 & Khoản 2",
        effective_from="2016-07-01",
        effective_to=None,
        applicability_conditions="Suy giảm KNLĐ từ 31% trở lên do TNLĐ-BNN (chi trả từ Quỹ BH TNLĐ-BNN)",
        required_inputs=["impairment_percent", "reference_salary", "years_insured", "monthly_salary"],
        formula="Trợ cấp tháng = [30% + (P - 31) * 2%] * Mức tham chiếu + [0.5% + (Năm - 1) * 0.3%] * Lương đóng BHXH",
        rounding_rule="Chi trả hàng tháng",
    ),
}


@dataclass
class CalculationResult:
    benefit_type: str
    total_amount: float
    formula_description: str
    legal_basis: str
    variables: Dict[str, Any]
    formula_id: str = ""
    breakdown: List[str] = field(default_factory=list)
    is_eligible: bool = True
    ineligibility_reason: str = ""
    needs_clarification: bool = False
    missing_fields: List[str] = field(default_factory=list)
    explanation: str = ""


class BenefitCalculator:
    """Deterministic, statute-grounded benefit calculator for VietLabor AI."""

    @classmethod
    def get_formula_metadata(cls, formula_id: str) -> Optional[FormulaMetadata]:
        return FORMULA_REGISTRY.get(formula_id)

    # --------------------------------------------------------------------------
    # 1. CHẾ ĐỘ ỐM ĐAU (SICKNESS BENEFIT)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_sickness(
        cls,
        preceding_salary: Optional[float],
        sick_days: Optional[int],
        is_long_term: bool = False,
        contribution_years: Optional[float] = None,
        is_armed_forces: bool = False,
        condition_type: str = "normal",  # "normal", "hazardous", "heavy_hazardous"
    ) -> CalculationResult:
        """
        Tính chế độ ốm đau theo Điều 26, Điều 28 Luật BHXH (58/VBHN-VPQH) & TT 12/2025/TT-BNV.
        Branching:
        - Sĩ quan, quân đội: 100%
        - Ốm đau thông thường / dài ngày trong 180 ngày đầu: 75%
        - Ốm đau dài ngày quá 180 ngày:
          * Đóng BHXH >= 30 năm: 65%
          * Đóng BHXH 15 đến < 30 năm: 55%
          * Đóng BHXH < 15 năm: 50%
        - Mức ngày = (Tiền lương tháng * Tỷ lệ) / 24 ngày.
        """
        missing: List[str] = []
        if preceding_salary is None or preceding_salary <= 0:
            missing.append("preceding_salary")
        if sick_days is None or sick_days <= 0:
            missing.append("sick_days")

        if is_long_term and sick_days is not None and sick_days > 180 and contribution_years is None:
            missing.append("contribution_years")

        if missing:
            return CalculationResult(
                benefit_type="SICKNESS",
                total_amount=0.0,
                formula_id="SICKNESS_STANDARD_75",
                formula_description="Trợ cấp ốm đau = (Tiền lương tháng liền kề * Tỷ lệ hưởng / 24) * Số ngày nghỉ",
                legal_basis="Điều 26, Điều 28 Văn bản hợp nhất 58/VBHN-VPQH & Thông tư 12/2025/TT-BNV",
                variables={"is_long_term": is_long_term, "is_armed_forces": is_armed_forces},
                needs_clarification=True,
                missing_fields=missing,
                explanation="Cần cung cấp mức tiền lương đóng BHXH tháng liền kề, số ngày nghỉ và thời gian đóng BHXH (nếu mắc bệnh dài ngày quá 180 ngày).",
            )

        # -- Type narrowing for Pyright (guaranteed non-None after missing-field guard) --
        assert preceding_salary is not None
        assert sick_days is not None

        # Determine rate
        if is_armed_forces:
            rate = 1.0
            formula_id = "SICKNESS_ARMED_FORCES_100"
            rate_desc = "100% mức tiền lương tháng đóng BHXH của tháng liền kề (Lực lượng vũ trang - Khoản 1 Điều 28)"
        elif not is_long_term or sick_days <= 180:
            rate = 0.75
            formula_id = "SICKNESS_STANDARD_75"
            rate_desc = "75% mức tiền lương tháng đóng BHXH của tháng liền kề (Khoản 1 Điều 28)"
        else:
            # Long term sickness exceeding 180 days (Khoản 2 Điều 28)
            _cy = contribution_years if contribution_years is not None else 0.0
            if _cy >= 30.0:
                rate = 0.65
                formula_id = "SICKNESS_LONGTERM_65"
                rate_desc = "65% mức tiền lương (Bệnh dài ngày quá 180 ngày, đóng BHXH >= 30 năm - Điểm a Khoản 2 Điều 28)"
            elif _cy >= 15.0:
                rate = 0.55
                formula_id = "SICKNESS_LONGTERM_55"
                rate_desc = "55% mức tiền lương (Bệnh dài ngày quá 180 ngày, đóng BHXH từ 15 đến dưới 30 năm - Điểm b Khoản 2 Điều 28)"
            else:
                rate = 0.50
                formula_id = "SICKNESS_LONGTERM_50"
                rate_desc = "50% mức tiền lương (Bệnh dài ngày quá 180 ngày, đóng BHXH dưới 15 năm - Điểm c Khoản 2 Điều 28)"

        daily_benefit = (preceding_salary * rate) / 24.0
        total = round(daily_benefit * sick_days, 2)

        breakdown = [
            f"1. Mức lương tháng liền kề trước khi nghỉ: {preceding_salary:,.0f} VNĐ",
            f"2. Tỷ lệ hưởng áp dụng: {rate_desc}",
            f"3. Mức hưởng 01 ngày làm việc: ({preceding_salary:,.0f} x {rate * 100:.0f}%) / 24 = {daily_benefit:,.0f} VNĐ/ngày",
            f"4. Tổng số tiền hưởng cho {sick_days} ngày nghỉ: {daily_benefit:,.0f} x {sick_days} = {total:,.0f} VNĐ",
        ]

        return CalculationResult(
            benefit_type="SICKNESS",
            total_amount=total,
            formula_id=formula_id,
            formula_description=f"Mức hưởng = (Lương đóng BHXH tháng liền kề x {rate * 100:.0f}% / 24 ngày) x {sick_days} ngày",
            legal_basis="Điều 28 Văn bản hợp nhất 58/VBHN-VPQH & Điều 6 Thông tư 12/2025/TT-BNV",
            variables={
                "preceding_salary": preceding_salary,
                "sick_days": sick_days,
                "rate": rate,
                "daily_benefit": daily_benefit,
                "is_long_term": is_long_term,
                "contribution_years": contribution_years,
                "is_armed_forces": is_armed_forces,
            },
            breakdown=breakdown,
            needs_clarification=False,
            explanation=f"Người lao động được cơ quan BHXH chi trả chế độ ốm đau tổng cộng {total:,.0f} VNĐ.",
        )

    # --------------------------------------------------------------------------
    # 2. CHẾ ĐỘ THAI SẢN (MATERNITY BENEFIT)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_maternity(
        cls,
        avg_salary_6m: Optional[float],
        contribution_months_in_12m: Optional[int] = None,
        leave_months: Optional[float] = None,
        children_count: int = 1,
        is_paternity: bool = False,
        paternity_case: str = "normal",  # "normal" (5d), "surgery" (7d), "twins" (10d), "twins_surgery" (14d)
        paternity_days: Optional[int] = None,
        reference_salary: float = CURRENT_REFERENCE_SALARY,
        is_special_condition: bool = False,  # dưỡng thai chỉ cần 3m trong 12m
    ) -> CalculationResult:
        """
        Tính chế độ thai sản theo Điều 31, 34, 38, 39 Luật BHXH (58/VBHN-VPQH).
        Branches:
        - Lao động nữ sinh con: 100% * lương BQ 6 tháng * số tháng nghỉ (sinh 1: 6 tháng, sinh đôi: 7 tháng...)
        - Trợ cấp một lần khi sinh con: 2 lần mức tham chiếu / mỗi con.
        - Trường hợp đóng chưa đủ 6 tháng: tính theo mức bình quân các tháng đã đóng (nếu đủ điều kiện).
        - Lao động nam có vợ sinh con (chế độ thai sản của chồng):
          * Bình thường: 5 ngày
          * Sinh mổ / dưới 32 tuần: 7 ngày
          * Sinh đôi: 10 ngày (+ 3 ngày mỗi con thêm)
          * Sinh đôi sinh mổ: 14 ngày
          * Tiền hưởng = (Lương BQ 6 tháng / 24) * số ngày nghỉ.
        """
        missing: List[str] = []
        if avg_salary_6m is None or avg_salary_6m <= 0:
            missing.append("avg_salary_6m")

        if missing:
            return CalculationResult(
                benefit_type="MATERNITY",
                total_amount=0.0,
                formula_id="MATERNITY_STANDARD",
                formula_description="Trợ cấp thai sản = (Lương bình quân * Thời gian nghỉ) + Trợ cấp 1 lần (nếu có)",
                legal_basis="Điều 38, Điều 39 Văn bản hợp nhất 58/VBHN-VPQH",
                variables={"is_paternity": is_paternity, "children_count": children_count},
                needs_clarification=True,
                missing_fields=missing,
                explanation="Cần cung cấp mức bình quân tiền lương tháng đóng BHXH của 6 tháng liền kề trước khi nghỉ việc để tính chế độ.",
            )

        # -- Type narrowing for Pyright --
        assert avg_salary_6m is not None

        # Gate check: contribution threshold (Điều 31)
        if contribution_months_in_12m is not None:
            min_required = 3 if is_special_condition else 6
            if contribution_months_in_12m < min_required and not is_paternity:
                return CalculationResult(
                    benefit_type="MATERNITY",
                    total_amount=0.0,
                    formula_id="MATERNITY_STANDARD",
                    formula_description="Điều kiện: Đóng BHXH từ đủ 6 tháng trở lên trong 12 tháng trước khi sinh (Điều 31)",
                    legal_basis="Khoản 2 Điều 31 Văn bản hợp nhất 58/VBHN-VPQH",
                    variables={"contribution_months_in_12m": contribution_months_in_12m, "min_required": min_required},
                    is_eligible=False,
                    ineligibility_reason=f"Người lao động chỉ đóng {contribution_months_in_12m} tháng, chưa đủ điều kiện tối thiểu {min_required} tháng trong 12 tháng trước khi sinh theo quy định tại Điều 31 Luật BHXH.",
                    needs_clarification=False,
                    explanation=f"Chưa đủ điều kiện hưởng chế độ thai sản khi sinh con do đóng chưa đủ {min_required} tháng BHXH trong 12 tháng trước sinh.",
                )

        # Paternity branch
        if is_paternity:
            days_map = {
                "normal": 5,
                "surgery": 7,
                "c_section": 7,
                "sinh_mo": 7,
                "under_32w": 7,
                "twins": 10,
                "twins_surgery": 14,
                "twins_c_section": 14,
                "sinh_doi_mo": 14,
            }
            if paternity_days is None:
                paternity_days = days_map.get(paternity_case, 5)
                if children_count > 2 and "twins" in paternity_case:
                    paternity_days += (children_count - 2) * 3

            daily_rate = avg_salary_6m / 24.0
            total = round(daily_rate * paternity_days, 2)

            breakdown = [
                f"1. Chế độ thai sản của lao động nam khi vợ sinh con (Khoản 2 Điều 34)",
                f"2. Số ngày nghỉ được hưởng theo quy định: {paternity_days} ngày làm việc (trường hợp: {paternity_case})",
                f"3. Mức hưởng 01 ngày làm việc: {avg_salary_6m:,.0f} / 24 = {daily_rate:,.0f} VNĐ/ngày",
                f"-> Tổng mức hưởng trợ cấp thai sản của chồng: {daily_rate:,.0f} x {paternity_days} = {total:,.0f} VNĐ",
            ]

            return CalculationResult(
                benefit_type="MATERNITY_PATERNITY",
                total_amount=total,
                formula_id="MATERNITY_PATERNITY",
                formula_description="Trợ cấp thai sản cho nam = (Lương BQ 6 tháng / 24) * Số ngày nghỉ",
                legal_basis="Điều 34 Khoản 2 & Điều 39 Khoản 1 Điểm b Văn bản hợp nhất 58/VBHN-VPQH",
                variables={
                    "avg_salary_6m": avg_salary_6m,
                    "paternity_days": paternity_days,
                    "paternity_case": paternity_case,
                    "daily_rate": daily_rate,
                },
                breakdown=breakdown,
                needs_clarification=False,
                explanation=f"Lao động nam được cơ quan BHXH chi trả chế độ thai sản khi vợ sinh con là {total:,.0f} VNĐ.",
            )

        # Standard female leave branch
        if leave_months is None:
            # 6 months for 1 child, + 1 month per additional child (Khoản 1 Điều 34)
            leave_months = 6.0 + max(0, children_count - 1) * 1.0

        monthly_benefit = avg_salary_6m * leave_months
        lump_sum_allowance = 2.0 * reference_salary * children_count
        total = monthly_benefit + lump_sum_allowance

        breakdown = [
            f"1. Trợ cấp thai sản hàng tháng ({leave_months} tháng): {avg_salary_6m:,.0f} x {leave_months} = {monthly_benefit:,.0f} VNĐ (Khoản 1 Điều 39)",
            f"2. Trợ cấp một lần khi sinh con ({children_count} con): 2.0 x {reference_salary:,.0f} x {children_count} = {lump_sum_allowance:,.0f} VNĐ (Điều 38)",
            f"-> Tổng số tiền chế độ thai sản nhận được: {total:,.0f} VNĐ",
        ]

        return CalculationResult(
            benefit_type="MATERNITY",
            total_amount=total,
            formula_id="MATERNITY_STANDARD",
            formula_description="Mức hưởng = (100% lương BQ 6 tháng x số tháng nghỉ) + (2.0 x mức tham chiếu x số con)",
            legal_basis="Điều 38, Điều 39 Văn bản hợp nhất 58/VBHN-VPQH",
            variables={
                "avg_salary_6m": avg_salary_6m,
                "leave_months": leave_months,
                "children_count": children_count,
                "reference_salary": reference_salary,
                "monthly_benefit": monthly_benefit,
                "lump_sum_allowance": lump_sum_allowance,
            },
            breakdown=breakdown,
            needs_clarification=False,
            explanation=f"Người lao động đủ điều kiện nghỉ thai sản được nhận tổng cộng {total:,.0f} VNĐ từ cơ quan BHXH.",
        )

    # --------------------------------------------------------------------------
    # 3. BHXH MỘT LẦN (LUMP-SUM SOCIAL INSURANCE)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_lump_sum_bhxh(
        cls,
        avg_salary: Optional[float] = None,
        years_before_2014: float = 0.0,
        years_from_2014: float = 0.0,
        months_before_2014: int = 0,
        months_from_2014: int = 0,
        is_eligible: bool = True,
        ineligibility_reason: str = "",
        avg_salary_all: Optional[float] = None,
    ) -> CalculationResult:
        """
        Tính BHXH một lần theo Điều 70 Luật BHXH (58/VBHN-VPQH) & Điều 19 NĐ 158/2025/NĐ-CP.
        Rounding rules:
        - Tháng lẻ 1 đến 6 tháng = 0.5 năm; 7 đến 11 tháng = 1.0 năm.
        - Trước 2014: 1.5 tháng mức BQ / năm.
        - Từ 2014 trở đi: 2.0 tháng mức BQ / năm.
        - Đóng dưới 1 năm: tính bằng số tiền đã đóng, tối đa bằng 2 tháng mức bình quân.
        """
        effective_salary = avg_salary if avg_salary is not None else avg_salary_all

        # Check eligibility gate
        if not is_eligible:
            reason = ineligibility_reason or "Người lao động chưa đáp ứng các điều kiện rút BHXH một lần theo Khoản 1 Điều 70 Luật BHXH (như sau 12 tháng nghỉ việc, ra nước ngoài định cư, hoặc mắc bệnh hiểm nghèo)."
            return CalculationResult(
                benefit_type="LUMP_SUM_BHXH",
                total_amount=0.0,
                formula_id="LUMP_SUM_BHXH_STANDARD",
                formula_description="Điều kiện rút BHXH một lần: Khoản 1 Điều 70 58/VBHN-VPQH",
                legal_basis="Điều 70 Văn bản hợp nhất 58/VBHN-VPQH & Nghị định 158/2025/NĐ-CP",
                variables={"is_eligible": False},
                is_eligible=False,
                ineligibility_reason=reason,
                needs_clarification=False,
                explanation=reason,
            )

        if effective_salary is None or effective_salary <= 0:
            return CalculationResult(
                benefit_type="LUMP_SUM_BHXH",
                total_amount=0.0,
                formula_id="LUMP_SUM_BHXH_STANDARD",
                formula_description="BHXH một lần = Lương bình quân * (1.5 * năm trước 2014 + 2.0 * năm từ 2014)",
                legal_basis="Điều 70 Văn bản hợp nhất 58/VBHN-VPQH & Điều 19 Nghị định 158/2025/NĐ-CP",
                variables={"years_before_2014": years_before_2014, "years_from_2014": years_from_2014},
                needs_clarification=True,
                missing_fields=["avg_salary"],
                explanation="Cần cung cấp mức bình quân tiền lương tháng đóng BHXH của toàn bộ quá trình đóng để tính chính xác số tiền BHXH một lần.",
            )

        # Handle month fraction rounding (Khoản 2 Điều 19 NĐ 158/2025/NĐ-CP)
        tot_years_before = years_before_2014
        tot_years_from = years_from_2014

        # Convert months if passed
        extra_months = months_before_2014 + months_from_2014
        if extra_months > 0:
            if 1 <= extra_months <= 6:
                tot_years_from += 0.5
            elif extra_months >= 7:
                tot_years_from += 1.0

        total_years = tot_years_before + tot_years_from

        # Under 1 year contribution rule (Điểm c Khoản 2 Điều 70)
        if 0 < total_years < 1.0:
            # 22% of total contribution salaries, capped at 2 * avg_salary
            # Estimated based on months contributed (e.g., 0.5 year = 6 months * 0.22 * avg = 1.32 avg)
            months_multiplier = min(2.0, total_years * 12 * 0.22)
            total = round(months_multiplier * effective_salary, 2)
            formula_id = "LUMP_SUM_BHXH_STANDARD"
            breakdown = [
                f"1. Thời gian đóng BHXH dưới 01 năm ({total_years * 12:.0f} tháng đóng): Điểm c Khoản 2 Điều 70 58/VBHN-VPQH",
                f"2. Mức hưởng bằng số tiền đã đóng vào quỹ (22% x tổng tiền lương đóng), tối đa bằng 02 tháng mức bình quân",
                f"3. Hệ số hưởng áp dụng: {months_multiplier:.2f} tháng lương bình quân",
                f"-> Tổng số tiền BHXH một lần nhận được: {total:,.0f} VNĐ",
            ]
        else:
            months_multiplier = (tot_years_before * 1.5) + (tot_years_from * 2.0)
            total = round(months_multiplier * effective_salary, 2)
            formula_id = "LUMP_SUM_BHXH_STANDARD"
            breakdown = [
                f"1. Thời gian đóng trước 2014 ({tot_years_before:.1f} năm): {tot_years_before:.1f} x 1.5 = {tot_years_before * 1.5:.2f} tháng",
                f"2. Thời gian đóng từ 2014 trở đi ({tot_years_from:.1f} năm): {tot_years_from:.1f} x 2.0 = {tot_years_from * 2.0:.2f} tháng",
                f"3. Tổng số tháng hưởng trợ cấp: {months_multiplier:.2f} tháng lương bình quân",
                f"-> Tổng số tiền BHXH một lần nhận được: {months_multiplier:.2f} x {effective_salary:,.0f} = {total:,.0f} VNĐ",
            ]

        return CalculationResult(
            benefit_type="LUMP_SUM_BHXH",
            total_amount=total,
            formula_id=formula_id,
            formula_description="BHXH một lần = Lương bình quân x (1.5 x số năm trước 2014 + 2.0 x số năm từ 2014)",
            legal_basis="Điều 70 Văn bản hợp nhất 58/VBHN-VPQH & Điều 19 Nghị định 158/2025/NĐ-CP",
            variables={
                "avg_salary": effective_salary,
                "years_before_2014": tot_years_before,
                "years_from_2014": tot_years_from,
                "months_multiplier": months_multiplier,
            },
            breakdown=breakdown,
            needs_clarification=False,
            explanation=f"Với {total_years:.1f} năm đóng BHXH, người lao động được nhận số tiền BHXH một lần là {total:,.0f} VNĐ.",
        )

    # --------------------------------------------------------------------------
    # 4. CHẾ ĐỘ HƯU TRÍ (PENSION BENEFIT)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_pension(
        cls,
        avg_salary: Optional[float],
        gender: Optional[str],  # "female" or "male"
        contribution_years: Optional[float],
        years_early: float = 0.0,
        reference_salary: float = CURRENT_REFERENCE_SALARY,
    ) -> CalculationResult:
        """
        Tính mức lương hưu hằng tháng theo Điều 64, 65, 66 Luật BHXH (58/VBHN-VPQH).
        Branches:
        - Nữ: 15 năm = 45%, mỗi năm sau + 2%, tối đa 75% (đạt tại 30 năm).
        - Nam:
          * Đóng >= 20 năm: 20 năm = 45%, mỗi năm sau + 2%, tối đa 75% (đạt tại 35 năm).
          * Đóng từ 15 đến dưới 20 năm: 15 năm = 40%, mỗi năm sau + 2.25%.
        - Nghỉ hưu sớm do suy giảm KNLĐ (Điều 65): giảm 2% cho mỗi năm nghỉ hưu trước tuổi.
        - Mức tối thiểu: bằng mức tham chiếu (hoặc lương cơ sở).
        """
        missing: List[str] = []
        if avg_salary is None or avg_salary <= 0:
            missing.append("avg_salary")
        if gender is None or gender.lower() not in ["female", "male", "nu", "nam", "nữ"]:
            missing.append("gender")
        if contribution_years is None or contribution_years <= 0:
            missing.append("contribution_years")

        if missing:
            return CalculationResult(
                benefit_type="PENSION",
                total_amount=0.0,
                formula_id="PENSION_FEMALE_STANDARD",
                formula_description="Lương hưu hằng tháng = Tỷ lệ hưởng (%) * Mức bình quân tiền lương tháng đóng BHXH",
                legal_basis="Điều 64, Điều 66 Văn bản hợp nhất 58/VBHN-VPQH (Luật BHXH)",
                variables={"years_early": years_early},
                needs_clarification=True,
                missing_fields=missing,
                explanation="Cần cung cấp mức bình quân tiền lương tháng đóng BHXH, giới tính và tổng số năm đóng BHXH để tính lương hưu.",
            )

        # -- Type narrowing for Pyright --
        assert avg_salary is not None
        assert gender is not None
        assert contribution_years is not None

        g = gender.lower()
        is_female = g in ["female", "nu", "nữ"]

        # Minimum tenure gate under current law (Điều 64)
        if contribution_years < 15.0:
            return CalculationResult(
                benefit_type="PENSION",
                total_amount=0.0,
                formula_id="PENSION_FEMALE_STANDARD" if is_female else "PENSION_MALE_STANDARD",
                formula_description="Điều kiện hưởng lương hưu: Đóng BHXH từ đủ 15 năm trở lên (Điều 64)",
                legal_basis="Điều 64 Văn bản hợp nhất 58/VBHN-VPQH",
                variables={"contribution_years": contribution_years},
                is_eligible=False,
                ineligibility_reason=f"Thời gian đóng BHXH là {contribution_years:.1f} năm, chưa đủ điều kiện tối thiểu 15 năm đóng BHXH để hưởng lương hưu theo Điều 64 58/VBHN-VPQH.",
                needs_clarification=False,
                explanation=f"Người lao động chưa đủ điều kiện hưởng lương hưu hàng tháng vì thời gian đóng BHXH mới đạt {contribution_years:.1f} năm (yêu cầu từ đủ 15 năm).",
            )

        # Standard percentage calculation (Khoản 1 Điều 66)
        if is_female:
            base_years = 15.0
            base_rate = 0.45
            rate = base_rate + max(0.0, contribution_years - base_years) * 0.02
            rate = min(0.75, rate)
            formula_id = "PENSION_FEMALE_STANDARD"
            rate_desc = f"Lao động nữ: 15 năm đầu = 45% + {(contribution_years - 15) * 2:.1f}% ({contribution_years - 15:.1f} năm x 2%) = {rate * 100:.1f}% (tối đa 75%)"
        else:
            if contribution_years >= 20.0:
                base_years = 20.0
                base_rate = 0.45
                rate = base_rate + max(0.0, contribution_years - base_years) * 0.02
                rate = min(0.75, rate)
                formula_id = "PENSION_MALE_STANDARD"
                rate_desc = f"Lao động nam (>=20 năm): 20 năm đầu = 45% + {(contribution_years - 20) * 2:.1f}% ({contribution_years - 20:.1f} năm x 2%) = {rate * 100:.1f}% (tối đa 75%)"
            else:
                base_years = 15.0
                base_rate = 0.40
                rate = base_rate + (contribution_years - 15.0) * 0.0225
                formula_id = "PENSION_MALE_15_TO_20Y"
                rate_desc = f"Lao động nam (15-20 năm): 15 năm đầu = 40% + {(contribution_years - 15) * 2.25:.2f}% ({contribution_years - 15:.1f} năm x 2.25%) = {rate * 100:.2f}%"

        # Early retirement deduction (Khoản 2 Điều 66)
        deduction = 0.0
        if years_early > 0:
            deduction = years_early * 0.02
            rate = max(0.0, rate - deduction)
            formula_id = "PENSION_EARLY_IMPAIRMENT"

        monthly_pension = round(rate * avg_salary, 2)
        # Floor comparison
        effective_pension = max(monthly_pension, reference_salary)

        breakdown = [
            f"1. Giới tính: {'Nữ' if is_female else 'Nam'}, Thời gian đóng BHXH: {contribution_years:.1f} năm",
            f"2. Tỷ lệ hưởng lương hưu tiêu chuẩn: {rate_desc}",
        ]
        if years_early > 0:
            breakdown.append(f"3. Giảm trừ nghỉ hưu trước tuổi ({years_early} năm): -{deduction * 100:.1f}% (Khoản 2 Điều 66)")
            breakdown.append(f"4. Tỷ lệ hưởng sau giảm trừ: {rate * 100:.2f}%")
        breakdown.append(f"-> Mức lương hưu hàng tháng: {rate * 100:.2f}% x {avg_salary:,.0f} = {monthly_pension:,.0f} VNĐ/tháng (tối thiểu {reference_salary:,.0f} VNĐ)")

        return CalculationResult(
            benefit_type="PENSION",
            total_amount=effective_pension,
            formula_id=formula_id,
            formula_description="Lương hưu = Tỷ lệ hưởng (%) * Lương bình quân đóng BHXH (Khoản 1, 2 Điều 66)",
            legal_basis="Điều 64, Điều 66 Văn bản hợp nhất 58/VBHN-VPQH",
            variables={
                "avg_salary": avg_salary,
                "gender": "female" if is_female else "male",
                "contribution_years": contribution_years,
                "years_early": years_early,
                "pension_rate": rate,
                "monthly_pension": effective_pension,
            },
            breakdown=breakdown,
            needs_clarification=False,
            explanation=f"Mức lương hưu hàng tháng của người lao động được xác định là {effective_pension:,.0f} VNĐ/tháng.",
        )

    # --------------------------------------------------------------------------
    # 5. BỒI THƯỜNG TNLĐ TỪ NSDLĐ (EMPLOYER ACCIDENT COMPENSATION)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_employer_accident_compensation(
        cls,
        monthly_salary: Optional[float],
        impairment_percent: Optional[int],
        is_employee_fault: bool = False,
    ) -> CalculationResult:
        """
        Tính bồi thường/trợ cấp TNLĐ của người sử dụng lao động theo Điều 38, 39 Luật ATVSLĐ & Điều 3 06/VBHN-BNV.
        Thresholds:
        - 5% - 10%: ít nhất 1.5 tháng tiền lương.
        - 11% - 80%: 1.5 + (P - 10) * 0.4 tháng tiền lương.
        - >= 81% hoặc chết: ít nhất 30.0 tháng tiền lương.
        - Lỗi do người lao động: ít nhất 40% mức bồi thường tương ứng.
        """
        missing: List[str] = []
        if monthly_salary is None or monthly_salary <= 0:
            missing.append("monthly_salary")
        if impairment_percent is None or impairment_percent < 5:
            missing.append("impairment_percent")

        if missing:
            return CalculationResult(
                benefit_type="EMPLOYER_ACCIDENT_COMPENSATION",
                total_amount=0.0,
                formula_id="EMPLOYER_ACCIDENT_5_TO_10",
                formula_description="Bồi thường TNLĐ = Hệ số tháng lương theo mức suy giảm * Tiền lương tháng",
                legal_basis="Điều 38, Điều 39 Luật An toàn, vệ sinh lao động 84/2015/QH13 & Văn bản hợp nhất 06/VBHN-BNV",
                variables={"is_employee_fault": is_employee_fault},
                needs_clarification=True,
                missing_fields=missing,
                explanation="Cần cung cấp mức tiền lương theo hợp đồng lao động và tỷ lệ suy giảm KNLĐ (từ 5% trở lên) để tính mức bồi thường của công ty.",
            )

        # -- Type narrowing for Pyright --
        assert monthly_salary is not None
        assert impairment_percent is not None

        # Base multiplier
        if impairment_percent <= 10:
            months = 1.5
            formula_id = "EMPLOYER_ACCIDENT_5_TO_10"
            rule_desc = f"Suy giảm {impairment_percent}% (từ 5% đến 10%): Ít nhất 1.5 tháng tiền lương (Điểm a Khoản 4 Điều 38)"
        elif impairment_percent >= 81:
            months = 30.0
            formula_id = "EMPLOYER_ACCIDENT_81_PLUS"
            rule_desc = f"Suy giảm {impairment_percent}% (từ 81% trở lên hoặc tử vong): Ít nhất 30.0 tháng tiền lương (Điểm b Khoản 4 Điều 38)"
        else:
            months = 1.5 + (impairment_percent - 10) * 0.4
            formula_id = "EMPLOYER_ACCIDENT_11_TO_80"
            rule_desc = f"Suy giảm {impairment_percent}% (từ 11% đến 80%): 1.5 + ({impairment_percent} - 10) x 0.4 = {months:.1f} tháng lương (Điểm a Khoản 4 Điều 38)"

        # Check fault
        if is_employee_fault:
            base_months = months
            months = round(months * 0.4, 4)
            formula_id = "EMPLOYER_ACCIDENT_FAULT"
            regime = f"Trợ cấp TNLĐ do lỗi của người lao động: 40% của mức bồi thường {base_months:.1f} tháng = {months:.2f} tháng lương (Điều 39)"
            article_cite = "Điều 39 Luật 84/2015/QH13"
        else:
            regime = f"Bồi thường TNLĐ thuộc trách nhiệm NSDLĐ: {months:.1f} tháng lương (Điều 38)"
            article_cite = "Điều 38 Luật 84/2015/QH13 & Điều 3 06/VBHN-BNV"

        total = round(months * monthly_salary, 2)

        breakdown = [
            f"1. Tỷ lệ suy giảm khả năng lao động: {impairment_percent}%",
            f"2. Căn cứ tính mức bồi thường: {rule_desc}",
            f"3. Chế độ áp dụng: {regime} ({article_cite})",
            f"-> Tổng tiền NSDLĐ phải chi trả: {months:.2f} x {monthly_salary:,.0f} = {total:,.0f} VNĐ",
            "Lưu ý: NSDLĐ còn phải trả 100% tiền lương trong thời gian điều trị và chi trả toàn bộ chi phí y tế phần ngoài BHYT (Điều 38).",
        ]

        return CalculationResult(
            benefit_type="EMPLOYER_ACCIDENT_COMPENSATION",
            total_amount=total,
            formula_id=formula_id,
            formula_description=f"Hệ số tháng lương = {months:.2f} tháng lương",
            legal_basis="Điều 38, Điều 39 Luật An toàn, vệ sinh lao động 84/2015/QH13 & Văn bản hợp nhất 06/VBHN-BNV",
            variables={
                "monthly_salary": monthly_salary,
                "impairment_percent": impairment_percent,
                "is_employee_fault": is_employee_fault,
                "months_multiplier": months,
            },
            breakdown=breakdown,
            needs_clarification=False,
            explanation=f"Doanh nghiệp có trách nhiệm chi trả bồi thường/trợ cấp TNLĐ tối thiểu là {total:,.0f} VNĐ.",
        )

    # --------------------------------------------------------------------------
    # 6. TRỢ CẤP TỪ QUỸ BH TNLĐ-BNN (INSURANCE FUND ACCIDENT BENEFIT)
    # --------------------------------------------------------------------------
    @classmethod
    def calculate_fund_accident_benefit(
        cls,
        impairment_percent: Optional[int],
        years_insured: float = 1.0,
        monthly_salary: Optional[float] = None,
        reference_salary: float = CURRENT_REFERENCE_SALARY,
    ) -> CalculationResult:
        """
        Tính trợ cấp từ Quỹ BH TNLĐ-BNN theo Điều 48, 49 Luật ATVSLĐ & 04/VBHN-BNV.
        - 5% đến 30% (Trợ cấp một lần - Điều 48):
          * Tham chiếu: 5% = 5 lần mức tham chiếu; mỗi 1% thêm = 0.5 lần.
          * Thâm niên: < 1 năm = 0.5 tháng lương; mỗi năm thêm = 0.3 tháng lương.
        - Từ 31% trở lên (Trợ cấp hàng tháng - Điều 49):
          * Tham chiếu: 31% = 30% mức tham chiếu; mỗi 1% thêm = 2% mức tham chiếu.
          * Thâm niên: < 1 năm = 0.5% tháng lương; mỗi năm thêm = 0.3% tháng lương.
        """
        if impairment_percent is None or impairment_percent < 5:
            return CalculationResult(
                benefit_type="FUND_ACCIDENT_BENEFIT",
                total_amount=0.0,
                formula_id="FUND_ACCIDENT_ONE_TIME",
                formula_description="Trợ cấp Quỹ TNLĐ-BNN: 5%-30% nhận một lần; từ 31% trở lên nhận hàng tháng",
                legal_basis="Điều 48, Điều 49 Luật An toàn, vệ sinh lao động 84/2015/QH13 & 04/VBHN-BNV",
                variables={"reference_salary": reference_salary},
                needs_clarification=True,
                missing_fields=["impairment_percent"],
                explanation="Cần cung cấp tỷ lệ suy giảm khả năng lao động (từ 5% trở lên) để xác định mức trợ cấp từ Quỹ TNLĐ-BNN.",
            )

        if impairment_percent <= 30:
            # Trợ cấp một lần (Điều 48)
            base_ref_multiplier = 5.0 + (impairment_percent - 5) * 0.5
            lump_ref_part = base_ref_multiplier * reference_salary

            seniority_months = 0.5 if years_insured <= 1.0 else 0.5 + (years_insured - 1.0) * 0.3
            salary_part = (seniority_months * monthly_salary) if monthly_salary else 0.0

            total = round(lump_ref_part + salary_part, 2)
            breakdown = [
                f"1. Trợ cấp một lần theo mức suy giảm ({impairment_percent}%): [5.0 + ({impairment_percent} - 5) x 0.5] x {reference_salary:,.0f} = {lump_ref_part:,.0f} VNĐ",
                f"2. Trợ cấp tính theo thời gian đóng BHXH ({years_insured} năm): {seniority_months:.1f} tháng lương = {salary_part:,.0f} VNĐ",
                f"-> Tổng trợ cấp một lần từ Quỹ TNLĐ-BNN: {total:,.0f} VNĐ",
            ]

            return CalculationResult(
                benefit_type="FUND_ACCIDENT_ONE_TIME",
                total_amount=total,
                formula_id="FUND_ACCIDENT_ONE_TIME",
                formula_description="Trợ cấp 1 lần = [5.0 + (P-5)*0.5]*Mức tham chiếu + [0.5 + (Năm-1)*0.3]*Lương đóng BHXH",
                legal_basis="Điều 48 Luật An toàn, vệ sinh lao động 84/2015/QH13 & Văn bản hợp nhất 04/VBHN-BNV",
                variables={
                    "impairment_percent": impairment_percent,
                    "reference_salary": reference_salary,
                    "years_insured": years_insured,
                    "monthly_salary": monthly_salary,
                },
                breakdown=breakdown,
                needs_clarification=False,
                explanation=f"Người lao động suy giảm {impairment_percent}% KNLĐ được Quỹ TNLĐ-BNN chi trả trợ cấp một lần là {total:,.0f} VNĐ.",
            )
        else:
            # Trợ cấp hàng tháng (Điều 49)
            monthly_ref_rate = 0.30 + (impairment_percent - 31) * 0.02
            monthly_from_ref = monthly_ref_rate * reference_salary

            seniority_rate = 0.005 if years_insured <= 1.0 else 0.005 + (years_insured - 1.0) * 0.003
            monthly_from_salary = (seniority_rate * monthly_salary) if monthly_salary else 0.0

            total_monthly = round(monthly_from_ref + monthly_from_salary, 2)
            breakdown = [
                f"1. Trợ cấp hàng tháng theo mức suy giảm ({impairment_percent}%): [30% + ({impairment_percent} - 31) x 2%] x {reference_salary:,.0f} = {monthly_from_ref:,.0f} VNĐ/tháng",
                f"2. Trợ cấp theo thời gian đóng BHXH ({years_insured} năm): {seniority_rate * 100:.1f}% tháng lương = {monthly_from_salary:,.0f} VNĐ/tháng",
                f"-> Tổng trợ cấp hàng tháng từ Quỹ TNLĐ-BNN: {total_monthly:,.0f} VNĐ/tháng",
            ]

            return CalculationResult(
                benefit_type="FUND_ACCIDENT_MONTHLY",
                total_amount=total_monthly,
                formula_id="FUND_ACCIDENT_MONTHLY",
                formula_description="Trợ cấp hàng tháng = [30% + (P-31)*2%]*Mức tham chiếu + [0.5% + (Năm-1)*0.3%]*Lương đóng BHXH",
                legal_basis="Điều 49 Luật An toàn, vệ sinh lao động 84/2015/QH13 & Văn bản hợp nhất 04/VBHN-BNV",
                variables={
                    "impairment_percent": impairment_percent,
                    "reference_salary": reference_salary,
                    "years_insured": years_insured,
                    "monthly_salary": monthly_salary,
                },
                breakdown=breakdown,
                needs_clarification=False,
                explanation=f"Người lao động suy giảm {impairment_percent}% KNLĐ được Quỹ TNLĐ-BNN chi trả trợ cấp hàng tháng là {total_monthly:,.0f} VNĐ/tháng.",
            )

    # --------------------------------------------------------------------------
    # 7. NATURAL LANGUAGE PARSER & MATCHER
    # --------------------------------------------------------------------------
    @classmethod
    def extract_and_calculate(
        cls,
        query: str,
        facts: Optional[Dict[str, Any]] = None,
    ) -> Optional[CalculationResult]:
        """Automatically parses natural language query or structured facts and calculates benefits deterministically."""
        t = query.lower()
        facts = facts or {}

        # 0. Check if query or facts indicate calculation intent
        has_facts = bool(facts)
        is_calc_query = any(k in t for k in [
            "bao nhiêu tiền", "được bao nhiêu tiền", "tính như thế nào", "tính sao", "tính tiền",
            "nhận được bao nhiêu tiền", "được nhận", "nhận bao nhiêu", "được bao nhiêu", "hưởng bao nhiêu",
            "bồi thường bao nhiêu", "trợ cấp bao nhiêu", "cách tính", "công thức tính",
            "tính lương hưu", "tính trợ cấp", "tính thai sản", "tính ốm đau", "tính bảo hiểm một lần",
            "chi trả bao nhiêu", "tổng cộng bao nhiêu", "bao nhiêu", "rút được bao nhiêu", "rút bao nhiêu"
        ])
        has_numeric_salary = bool(re.search(r"\d+\s*(?:triệu|tr|đồng|vnđ)", t))
        has_numeric_days = bool(re.search(r"\d+\s*ngày", t)) and any(k in t for k in ["ốm", "thai sản", "nghỉ", "vợ sinh", "bệnh"])
        has_numeric_impairment = bool(re.search(r"\d+\s*%", t)) and any(k in t for k in ["tai nạn", "tnlđ", "suy giảm"])
        has_numeric_years = bool(re.search(r"\d+\s*năm", t)) and any(k in t for k in ["đóng bhxh", "rút", "một lần", "hưu"])

        # If facts are not provided, filter out pure procedural questions
        from rag.query_processor import is_scenario_or_legal_consultation
        is_scenario = is_scenario_or_legal_consultation(query)
        if is_scenario and not is_calc_query:
            return None

        if not has_facts:
            is_pure_substantive = any(k in t for k in [
                "hồ sơ", "thủ tục", "thời hạn giải quyết", "nguyên tắc"
            ]) and not (is_calc_query or has_numeric_salary)
            if is_pure_substantive:
                return None
            if not (is_calc_query or has_numeric_salary or has_numeric_days or has_numeric_impairment or has_numeric_years):
                return None

        # Helper for salary parsing
        def parse_salary(text: str) -> Optional[float]:
            m_trieu = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|tr)", text)
            if m_trieu:
                val_str = m_trieu.group(1).replace(",", ".")
                return float(val_str) * 1_000_000
            m_num = re.search(r"(\d{1,3}(?:\.\d{3}){2,})", text)
            if m_num:
                return float(m_num.group(1).replace(".", ""))
            return None

        # Helper for days
        def parse_days(text: str) -> Optional[int]:
            m = re.search(r"(\d+)\s*ngày", text)
            return int(m.group(1)) if m else None

        # Helper for impairment
        def parse_impairment(text: str) -> Optional[int]:
            m = re.search(r"(\d+)\s*%", text)
            return int(m.group(1)) if m else None

        # 1. Pension domain
        is_pension = any(k in t for k in ["lương hưu", "nghỉ hưu", "hưu trí"]) or "gender" in facts or "years_early" in facts
        if is_pension:
            avg_sal = facts.get("avg_salary") or parse_salary(t)
            m_years = re.search(r"(\d+)\s*năm", t)
            years = facts.get("contribution_years") or (float(m_years.group(1)) if m_years else None)
            gender = facts.get("gender")
            if not gender:
                if any(k in t for k in ["nữ", "chị", "bà", "cô"]):
                    gender = "female"
                elif any(k in t for k in ["nam", "anh", "ông"]):
                    gender = "male"
            y_early = facts.get("years_early", 0.0)
            if not y_early:
                m_early = re.search(r"(?:nghỉ hưu sớm|trước tuổi)\s*(\d+)\s*năm", t)
                if m_early:
                    y_early = float(m_early.group(1))
            return cls.calculate_pension(
                avg_salary=avg_sal,
                gender=gender,
                contribution_years=years,
                years_early=y_early,
            )

        # 2. Sickness domain
        is_sickness = any(k in t for k in ["nghỉ ốm", "ốm đau", "chăm sóc con ốm", "bệnh dài ngày", "bị ốm", "ốm"]) or "sick_days" in facts
        if is_sickness:
            preceding_sal = facts.get("preceding_salary") or parse_salary(t)
            days = facts.get("sick_days") or parse_days(t)
            is_lt = facts.get("is_long_term", False) or any(k in t for k in ["dài ngày", "bệnh dài ngày", "ung thư", "lao"])
            years = facts.get("contribution_years")
            if years is None:
                m_years = re.search(r"(\d+)\s*năm", t)
                if m_years:
                    years = float(m_years.group(1))
            is_af = facts.get("is_armed_forces", False) or any(k in t for k in ["sĩ quan", "quân đội", "công an", "lực lượng vũ trang"])
            return cls.calculate_sickness(
                preceding_salary=preceding_sal,
                sick_days=days,
                is_long_term=is_lt,
                contribution_years=years,
                is_armed_forces=is_af,
            )

        # 3. Maternity domain
        is_maternity = any(k in t for k in ["thai sản", "nghỉ sinh", "sinh con", "sinh đôi", "sinh ba", "sinh một con", "vợ sinh"]) or "avg_salary_6m" in facts or "children_count" in facts or "paternity_case" in facts or "contribution_months_in_12m" in facts
        if is_maternity:
            avg_sal = facts.get("avg_salary_6m") or parse_salary(t)
            is_pat = facts.get("is_paternity", False) or any(k in t for k in ["chồng", "nam", "vợ sinh", "cha"])
            pat_case = facts.get("paternity_case", "normal")
            if "paternity_case" not in facts:
                if "mổ" in t or "phẫu thuật" in t:
                    pat_case = "twins_surgery" if "đôi" in t else "surgery"
                elif "đôi" in t or "2 con" in t:
                    pat_case = "twins"

            leave_m = facts.get("leave_months")
            if leave_m is None:
                m_leave = re.search(r"nghỉ\s*(\d+)\s*tháng", t)
                if m_leave:
                    leave_m = float(m_leave.group(1))

            children = facts.get("children_count")
            if children is None:
                if "sinh ba" in t or "3 con" in t:
                    children = 3
                elif "sinh đôi" in t or "2 con" in t:
                    children = 2
                else:
                    m_children = re.search(r"(\d+)\s*con", t)
                    children = int(m_children.group(1)) if m_children else 1

            return cls.calculate_maternity(
                avg_salary_6m=avg_sal,
                contribution_months_in_12m=facts.get("contribution_months_in_12m"),
                leave_months=leave_m,
                children_count=children,
                is_paternity=is_pat,
                paternity_case=pat_case,
                paternity_days=facts.get("paternity_days"),
                is_special_condition=facts.get("is_special_condition", False),
            )

        # 4. Lump-sum BHXH
        is_lump_sum_bhxh = any(k in t for k in [
            "bhxh một lần", "bhxh 1 lần", "bảo hiểm xã hội một lần", "rút bhxh", "lấy bhxh một lần",
            "rút một lần", "rút tiền bhxh", "rút được bhxh", "lấy một lần", "hưởng bhxh một lần"
        ]) or "years_before_2014" in facts or "years_from_2014" in facts or "months_from_2014" in facts
        if is_lump_sum_bhxh:
            avg_sal = facts.get("avg_salary") or facts.get("avg_salary_all") or parse_salary(t)
            m_before = re.search(r"(\d+)\s*năm(?:[^\d]+)?trước(?:\s*năm)?\s*2014", t)
            m_from = re.search(r"(\d+)\s*năm(?:[^\d]+)?(?:từ|sau)(?:\s*năm)?\s*2014", t)
            y_before: float = float(facts["years_before_2014"]) if "years_before_2014" in facts else (float(m_before.group(1)) if m_before else 0.0)
            y_from: float = float(facts["years_from_2014"]) if "years_from_2014" in facts else (float(m_from.group(1)) if m_from else 0.0)
            if "years_from_2014" not in facts and not m_before and not m_from:
                m_total_years = re.search(r"(\d+)\s*năm", t)
                if m_total_years:
                    y_from = float(m_total_years.group(1))

            m_b: int = int(facts.get("months_before_2014", 0))
            m_f: int = int(facts.get("months_from_2014", 0))
            if not m_b and not m_f:
                m_extra_months = re.search(r"(\d+)\s*tháng", t)
                if m_extra_months and "trước sinh" not in t and "liền kề" not in t:
                    m_f = int(m_extra_months.group(1))

            eligible = facts.get("is_eligible", True)
            if "đang đi làm" in t or "chưa nghỉ việc" in t:
                eligible = False

            return cls.calculate_lump_sum_bhxh(
                avg_salary=avg_sal,
                years_before_2014=y_before,
                years_from_2014=y_from,
                months_before_2014=m_b,
                months_from_2014=m_f,
                is_eligible=eligible,
            )

        # 5. Employer Accident compensation
        has_accident_kw = any(k in t for k in [
            "tai nạn", "tnlđ", "bị thương", "chấn thương", "thương tật", "gãy chân", "gãy tay", "mất sức lao động"
        ])
        is_accident_employer = (
            any(k in t for k in [
                "bồi thường tai nạn lao động", "tai nạn ở công ty", "tai nạn lao động công ty",
                "công ty phải bồi thường tai nạn", "doanh nghiệp bồi thường tai nạn", "công ty bồi thường tai nạn"
            ])
            or (has_accident_kw and any(c in t for c in ["công ty", "doanh nghiệp", "người sử dụng lao động"]) and any(bt in t for bt in ["bồi thường", "trợ cấp", "chi trả", "thanh toán", "đền bù"]))
            or ("is_employee_fault" in facts and has_accident_kw)
        )
        if is_accident_employer:
            sal = facts.get("monthly_salary") or parse_salary(t)
            imp = facts.get("impairment_percent") or parse_impairment(t)
            is_fault = facts.get("is_employee_fault", False) or any(k in t for k in ["lỗi của chính", "lỗi do người lao động", "lỗi hoàn toàn do", "vi phạm quy chuẩn", "tự ý vi phạm"])
            return cls.calculate_employer_accident_compensation(
                impairment_percent=imp,
                monthly_salary=sal,
                is_employee_fault=is_fault,
            )

        # 6. Fund Accident benefit
        is_accident_fund = (
            has_accident_kw and any(k in t for k in [
                "quỹ bảo hiểm tai nạn", "quỹ tnlđ", "quỹ trợ cấp tai nạn", "bảo hiểm tai nạn chi trả",
                "quỹ tnld-bnn", "quỹ bảo hiểm xã hội trợ cấp tai nạn"
            ])
        ) or ("years_insured" in facts and has_accident_kw)
        if is_accident_fund or (has_accident_kw and "suy giảm" in t and "%" in t and ("quỹ" in t or "hưởng gì" in t or "trợ cấp" in t)):
            imp = facts.get("impairment_percent") or parse_impairment(t)
            sal = facts.get("monthly_salary") or parse_salary(t)
            m_years = re.search(r"(\d+)\s*năm", t)
            y_ins = facts.get("years_insured") or (float(m_years.group(1)) if m_years else 1.0)
            return cls.calculate_fund_accident_benefit(
                impairment_percent=imp,
                years_insured=y_ins,
                monthly_salary=sal,
            )

        return None

