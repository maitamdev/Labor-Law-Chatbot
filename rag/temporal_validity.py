"""
Temporal validity checker for legal documents.
Tracks effective dates, expiration, and transitional provisions.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class StatuteValidity:
    code: str
    effective_from: date
    effective_to: Optional[date] = None
    status: str = "active"  # active, amended, expired

STATUTE_REGISTRY = {
    "BLLD_2019": StatuteValidity("BLLD_2019", date(2021, 1, 1), None, "active"),
    "BLLD_2012": StatuteValidity("BLLD_2012", date(2013, 5, 1), date(2020, 12, 31), "expired"),
    "ND_145_2020": StatuteValidity("ND_145_2020", date(2021, 2, 1), None, "active"),
    "ND_12_2022": StatuteValidity("ND_12_2022", date(2022, 1, 17), None, "active"),
    "ND_283_2026": StatuteValidity("ND_283_2026", date(2026, 1, 1), None, "active"),
}

def is_valid_at_date(statute_code: str, query_date: Optional[date] = None) -> bool:
    """Check if statute is in force at given date (defaults to today)."""
    if query_date is None:
        query_date = date.today()
    record = STATUTE_REGISTRY.get(statute_code)
    if not record:
        return True
    if record.effective_from > query_date:
        return False
    if record.effective_to and record.effective_to < query_date:
        return False
    return True
