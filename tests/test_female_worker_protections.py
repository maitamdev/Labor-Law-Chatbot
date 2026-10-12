"""
Unit tests for female worker protections (Article 137 BLLD 2019).
"""
def is_prohibited_discipline_during_maternity(is_pregnant: bool, child_age_months: int) -> bool:
    """Employers cannot discipline female employees during pregnancy or nursing child under 12m."""
    if is_pregnant:
        return True
    if child_age_months < 12:
        return True
    return False

def test_female_worker_discipline_protection():
    assert is_prohibited_discipline_during_maternity(is_pregnant=True, child_age_months=0) is True
    assert is_prohibited_discipline_during_maternity(is_pregnant=False, child_age_months=8) is True
    assert is_prohibited_discipline_during_maternity(is_pregnant=False, child_age_months=14) is False
