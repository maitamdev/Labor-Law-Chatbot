"""Audit filtering must agree across the screen and authorized CSV export."""
import csv
import io

import pytest

from app.accounts import AccountError
from app.admin_service import audit_day, audit_details, filter_audits


def event(action="account.update", created_at="2026-10-23T18:30:00Z", **extra):
    return dict(id="event", action=action, created_at=created_at,
                actor_id="admin-uuid", target_id="user-uuid", **extra)


def test_date_range_is_inclusive_and_uses_vietnam_day_at_utc_midnight():
    before = event(created_at="2026-10-23T16:59:59Z")
    midnight = event(created_at="2026-10-23T17:00:00Z")
    end = event(created_at="2026-10-24T16:59:59Z")
    after = event(created_at="2026-10-24T17:00:00Z")
    assert filter_audits([before, midnight, end, after], {"from":"2026-10-24", "to":"2026-10-24"}) == [midnight, end]
    assert audit_day("invalid") == ""


def test_action_and_accent_insensitive_search_combine_with_dates():
    row = event()
    other = event(action="legal_documents.update")
    assert filter_audits([row, other], {"action":"account.update", "query":"cap nhat quyen", "from":"2026-10-24"}) == [row]
    assert filter_audits([row], {"query":"24/10/2026"}) == [row]
    assert filter_audits([row], {"query":"not-found"}) == []


@pytest.mark.parametrize("filters", [[], {"from":"2026-02-30"}, {"to":"2026-1-1"}, {"from":"2026-10-25", "to":"2026-10-24"}, {"query":"x"*201}])
def test_invalid_filters_are_rejected(filters):
    with pytest.raises(AccountError):
        filter_audits([event()], filters)


def test_details_allowlist_excludes_arbitrary_sensitive_fields():
    row = event(details={"reason":"Rà soát quyền", "role":"admin", "password":"secret", "access_token":"token", "operation":{"nested":"ignored"}})
    assert audit_details(row) == [("Vai trò sau thay đổi", "admin"), ("Lý do thay đổi", "Rà soát quyền")]


def test_csv_dispatch_rechecks_admin_and_exports_only_matching_rows(monkeypatch):
    import ui.account_controller as controller
    state = {}
    monkeypatch.setattr(controller.st, "session_state", state)
    class Client:
        checks = 0
        def require_admin(self):
            self.checks += 1
        def rows(self, table):
            assert table == "admin_audit"
            return [{**event(details={"reason":"Rà soát", "password":"never-export"}), "target_id":" \t=HYPERLINK(1)"}, event(action="feedback.update")]
    client = Client()
    controller.dispatch_portal(client, {"role":"admin"}, {"type":"admin_audit_export", "filters":{"action":"account.update"}})
    assert client.checks == 1
    content = state["portal_download"]["content"].lstrip("\ufeff")
    rows = list(csv.reader(io.StringIO(content)))
    assert len(rows) == 2
    assert rows[1][2] == "account.update"
    assert rows[1][3].startswith("' \t=")
    assert "never-export" not in content
    assert "feedback.update" not in content


def test_non_admin_csv_dispatch_fails_before_reading_rows():
    from ui.account_controller import dispatch_portal
    class Denied:
        def require_admin(self):
            raise AccountError("không có quyền")
        def rows(self, table):
            pytest.fail("Read before authorization")
    with pytest.raises(AccountError, match="quyền"):
        dispatch_portal(Denied(), {"role":"user"}, {"type":"admin_audit_export"})
