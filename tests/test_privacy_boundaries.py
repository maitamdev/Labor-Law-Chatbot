"""Privacy restrictions at application boundaries, independently of the DB UI."""

import json
import time

import pytest

from app import answer_cache
from app.accounts import AccountError, Accounts
from app.admin_service import AdminService
from config.supabase import SupabaseConfig
from tests.test_accounts_admin import Response, Transport
from ui.components.account_portal import portal_markup
from ui.utils.cloud_history import SupabaseSessionManager

OWNER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"
PROFILE = dict(
    id=OWNER,
    email="owner@example.test",
    full_name="Owner",
    role="admin",
    status="active",
    email_verified=True,
    created_at="2026-10-24T00:00:00Z",
)


def test_ordinary_admin_invitation_never_uses_service_credentials():
    transport = Transport(
        [
            Response({"id": OWNER, "email_confirmed_at": "confirmed"}),
            Response([PROFILE]),
            Response({"manage_admins": False}),
        ]
    )
    client = Accounts(
        SupabaseConfig("https://example.supabase.co", "public", "server-secret"),
        {"access_token": "access", "refresh_token": "refresh", "expires_at": time.time() + 3600},
        transport,
    )
    with pytest.raises(AccountError, match="quản trị viên chính"):
        client.invite_admin("new@example.test")
    assert all("server-secret" not in str(call) for call in transport.calls)


def test_unavailable_permissions_fail_closed():
    transport = Transport(
        [
            Response({"id": OWNER, "email_confirmed_at": "confirmed"}),
            Response([PROFILE]),
            Response({"code": "PGRST202"}, 404),
        ]
    )
    client = Accounts(
        SupabaseConfig("https://example.supabase.co", "public"),
        {"access_token": "access", "refresh_token": "refresh", "expires_at": time.time() + 3600},
        transport,
    )
    assert client.admin_permissions() == {"manage_admins": False, "configured": False}


def test_ordinary_admin_has_no_role_editor_invite_or_admin_recovery_controls():
    other = {**PROFILE, "id": OTHER}
    html = portal_markup(
        "admin-user-detail",
        PROFILE,
        data={"profiles": [other], "permissions": {"manage_admins": False}},
        selected=OTHER,
    )
    assert 'data-open-dialog="invite-admin"' not in html
    assert 'data-form="admin_account_update"' not in html
    assert 'data-action="admin_reset_user"' not in html
    user = {**other, "role": "user"}
    html = portal_markup(
        "admin-user-detail", PROFILE, data={"profiles": [user], "permissions": {"manage_admins": False}}, selected=OTHER
    )
    assert 'data-form="admin_account_update"' in html
    assert '<select name="role"' not in html


def test_export_uses_authenticated_owner_not_supplied_target(monkeypatch):
    import ui.account_controller as controller

    state = {}
    monkeypatch.setattr(controller.st, "session_state", state)

    class Client:
        def identity(self):
            return PROFILE

        def rows(self, table, **kwargs):
            assert table == "conversations"
            assert kwargs["filters"] == {"owner_id": "eq." + OWNER}
            return [{"payload": {"messages": [{"content": "MY PRIVATE CHAT"}]}}]

    controller.dispatch_portal(
        Client(), PROFILE, {"type": "account_export_history", "id": OTHER, "fields": {"owner_id": OTHER}}
    )
    result = json.loads(state["portal_download"]["content"])
    assert result["conversations"][0]["messages"][0]["content"] == "MY PRIVATE CHAT"


def test_namespace_erasure_preserves_other_accounts_cache():
    answer_cache.clear()
    mine = answer_cache.make_key("private question", OWNER)
    theirs = answer_cache.make_key("private question", OTHER)
    answer_cache.put(mine, {"answer": "mine"})
    answer_cache.put(theirs, {"answer": "theirs"})
    answer_cache.clear_namespace(OWNER)
    assert answer_cache.get(mine) is None
    assert answer_cache.get(theirs)["answer"] == "theirs"
    answer_cache.clear()


def test_erased_history_invalidates_other_device_snapshot_and_stale_save():
    class Client:
        version = 0
        data = [{"id": "private", "messages": []}]

        def rpc(self, fn, body=None):
            if fn == "my_history_version":
                return self.version
            if body["expected_history_version"] != self.version:
                raise AccountError("history erased")

        def rows(self, *args, **kwargs):
            return [{"payload": c} for c in self.data]

    client = Client()
    manager = SupabaseSessionManager(client, OWNER)
    assert manager.load_conversations()
    client.data = []
    client.version = 1
    with pytest.raises(AccountError, match="erased"):
        manager.save_conversations([{"id": "old", "messages": []}])
    manager.synchronize_privacy()
    assert manager.load_conversations() == []


def test_feedback_review_uses_consent_version_and_server_rpc():
    class Client:
        def require_admin(self):
            return PROFILE

        def rpc(self, fn, body):
            assert fn == "review_feedback_safe"
            assert body["expected_privacy_version"] == 2

    AdminService(Client()).review_feedback(
        {"id": OTHER, "status": "resolved", "privacy_version": "2", "admin_note": "Reviewed"}
    )


def test_admin_loader_scopes_columns_and_excludes_feedback_owner():
    selects = {}

    class Client:
        def require_admin(self):
            return PROFILE

        def admin_permissions(self):
            return {"manage_admins": True, "configured": True}

        def rows(self, table, **kwargs):
            selects[table] = kwargs.get("select", "*")
            return []

    service = AdminService(Client())
    service.load("admin-users")
    service.load("admin-feedback")
    assert selects["profiles"] == "id,email,full_name,role,status,email_verified,created_at"
    assert "owner_id" not in selects["feedback"]
    assert "invited_by" not in selects["admin_invitations"]


def test_ordinary_admin_cannot_promote_user_or_reset_admin_password(monkeypatch):
    import ui.account_controller as controller

    monkeypatch.setattr(controller.st, "session_state", {})

    class Client:
        def require_admin(self):
            return PROFILE

        def require_security_admin(self):
            raise AccountError("Chỉ quản trị viên chính")

        def rows(self, table, **kwargs):
            return [{"id": OTHER, "email": "other@example.test", "role": "admin", "status": "active"}]

    with pytest.raises(AccountError, match="quản trị viên chính"):
        AdminService(Client()).account_update(
            {"id": OTHER, "role": "user", "status": "blocked", "reason": "Khóa admin"}
        )
    with pytest.raises(AccountError, match="quản trị viên chính"):
        controller.dispatch_portal(Client(), PROFILE, {"type": "admin_reset_user", "id": OTHER})


def test_withdrawn_feedback_cannot_be_exported(monkeypatch):
    import ui.account_controller as controller

    monkeypatch.setattr(controller.st, "session_state", {})

    class Client:
        def require_admin(self):
            return PROFILE

        def rows(self, table, **kwargs):
            return [
                {
                    "id": OTHER,
                    "share_consent": False,
                    "question": "",
                    "answer": "",
                    "comment": "Góp ý",
                    "admin_note": "",
                }
            ]

    with pytest.raises(AccountError, match="không có nội dung được chia sẻ"):
        controller.dispatch_portal(Client(), PROFILE, {"type": "admin_feedback_export", "id": OTHER})


@pytest.mark.parametrize(
    "server_msg,expected",
    [
        ("feedback privacy changed", "quyền riêng tư"),
        ("history erased; reload required", "đã được xóa ở phiên khác"),
        ("security administrator required", "quản trị viên chính"),
        ("protected administrator", "quản trị viên chính"),
        ("cannot lock or demote yourself", "tự hạ quyền"),
        ("feedback unavailable", "Không tìm thấy phản hồi"),
    ],
)
def test_known_rpc_privacy_exceptions_map_to_safe_vietnamese_errors(server_msg, expected):
    transport = Transport([Response({"code": "P0001", "message": server_msg}, 400)])
    client = Accounts(
        SupabaseConfig("https://example.supabase.co", "public"),
        {"access_token": "access", "refresh_token": "refresh", "expires_at": time.time() + 3600},
        transport,
    )
    with pytest.raises(AccountError, match=expected):
        client.rpc("review_feedback_safe", {})
