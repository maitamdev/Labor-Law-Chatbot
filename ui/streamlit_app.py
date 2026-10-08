# -*- coding: utf-8 -*-
"""
VietLabor AI - Streamlit Web Application (Phase 6)
Official user interface matching the approved mockup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Enforce 100% offline mode for Hugging Face Hub (zero external network requests, zero warnings, zero progress bars)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# Silence Windows-specific asyncio ProactorEventLoop connection lost errors (WinError 10054 on page refresh/close)
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport

        _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def _silenced_call_connection_lost(self, exc):
            try:
                _orig_call_connection_lost(self, exc)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass

        _ProactorBasePipeTransport._call_connection_lost = _silenced_call_connection_lost
    except Exception:
        pass

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

import importlib
import ui.utils.session
importlib.reload(ui.utils.session)
from ui.utils.session import SessionManager

import ui.utils.document_reader
importlib.reload(ui.utils.document_reader)

import ui.components.approved_layout
importlib.reload(ui.components.approved_layout)
from ui.components.approved_layout import render_approved_layout, NAVIGATION

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title="VietLabor AI - Trợ lý pháp luật lao động",
    page_icon="§",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. Inject Custom CSS
CSS_PATH = PROJECT_ROOT / "ui" / "styles" / "app.css"
if CSS_PATH.exists():
    css_content = CSS_PATH.read_text(encoding="utf-8")
    st.html(f"<style>{css_content}</style>")


# 3. Session-local ChatService.
#
# Never cache the ChatService with st.cache_resource: the chain contains mutable
# conversation memory and a globally cached instance can mix facts between
# browser sessions. Heavy embedding weights are already cached by the model
# wrapper itself.
APP_BUILD_VERSION = "2026.10.08.v3.19_rich_detailed_advisory_prompts"

def get_chat_service(build_version: str = APP_BUILD_VERSION):
    from app.chat_service import ChatService
    cache_key = f"chat_service::{build_version}"
    if cache_key not in st.session_state:
        service = ChatService()
        active_id = st.session_state.get("active_conv_id")
        if isinstance(active_id, str) and active_id:
            active_conv = session_mgr.get_conversation(active_id)
            service.restore_conversation((active_conv or {}).get("messages", []))
        st.session_state[cache_key] = service
    return st.session_state[cache_key]


session_mgr = SessionManager()

# Load the local model in the background while the user reads the screen
# (cold first token ~8s -> <1s). Runs once per process; never blocks the UI.
from app.warmup import start_background_warmup
start_background_warmup()

# 4. Initialize Active Conversation State
requested_conv_id = st.session_state.get("active_conv_id")
resolved_conv = session_mgr.ensure_conversation(requested_conv_id)
if requested_conv_id != resolved_conv["id"]:
    st.session_state["active_conv_id"] = resolved_conv["id"]
    st.session_state["pending_memory_sync"] = resolved_conv["id"]


# 5. Callbacks for Sidebar Actions
def handle_new_chat():
    active_id = st.session_state.get("active_conv_id")
    active_conv = session_mgr.get_conversation(active_id) if isinstance(active_id, str) and active_id else None
    if active_conv and not active_conv.get("messages"):
        st.session_state["ui_view"] = "chat"
        st.rerun()
        return

    new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
    st.session_state["active_conv_id"] = new_c["id"]
    st.session_state.pop("pending_memory_sync", None)
    for state_key, service in list(st.session_state.items()):
        if state_key.startswith("chat_service::"):
            service.reset_conversation()
            setattr(service, "_synced_conv_id", new_c["id"])
    st.session_state["ui_view"] = "chat"
    st.session_state["ui_notice"] = "Đã bắt đầu cuộc trò chuyện mới."
    st.rerun()


def handle_switch_conv(conv_id: str):
    st.session_state["active_conv_id"] = conv_id
    st.session_state["ui_view"] = "chat"
    st.session_state["pending_memory_sync"] = conv_id
    st.rerun()


def handle_card_submit(query: str):
    st.session_state["submitted_query"] = query
    st.rerun()


def handle_regenerate():
    conv_id = st.session_state.get("active_conv_id")
    if not isinstance(conv_id, str) or not conv_id:
        return
    question = session_mgr.pop_last_exchange(conv_id)
    if not question:
        return
    # Re-align the chain memory with the conversation minus the dropped pair.
    for state_key, state_value in list(st.session_state.items()):
        if state_key.startswith("chat_service::"):
            remaining = (session_mgr.get_conversation(conv_id) or {}).get("messages", [])
            state_value.restore_conversation(remaining)
    st.session_state["submitted_query"] = question
    st.rerun()


def handle_feedback(msg_id: str, rating: str):
    from app.feedback import build_feedback_record, record_feedback

    conv_id = st.session_state.get("active_conv_id")
    if not isinstance(conv_id, str) or not conv_id:
        return
    conv = session_mgr.get_conversation(conv_id)
    msgs = (conv or {}).get("messages", [])
    for idx, m in enumerate(msgs):
        if m.get("id") == msg_id:
            question = next(
                (p.get("content", "") for p in reversed(msgs[:idx]) if p.get("role") == "user"), "",
            )
            record_feedback(build_feedback_record(
                rating=rating, question=question, answer=str(m.get("content", "")),
                conv_id=str(conv_id), msg_id=msg_id, structured_data=m.get("structured_data"),
            ))
            session_mgr.set_message_feedback(conv_id, msg_id, rating)
            break
    st.rerun()


# 6. Render the approved interactive application surface.
active_id = str(st.session_state["active_conv_id"])
submitted = st.session_state.pop("submitted_query", None)
submitted_attachment = st.session_state.pop("submitted_attachment", None)
if submitted or submitted_attachment:
    active_conv = session_mgr.get_conversation(active_id)
    if st.session_state.get("ui_view") == "home" or not active_conv or (st.session_state.get("ui_view") != "chat" and active_conv.get("messages")):
        new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
        active_id = new_c["id"]
        st.session_state["active_conv_id"] = active_id
        for state_key, service in list(st.session_state.items()):
            if state_key.startswith("chat_service::"):
                service.reset_conversation()

    msg_attachment = None
    extracted_text = ""
    if submitted_attachment and isinstance(submitted_attachment, dict):
        from ui.utils.document_reader import extract_attachment_text
        extracted_text, att_name, size_str = extract_attachment_text(submitted_attachment)
        if att_name:
            ext = Path(att_name).suffix.lower()
            msg_attachment = {
                "name": att_name,
                "size_formatted": size_str,
                "file_type": ext,
            }

    content_to_save = submitted or ""
    if not content_to_save and msg_attachment:
        content_to_save = f"Vui lòng xem và rà soát tính pháp lý của văn bản/hợp đồng đính kèm ({msg_attachment['name']}) theo quy định pháp luật lao động Việt Nam."

    try:
        session_mgr.append_message(
            conv_id=active_id,
            role="user",
            content=content_to_save,
            attachment=msg_attachment,
        )
    except TypeError:
        session_mgr.append_message(
            conv_id=active_id,
            role="user",
            content=content_to_save,
        )
        if msg_attachment:
            with ui.utils.session._HISTORY_LOCK:
                convs = session_mgr.load_conversations()
                for c in convs:
                    if c["id"] == active_id and c.get("messages"):
                        c["messages"][-1]["attachment"] = msg_attachment
                        break
                session_mgr.save_conversations(convs)

    full_query = content_to_save
    if extracted_text:
        full_query = (
            f"{content_to_save}\n\n"
            f"--- NỘI DUNG TÀI LIỆU ĐÍNH KÈM ({msg_attachment.get('name') if msg_attachment else 'Văn bản'}) ---\n"
            f"{extracted_text}\n"
            f"--- HẾT NỘI DUNG TÀI LIỆU ---"
        )

    # INSTANT FAST-TRACK FOR SMALLTALK (Greetings, thanks, identity, etc.):
    # Answer immediately with 0 delay and NO thinking indicator.
    st_reply = None
    if not extracted_text:
        from app.chat_service import answer_smalltalk
        conv_messages = (session_mgr.get_conversation(active_id) or {}).get("messages", [])
        st_reply = answer_smalltalk(content_to_save, has_history=len(conv_messages) > 1)

    if st_reply is not None:
        session_mgr.append_message(
            conv_id=active_id,
            role="assistant",
            content=str(st_reply.get("answer", "")),
            structured_data=st_reply,
        )
        st.session_state["ui_view"] = "chat"
    else:
        # Only complex legal questions or document review trigger the asynchronous thinking state
        st.session_state["pending_query"] = full_query
        st.session_state["ui_view"] = "chat"

active_conv = session_mgr.get_conversation(active_id)
messages = (active_conv or {}).get("messages", [])
pending_query = st.session_state.get("pending_query")
view = st.session_state.get("ui_view", "home")
ui_result = render_approved_layout(
    view=view,
    messages=messages,
    conversations=session_mgr.load_conversations(),
    busy=bool(pending_query),
    active_id=active_id,
    notice=st.session_state.pop("ui_notice", ""),
)

# Component events are transient, validated again on the Python boundary.
action = ui_result.get("action") if hasattr(ui_result, "get") else getattr(ui_result, "action", None)
if not pending_query and isinstance(action, dict):
    kind = action.get("type")
    if kind == "navigate" and action.get("view") in {v for v, _, _ in NAVIGATION}:
        st.session_state["ui_view"] = action["view"]
        # Client-side 0ms navigation already displayed the target pane; no full rerun needed
    elif kind == "query":
        question = str(action.get("text") or "").strip()
        attachment = action.get("attachment")
        if (question or attachment) and len(question) <= 4000:
            # The normal conversation path performs persistence and memory sync.
            st.session_state["submitted_query"] = question
            st.session_state["submitted_attachment"] = attachment
            st.rerun()
    elif kind == "new_chat":
        handle_new_chat()
    elif kind == "switch":
        requested = str(action.get("id") or "")
        if session_mgr.get_conversation(requested):
            handle_switch_conv(requested)
    elif kind == "regenerate":
        handle_regenerate()
    elif kind == "delete":
        requested = str(action.get("id") or "")
        if session_mgr.get_conversation(requested):
            session_mgr.delete_conversation(requested)
            if st.session_state.get("active_conv_id") == requested:
                remaining = session_mgr.load_conversations()
                if remaining:
                    st.session_state["active_conv_id"] = remaining[0]["id"]
                    active_conv = remaining[0]
                    for state_key, service in list(st.session_state.items()):
                        if state_key.startswith("chat_service::"):
                            service.restore_conversation(active_conv.get("messages", []))
                else:
                    new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
                    st.session_state["active_conv_id"] = new_c["id"]
                    for state_key, service in list(st.session_state.items()):
                        if state_key.startswith("chat_service::"):
                            service.reset_conversation()
            st.session_state["ui_view"] = "chat"
            st.session_state["ui_notice"] = "Đã xóa cuộc trò chuyện."
            st.rerun()
    elif kind == "feedback" and action.get("rating") in {"up", "down"}:
        handle_feedback(str(action.get("id") or ""), action["rating"])
    elif kind == "general_feedback":
        from app.feedback import build_feedback_record, record_feedback
        comment = str(action.get("text") or "").strip()[:1000]
        if comment:
            saved = record_feedback(build_feedback_record("down", "", "", conv_id=active_id, comment=comment))
            st.session_state["ui_notice"] = "Đã lưu góp ý trên máy này. Cảm ơn bạn!" if saved else "Chưa lưu được góp ý. Vui lòng thử lại."
            st.rerun()

# 7. Keep the existing conversational fast path, streamed inference and
# evidence-locked answer pipeline; only the presentation has changed.
if pending_query:
    user_query = str(pending_query)
    from app.chat_service import answer_smalltalk

    resp_data = answer_smalltalk(user_query, has_history=len(messages) > 1)
    if resp_data is None:
        try:
            st.session_state["chat_service_initialized"] = True
            chat_service = get_chat_service()
            if st.session_state.pop("pending_memory_sync", None) or getattr(chat_service, "_synced_conv_id", None) != active_id:
                active_conv = session_mgr.get_conversation(active_id)
                chat_service.restore_conversation((active_conv or {}).get("messages", []))
                setattr(chat_service, "_synced_conv_id", active_id)
            resp_data = chat_service.ask(user_query, update_memory=True)
        except (ConnectionError, FileNotFoundError):
            resp_data = {
                "answer": "Không thể kết nối mô hình AI cục bộ. Vui lòng mở Ollama và kiểm tra mô hình đã được cài đặt, sau đó thử lại.",
                "findings": [], "citations": [], "needs_clarification": False,
                "clarification_question": None, "suggested_followups": [],
            }
        except Exception:
            resp_data = {
                "answer": "Hệ thống chưa thể xử lý câu hỏi này. Vui lòng thử lại hoặc diễn đạt câu hỏi ngắn gọn hơn.",
                "findings": [], "citations": [], "needs_clarification": False,
                "clarification_question": None, "suggested_followups": [],
            }
    session_mgr.append_message(
        conv_id=active_id, role="assistant", content=str(resp_data.get("answer", "")), structured_data=resp_data,
    )
    # v7 reload trigger


    st.session_state.pop("pending_query", None)
    st.rerun()
