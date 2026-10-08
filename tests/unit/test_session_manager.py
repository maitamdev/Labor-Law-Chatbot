# -*- coding: utf-8 -*-
"""Unit test suite verifying session utilities and title generation."""
from ui.utils.session import generate_title_from_query, SessionManager


def test_generate_title_from_query():
    title1 = generate_title_from_query("Thời gian thử việc tối đa là bao lâu?")
    assert "Thử việc" in title1 or "Thời gian" in title1

    title2 = generate_title_from_query("Quy định nghỉ việc hợp đồng không xác định thời hạn?")
    assert "nghỉ việc" in title2.lower() or "hđ" in title2.lower()


def test_session_manager_class_exists():
    sm = SessionManager()
    assert hasattr(sm, "load_conversations")
    assert hasattr(sm, "save_conversations")
    assert hasattr(sm, "create_conversation")
