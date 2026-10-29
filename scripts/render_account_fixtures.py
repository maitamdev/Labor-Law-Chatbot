"""Render real components with test-only data for frontend interaction checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    from ui.components.account_portal import portal_markup
    from ui.components.approved_layout import layout_markup

    profile = {
        "id": "00000000-0000-0000-0000-000000000001",
        "full_name": "Mai Trần Thiện Tâm",
        "email": "tam@example.com",
        "role": "admin",
        "status": "active",
        "email_verified": True,
        "created_at": "2026-10-22T00:00:00Z",
    }
    fixtures = {
        "home": layout_markup("home", [], [], False, ""),
        "chat": layout_markup(
            "chat",
            [
                {"id": "q1", "role": "user", "content": "Private question"},
                {"id": "a1", "role": "assistant", "content": "Private answer", "structured_data": {}},
            ],
            [],
            False,
            "c1",
            username="Test User",
        ),
        "account-password": portal_markup("account-password", profile),
        "admin-users": portal_markup("admin-users", profile, {"profiles": [profile]}),
    }
    directory = ROOT / "storage" / "test_tools"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ui-fixtures.json").write_text(json.dumps(fixtures, ensure_ascii=False), encoding="utf-8")
    print("Rendered test-only component fixtures into storage/test_tools/ui-fixtures.json")


if __name__ == "__main__":
    main()
