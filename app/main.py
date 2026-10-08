"""Supported command-line entry point for the Streamlit application."""

from __future__ import annotations

import subprocess
import sys

from config.settings import APP_HOST, APP_PORT, PROJECT_ROOT


def main() -> int:
    """Launches Streamlit with safe local-only defaults."""
    app_path = PROJECT_ROOT / "ui" / "streamlit_app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        APP_HOST,
        "--server.port",
        str(APP_PORT),
    ]
    try:
        return subprocess.call(command, cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        # Streamlit receives the same interrupt; keep normal shutdown quiet.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
