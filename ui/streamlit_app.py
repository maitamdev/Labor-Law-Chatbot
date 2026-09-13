# -*- coding: utf-8 -*-
"""
VietLabor AI - Streamlit Web Application (Phase 6)
Official user interface matching the approved mockup.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.chat_service import ChatService
from ui.components.chat_message import render_assistant_message, render_user_message
from ui.components.composer import render_composer
from ui.components.right_panel import render_right_panel
from ui.components.sidebar import render_sidebar
from ui.components.welcome import render_welcome_screen
from ui.utils.session import SessionManager

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title="VietLabor AI - Trợ lý pháp luật lao động",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject Custom CSS
CSS_PATH = Path("ui/styles/app.css")
if CSS_PATH.exists():
    css_content = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


# 3. Cache ChatService Singleton
@st.cache_resource(show_spinner=False)
def get_chat_service() -> ChatService:
    return ChatService()


chat_service = get_chat_service()
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
    chat_service.reset_conversation()
    st.rerun()


def handle_switch_conv(conv_id: str):
    st.session_state["active_conv_id"] = conv_id
    chat_service.reset_conversation()
    # Replay previous turn facts if needed into memory
    active_conv = session_mgr.get_conversation(conv_id)
    if active_conv and active_conv.get("messages"):
        for m in active_conv["messages"][-3:]:
            if m["role"] == "user":
                chat_service.chain.memory._extract_facts(m["content"])
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
        with st.spinner("Đang tra cứu căn cứ pháp lý..."):
            try:
                resp_data = chat_service.ask(user_query, update_memory=True)
            except Exception as e:
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
            content=resp_data["answer"],
            structured_data=resp_data,
        )

        st.rerun()

with col_right:
    render_right_panel(on_topic_click=handle_card_submit)
