"""
Unit tests for overtime and night work wage calculation (Article 98 BLLD 2019).
"""
def calculate_overtime_multiplier(day_type: str, is_night: bool = False) -> float:
    base = 1.5 if day_type == "normal" else (2.0 if day_type == "weekly_off" else 3.0)
    if is_night:
        # Extra 30% for night work + extra 20% on overtime base
        base = base + 0.3 + (0.2 * (1.0 if day_type == "normal" else (1.5 if day_type == "weekly_off" else 2.0)))
    return round(base, 2)

def test_overtime_multipliers():
    assert calculate_overtime_multiplier("normal", False) == 1.5
    assert calculate_overtime_multiplier("weekly_off", False) == 2.0
    assert calculate_overtime_multiplier("holiday", False) == 3.0
    assert calculate_overtime_multiplier("normal", True) == 2.0  # 1.5 + 0.3 + 0.2
