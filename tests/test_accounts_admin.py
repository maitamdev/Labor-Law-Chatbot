"""Account boundaries, consent and private persistence without real credentials."""

import copy
import time

import pytest

from app.accounts import AccountError, Accounts
from app.admin_service import AdminService, submit_feedback
from config.supabase import SupabaseConfig
from ui.utils.cloud_history import SupabaseSessionManager


class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.ok = status < 400
        self.status_code = status
        self.headers = {"Content-Type": "application/json"}
        self.content = b"{}"

    def json(self):
        return self.data


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


CONFIG = SupabaseConfig("https://example.supabase.co", "public-test", "server-secret")
USER_ID = "00000000-0000-0000-0000-000000000001"
PROFILE = {
    "id": USER_ID,
    "email": "user@example.com",
    "full_name": "Test User",
    "role": "user",
    "status": "active",
    "email_verified": True,
}


def session():
    return {"access_token": "user-access", "refresh_token": "user-refresh", "expires_at": time.time() + 3600}


def test_signup_only_sends_name_not_role_or_password_confirmation():
    transport = Transport([Response({"user": {"id": USER_ID}})])
    client = Accounts(CONFIG, transport=transport)
    client.signup("USER@example.com", "not-a-real-password", "Test User", "not-a-real-password")
    body = transport.calls[0][2]["json"]
    assert body["data"] == {"full_name": "Test User"}
    assert body["email"] == "user@example.com"
    assert not client.session
    assert "server-secret" not in str(transport.calls)


def test_role_comes_from_database_not_user_metadata():
    transport = Transport(
        [
            Response({"id": USER_ID, "email_confirmed_at": "2026-10-22", "user_metadata": {"role": "admin"}}),
            Response([PROFILE]),
        ]
    )
    client = Accounts(CONFIG, session(), transport)
    with pytest.raises(AccountError, match="không có quyền"):
        client.require_admin()


def test_blocked_user_is_rejected_even_with_a_valid_token():
    transport = Transport(
        [Response({"id": USER_ID, "email_confirmed_at": "2026-10-22"}), Response([{**PROFILE, "status": "blocked"}])]
    )
    with pytest.raises(AccountError, match="khóa"):
        Accounts(CONFIG, session(), transport).identity()


def test_session_refresh_is_private_and_not_shared_between_accounts():
    a = Accounts(
        CONFIG,
        {"access_token": "old", "refresh_token": "refresh-a", "expires_at": 0},
        Transport([Response({"access_token": "new-a", "refresh_token": "new-r-a", "expires_in": 3600})]),
    )
    b = Accounts(CONFIG, session(), Transport([]))
    assert a.token() == "new-a"
    assert b.token() == "user-access"


def test_unconfigured_auth_has_actionable_error_without_network():
    transport = Transport([])
    with pytest.raises(AccountError, match="Chưa kết nối Supabase"):
        Accounts(SupabaseConfig(), transport=transport).login("a@example.com", "anything")
    assert not transport.calls


def test_raw_server_errors_never_expose_keys_or_response_details():
    transport = Transport([Response({"message": "secret SQL password server-secret"}, 500)])
    with pytest.raises(AccountError) as error:
        Accounts(CONFIG, transport=transport).recover("a@example.com")
    assert "server-secret" not in str(error.value)
    assert "SQL" not in str(error.value)


def test_change_password_checks_current_password_before_mutation():
    transport = Transport(
        [
            Response({"id": USER_ID, "email_confirmed_at": "2026-10-22"}),
            Response([PROFILE]),
            Response({"error_code": "invalid_credentials"}, 400),
        ]
    )
    client = Accounts(CONFIG, session(), transport)
    with pytest.raises(AccountError, match="hiện tại"):
        client.change_password("wrong", "new-test-password", "new-test-password")
    assert not any(method == "PUT" for method, _, _ in transport.calls)


def test_consent_false_discards_message_text_and_identifiers():
    class Client:
        saved = None

        def identity(self):
            return PROFILE

        def rest(self, method, table, body):
            self.saved = body

    client = Client()
    submit_feedback(
        client,
        rating="down",
        question="PRIVATE QUESTION",
        answer="PRIVATE ANSWER",
        comment="Needs source",
        share_consent=False,
    )
    assert client.saved["question"] == client.saved["answer"] == ""
    assert client.saved["comment"] == "Needs source"
    assert not {"conv_id", "msg_id", "title"} & client.saved.keys()
    submit_feedback(client, rating="down", question="SHARED", answer="SHARED ANSWER", share_consent=True)
    assert client.saved["question"] == "SHARED"


def test_admin_loader_never_queries_private_conversations():
    class Client:
        tables = []

        def require_admin(self):
            return {**PROFILE, "role": "admin"}

        def rpc(self, *args):
            return {}

        def admin_permissions(self):
            return {"manage_admins": False, "configured": True}

        def rows(self, table, **kwargs):
            self.tables.append(table)
            return []

    client = Client()
    for view in [
        "admin-dashboard",
        "admin-users",
        "admin-user-detail",
        "admin-documents",
        "admin-feedback",
        "admin-operations",
        "admin-audit",
        "admin-settings",
    ]:
        AdminService(client).load(view)
    assert "conversations" not in client.tables
    assert "auth.users" not in client.tables


def test_cloud_history_mutations_are_owner_scoped_and_atomic():
    class Client:
        def __init__(self):
            self.data = []
            self.calls = []

        def rows(self, table, **kwargs):
            assert kwargs["filters"] == {"owner_id": "eq." + USER_ID}
            return [{"payload": copy.deepcopy(c)} for c in self.data]

        def rpc(self, function, body=None):
            if function == "my_history_version":
                return 0
            self.calls.append((function, body))
            current = {c["id"]: c for c in self.data}
            for c in body["changed"]:
                current[c["id"]] = copy.deepcopy(c)
            for key in body["deleted"]:
                current.pop(key, None)
            self.data = list(current.values())

    client = Client()
    manager = SupabaseSessionManager(client, USER_ID)
    conv = manager.create_conversation()
    manager.append_message(conv["id"], "user", "Question")
    manager.append_message(conv["id"], "assistant", "Answer")
    assert len(manager.get_conversation(conv["id"])["messages"]) == 2
    manager.delete_conversation(conv["id"])
    assert client.data == []
    assert all(call[0] == "save_my_conversations" for call in client.calls)


def test_business_backup_excludes_accounts_chats_and_auth(tmp_path, monkeypatch):
    from app import admin_jobs

    class Client:
        tables = []

        def require_admin(self):
            return {**PROFILE, "role": "admin"}

        def rows(self, table, **kwargs):
            self.tables.append(table)
            return []

    client = Client()
    monkeypatch.setattr(admin_jobs, "BACKUP_DIR", tmp_path)
    admin_jobs.create_backup(client)
    assert client.tables == ["legal_documents", "app_settings"]
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_portal_denies_non_admin_and_escapes_untrusted_names():
    from ui.components.account_portal import portal_markup

    html = portal_markup("admin-users", PROFILE, {"profiles": []})
    assert "403" in html
    assert "Mời quản trị viên" not in html
    html = portal_markup("account-profile", {**PROFILE, "full_name": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "view",
    [
        "admin-dashboard",
        "admin-users",
        "admin-user-detail",
        "admin-documents",
        "admin-document-add",
        "admin-feedback",
        "admin-operations",
        "admin-audit",
        "admin-settings",
        "account-profile",
        "account-password",
        "account-recovery",
        "account-reset-success",
    ],
)
def test_all_portal_views_render_empty_state_without_fake_counts(view):
    from ui.components.account_portal import portal_markup

    html = portal_markup(view, {**PROFILE, "role": "admin"}, data={})
    assert "VietLabor" in html
    assert "1.284" not in html
    assert "128</strong>" not in html
    assert "Dữ liệu minh họa" not in html


def test_password_and_recovery_pages_have_distinct_requirements():
    from ui.components.account_portal import portal_markup

    change = portal_markup("account-password", PROFILE)
    reset = portal_markup("account-recovery")
    assert 'name="current_password"' in change
    assert 'name="current_password"' not in reset
    assert 'data-form="account_reset_password"' in reset


@pytest.mark.parametrize(
    "source",
    [
        "https://congbao.chinhphu.vn/van-ban/test",
        "https://vanban.chinhphu.vn/test",
        "https://chinhphu.vn/test",
        "https://moj.gov.vn/test",
    ],
)
def test_official_source_accepts_the_government_hosts_used_by_the_ui(source):
    from app.admin_service import official_source

    assert official_source(source) == source


@pytest.mark.parametrize(
    "source",
    [
        "https://chinhphu.vn.example.com/test",
        "https://fakechinhphu.vn/test",
        "http://congbao.chinhphu.vn/test",
        "https://user:secret@moj.gov.vn/test",
    ],
)
def test_official_source_rejects_lookalike_hosts_and_unsafe_urls(source):
    from app.admin_service import official_source

    with pytest.raises(AccountError):
        official_source(source)


def test_zero_counts_are_visible_and_empty_chart_has_an_explanation():
    from ui.components.account_portal import portal_markup

    html = portal_markup("admin-dashboard", {**PROFILE, "role": "admin"}, data={"stats": {"users": 0, "queries": 0}})
    assert html.count("<strong>0</strong>") >= 3
    assert "Chưa có lượt tra cứu" in html


def test_user_invite_without_service_credentials_is_explained():
    from ui.components.account_portal import portal_markup

    html = portal_markup(
        "admin-users", {**PROFILE, "role": "admin"}, data={"can_invite": False, "permissions": {"manage_admins": True}}
    )
    assert 'data-open-dialog="invite-admin"' in html
    assert "khóa máy chủ" in html
    assert 'data-form="admin_invite"' not in html


def test_bad_health_result_does_not_break_the_operations_page():
    from ui.components.account_portal import portal_markup

    html = portal_markup(
        "admin-operations",
        {**PROFILE, "role": "admin"},
        data={
            "admin_jobs": [
                {
                    "id": USER_ID,
                    "kind": "health",
                    "status": "succeeded",
                    "result": "not JSON",
                    "created_at": "2026-10-22T00:00:00Z",
                }
            ]
        },
    )
    assert "Vận hành AI" in html
    assert "Mô hình AI" in html


def test_admin_invitation_uses_server_credentials_and_redirect_url():
    transport = Transport(
        [
            Response({"id": USER_ID, "email_confirmed_at": "2026-10-22"}),
            Response([{**PROFILE, "role": "admin"}]),
            Response({"manage_admins": True}),
            Response("test-invitation-id"),
            Response({"id": "new-user"}),
        ]
    )
    client = Accounts(CONFIG, session(), transport)
    client.invite_admin("new-admin@example.com")
    method, url, options = transport.calls[-1]
    assert method == "POST" and url.endswith("/auth/v1/invite")
    assert options["headers"]["apikey"] == CONFIG.service_key
    assert options["params"]["redirect_to"] == CONFIG.public_url
