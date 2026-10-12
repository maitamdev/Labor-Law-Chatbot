"""
Unit tests for probation statutory rules (Articles 24, 25, 27 BLLD 2019).
"""
def max_probation_days(job_tier: str) -> int:
    mapping = {
        "manager": 180,
        "college_or_above": 60,
        "vocational_secondary": 30,
        "simple_work": 0,
    }
    return mapping.get(job_tier, 60)

def test_max_probation_days():
    assert max_probation_days("manager") == 180
    assert max_probation_days("college_or_above") == 60
    assert max_probation_days("vocational_secondary") == 30
    assert max_probation_days("simple_work") == 0
