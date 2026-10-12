"""
Unit tests for occupational accident compensation thresholds (Law on OSH 2015).
"""
def calculate_accident_compensation_months(loss_pct: int, employer_fault: bool) -> float:
    """Calculate minimum months of salary compensation based on working capacity loss."""
    if loss_pct < 5:
        return 0.0
    if 5 <= loss_pct <= 10:
        base = 1.5
    else:
        # Every additional 1% increases by 0.4 months salary
        base = 1.5 + (loss_pct - 10) * 0.4
    if not employer_fault:
        return round(base * 0.4, 2)  # At least 40% if employee was at fault
    return round(base, 2)

def test_accident_compensation():
    assert calculate_accident_compensation_months(4, True) == 0.0
    assert calculate_accident_compensation_months(5, True) == 1.5
    assert calculate_accident_compensation_months(10, True) == 1.5
    assert calculate_accident_compensation_months(20, True) == 5.5
