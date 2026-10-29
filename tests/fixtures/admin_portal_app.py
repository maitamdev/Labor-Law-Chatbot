"""Isolated UI test app. No real Auth, Supabase connection, or production writes."""

import copy
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st

from app.accounts import AccountError
from config.supabase import SupabaseConfig
from ui.account_controller import render_account_portal
from ui.utils.cloud_history import SupabaseSessionManager

ADMIN_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"
DOCUMENT_ID = "00000000-0000-0000-0000-000000000003"
FEEDBACK_ID = "00000000-0000-0000-0000-000000000004"
SHARED_FEEDBACK_ID = "00000000-0000-0000-0000-000000000005"
OTHER_FEEDBACK_ID = "00000000-0000-0000-0000-000000000007"
ORDINARY_ADMIN_ID = "00000000-0000-0000-0000-000000000008"
NOW = "2026-10-22T08:00:00+00:00"


class FixtureAccounts:
    config = SupabaseConfig("https://fixture.invalid", "fixture-only")

    def __init__(self):
        self.session = {"fixture": True}
        self.calls = []
        self.files = {}
        self.activity_counts = [0] * 7
        self.actor_id = ADMIN_ID
        self.history_versions = {}
        self.simulate_concurrent_withdraw = False
        self.stale_device = None
        self.stale_save_blocked = False
        self.tables = {
            "profiles": [
                dict(id=ADMIN_ID, email="admin@example.test", full_name="Thiện Tâm", role="admin", status="active", email_verified=True, created_at=NOW),
                dict(id=USER_ID, email="user@example.test", full_name="Nguyễn Minh Anh", role="user", status="active", email_verified=True, created_at=NOW),
            ],
            "app_settings": [dict(id="general", app_name="VietLaborAI", workspace_name="Quản trị VietLaborAI", updated_at=NOW)],
            "legal_documents": [dict(id=DOCUMENT_ID, title="Văn bản kiểm thử giao diện", document_no="TEST-01", issuer="Quốc hội", effective_from="2026-01-01", source_url="https://congbao.chinhphu.vn/test", validity="CURRENT", status="review", updated_at=NOW, created_at=NOW, preview_text="Nội dung kiểm thử, không đưa vào kho sản xuất.", review_note="", storage_path="fixture/source.pdf")],
            "feedback": [dict(id=FEEDBACK_ID, comment="Cần kiểm tra căn cứ trích dẫn", rating="down", share_consent=False, question="", answer="", status="pending", admin_note="", created_at=NOW), dict(id=SHARED_FEEDBACK_ID, comment="Phản hồi đã cho phép chia sẻ", rating="up", share_consent=True, question="Câu hỏi được chia sẻ trong kiểm thử", answer="Câu trả lời được chia sẻ trong kiểm thử", status="pending", admin_note="", created_at=NOW)],
            "admin_jobs": [],
            "admin_invitations": [],
            "admin_audit": [
                dict(id=str(uuid.uuid4()), actor_id=None, action="administrator.bootstrap", target_id=ADMIN_ID, created_at=NOW),
                dict(id=str(uuid.uuid4()), actor_id=ADMIN_ID, action="legal_documents.update", target_id=DOCUMENT_ID, created_at="2026-10-22T07:00:00+00:00"),
                dict(id=str(uuid.uuid4()), actor_id=ADMIN_ID, action="feedback.update", target_id=FEEDBACK_ID, created_at="2026-10-21T09:00:00+00:00"),
            ],
        }
        for row in self.tables["feedback"]:
            row.update(owner_id=USER_ID, privacy_version=0)
        self.tables["conversations"] = [
            dict(id="user-private",owner_id=USER_ID,payload={"id":"user-private","messages":[{"role":"user","content":"MY OWN PRIVATE HISTORY"}]}),
            dict(id="admin-private",owner_id=ADMIN_ID,payload={"id":"admin-private","messages":[{"role":"user","content":"OTHER ACCOUNT PRIVATE HISTORY"}]}),
        ]

    def identity(self):
        return next(row for row in self.tables["profiles"] if row["id"] == self.actor_id)

    def require_admin(self):
        profile = self.identity()
        if profile["role"] != "admin" or profile["status"] != "active":
            raise AccountError("Bạn không có quyền quản trị.")
        return profile

    def admin_permissions(self):
        self.require_admin()
        return {"manage_admins":self.actor_id == ADMIN_ID, "configured":True}

    def require_security_admin(self):
        if not self.admin_permissions()["manage_admins"]:
            raise AccountError("Chỉ quản trị viên chính được quản lý quyền admin.")

    def rows(self, table, **kwargs):
        self.calls.append(("rows", table))
        rows = self.tables[table]
        for key, value in (kwargs.get("filters") or {}).items():
            if value.startswith("eq."):
                rows = [r for r in rows if str(r.get(key)) == value[3:]]
        select = kwargs.get("select", "*")
        if select != "*":
            rows = [{key:row.get(key) for key in select.split(",")} for row in rows]
        elif table == "feedback":
            rows = [{k: v for k, v in row.items() if k != "owner_id"} for row in rows]
        result = copy.deepcopy(rows)
        if table == "feedback" and self.simulate_concurrent_withdraw:
            self.simulate_concurrent_withdraw = False
            for row in self.tables["feedback"]:
                if row["id"] == SHARED_FEEDBACK_ID:
                    row.update(share_consent=False, question="", answer="", admin_note="", privacy_version=row["privacy_version"] + 1)
        return result

    def rpc(self, function, body=None):
        self.calls.append(("rpc", function))
        if function == "my_admin_permissions":
            return self.admin_permissions()
        if function == "my_history_version":
            return self.history_versions.get(self.actor_id, 0)
        if function == "my_feedback":
            return [{key:row[key] for key in ("id","rating","comment","share_consent","status","created_at")}
                    for row in self.tables["feedback"] if row["owner_id"] == self.actor_id]
        if function in {"withdraw_my_feedback_consent", "delete_my_feedback"}:
            row = next((row for row in self.tables["feedback"] if row["id"] == body["feedback_id"] and row["owner_id"] == self.actor_id), None)
            if row is None:
                raise AccountError("Không tìm thấy phản hồi của bạn.")
            if function == "delete_my_feedback":
                self.tables["feedback"].remove(row)
            else:
                row.update(share_consent=False,question="",answer="",admin_note="",privacy_version=row["privacy_version"]+1)
            return None
        if function == "save_my_conversations":
            current_v = self.history_versions.get(self.actor_id, 0)
            if body.get("expected_history_version") != current_v:
                raise AccountError("Lịch sử trò chuyện đã được xóa ở phiên khác. Vui lòng tải lại trang.")
            existing = {r["id"]: r for r in self.tables["conversations"] if r["owner_id"] == self.actor_id}
            for item in body.get("changed") or []:
                existing[item["id"]] = dict(id=item["id"], owner_id=self.actor_id, payload=copy.deepcopy(item))
            for del_id in body.get("deleted") or []:
                existing.pop(del_id, None)
            others = [r for r in self.tables["conversations"] if r["owner_id"] != self.actor_id]
            self.tables["conversations"] = others + list(existing.values())
            return None
        if function == "delete_my_conversations":
            self.tables["conversations"] = [row for row in self.tables["conversations"] if row["owner_id"] != self.actor_id]
            self.history_versions[self.actor_id] = self.history_versions.get(self.actor_id,0)+1
            if self.stale_device is not None:
                try:
                    self.stale_device.save_conversations([{"id": "resurrected-chat", "messages": [{"role": "user", "content": "STALE RESURRECTED CHAT"}]}])
                except AccountError:
                    self.stale_save_blocked = True
            return None
        if function == "review_feedback_safe":
            self.require_admin()
            row = next((row for row in self.tables["feedback"] if row["id"] == body["target_feedback"]), None)
            if row is None or row["privacy_version"] != body["expected_privacy_version"]:
                raise AccountError("Phản hồi đã thay đổi quyền riêng tư. Tải lại trước khi lưu.")
            row.update(status=body["new_status"],admin_note=body["new_note"])
            return None
        if function == "admin_dashboard":
            return dict(users=len(self.tables["profiles"]), queries=sum(self.activity_counts), pending_feedback=sum(r["status"] != "resolved" for r in self.tables["feedback"]), pending_documents=1, median_ms=15300 if any(self.activity_counts) else None, p95_ms=None, daily=[dict(day=f"2026-10-{d}", count=self.activity_counts[d-16]) for d in range(16, 23)])
        if function == "admin_update_account":
            self.require_admin()
            user = next(r for r in self.tables["profiles"] if r["id"] == body["target_id"])
            if (user["role"] == "admin" or body["new_role"] == "admin") and not self.admin_permissions()["manage_admins"]:
                raise AccountError("Chỉ quản trị viên chính được quản lý quyền admin.")
            if user["id"] == self.actor_id and (body["new_role"] != "admin" or body["new_status"] != "active"):
                raise AccountError("Không thể tự hạ quyền hoặc khóa tài khoản đang sử dụng.")
            if user["id"] == ADMIN_ID and self.actor_id != ADMIN_ID:
                raise AccountError("Chỉ quản trị viên chính được quản lý quyền admin.")
            user.update(role=body["new_role"], status=body["new_status"])
            self.tables["admin_audit"].insert(0, dict(id=str(uuid.uuid4()), actor_id=self.actor_id,
                action="account.update", target_id=user["id"], created_at=NOW,
                details={"role":body["new_role"], "status":body["new_status"], "reason":body["reason"]}))
        elif function == "approve_legal_document":
            doc = next(r for r in self.tables["legal_documents"] if r["id"] == body["target_document"])
            if doc["updated_at"] != body["expected_updated_at"] or doc["status"] not in {"draft", "review"}:
                raise AccountError("Văn bản đã thay đổi.")
            doc.update(status="approved", reviewed_by=ADMIN_ID, reviewed_at=NOW)
            return self.rest("POST", "admin_jobs", body={"kind":"index", "document_id":doc["id"]})[0]["id"]
        return None

    def rest(self, method, table, *, params=None, body=None, **kwargs):
        self.calls.append((method, table))
        if method == "GET":
            return self.rows(table, filters=params)
        if method == "PATCH":
            updated = []
            for row in self.tables[table]:
                if all(not str(value).startswith("eq.") or str(row.get(key)) == value[3:]
                       for key, value in (params or {}).items()):
                    row.update(body)
                    updated.append(copy.deepcopy(row))
            return updated if kwargs.get("prefer") == "return=representation" else None
        if method == "POST":
            row = dict(id=str(uuid.uuid4()), created_at=NOW, status="pending", result="")
            row.update(body)
            self.tables[table].insert(0, row)
            return [copy.deepcopy(row)]

    def upload(self, path, content):
        self.files[path] = content

    def recover(self, email):
        self.calls.append(("recover", email))

    def invite_admin(self, email):
        raise AccountError("Ứng dụng kiểm thử không gửi email ra bên ngoài.")

    def update_name(self, name):
        self.identity()["full_name"] = name

    def change_password(self, current, new, confirm, **kwargs):
        if not kwargs.get("recovery") and current != "fixture-password":
            raise AccountError("Mật khẩu hiện tại không đúng.")
        if new != confirm or len(new) < 8:
            raise AccountError("Mật khẩu mới không hợp lệ.")
        self.calls.append(("password", "updated"))

    def logout(self, scope="local"):
        if scope != "others":
            self.session.clear()


st.set_page_config(layout="wide")
st.html("<style>" + (ROOT / "ui/styles/app.css").read_text(encoding="utf-8") + "</style>")
if "fixture_client" not in st.session_state:
    st.session_state["fixture_client"] = FixtureAccounts()
    st.session_state["portal_view"] = "admin-dashboard"
client = st.session_state["fixture_client"]
if st.query_params.get("scenario") == "recovery":
    del st.query_params["scenario"]
    st.session_state.update(portal_view="account-recovery", _recovery_client=client, _recovery_type="recovery")
elif st.query_params.get("scenario") == "activity":
    del st.query_params["scenario"]
    client.activity_counts = [2, 5, 3, 0, 6, 7, 4]
    st.session_state["portal_view"] = "admin-dashboard"
elif st.query_params.get("scenario") == "user-privacy":
    del st.query_params["scenario"]
    client.actor_id = USER_ID
    if not any(r["id"] == OTHER_FEEDBACK_ID for r in client.tables["feedback"]):
        client.tables["feedback"].append(
            dict(
                id=OTHER_FEEDBACK_ID,
                owner_id=ADMIN_ID,
                comment="Phản hồi của tài khoản khác",
                rating="down",
                share_consent=True,
                question="Câu hỏi riêng của tài khoản khác",
                answer="Câu trả lời riêng của tài khoản khác",
                status="pending",
                admin_note="",
                created_at=NOW,
                privacy_version=0,
            )
        )
    client.stale_device = SupabaseSessionManager(client, USER_ID)
    client.stale_device.load_conversations()
    st.session_state["portal_view"] = "account-privacy"
elif st.query_params.get("scenario") == "ordinary-admin":
    del st.query_params["scenario"]
    if not any(r["id"] == ORDINARY_ADMIN_ID for r in client.tables["profiles"]):
        client.tables["profiles"].append(
            dict(
                id=ORDINARY_ADMIN_ID,
                email="mod@example.test",
                full_name="Trần Quản Trị",
                role="admin",
                status="active",
                email_verified=True,
                created_at=NOW,
            )
        )
    client.actor_id = ORDINARY_ADMIN_ID
    st.session_state["portal_view"] = "admin-users"
elif st.query_params.get("scenario") == "stale-feedback-withdraw":
    del st.query_params["scenario"]
    client.actor_id = ADMIN_ID
    client.simulate_concurrent_withdraw = True
    st.session_state["portal_view"] = "admin-feedback"
    st.session_state["portal_selected"] = SHARED_FEEDBACK_ID

# Jobs stay in this fixture's in-memory store and never touch real files/models.
import app.admin_jobs


def fixture_job(accounts, job_id, *, admin_checked=False):
    job = next(r for r in accounts.tables["admin_jobs"] if r["id"] == job_id)
    job.update(status="succeeded", finished_at=NOW, result='{"ollama":"ready"}' if job["kind"] == "health" else "Hoàn tất tác vụ kiểm thử")


app.admin_jobs.launch = fixture_job
app.admin_jobs.list_backups = lambda: [dict(id="00000000-0000-0000-0000-000000000006", created_at=1792656000, size=1024)]
render_account_portal(client, client.identity())
st.button("Mở quản trị kiểm thử", on_click=lambda: st.session_state.update(portal_view="admin-dashboard"))
