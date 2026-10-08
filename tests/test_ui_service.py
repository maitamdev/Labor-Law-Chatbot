# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 6 UI & Chat Service Unit Tests
Tests ChatService adapter, session persistence, and UI schema validation.
"""
import pytest
from pathlib import Path
import tempfile
import json

from app.chat_service import ChatService, answer_smalltalk
from rag.output_validator import format_answer_markdown
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
    assert generate_title_from_query("Tôi đi làm thêm và ký thỏa thuận công việc") == "Xác định quan hệ lao động"
    assert generate_title_from_query("Công ty có được giữ bằng đại học bản chính không?") == "Công ty giữ bằng đại học"
    assert generate_title_from_query("Tôi đi làm mà bị sếp đấm") == "Bạo lực tại nơi làm việc"
    assert generate_title_from_query("Vào làm chính thức rồi cuối tuần mới ký HĐLĐ") == "Đi làm trước khi ký HĐLĐ"
    assert generate_title_from_query("Nguyên tắc nền tảng khi giao kết HĐLĐ") == "Nguyên tắc giao kết HĐLĐ"
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


def test_session_manager_recovers_stale_conversation_id(temp_session_mgr):
    first = temp_session_mgr.create_conversation("Cuộc trò chuyện thứ nhất")
    second = temp_session_mgr.create_conversation("Cuộc trò chuyện thứ hai")

    assert temp_session_mgr.ensure_conversation(first["id"])["id"] == first["id"]

    temp_session_mgr.delete_conversation(first["id"])
    assert temp_session_mgr.ensure_conversation(first["id"])["id"] == second["id"]

    temp_session_mgr.delete_conversation(second["id"])
    recovered = temp_session_mgr.ensure_conversation("68b366e4")
    assert recovered["id"] != "68b366e4"
    assert temp_session_mgr.get_conversation(recovered["id"]) is not None


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


@pytest.mark.ollama
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


def test_conversation_chatgpt_style_lifecycle(temp_session_mgr):
    # 1. Start fresh conversation
    c1 = temp_session_mgr.create_conversation("Cuộc trò chuyện mới")
    assert c1["title"] == "Cuộc trò chuyện mới"
    assert len(c1["messages"]) == 0

    # 2. First user question auto-names the conversation
    temp_session_mgr.append_message(c1["id"], "user", "Tôi làm việc bị té thì có được bồi thường tai nạn lao động không?")
    updated1 = temp_session_mgr.get_conversation(c1["id"])
    assert updated1["title"] == "Bồi thường tai nạn lao động"
    assert len(updated1["messages"]) == 1

    # 3. Follow-up assistant message
    temp_session_mgr.append_message(c1["id"], "assistant", "Theo Điều 38 Luật ATVSLĐ...")
    updated1 = temp_session_mgr.get_conversation(c1["id"])
    assert updated1["title"] == "Bồi thường tai nạn lao động"
    assert len(updated1["messages"]) == 2

    # 4. Start second conversation (independent)
    c2 = temp_session_mgr.create_conversation("Cuộc trò chuyện mới")
    temp_session_mgr.append_message(c2["id"], "user", "Công ty tự ý trừ phí tiền lương của tôi")
    updated2 = temp_session_mgr.get_conversation(c2["id"])
    assert updated2["title"] == "Khấu trừ tiền lương trái phép"
    assert len(updated2["messages"]) == 1

    # C1 remains unchanged and intact
    c1_check = temp_session_mgr.get_conversation(c1["id"])
    assert len(c1_check["messages"]) == 2
    assert c1_check["title"] == "Bồi thường tai nạn lao động"

    # 5. Deleting C1 leaves C2 as primary
    temp_session_mgr.delete_conversation(c1["id"])
    assert temp_session_mgr.get_conversation(c1["id"]) is None
    convs = temp_session_mgr.load_conversations()
    assert len(convs) == 1
    assert convs[0]["id"] == c2["id"]


def test_corpus_scope_and_anti_prompt_leak():
    # 1. Scope question matches corpus_scope with 0ms fast-track
    reply = answer_smalltalk("có bao nhiêu luật")
    assert reply is not None
    assert reply["is_smalltalk"] is True
    assert reply["smalltalk_intent"] == "corpus_scope"
    assert "Bộ luật Lao động 2019" in reply["answer"]
    assert "Luật An toàn, vệ sinh lao động" in reply["answer"]
    assert "Luật Bảo hiểm xã hội" in reply["answer"]

    # 2. Leaked preamble and raw LEGAL_CONTEXT are deterministically cleaned
    raw_leak = (
        "Bài tư vấn pháp lý cho câu hỏi 'có bao nhiêu luật' dựa trên LEGAL_CONTEXT cung cấp như sau: "
        "Trong LEGAL_CONTEXT, chỉ có một quy định pháp luật liên quan đến nội quy lao động được đề cập, "
        "cụ thể là Điều 118 của Bộ luật Lao động. Do đó, có một luật liên quan đến nội quy lao động trong LEGAL_CONTEXT."
    )
    cleaned = format_answer_markdown(raw_leak)
    assert "LEGAL_CONTEXT" not in cleaned
    assert "Bài tư vấn pháp lý" not in cleaned
    assert "Điều 118" in cleaned
