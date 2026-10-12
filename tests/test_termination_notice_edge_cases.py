"""
Unit tests for statutory termination notice periods (Article 35 & 36 BLLD 2019).
"""
def calculate_required_notice_days(contract_type: str) -> int:
    """Return statutory notice days under Article 35/36 BLLD 2019."""
    if contract_type == "indefinite":
        return 45
    elif contract_type == "fixed_12_to_36":
        return 30
    elif contract_type == "fixed_under_12":
        return 3
    raise ValueError(f"Unknown contract type: {contract_type}")

def test_statutory_notice_periods():
    assert calculate_required_notice_days("indefinite") == 45
    assert calculate_required_notice_days("fixed_12_to_36") == 30
    assert calculate_required_notice_days("fixed_under_12") == 3
