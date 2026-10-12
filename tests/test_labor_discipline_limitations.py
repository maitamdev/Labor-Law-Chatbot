"""
Unit tests for labor discipline statute of limitations (Article 123 BLLD 2019).
"""
def get_discipline_statute_of_limitations_months(is_financial_property_violation: bool) -> int:
    return 12 if is_financial_property_violation else 6

def test_labor_discipline_limitations():
    assert get_discipline_statute_of_limitations_months(False) == 6
    assert get_discipline_statute_of_limitations_months(True) == 12
