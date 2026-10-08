# -*- coding: utf-8 -*-
"""Unit test suite verifying integrity of standardized labor law templates."""
from ui.utils.legal_templates import LEGAL_TEMPLATES


def test_legal_templates_count_and_keys():
    assert len(LEGAL_TEMPLATES) == 8
    expected_ids = [
        "hop_dong_lao_dong",
        "hop_dong_thu_viec",
        "don_xin_thoi_viec",
        "don_doi_luong_tro_cap",
        "thoa_thuan_nda",
        "bien_ban_ban_giao",
        "don_khieu_nai_lao_dong",
        "giay_uy_quyen",
    ]
    actual_ids = [t["id"] for t in LEGAL_TEMPLATES]
    assert actual_ids == expected_ids


def test_legal_templates_content_richness():
    for t in LEGAL_TEMPLATES:
        assert len(t["title"]) > 5
        assert len(t["basis"]) > 5
        assert len(t["summary"]) > 20
        assert len(t["query"]) > 10
        assert len(t["content"]) > 1500
        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in t["content"]
