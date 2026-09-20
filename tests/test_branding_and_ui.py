# -*- coding: utf-8 -*-
"""
Tests for UI branding, logo loading, base64 encoding, and component integration.
"""
from __future__ import annotations

import base64
from pathlib import Path
from PIL import Image

from ui.utils.branding import PRIMARY_LOGO_PATH, STATIC_LOGO_THUMB, get_logo_base64, get_logo_path


def test_primary_logo_exists():
    """Verify primary logo.png exists at project root."""
    path = get_logo_path()
    assert path.exists(), "Primary logo.png must exist at project root"
    assert path.name == "logo.png"


def test_optimized_logo_thumbnail():
    """Verify optimized 256x256 thumbnail exists and has valid dimensions."""
    assert STATIC_LOGO_THUMB.exists(), "Static logo thumbnail must exist"
    with Image.open(STATIC_LOGO_THUMB) as img:
        assert img.format == "PNG"
        assert img.size == (256, 256)


def test_logo_base64_caching_and_validity():
    """Verify get_logo_base64 returns valid PNG base64 and matches PNG signature."""
    b64_1 = get_logo_base64()
    b64_2 = get_logo_base64()
    assert b64_1 == b64_2, "Cached base64 should return identical instance"
    assert len(b64_1) > 1000, "Base64 string should contain image payload"

    # Decode and check PNG magic bytes
    decoded = base64.b64decode(b64_1)
    assert decoded.startswith(b"\x89PNG\r\n\x1a\n"), "Decoded bytes must be valid PNG format"


def test_ui_components_import_cleanly():
    """Verify all UI components importing branding load cleanly."""
    import ui.components.chat_message as chat_message
    import ui.components.sidebar as sidebar
    import ui.components.welcome as welcome
    import ui.streamlit_app as app

    assert hasattr(chat_message, "render_assistant_message")
    assert hasattr(sidebar, "render_sidebar")
    assert hasattr(welcome, "render_welcome_screen")
