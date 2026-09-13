# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 6 UI & Chat Service Unit Tests
Tests ChatService adapter, session persistence, and UI schema validation.
"""
import pytest
from pathlib import Path
import tempfile
import json

from app.chat_service import ChatService
from ui.utils.session import SessionManager, generate_title_from_query
from ui.utils.formatting import format_provision_badge, format_relative_date


@pytest.fixture
def chat_service():
    return ChatService()


@pytest.fixture
def temp_session_mgr():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_file = Path(tmp_dir) / "chat_history.json"
        yield SessionManager(storage_path=storage_file)


def test_title_generation_from_queries():
    assert generate_title_from_query("Công ty bắt tôi thử việc 3 tháng có đúng không?") == "Thử việc 3 tháng"
    assert generate_title_from_query("Tôi ký hợp đồng 2 năm, muốn nghỉ việc phải báo trước bao lâu?") == "Nghỉ việc hợp đồng 2 năm"
    assert generate_title_from_query("Làm thêm ngày lễ được trả lương thế nào?") == "Lương làm thêm ngày lễ"
    assert generate_title_from_query("Công ty có được giữ bằng đại học bản chính không?") == "Công ty giữ bằng đại học"
    assert generate_title_from_query("Thủ tục ly hôn thuận tình") == "Thủ tục ly hôn"


def test_session_manager_lifecycle(temp_session_mgr):
    # 1. Create conversation
    conv = temp_session_mgr.create_conversation("Cuộc trò chuyện mới")
    assert conv["id"] is not None
    assert conv["title"] == "Cuộc trò chuyện mới"
    assert len(temp_session_mgr.load_conversations()) == 1

    # 2. Append User Message (auto title generation)
    temp_session_mgr.append_message(
        conv_id=conv["id"],
        role="user",
        content="Công ty bắt tôi thử việc 3 tháng có đúng không?",
    )
    updated = temp_session_mgr.get_conversation(conv["id"])
    assert updated["title"] == "Thử việc 3 tháng"
    assert len(updated["messages"]) == 1

    # 3. Append Assistant Message
    temp_session_mgr.append_message(
        conv_id=conv["id"],
        role="assistant",
        content="Để xác định thời gian thử việc...",
        structured_data={"needs_clarification": True},
    )
    updated2 = temp_session_mgr.get_conversation(conv["id"])
    assert len(updated2["messages"]) == 2
    assert updated2["messages"][1]["structured_data"]["needs_clarification"] is True

    # 4. Rename Conversation
    temp_session_mgr.update_conversation_title(conv["id"], "Thử việc kế toán")
    assert temp_session_mgr.get_conversation(conv["id"])["title"] == "Thử việc kế toán"

    # 5. Delete Conversation
    temp_session_mgr.delete_conversation(conv["id"])
    assert len(temp_session_mgr.load_conversations()) == 0


def test_provision_badge_formatting():
    badge = format_provision_badge(article="35", clause="1", point="b")
    assert badge == "Điều 35 · Khoản 1 · Điểm b"

    badge2 = format_provision_badge(article="107", clause="2")
    assert badge2 == "Điều 107 · Khoản 2"

    badge3 = format_provision_badge(article="24")
    assert badge3 == "Điều 24"


def test_chat_service_schema_and_clarification(chat_service):
    chat_service.reset_conversation()
    res = chat_service.ask("Công ty bắt tôi thử việc 3 tháng có đúng không?", update_memory=False)

    assert "answer" in res
    assert "findings" in res
    assert "citations" in res
    assert "needs_clarification" in res
    assert "clarification_question" in res
    assert "out_of_scope" in res
    assert "suggested_followups" in res
    assert "latency_ms" in res

    # Verify clarification behavior
    assert res["needs_clarification"] is True
    assert "Người quản lý doanh nghiệp" in res["suggested_followups"]
    assert "Cao đẳng trở lên" in res["suggested_followups"]


def test_chat_service_legal_answer_with_citations(chat_service):
    chat_service.reset_conversation()
    res = chat_service.ask("Tôi ký hợp đồng 2 năm, muốn nghỉ việc phải báo trước bao lâu?", update_memory=False)

    assert res["needs_clarification"] is False
    assert res["out_of_scope"] is False
    assert len(res["citations"]) > 0

    top_cite = res["citations"][0]
    assert "document_title" in top_cite
    assert "article" in top_cite
    assert top_cite["article"] == "35"
    assert top_cite["source_url"].startswith("http")


def test_chat_service_out_of_scope(chat_service):
    chat_service.reset_conversation()
    res = chat_service.ask("Thủ tục ly hôn thuận tình cần những giấy tờ gì?", update_memory=False)

    assert res["out_of_scope"] is True
    assert len(res["citations"]) == 0
    assert len(res["suggested_followups"]) > 0
