# -*- coding: utf-8 -*-
"""Unit test suite verifying citation formatters and URL security."""
from ui.components.citation_card import _safe_official_url
from ui.utils.formatting import format_provision_badge


def test_safe_official_url():
    assert _safe_official_url("https://congbao.chinhphu.vn/document") == "https://congbao.chinhphu.vn/document"
    assert not _safe_official_url("javascript:alert(1)")
    assert not _safe_official_url("https://evil.site/doc")


def test_format_provision_badge():
    badge = format_provision_badge("Điều 21", "Bộ luật Lao động 2019")
    assert "Điều 21" in badge
    assert "BLLĐ 2019" in badge or "Bộ luật" in badge
