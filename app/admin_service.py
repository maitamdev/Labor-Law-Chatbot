"""Administrative business operations. Every entry rechecks the trusted role."""

from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from app.accounts import AccountError

_ADMIN_EXECUTOR = ThreadPoolExecutor(max_workers=10, thread_name_prefix="vietlabor-admin")

VIETNAM_TIME = timezone(timedelta(hours=7))
AUDIT_LABELS = {
    "administrator.bootstrap": "Thiết lập quản trị viên",
    "administrator.invite": "Gửi lời mời admin",
    "administrator.accept_invitation": "Chấp nhận lời mời admin",
    "administrator.cancel_invitation": "Hủy lời mời admin",
    "account.update": "Cập nhật quyền tài khoản",
    "legal_documents.insert": "Thêm văn bản",
    "legal_documents.update": "Cập nhật văn bản",
    "feedback.update": "Xử lý phản hồi",
    "app_settings.update": "Cập nhật cài đặt",
    "admin_jobs.insert": "Tạo tác vụ vận hành",
    "admin_jobs.update": "Cập nhật tác vụ",
    "business_metadata.restore": "Khôi phục metadata",
}


def audit_day(value):
    """Use the same Vietnam calendar day in the screen and exported CSV."""
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(VIETNAM_TIME).date().isoformat()
    except (ValueError, TypeError):
        return ""


def audit_search_text(row):
    day = audit_day(row.get("created_at"))
    return " ".join(str(v or "") for v in (
        row.get("created_at"), day, "/".join(reversed(day.split("-"))),
        row.get("actor_id") or "Hệ thống", row.get("target_id") or "Hệ thống",
        row.get("action"), AUDIT_LABELS.get(row.get("action"), ""),
    ))


def normalized_search(value):
    text = unicodedata.normalize("NFD", str(value).lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def filter_audits(rows, filters=None):
    if filters is not None and not isinstance(filters, dict):
        raise AccountError("Bộ lọc nhật ký không hợp lệ.")
    filters = filters or {}
    start, end = str(filters.get("from", "")), str(filters.get("to", ""))
    for value in (start, end):
        if value:
            try:
                if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") != value:
                    raise ValueError
            except ValueError:
                raise AccountError("Ngày lọc nhật ký không hợp lệ.") from None
    if start and end and start > end:
        raise AccountError("Ngày kết thúc phải từ ngày bắt đầu trở đi.")
    action = str(filters.get("action", ""))
    query = str(filters.get("query", ""))
    if len(query) > 200 or len(action) > 120:
        raise AccountError("Bộ lọc nhật ký quá dài.")
    query = normalized_search(query.strip())
    return [row for row in rows if
            (not action or row.get("action") == action)
            and (not start or audit_day(row.get("created_at")) >= start)
            and (not end or bool(audit_day(row.get("created_at"))) and audit_day(row.get("created_at")) <= end)
            and query in normalized_search(audit_search_text(row))]


def audit_details(row):
    """Expose only the audit fields our workflows intentionally record."""
    details = row.get("details")
    if not isinstance(details, dict):
        return []
    labels = {"operation": "Thao tác dữ liệu", "role": "Vai trò sau thay đổi", "status": "Trạng thái sau thay đổi", "reason": "Lý do thay đổi"}
    return [(label, str(details[key])[:500]) for key, label in labels.items()
            if key in details and isinstance(details[key], (str, int, bool))]


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def safe_id(value):
    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        raise AccountError("Mã dữ liệu không hợp lệ.") from None


def official_source(value):
    parsed = urlsplit(str(value).strip())
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or not (host.endswith(".gov.vn") or host == "gov.vn" or host == "chinhphu.vn" or host.endswith(".chinhphu.vn"))
    ):
        raise AccountError("Cần đường dẫn HTTPS đến nguồn chính thức thuộc gov.vn hoặc chinhphu.vn.")
    return str(value).strip()[:1500]


class AdminService:
    def __init__(self, accounts):
        self.accounts = accounts

    def load(self, view, *, preload_all=False):
        self.accounts.require_admin()
        select_columns = {
            "profiles": "id,email,full_name,role,status,email_verified,created_at",
            "feedback": "id,rating,comment,share_consent,question,answer,status,admin_note,created_at,privacy_version",
            "admin_audit": "id,actor_id,action,target_id,details,created_at",
        }
        if preload_all and getattr(self.accounts, "_real_transport", False):
            all_tables = ("profiles", "legal_documents", "feedback", "admin_jobs", "admin_audit")
            futures = {
                "app_settings": _ADMIN_EXECUTOR.submit(self.accounts.rows, "app_settings", order="updated_at.desc"),
                "permissions": _ADMIN_EXECUTOR.submit(self.accounts.admin_permissions),
                "stats": _ADMIN_EXECUTOR.submit(self.accounts.rpc, "admin_dashboard"),
            }
            for table in all_tables:
                kw = {"order": "created_at.desc"}
                if table in select_columns:
                    kw["select"] = select_columns[table]
                futures[table] = _ADMIN_EXECUTOR.submit(self.accounts.rows, table, **kw)
            inv_future = _ADMIN_EXECUTOR.submit(
                self.accounts.rows,
                "admin_invitations",
                select="id,email,created_at,expires_at,accepted_at,cancelled",
                order="created_at.desc",
            )
            my_fb_future = _ADMIN_EXECUTOR.submit(self.accounts.rpc, "my_feedback")
            data = {k: fut.result() for k, fut in futures.items()}
            if data["permissions"].get("manage_admins"):
                try:
                    data["admin_invitations"] = inv_future.result()
                except AccountError:
                    data["admin_invitations"] = []
            try:
                data["my_feedback"] = my_fb_future.result() or []
                data["privacy_configured"] = True
            except AccountError:
                data["my_feedback"] = []
                data["privacy_configured"] = False
            return data

        data = {
            "app_settings": self.accounts.rows("app_settings", order="updated_at.desc"),
            "permissions": self.accounts.admin_permissions(),
        }
        if preload_all or view in {"admin-dashboard", "admin-operations"}:
            data["stats"] = self.accounts.rpc("admin_dashboard")
        tables = {
            "admin-dashboard": ("admin_audit",),
            "admin-users": ("profiles",),
            "admin-user-detail": ("profiles",),
            "admin-documents": ("legal_documents",),
            "admin-document-add": ("legal_documents",),
            "admin-feedback": ("feedback",),
            "admin-operations": ("admin_jobs",),
            "admin-audit": ("admin_audit", "admin_jobs"),
            "admin-settings": ("app_settings",),
        }
        requested_tables = (
            ("profiles", "legal_documents", "feedback", "admin_jobs", "admin_audit")
            if preload_all else tables.get(view, ())
        )
        for table in requested_tables:
            if table in data:
                continue
            data[table] = self.accounts.rows(
                table, order="updated_at.desc" if table == "app_settings" else "created_at.desc",
                **({"select": select_columns[table]} if table in select_columns else {}),
            )
        if (preload_all or view in {"admin-users", "admin-user-detail"}) and data["permissions"]["manage_admins"]:
            data["admin_invitations"] = self.accounts.rows(
                "admin_invitations",
                select="id,email,created_at,expires_at,accepted_at,cancelled",
                order="created_at.desc",
            )
        if preload_all:
            try:
                data["my_feedback"] = self.accounts.rpc("my_feedback") or []
                data["privacy_configured"] = True
            except AccountError:
                data["my_feedback"] = []
                data["privacy_configured"] = False
        return data

    def account_update(self, fields):
        self.accounts.require_admin()
        role = str(fields.get("role", ""))
        status = str(fields.get("status", ""))
        reason = str(fields.get("reason", "")).strip()
        if role not in {"user", "admin"} or status not in {"active", "blocked"}:
            raise AccountError("Vai trò hoặc trạng thái tài khoản không hợp lệ.")
        if not 3 <= len(reason) <= 500:
            raise AccountError("Lý do thay đổi cần dài từ 3 đến 500 ký tự.")
        target_id = safe_id(fields.get("id"))
        targets = self.accounts.rows("profiles", filters={"id":"eq." + target_id})
        if not targets:
            raise AccountError("Không tìm thấy tài khoản.")
        if role == "admin" or targets[0]["role"] == "admin":
            self.accounts.require_security_admin()
        self.accounts.rpc(
            "admin_update_account",
            {
                "target_id": target_id,
                "new_role": role,
                "new_status": status,
                "reason": reason,
            },
        )

    def document_save(self, fields, upload=None):
        self.accounts.require_admin()
        title = str(fields.get("title", "")).strip()
        if not 2 <= len(title) <= 300:
            raise AccountError("Tên văn bản cần dài từ 2 đến 300 ký tự.")
        source = official_source(fields.get("source_url", ""))
        row = {
            "title": title,
            "source_url": source,
            "document_no": str(fields.get("document_no", ""))[:150],
            "issuer": str(fields.get("issuer", ""))[:200],
            "review_note": str(fields.get("review_note", ""))[:3000],
            "effective_from": fields.get("effective_from") or None,
            "validity": str(fields.get("validity", "unverified")),
            "updated_at": utcnow(),
        }
        if row["validity"] not in {"unverified", "CURRENT", "PARTIALLY_EFFECTIVE", "REPEALED", "HISTORICAL"}:
            raise AccountError("Trạng thái hiệu lực không hợp lệ.")
        if row["effective_from"]:
            try:
                datetime.strptime(row["effective_from"], "%Y-%m-%d")
            except ValueError:
                raise AccountError("Ngày có hiệu lực không hợp lệ.") from None
        if fields.get("id"):
            doc_id = safe_id(fields["id"])
            expected_updated_at = str(fields.get("updated_at", ""))
            params = {"id": "eq." + doc_id}
            if expected_updated_at:
                params["updated_at"] = "eq." + expected_updated_at
            # Editing metadata invalidates prior approval. Re-review before publishing.
            updated = self.accounts.rest(
                "PATCH",
                "legal_documents",
                params=params,
                body={**row, "status": "review", "reviewed_at": None, "reviewed_by": None},
                prefer="return=representation",
            )
            if not updated:
                raise AccountError("Văn bản đã thay đổi ở một phiên khác. Tải lại trước khi lưu.")
        else:
            if not upload:
                raise AccountError("Vui lòng chọn tệp PDF văn bản.")
            try:
                content = base64.b64decode(upload.get("data", ""), validate=True)
            except (ValueError, TypeError):
                raise AccountError("Tệp tải lên không hợp lệ.") from None
            if not 1 <= len(content) <= 10 * 1024 * 1024 or not content.startswith(b"%PDF-"):
                raise AccountError("Chỉ nhận PDF hợp lệ, tối đa 10 MB.")
            import fitz

            try:
                with fitz.open(stream=content, filetype="pdf") as pdf:
                    if pdf.is_encrypted or not 1 <= pdf.page_count <= 500:
                        raise AccountError("Tệp phải có 1–500 trang và không đặt mật khẩu.")
                    pages = pdf.page_count
                    preview = "\n".join(
                        str(pdf.load_page(index).get_text("text"))
                        for index in range(min(3, pdf.page_count))
                    )[:8000]
            except (RuntimeError, ValueError) as exc:
                if isinstance(exc, AccountError):
                    raise
                raise AccountError("Không đọc được tệp PDF này.") from None
            if len(preview.strip()) < 40:
                raise AccountError(
                    "PDF chưa có lớp văn bản đọc được. Hãy OCR và kiểm tra nội dung trước khi đưa vào kho."
                )
            doc_id = str(uuid.uuid4())
            path = doc_id + "/source.pdf"
            self.accounts.upload(path, content)
            file_name = re.sub(r"[^\w.\- ()]", "_", str(upload.get("name", "document.pdf")))[:150]
            try:
                self.accounts.rest(
                    "POST",
                    "legal_documents",
                    body={
                        **row,
                        "id": doc_id,
                        "storage_path": path,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "file_name": file_name,
                        "size_bytes": len(content),
                        "page_count": pages,
                        "preview_text": preview,
                        "status": "draft",
                    },
                )
            except AccountError:
                # A lost response may hide a successful insert. Keep the source
                # file whenever the row exists or its state cannot be checked.
                saved = self.accounts.rest(
                    "GET",
                    "legal_documents",
                    params={"id": "eq." + doc_id, "select": "id", "limit": "1"},
                )
                if not saved:
                    self.accounts.remove_upload(path)
                raise
        return doc_id

    def approve_document(self, doc_id, confirmed):
        self.accounts.require_admin()
        if confirmed is not True:
            raise AccountError("Bạn cần xác nhận đã kiểm tra nguồn, hiệu lực và nội dung văn bản.")
        doc_id = safe_id(doc_id)
        rows = self.accounts.rest(
            "GET",
            "legal_documents",
            params={
                "id": "eq." + doc_id,
                "select": "id,status,source_url,validity,effective_from,updated_at",
                "limit": "1",
            },
        )
        if not rows:
            raise AccountError("Không tìm thấy văn bản.")
        row = rows[0]
        official_source(row["source_url"])
        if row["validity"] not in {"CURRENT", "PARTIALLY_EFFECTIVE"} or not row.get("effective_from"):
            raise AccountError("Cần xác minh trạng thái và ngày có hiệu lực trước khi duyệt.")
        return self.accounts.rpc(
            "approve_legal_document",
            {"target_document": doc_id, "expected_updated_at": row["updated_at"]},
        )

    def cancel_invitation(self, invitation_id):
        self.accounts.require_security_admin()
        self.accounts.rpc("cancel_administrator_invitation", {"invitation_id": safe_id(invitation_id)})

    def enqueue(self, kind, document_id=None, payload=None):
        self.accounts.require_admin()
        if kind not in {"index", "health", "backup", "restore"}:
            raise AccountError("Tiến trình không hợp lệ.")
        return self.accounts.rest(
            "POST",
            "admin_jobs",
            body={"kind": kind, "document_id": safe_id(document_id) if document_id else None, "payload": payload or {}},
            prefer="return=representation",
        )[0]["id"]

    def review_feedback(self, fields):
        self.accounts.require_admin()
        status = str(fields.get("status", ""))
        if status not in {"pending", "reviewing", "resolved"}:
            raise AccountError("Trạng thái phản hồi không hợp lệ.")
        try:
            version = int(fields.get("privacy_version", ""))
        except (ValueError, TypeError):
            raise AccountError("Phản hồi đã thay đổi. Tải lại trước khi lưu.") from None
        self.accounts.rpc("review_feedback_safe", {"target_feedback":safe_id(fields.get("id")),
            "new_status":status,"new_note":str(fields.get("admin_note", ""))[:4000],
            "expected_privacy_version":version})

    def save_settings(self, fields):
        self.accounts.require_admin()
        app_name = str(fields.get("app_name", "")).strip()
        workspace = str(fields.get("workspace_name", "")).strip()
        if not 2 <= len(app_name) <= 60 or not 2 <= len(workspace) <= 80:
            raise AccountError("Tên ứng dụng hoặc khu quản trị không hợp lệ.")
        updated = self.accounts.rest(
            "PATCH",
            "app_settings",
            params={"id": "eq.general"},
            body={"app_name": app_name, "workspace_name": workspace, "updated_at": utcnow()},
            prefer="return=representation",
        )
        if not updated:
            raise AccountError("Không tìm thấy cài đặt chung. Kiểm tra migration Supabase.")


def submit_feedback(accounts, *, rating, comment="", question="", answer="", share_consent=False):
    profile = accounts.identity()
    if rating not in {"up", "down"} or not isinstance(share_consent, bool):
        raise AccountError("Phản hồi không hợp lệ.")
    # An unchecked box produces no question, answer, message ID, or chat title.
    row = {
        "owner_id": profile["id"],
        "rating": rating,
        "comment": str(comment)[:2000],
        "share_consent": share_consent,
        "question": str(question)[:4000] if share_consent else "",
        "answer": str(answer)[:12000] if share_consent else "",
    }
    accounts.rest("POST", "feedback", body=row)
