"""Supabase Auth and PostgREST, with user-scoped credentials and bounded requests.

No global SDK session, no JWT roles trusted from the browser, no service key for
ordinary queries. Authorization is also enforced in the supplied SQL migration.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter

from config.supabase import SupabaseConfig


def _create_pooled_session() -> requests.Session:
    http = requests.Session()
    adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32)
    http.mount("https://", adapter)
    http.mount("http://", adapter)
    return http


class AccountError(ValueError):
    pass


def validate_password(password: str, confirm: str | None = None):
    if not isinstance(password, str) or not 8 <= len(password) <= 256:
        raise AccountError("Mật khẩu cần dài từ 8 đến 256 ký tự.")
    if confirm is not None and password != confirm:
        raise AccountError("Hai mật khẩu chưa khớp.")


def validate_email(email: str) -> str:
    email = str(email).strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise AccountError("Vui lòng nhập địa chỉ email hợp lệ.")
    return email


class Accounts:
    def __init__(self, config: SupabaseConfig, session: dict | None = None, transport=None):
        self.config = config
        self.session = dict(session or {})
        self._real_transport = transport is None
        self.transport = transport if transport is not None else _create_pooled_session()
        self._lock = threading.RLock()
        self._identity_cache: tuple[str, float, dict] | None = None
        self._permissions_cache: tuple[str, float, dict] | None = None

    def invalidate_cache(self):
        with self._lock:
            self._identity_cache = None
            self._permissions_cache = None

    def request(
        self,
        method,
        path,
        *,
        body=None,
        params=None,
        token=None,
        prefer=None,
        raw=None,
        content_type=None,
        service=False,
    ) -> Any:
        if not self.config.configured:
            raise AccountError(
                "Chưa kết nối Supabase. Hãy cấu hình theo docs/SUPABASE_SETUP.md; bạn vẫn có thể dùng AI với tư cách khách."
            )
        key = self.config.service_key if service else self.config.key
        if service and not key:
            raise AccountError("Chưa cấu hình khóa máy chủ để gửi lời mời admin. Xem hướng dẫn Supabase.")
        headers = {"apikey": key, "Content-Type": content_type or "application/json"}
        if token or service:
            headers["Authorization"] = "Bearer " + (key if service else str(token))
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = self.transport.request(
                method,
                self.config.url + path,
                headers=headers,
                params=params,
                json=body if raw is None else None,
                data=raw,
                timeout=(5, 25),
            )
        except requests.RequestException:
            raise AccountError("Chưa kết nối được Supabase. Kiểm tra mạng và thử lại.") from None
        if not response.ok:
            # Never render raw exceptions, response bodies, URLs, credentials, or SQL.
            try:
                payload = response.json()
                code = payload.get("error_code") or payload.get("code")
                msg = str(payload.get("message") or "")
            except (ValueError, AttributeError):
                code = ""
                msg = ""
            if code == "email_not_confirmed":
                raise AccountError("Email chưa được xác minh. Hãy kiểm tra hộp thư của bạn.")
            if code in {"otp_expired", "otp_disabled"}:
                raise AccountError("Liên kết đã hết hạn hoặc đã được dùng. Hãy gửi yêu cầu email mới.")
            if code in {"invalid_credentials", "invalid_grant"}:
                raise AccountError("Email hoặc mật khẩu không đúng.")
            if response.status_code == 429:
                raise AccountError("Bạn thao tác quá nhanh hoặc email đã đạt giới hạn gửi. Hãy thử lại sau.")
            if response.status_code in {401, 403}:
                raise AccountError("Phiên đăng nhập hết hạn hoặc bạn không có quyền thực hiện thao tác này.")
            if code in {"42P01", "PGRST202", "PGRST205"}:
                raise AccountError("Cơ sở dữ liệu chưa sẵn sàng. Hãy chạy SQL trong supabase/migrations trước.")
            if msg == "feedback privacy changed":
                raise AccountError("Phản hồi đã thay đổi quyền riêng tư. Tải lại trước khi lưu.")
            if msg == "history erased; reload required":
                raise AccountError("Lịch sử trò chuyện đã được xóa ở phiên khác. Vui lòng tải lại trang.")
            if msg in {"security administrator required", "protected administrator"}:
                raise AccountError("Chỉ quản trị viên chính được cấp, thu hồi quyền hoặc quản lý tài khoản admin.")
            if msg == "cannot lock or demote yourself":
                raise AccountError("Không thể tự hạ quyền hoặc khóa tài khoản đang sử dụng.")
            if msg == "feedback unavailable":
                raise AccountError("Không tìm thấy phản hồi của bạn.")
            if msg in {"invitation unavailable", "invitation not found"}:
                raise AccountError("Lời mời không tồn tại, đã hủy hoặc đã hết hạn.")
            if response.status_code == 409:
                raise AccountError("Dữ liệu đã thay đổi hoặc bị trùng. Hãy tải lại và thử lại.")
            raise AccountError("Supabase chưa thực hiện được yêu cầu. Kiểm tra cấu hình hoặc dữ liệu rồi thử lại.")
        if not response.content:
            return None
        if "json" not in response.headers.get("Content-Type", ""):
            return response.content
        try:
            return response.json()
        except ValueError:
            raise AccountError("Supabase trả về dữ liệu không hợp lệ. Vui lòng thử lại.") from None

    def _remember(self, data):
        if not data.get("access_token") or not data.get("refresh_token"):
            raise AccountError("Không nhận được phiên đăng nhập hợp lệ.")
        self.invalidate_cache()
        self.session.update(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + int(data.get("expires_in", 3600)),
        )

    def token(self):
        with self._lock:
            if not self.session.get("access_token"):
                raise AccountError("Bạn cần đăng nhập để tiếp tục.")
            if float(self.session.get("expires_at", 0)) < time.time() + 60:
                self._remember(
                    self.request(
                        "POST",
                        "/auth/v1/token",
                        params={"grant_type": "refresh_token"},
                        body={"refresh_token": self.session["refresh_token"]},
                    )
                )
            return self.session["access_token"]

    def login(self, email, password):
        email = validate_email(email)
        if not isinstance(password, str) or not 1 <= len(password) <= 256:
            raise AccountError("Email hoặc mật khẩu không đúng.")
        self._remember(
            self.request(
                "POST", "/auth/v1/token", params={"grant_type": "password"}, body={"email": email, "password": password}
            )
        )
        return self.identity()

    def signup(self, email, password, name, confirm):
        email = validate_email(email)
        validate_password(password, confirm)
        name = str(name).strip()
        if not 2 <= len(name) <= 100:
            raise AccountError("Họ tên cần dài từ 2 đến 100 ký tự.")
        # Never accept role, status or arbitrary metadata from a signup form.
        self.request(
            "POST",
            "/auth/v1/signup",
            params={"redirect_to": self.config.public_url},
            body={"email": email, "password": password, "data": {"full_name": name}},
        )
        return "Hãy kiểm tra email để xác minh tài khoản, sau đó đăng nhập. Nếu email đã được dùng, hãy đăng nhập hoặc khôi phục mật khẩu."

    def recover(self, email):
        email = validate_email(email)
        self.request("POST", "/auth/v1/recover", params={"redirect_to": self.config.public_url}, body={"email": email})
        return "Nếu email khớp với tài khoản, liên kết khôi phục sẽ được gửi tới hộp thư. Hãy kiểm tra cả thư mục spam."

    def verify_email_link(self, token_hash, link_type):
        if link_type not in {"recovery", "email", "signup", "invite"} or not re.fullmatch(
            r"[A-Za-z0-9_-]{16,512}", str(token_hash)
        ):
            raise AccountError("Liên kết xác thực không hợp lệ hoặc đã hết hạn.")
        data = self.request("POST", "/auth/v1/verify", body={"token_hash": token_hash, "type": link_type})
        self._remember(data)
        return data

    def identity(self):
        token = self.token()
        if self._real_transport:
            with self._lock:
                cached = self._identity_cache
                if cached and cached[0] == token and (time.monotonic() - cached[1]) < 5.0:
                    return dict(cached[2])
        user = self.request("GET", "/auth/v1/user", token=token)
        rows = self.rest(
            "GET",
            "profiles",
            params={
                "id": "eq." + user["id"],
                "select": "id,email,full_name,role,status,created_at,email_verified",
                "limit": "1",
            },
        )
        if not rows or rows[0]["status"] != "active":
            self.invalidate_cache()
            raise AccountError("Tài khoản đang bị khóa hoặc hồ sơ chưa sẵn sàng.")
        profile = rows[0]
        if not user.get("email_confirmed_at"):
            self.invalidate_cache()
            raise AccountError("Bạn cần xác minh email trước khi sử dụng tài khoản.")
        profile["username"] = profile.get("full_name") or profile["email"]
        if self._real_transport:
            with self._lock:
                self._identity_cache = (token, time.monotonic(), dict(profile))
        return profile

    def require_admin(self):
        profile = self.identity()
        if profile["role"] != "admin":
            raise AccountError("Bạn không có quyền truy cập khu quản trị.")
        return profile

    def admin_permissions(self):
        self.require_admin()
        token = self.token()
        if self._real_transport:
            with self._lock:
                cached = self._permissions_cache
                if cached and cached[0] == token and (time.monotonic() - cached[1]) < 5.0:
                    return dict(cached[2])
        try:
            permissions = self.rpc("my_admin_permissions")
        except AccountError:
            # Old/missing migration or an unavailable permission check must
            # never restore the former unrestricted administrator privileges.
            return {"manage_admins": False, "configured": False}
        result = {
            "manage_admins": isinstance(permissions, dict) and permissions.get("manage_admins") is True,
            "configured": True,
        }
        if self._real_transport:
            with self._lock:
                self._permissions_cache = (token, time.monotonic(), dict(result))
        return result

    def require_security_admin(self):
        permissions = self.admin_permissions()
        if not permissions["configured"]:
            raise AccountError("Cần áp dụng SQL bảo vệ quyền riêng tư 202610240003 trước khi quản lý quyền admin.")
        if not permissions["manage_admins"]:
            raise AccountError("Chỉ quản trị viên chính được cấp, thu hồi quyền hoặc quản lý tài khoản admin.")

    def rest(self, method, table, *, body=None, params=None, prefer=None):
        if not re.fullmatch(r"[a-z_]+", table):
            raise ValueError("Invalid table")
        return self.request(method, "/rest/v1/" + table, token=self.token(), body=body, params=params, prefer=prefer)

    def rpc(self, function, body=None):
        if not re.fullmatch(r"[a-z_]+", function):
            raise ValueError("Invalid function")
        return self.request("POST", "/rest/v1/rpc/" + function, token=self.token(), body=body or {})

    def rows(self, table, *, select="*", filters=None, order="created_at.desc", page_size=200):
        if not isinstance(page_size, int) or page_size <= 0:
            raise ValueError("page_size must be positive")
        result = []
        for offset in range(0, 100_000, page_size):
            batch = self.rest(
                "GET",
                table,
                params={
                    **(filters or {}),
                    "select": select,
                    "order": order,
                    "offset": str(offset),
                    "limit": str(page_size),
                },
            )
            if not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch):
                raise AccountError("Supabase trả về danh sách dữ liệu không hợp lệ. Vui lòng thử lại.")
            result.extend(batch)
            if len(batch) < page_size:
                return result
        raise AccountError("Dữ liệu quá lớn. Cần thu hẹp khoảng thời gian truy vấn.")

    def update_name(self, name):
        if not 2 <= len(str(name).strip()) <= 100:
            raise AccountError("Họ tên cần dài từ 2 đến 100 ký tự.")
        self.rpc("update_my_profile", {"new_name": str(name).strip()})
        self.invalidate_cache()

    def change_password(self, current, new, confirm, *, recovery=False):
        validate_password(new, confirm)
        token = self.token()
        if not recovery:
            profile = self.identity()
            check = Accounts(self.config, transport=self.transport)
            try:
                check.login(profile["email"], current)
            except AccountError:
                raise AccountError("Mật khẩu hiện tại không đúng hoặc không thể xác thực.") from None
            finally:
                if check.session:
                    check.logout("local")
        self.request("PUT", "/auth/v1/user", token=token, body={"password": new})
        # Refresh tokens of other sessions are revoked. Existing access tokens
        # can remain valid until expiry; do not claim immediate global revocation.
        self.logout("others")

    def logout(self, scope="local"):
        if self.session.get("access_token"):
            self.request("POST", "/auth/v1/logout", token=self.token(), params={"scope": scope})
        if scope != "others":
            self.session.clear()
        self.invalidate_cache()

    def invite_admin(self, email):
        self.require_security_admin()
        email = validate_email(email)
        # Store a trusted invitation first; the Auth trigger accepts it only for
        # the verified matching email. An invited user is NOT admin on signup.
        invitation = self.rpc("invite_administrator", {"target_email": email})
        try:
            self.request(
                "POST",
                "/auth/v1/invite",
                body={"email": email},
                params={"redirect_to": self.config.public_url},
                service=True,
            )
        except AccountError:
            self.rpc("cancel_administrator_invitation", {"invitation_id": invitation})
            raise

    def upload(self, path, content, content_type="application/pdf"):
        self.require_admin()
        return self.request(
            "POST",
            "/storage/v1/object/legal-documents/" + quote(path, safe="/"),
            token=self.token(),
            raw=content,
            content_type=content_type,
        )

    def remove_upload(self, path):
        self.require_admin()
        return self.request(
            "DELETE",
            "/storage/v1/object/legal-documents",
            token=self.token(),
            body={"prefixes": [str(path)]},
        )

    def download(self, path):
        self.require_admin()
        return self.request(
            "GET", "/storage/v1/object/authenticated/legal-documents/" + quote(path, safe="/"), token=self.token()
        )
