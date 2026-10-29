"""Local account storage for the Streamlit chat application.

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with a random salt. Account
records live locally under ``storage/users/accounts.json`` and never leave the
machine.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from typing import Any

from config.settings import STORAGE_DIR

AUTH_STORAGE_PATH = STORAGE_DIR / "users" / "accounts.json"
PASSWORD_ITERATIONS = 310_000
MAX_PASSWORD_LENGTH = 256
_AUTH_LOCK = threading.RLock()


class AuthError(ValueError):
    """An expected account validation or storage error."""


def _read_accounts() -> list[dict[str, Any]]:
    if not AUTH_STORAGE_PATH.exists():
        return []
    try:
        with AUTH_STORAGE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthError("Không đọc được dữ liệu tài khoản trên máy này.") from exc
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("accounts"), list):
        raise AuthError("Tệp dữ liệu tài khoản không đúng định dạng.")
    return [item for item in data["accounts"] if isinstance(item, dict)]


def _write_accounts(accounts: list[dict[str, Any]]) -> None:
    AUTH_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = AUTH_STORAGE_PATH.with_name(f".{AUTH_STORAGE_PATH.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump({"version": 1, "accounts": accounts}, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, AUTH_STORAGE_PATH)
    except OSError as exc:
        raise AuthError("Không lưu được dữ liệu tài khoản trên máy này.") from exc
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _username_key(username: str) -> str:
    return username.strip().casefold()


def _validate_username(username: str) -> str:
    clean = username.strip()
    if not 3 <= len(clean) <= 32:
        raise AuthError("Tên đăng nhập cần dài từ 3 đến 32 ký tự.")
    if not all(char.isalnum() or char in "._-" for char in clean):
        raise AuthError("Tên đăng nhập chỉ được gồm chữ, số, dấu chấm, gạch ngang hoặc gạch dưới.")
    return clean


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)


def _public_account(record: dict[str, Any], *, first_account: bool = False) -> dict[str, Any]:
    public: dict[str, Any] = {"id": str(record.get("id", "")), "username": str(record.get("username", ""))}
    if first_account:
        public["first_account"] = True
    return public


def create_account(username: str, password: str) -> dict[str, Any]:
    """Create an account and return only its public identity fields."""
    clean_username = _validate_username(username)
    if not isinstance(password, str) or not 8 <= len(password) <= MAX_PASSWORD_LENGTH:
        raise AuthError("Mật khẩu cần dài từ 8 đến 256 ký tự.")

    salt = os.urandom(16)
    record = {
        "id": uuid.uuid4().hex,
        "username": clean_username,
        "username_key": _username_key(clean_username),
        "password_salt": salt.hex(),
        "password_hash": _password_hash(password, salt).hex(),
        "password_iterations": PASSWORD_ITERATIONS,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with _AUTH_LOCK:
        accounts = _read_accounts()
        if any(_username_key(str(item.get("username_key", item.get("username", "")))) == record["username_key"] for item in accounts):
            raise AuthError("Tên đăng nhập này đã được sử dụng.")
        first_account = not accounts
        accounts.append(record)
        _write_accounts(accounts)
    return _public_account(record, first_account=first_account)


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    """Return a public account on success, or ``None`` for invalid credentials."""
    username_key = _username_key(username)
    if not username_key or not isinstance(password, str) or len(password) > MAX_PASSWORD_LENGTH:
        return None
    with _AUTH_LOCK:
        accounts = _read_accounts()
        record = next(
            (item for item in accounts if _username_key(str(item.get("username_key", item.get("username", "")))) == username_key),
            None,
        )
        if record is None:
            return None
        try:
            salt = bytes.fromhex(str(record["password_salt"]))
            expected = bytes.fromhex(str(record["password_hash"]))
            iterations = int(record.get("password_iterations", PASSWORD_ITERATIONS))
            if not 100_000 <= iterations <= 2_000_000:
                return None
            actual = _password_hash(password, salt) if iterations == PASSWORD_ITERATIONS else hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, iterations,
            )
        except (KeyError, TypeError, ValueError):
            return None
        if not hmac.compare_digest(actual, expected):
            return None
        return _public_account(record)


def get_account(account_id: str) -> dict[str, Any] | None:
    """Resolve a session's opaque account ID back to its public identity."""
    if not re.fullmatch(r"[0-9a-f]{32}", str(account_id or "")):
        return None
    with _AUTH_LOCK:
        record = next((item for item in _read_accounts() if item.get("id") == account_id), None)
    return _public_account(record) if record else None
