# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Wave 2 Test Suite
tests/test_phase5h_wave2.py

Covers:
1. BHXH vs BHTN routing distinction
2. Compulsory vs voluntary BHXH routing & handling
3. Benefit calculation with missing facts (Premise Gate clarification)
4. Benefit calculation with complete facts (Maternity, Sickness, Lump-sum, Employer Accident, Fund Benefit)
5. Workplace accident compensation vs insurance fund benefit distinction
6. Impairment thresholds (5%, 31%, 81%)
7. Cross-domain issue decomposition
8. Current vs Historical law effectivity
9. Structured table / numeric schedule extraction
"""
import pytest
from rag.query_router import QueryRouter
from rag.issue_decomposer import IssueDecomposer
from rag.legal_calculator import BenefitCalculator, CURRENT_REFERENCE_SALARY
from rag.material_premise_gate import MaterialPremiseGate
from rag.legal_issue_parser import LegalIssueParser


@pytest.fixture
def router():
    return QueryRouter()


@pytest.fixture
def decomposer():
    return IssueDecomposer()


@pytest.fixture
def premise_gate():
    return MaterialPremiseGate()


@pytest.fixture
def issue_parser(router):
    return LegalIssueParser(router=router)


# =============================================================================
# 1. BHXH vs BHTN Routing Distinction
# =============================================================================

def test_bhxh_vs_bhtn_routing_distinction(router):
    # BHXH questions -> SOCIAL_INSURANCE
    q_bhxh = "Tôi nghỉ việc được nhận BHXH một lần không?"
    dec_bhxh = router.route(q_bhxh)
    assert dec_bhxh.domain == "SOCIAL_INSURANCE", f"Expected SOCIAL_INSURANCE, got {dec_bhxh.domain}"

    # BHTN questions -> UNEMPLOYMENT_INSURANCE
    q_bhtn = "Tôi nghỉ việc có được hưởng trợ cấp thất nghiệp không?"
    dec_bhtn = router.route(q_bhtn)
    assert dec_bhtn.domain == "UNEMPLOYMENT_INSURANCE", f"Expected UNEMPLOYMENT_INSURANCE, got {dec_bhtn.domain}"

    # Cross-domain questions -> CROSS_DOMAIN
    q_cross = "Tôi nghỉ việc thì được hưởng cả BHXH một lần và BHTN như thế nào?"
    dec_cross = router.route(q_cross)
    assert dec_cross.domain == "CROSS_DOMAIN", f"Expected CROSS_DOMAIN, got {dec_cross.domain}"


# =============================================================================
# 2. Compulsory vs Voluntary BHXH Routing & Handling
# =============================================================================

def test_compulsory_vs_voluntary_bhxh_routing(router):
    q_compulsory = "Đối tượng tham gia BHXH bắt buộc theo Nghị định 158/2025/NĐ-CP"
    dec_comp = router.route(q_compulsory)
    assert dec_comp.domain == "SOCIAL_INSURANCE"

    q_voluntary = "Phương thức đóng và mức đóng bảo hiểm xã hội tự nguyện theo Nghị định 159/2025"
    dec_vol = router.route(q_voluntary)
    assert dec_vol.domain == "SOCIAL_INSURANCE"


# =============================================================================
# 3. Calculation with Missing Facts (Material Premise Gate Clarification)
# =============================================================================

def test_calculation_missing_facts():
    # Sickness without salary & days
    calc_sick = BenefitCalculator.extract_and_calculate("Nghỉ ốm được bao nhiêu tiền?")
    assert calc_sick is not None
    assert calc_sick.needs_clarification is True
    assert "preceding_salary" in calc_sick.missing_fields or "sick_days" in calc_sick.missing_fields

    # Maternity without salary
    calc_mat = BenefitCalculator.extract_and_calculate("Thai sản được bao nhiêu tiền?")
    assert calc_mat is not None
    assert calc_mat.needs_clarification is True
    assert "avg_salary_6m" in calc_mat.missing_fields

    # Workplace accident without impairment percentage
    calc_acc = BenefitCalculator.extract_and_calculate("Bị tai nạn lao động thì công ty phải bồi thường bao nhiêu?")
    assert calc_acc is not None
    assert calc_acc.needs_clarification is True
    assert "impairment_percent" in calc_acc.missing_fields


# =============================================================================
# 4. Deterministic Benefit Calculations (Full Facts)
# =============================================================================

def test_sickness_benefit_calculation():
    # 10 days sick, salary 12,000,000 -> 75% / 24 days * 10 = 375,000 * 10 = 3,750,000
    res = BenefitCalculator.calculate_sickness(preceding_salary=12_000_000, sick_days=10)
    assert res.needs_clarification is False
    assert res.total_amount == 3_750_000.0
    assert "Điều 28" in res.legal_basis
    assert "75%" in res.formula_description


def test_maternity_benefit_calculation():
    # 6 months leave, avg salary 10,000,000, 1 child -> 10,000,000 * 6 + 2 * 2,340,000 = 64,680,000
    res = BenefitCalculator.calculate_maternity(
        avg_salary_6m=10_000_000,
        leave_months=6,
        children_count=1,
        reference_salary=2_340_000,
    )
    assert res.needs_clarification is False
    assert res.total_amount == 64_680_000.0
    assert "Điều 38, Điều 39" in res.legal_basis


def test_lump_sum_bhxh_calculation():
    # 3 years before 2014 (3 * 1.5 = 4.5), 7 years from 2014 (7 * 2.0 = 14.0) -> total 18.5 months * 8,000,000 = 148,000,000
    res = BenefitCalculator.calculate_lump_sum_bhxh(
        years_before_2014=3,
        years_from_2014=7,
        avg_salary_all=8_000_000,
    )
    assert res.needs_clarification is False
    assert res.total_amount == 148_000_000.0
    assert "Điều 70" in res.legal_basis


def test_employer_accident_compensation_no_fault():
    # 25% impairment, 10,000,000 salary: 1.5 + (25 - 10) * 0.4 = 7.5 months -> 75,000,000
    res = BenefitCalculator.calculate_employer_accident_compensation(
        impairment_percent=25,
        monthly_salary=10_000_000,
        is_employee_fault=False,
    )
    assert res.needs_clarification is False
    assert res.total_amount == 75_000_000.0
    assert "Điều 38" in res.legal_basis


def test_employer_accident_compensation_employee_fault():
    # 25% impairment, 10,000,000 salary, employee at fault -> 40% of 75,000,000 = 30,000,000
    res = BenefitCalculator.calculate_employer_accident_compensation(
        impairment_percent=25,
        monthly_salary=10_000_000,
        is_employee_fault=True,
    )
    assert res.needs_clarification is False
    assert res.total_amount == 30_000_000.0
    assert "Điều 39" in res.legal_basis


# =============================================================================
# 5. Impairment Thresholds
# =============================================================================

def test_impairment_thresholds():
    # Impairment under 5% -> not eligible for fund benefit
    res_under_5 = BenefitCalculator.calculate_fund_accident_benefit(impairment_percent=4)
    assert res_under_5.needs_clarification is True

    # 5% to 30% -> lump-sum benefit (Điều 48)
    res_10 = BenefitCalculator.calculate_fund_accident_benefit(
        impairment_percent=10,
        years_insured=1,
        monthly_salary=10_000_000,
        reference_salary=2_340_000,
    )
    assert res_10.benefit_type == "FUND_ACCIDENT_ONE_TIME"
    assert "Điều 48" in res_10.legal_basis

    # 31% or above -> monthly benefit (Điều 49)
    res_35 = BenefitCalculator.calculate_fund_accident_benefit(
        impairment_percent=35,
        years_insured=2,
        monthly_salary=10_000_000,
        reference_salary=2_340_000,
    )
    assert res_35.benefit_type == "FUND_ACCIDENT_MONTHLY"
    assert "Điều 49" in res_35.legal_basis

    # 81% or above -> maximum employer compensation 30 months
    res_81 = BenefitCalculator.calculate_employer_accident_compensation(
        impairment_percent=81,
        monthly_salary=10_000_000,
        is_employee_fault=False,
    )
    assert res_81.total_amount == 300_000_000.0  # 30 months * 10,000,000


# =============================================================================
# 6. Cross-Domain Decomposition
# =============================================================================

def test_cross_domain_decomposition(decomposer):
    q = "Tôi bị tai nạn tại công ty và phải nghỉ điều trị, công ty phải trả gì và BHXH giải quyết gì?"
    issues = decomposer.decompose(q)
    assert len(issues) >= 2, f"Expected at least 2 decomposed issues, got {len(issues)}"

    q2 = "Tôi nghỉ việc rồi muốn nhận BHTN và BHXH một lần."
    issues2 = decomposer.decompose(q2)
    assert len(issues2) >= 2, f"Expected at least 2 decomposed issues, got {len(issues2)}"


# =============================================================================
# 7. Occupational Safety vs Normal Sickness Routing
# =============================================================================

def test_workplace_accident_vs_normal_sickness_routing(router):
    q_accident = "Tôi bị máy ép vào tay trong ca làm việc, công ty phải bồi thường gì?"
    dec_acc = router.route(q_accident)
    assert dec_acc.domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]

    q_commute = "Tôi bị tai nạn trên đường đi làm về có được tính TNLĐ không?"
    dec_com = router.route(q_commute)
    assert dec_com.domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]

    q_sick = "Tôi bị ốm thông thường phải nghỉ viện 5 ngày có được BHXH thanh toán không?"
    dec_sick = router.route(q_sick)
    assert dec_sick.domain == "SOCIAL_INSURANCE"


# =============================================================================
# 8. Phase 5H.1 Statutory Numbering & Zero Old-Law Leakage Audit
# =============================================================================

def test_current_pension_provisions_numbering():
    """Verify pension formulas are indexed to Điều 64, 65, 66 (not 54, 55, 56)."""
    meta_female = BenefitCalculator.get_formula_metadata("PENSION_FEMALE_STANDARD")
    assert meta_female is not None
    assert "Điều 66" in meta_female.article

    meta_male = BenefitCalculator.get_formula_metadata("PENSION_MALE_STANDARD")
    assert meta_male is not None
    assert "Điều 66" in meta_male.article

    meta_early = BenefitCalculator.get_formula_metadata("PENSION_EARLY_IMPAIRMENT")
    assert meta_early is not None
    assert "Điều 65" in meta_early.article
    assert "Điều 66" in meta_early.article

    # Verify pension calculation output citations
    pension_res = BenefitCalculator.calculate_pension(
        avg_salary=10_000_000,
        contribution_years=25,
        gender="female",
    )
    assert pension_res.is_eligible is True
    assert "Điều 64" in pension_res.legal_basis
    assert "Điều 66" in pension_res.legal_basis
    assert "Điều 54" not in pension_res.legal_basis
    assert "Điều 56" not in pension_res.legal_basis


# =============================================================================
# 9. Phase 5H.1 Sickness Multi-Branch Percentages (75%, 65%, 55%, 50%, 100%)
# =============================================================================

def test_sickness_all_percentage_branches():
    salary = 24_000_000  # 1,000,000/day at 100%, 750,000/day at 75%

    # 1. 75% standard
    res_75 = BenefitCalculator.calculate_sickness(preceding_salary=salary, sick_days=10, is_long_term=False)
    assert res_75.total_amount == 7_500_000.0
    assert res_75.formula_id == "SICKNESS_STANDARD_75"

    # 2. 100% armed forces
    res_100 = BenefitCalculator.calculate_sickness(preceding_salary=salary, sick_days=10, is_armed_forces=True)
    assert res_100.total_amount == 10_000_000.0
    assert res_100.formula_id == "SICKNESS_ARMED_FORCES_100"

    # 3. 65% long-term > 180 days, contribution >= 30 years
    res_65 = BenefitCalculator.calculate_sickness(
        preceding_salary=salary, sick_days=200, is_long_term=True, contribution_years=32
    )
    # daily = 24M * 0.65 / 24 = 650,000 -> 200 days = 130,000,000
    assert res_65.total_amount == 130_000_000.0
    assert res_65.formula_id == "SICKNESS_LONGTERM_65"

    # 4. 55% long-term > 180 days, contribution 15 to < 30 years
    res_55 = BenefitCalculator.calculate_sickness(
        preceding_salary=salary, sick_days=200, is_long_term=True, contribution_years=20
    )
    # daily = 24M * 0.55 / 24 = 550,000 -> 200 days = 110,000,000
    assert res_55.total_amount == 110_000_000.0
    assert res_55.formula_id == "SICKNESS_LONGTERM_55"

    # 5. 50% long-term > 180 days, contribution < 15 years
    res_50 = BenefitCalculator.calculate_sickness(
        preceding_salary=salary, sick_days=200, is_long_term=True, contribution_years=10
    )
    # daily = 24M * 0.50 / 24 = 500,000 -> 200 days = 100,000,000
    assert res_50.total_amount == 100_000_000.0
    assert res_50.formula_id == "SICKNESS_LONGTERM_50"


# =============================================================================
# 10. Phase 5H.1 Maternity History & Paternity Leaves
# =============================================================================

def test_maternity_eligibility_and_paternity():
    # Ineligible due to insufficient contribution (<6m in 12m)
    res_ineligible = BenefitCalculator.calculate_maternity(
        avg_salary_6m=10_000_000,
        contribution_months_in_12m=4,
    )
    assert res_ineligible.is_eligible is False
    assert res_ineligible.total_amount == 0.0
    assert "Điều 31" in res_ineligible.legal_basis

    # Twins childbirth: 7 months leave + 2 * 2 * 2,340,000
    res_twins = BenefitCalculator.calculate_maternity(
        avg_salary_6m=10_000_000,
        children_count=2,
    )
    # leave = 6 + 1 = 7 months -> 70,000,000; allowance = 2 * 2,340,000 * 2 = 9,360,000 -> total 79,360,000
    assert res_twins.total_amount == 79_360_000.0

    # Paternity: standard normal birth = 5 days
    res_pat_5 = BenefitCalculator.calculate_maternity(
        avg_salary_6m=12_000_000,
        is_paternity=True,
        paternity_case="normal",
    )
    # daily = 12M / 24 = 500k -> 5 * 500k = 2,500,000
    assert res_pat_5.total_amount == 2_500_000.0

    # Paternity: C-section = 7 days
    res_pat_7 = BenefitCalculator.calculate_maternity(
        avg_salary_6m=12_000_000,
        is_paternity=True,
        paternity_case="c_section",
    )
    assert res_pat_7.total_amount == 3_500_000.0


# =============================================================================
# 11. Phase 5H.1 Lump-sum Partial Year Rounding
# =============================================================================

def test_lump_sum_partial_year_rounding():
    # 2 years 4 months from 2014 -> 4 months rounds to 0.5 year -> 2.5 years * 2.0 = 5.0 months * 10M = 50,000,000
    res_half = BenefitCalculator.calculate_lump_sum_bhxh(
        avg_salary=10_000_000,
        years_from_2014=2,
        months_from_2014=4,
    )
    assert res_half.total_amount == 50_000_000.0

    # 3 years 8 months from 2014 -> 8 months rounds to 1.0 year -> 4.0 years * 2.0 = 8.0 months * 10M = 80,000,000
    res_full = BenefitCalculator.calculate_lump_sum_bhxh(
        avg_salary=10_000_000,
        years_from_2014=3,
        months_from_2014=8,
    )
    assert res_full.total_amount == 80_000_000.0

    # Ineligible gate: still currently working
    res_inelig = BenefitCalculator.calculate_lump_sum_bhxh(
        avg_salary=10_000_000,
        years_from_2014=5,
        is_eligible=False,
        ineligibility_reason="Người lao động vẫn đang thuộc đối tượng tham gia BHXH bắt buộc",
    )
    assert res_inelig.is_eligible is False
    assert res_inelig.total_amount == 0.0


# =============================================================================
# 12. Phase 5H.1 Employer Accident Compensation Brackets
# =============================================================================

def test_employer_accident_all_brackets():
    salary = 10_000_000

    # 5% -> 1.5 months = 15M
    res_5 = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=5
    )
    assert res_5.total_amount == 15_000_000.0

    # 10% -> 1.5 months = 15M
    res_10 = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=10
    )
    assert res_10.total_amount == 15_000_000.0

    # 11% -> 1.5 + (11 - 10) * 0.4 = 1.9 months = 19M
    res_11 = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=11
    )
    assert res_11.total_amount == 19_000_000.0

    # 80% -> 1.5 + (80 - 10) * 0.4 = 29.5 months = 295M
    res_80 = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=80
    )
    assert res_80.total_amount == 295_000_000.0

    # 81% -> 30.0 months = 300M
    res_81 = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=81
    )
    assert res_81.total_amount == 300_000_000.0

    # 100% / Death -> 30.0 months = 300M
    res_death = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=100
    )
    assert res_death.total_amount == 300_000_000.0

    # Employee fault 40% of 11% (19M * 0.4 = 7.6M)
    res_fault = BenefitCalculator.calculate_employer_accident_compensation(
        monthly_salary=salary, impairment_percent=11, is_employee_fault=True
    )
    assert res_fault.total_amount == 7_600_000.0


# =============================================================================
# 13. Phase 5H.1 Corpus Scope Metadata Truthfulness
# =============================================================================

def test_manifest_scope_truthfulness():
    import csv
    manifest_path = "data/raw/extended_wave2_manifest.csv"
    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # This manifest grows as later official amendments are added; exact
    # historical row/article totals are not a scope-truthfulness invariant.
    assert len(rows) >= 10
    assert len({r["doc_id"] for r in rows}) == len(rows)
    assert {"VBHN_58_2025", "TT_12_2025", "ND_141_2026"} <= {r["doc_id"] for r in rows}

    total_official = sum(int(r["official_total_articles"]) for r in rows)
    total_ingested = sum(int(r["ingested_articles"]) for r in rows)

    assert total_official >= total_ingested > 0

    for r in rows:
        expected_scope = "FULL_TEXT" if r["doc_id"] in {"TT_12_2025", "VBHN_58_2025"} else "SCOPED_EXCERPT"
        assert r["corpus_scope"] == expected_scope, f"Doc {r['doc_id']} scope must be {expected_scope}"
        assert int(r["ingested_articles"]) <= int(r["official_total_articles"])
        if expected_scope == "FULL_TEXT":
            assert int(r["ingested_articles"]) == int(r["official_total_articles"])
