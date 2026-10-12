"""
Unit tests for severance allowance calculation (Article 46 BLLD 2019, Decree 145/2020).
"""
def calculate_severance_allowance(working_years: float, avg_salary_6m: float) -> float:
    """Calculate severance pay: 0.5 month salary per eligible working year."""
    if working_years < 1.0:
        return 0.0
    return working_years * 0.5 * avg_salary_6m

def test_severance_allowance_calculation():
    # 3 years eligible, average 6 months salary = 10,000,000 VND
    payout = calculate_severance_allowance(3.0, 10_000_000)
    assert payout == 15_000_000
    # Under 12 months = 0
    assert calculate_severance_allowance(0.8, 10_000_000) == 0.0
