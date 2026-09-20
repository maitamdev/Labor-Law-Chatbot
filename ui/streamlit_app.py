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

import threading
import streamlit as st

from ui.components.chat_message import render_assistant_message, render_user_message
from ui.components.composer import render_composer
from ui.components.right_panel import render_right_panel
from ui.components.sidebar import render_sidebar
from ui.components.welcome import render_welcome_screen
from ui.utils.branding import get_logo_path
from ui.utils.session import SessionManager

# 1. Streamlit Page Configuration
logo_path = get_logo_path()
st.set_page_config(
    page_title="VietLabor AI - Trợ lý pháp luật lao động",
    page_icon=str(logo_path) if logo_path.exists() else "§",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject Custom CSS
CSS_PATH = Path("ui/styles/app.css")
if CSS_PATH.exists():
    css_content = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# 3. Cache ChatService Singleton (Lazy-loaded on first query with background pre-warming)
APP_BUILD_VERSION = "2026.09.17.v3.7_de_facto_contract"

@st.cache_resource(show_spinner=False)
def get_chat_service(build_version: str = APP_BUILD_VERSION):
    from app.chat_service import ChatService
    return ChatService()


# Background pre-warming: pre-loads heavy AI/RAG modules without blocking the UI
def _background_warmup():
    try:
        get_chat_service()
    except Exception:
        pass


if "warmup_started" not in st.session_state:
    st.session_state["warmup_started"] = True
    threading.Thread(target=_background_warmup, daemon=True).start()


session_mgr = SessionManager()

# 4. Initialize Active Conversation State
if "active_conv_id" not in st.session_state or not st.session_state["active_conv_id"]:
    convs = session_mgr.load_conversations()
    if convs:
        st.session_state["active_conv_id"] = convs[0]["id"]
    else:
        new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
        st.session_state["active_conv_id"] = new_c["id"]


# 5. Callbacks for Sidebar Actions
def handle_new_chat():
    new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
    st.session_state["active_conv_id"] = new_c["id"]
    if "chat_service_initialized" in st.session_state:
        get_chat_service().reset_conversation()
    st.rerun()


def handle_switch_conv(conv_id: str):
    st.session_state["active_conv_id"] = conv_id
    if "chat_service_initialized" in st.session_state:
        cs = get_chat_service()
        cs.reset_conversation()
        # Replay previous turn facts if needed into memory
        active_conv = session_mgr.get_conversation(conv_id)
        if active_conv and active_conv.get("messages"):
            for m in active_conv["messages"][-3:]:
                if m["role"] == "user":
                    cs.chain.memory._extract_facts(m["content"])
    st.rerun()


def handle_card_submit(query: str):
    st.session_state["submitted_query"] = query
    st.rerun()


# 6. Render Left Sidebar
render_sidebar(
    session_mgr=session_mgr,
    active_conv_id=st.session_state.get("active_conv_id"),
    on_new_chat=handle_new_chat,
    on_switch_conv=handle_switch_conv,
    on_topic_select=handle_card_submit,
)

# 7. Render Sticky Bottom Chat Composer (handles chat input & card submissions)
user_query = render_composer()

active_id = st.session_state["active_conv_id"]

# If user submitted a new query, append to session immediately so it renders in the feed
if user_query:
    session_mgr.append_message(conv_id=active_id, role="user", content=user_query)

active_conv = session_mgr.get_conversation(active_id)
messages = active_conv.get("messages", []) if active_conv else []

# 8. Render Main 2-Column Layout (Center Chat ~68%, Right Panel ~32%)
col_chat, col_right = st.columns([0.68, 0.32], gap="large")

with col_chat:
    # Top Chat Header
    conv_title = active_conv.get("title") if active_conv else "Cuộc trò chuyện mới"
    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-title">{conv_title}</div>
        <div style="color: #94A3B8; font-size: 18px; cursor: pointer;">⋮</div>
    </div>
    """, unsafe_allow_html=True)

    # Empty State vs Message Feed
    if not messages:
        render_welcome_screen(on_card_click=handle_card_submit)
    else:
        for msg in messages:
            if msg["role"] == "user":
                render_user_message(content=msg["content"], timestamp=msg.get("timestamp", ""))
            else:
                render_assistant_message(msg=msg, on_chip_click=handle_card_submit)

    # If this run was triggered by a new query, run assistant inference right below the user message
    if user_query:
        with st.status("Đang tra cứu và đối soát căn cứ pháp lý...", expanded=True) as status_box:
            st.session_state["chat_service_initialized"] = True
            chat_service = get_chat_service()
            st.write("Đang tra cứu cơ sở dữ liệu luật lao động...")
            try:
                resp_data = chat_service.ask(user_query, update_memory=True)
                status_box.update(label="Hoàn tất tra cứu căn cứ pháp lý!", state="complete", expanded=False)
            except Exception as e:
                status_box.update(label="Có lỗi phát sinh trong quá trình tra cứu", state="error", expanded=False)
                resp_data = {
                    "answer": f"Đã xảy ra lỗi khi tra cứu: {str(e)}",
                    "findings": [],
                    "citations": [],
                    "needs_clarification": False,
                    "clarification_question": None,
                    "suggested_followups": [],
                }

        # Record assistant response
        session_mgr.append_message(
            conv_id=active_id,
            role="assistant",
            content=str(resp_data.get("answer", "")),
            structured_data=resp_data,
        )

        st.rerun()

with col_right:
    render_right_panel(on_topic_click=handle_card_submit)
