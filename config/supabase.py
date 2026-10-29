"""Server-only Supabase settings. Never expose secret keys in component payloads."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SupabaseConfig:
    url: str = ""
    key: str = field(default="", repr=False)
    service_key: str = field(default="", repr=False)
    public_url: str = "http://127.0.0.1:8501"

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    @classmethod
    def load(cls):
        values = {}
        path = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
        if path.exists():
            with path.open("rb") as handle:
                values = tomllib.load(handle).get("supabase", {})

        def read(key, default=""):
            return os.getenv(key, str(values.get(key, default))).strip()

        result = cls(
            read("SUPABASE_URL").rstrip("/"),
            read("SUPABASE_PUBLISHABLE_KEY") or read("SUPABASE_ANON_KEY"),
            read("SUPABASE_SECRET_KEY") or read("SUPABASE_SERVICE_ROLE_KEY"),
            read("APP_PUBLIC_URL", cls.public_url).rstrip("/"),
        )
        if result.url:
            parsed = urlsplit(result.url)
            if parsed.scheme != "https" and not (
                parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
            ):
                raise ValueError("SUPABASE_URL phải sử dụng HTTPS (ngoại trừ Supabase cục bộ).")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("SUPABASE_URL không hợp lệ.")
        return result
