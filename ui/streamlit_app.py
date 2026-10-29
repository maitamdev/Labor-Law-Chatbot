# -*- coding: utf-8 -*-
"""
VietLabor AI - Streamlit Web Application (Phase 6)
Official user interface matching the approved mockup.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Enforce 100% offline mode for Hugging Face Hub (zero external network requests, zero warnings, zero progress bars)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.accounts import AccountError
from ui.account_controller import (
    accounts_client,
    authenticate_action,
    feedback_action,
    history_manager,
    render_account_portal,
    resolve_account,
)
from ui.account_controller import logout as account_logout
from ui.account_controller import route as account_route
from ui.components.approved_layout import NAVIGATION, render_approved_layout
from ui.utils.session import InMemorySessionManager

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


def _complete_authentication(action: dict) -> None:
    if not is_authenticated:
        authenticate_action(cloud_accounts, action, session_mgr)


cloud_accounts = accounts_client()
_stored_account = resolve_account(cloud_accounts)
is_authenticated = _stored_account is not None
account_role = str((_stored_account or {}).get("role", "user"))
if is_authenticated:
    account_id = str(_stored_account["id"])
    account_username = str(_stored_account["username"])
else:
    if "guest_session_id" not in st.session_state:
        st.session_state["guest_session_id"] = "guest_" + uuid.uuid4().hex
    account_id = str(st.session_state["guest_session_id"])
    account_username = ""

_surface_state = st.session_state.get(f"approved_surface::{account_id or 'guest'}")
_early_action = _surface_state.get("action") if isinstance(_surface_state, dict) else None
if isinstance(_early_action, dict):
    _early_id = _early_action.get("action_id") or f"{_early_action.get('type')}_{_early_action.get('text')}_{_early_action.get('id')}_{_early_action.get('view')}"
    if _early_id != st.session_state.get("_last_handled_action_id"):
        if _early_action.get("type") == "navigate" and _early_action.get("view") in {v for v, _, _ in NAVIGATION}:
            # Apply navigation before building component markup. Updating it
            # after render sends the previous pane back to the browser.
            st.session_state["ui_view"] = _early_action["view"]
            st.session_state["_last_handled_action_id"] = _early_id
            st.session_state["_last_navigation_action_id"] = _early_id
        elif not st.session_state.get("pending_query") and _early_action.get("type") == "portal_route":
            st.session_state["_last_handled_action_id"] = _early_id
            account_route(str(_early_action.get("view", "")), _stored_account, cloud_accounts.config.configured, rerun=False)
        elif not st.session_state.get("pending_query") and _early_action.get("type") == "logout":
            st.session_state["_last_handled_action_id"] = _early_id
            account_logout(cloud_accounts)

render_account_portal(cloud_accounts, _stored_account)


# 3. Session-local ChatService.
#
# Never cache the ChatService with st.cache_resource: the chain contains mutable
# conversation memory and a globally cached instance can mix facts between
# browser sessions. Heavy embedding weights are already cached by the model
# wrapper itself.
from app.admin_jobs import active_index

APP_BUILD_VERSION = "2026.10.22.accounts-admin-v1::" + str((active_index() or {}).get("version", "v3"))


def _build_shared_hybrid_retriever():
    from app.admin_jobs import active_index
    from rag.hybrid_graph_retriever import HybridGraphRetriever
    from rag.qa_anchor import QuestionLawAnchorIndex
    generation = active_index()
    if generation:
        from rag.bm25_retriever import BM25Retriever
        from rag.dense_retriever import DenseRetriever
        from rag.vectorstore import LegalVectorStore
        root = generation["root"]
        corpus = root / "corpus.jsonl"
        retriever = HybridGraphRetriever(
            bm25_retriever=BM25Retriever(persist_dir=root/"bm25", corpus_path=corpus),
            dense_retriever=DenseRetriever(vectorstore=LegalVectorStore(persist_dir=root/"chroma", corpus_path=corpus, collection_name="vietlabor_chunks_v3")),
        )
    else:
        retriever = HybridGraphRetriever(index_version="v3")
    try:
        retriever.dense_retriever.vectorstore.embedding_model._ensure_model_loaded()
        QuestionLawAnchorIndex()._load()
    except Exception:
        pass
    return retriever


@st.cache_resource(show_spinner=False)
def get_hybrid_retriever_loader(build_version: str):
    """Load retrieval indexes in the background and share them across sessions."""
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vietlabor-retriever")
    return executor, executor.submit(_build_shared_hybrid_retriever)


def get_shared_hybrid_retriever(build_version: str):
    """Share retrieval indexes across sessions while keeping chat memory private."""
    _, future = get_hybrid_retriever_loader(build_version)
    return future.result()


@st.cache_resource(show_spinner=False)
def reset_answer_cache_for_build(build_version: str) -> bool:
    """Invalidate answers once after a build changes, not on every new session."""
    from app import answer_cache

    answer_cache.clear()
    return True


@st.cache_resource(show_spinner=False)
def get_chat_executor(build_version: str) -> ThreadPoolExecutor:
    """Keep expensive model calls off Streamlit's page-rendering thread."""
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="vietlabor-chat")


def get_chat_service(build_version: str = APP_BUILD_VERSION):
    cache_key = f"chat_service::{build_version}::{account_id}"
    if cache_key not in st.session_state:
        reset_answer_cache_for_build(build_version)
        from app.chat_service import ChatService
        from rag.chain import VietLaborRAGChain

        chain = VietLaborRAGChain(
            hybrid_retriever=get_shared_hybrid_retriever(build_version),
        )
        service = ChatService(chain=chain, cache_namespace=account_id)
        active_id = st.session_state.get("active_conv_id")
        if isinstance(active_id, str) and active_id:
            active_conv = session_mgr.get_conversation(active_id)
            service.restore_conversation((active_conv or {}).get("messages", []))
        st.session_state[cache_key] = service
    return st.session_state[cache_key]


if is_authenticated:
    try:
        session_mgr = history_manager(cloud_accounts, _stored_account)
    except AccountError:
        st.session_state["portal_view"] = "account-profile"
        st.session_state["portal_error"] = "Lịch sử tài khoản tạm thời chưa sẵn sàng. Vui lòng thử lại sau hoặc liên hệ quản trị viên."
        st.rerun()
else:
    if "guest_history_manager" not in st.session_state:
        st.session_state["guest_history_manager"] = InMemorySessionManager()
    session_mgr = st.session_state["guest_history_manager"]



def _chat_error_response(exc: Exception | None = None) -> dict:
    if isinstance(exc, (ConnectionError, FileNotFoundError)):
        answer = "Không thể kết nối mô hình AI cục bộ. Vui lòng mở Ollama và kiểm tra mô hình đã được cài đặt, sau đó thử lại."
    else:
        answer = "Hệ thống chưa thể xử lý câu hỏi này. Vui lòng thử lại hoặc diễn đạt câu hỏi ngắn gọn hơn."
    return {
        "answer": answer,
        "findings": [], "citations": [], "needs_clarification": False,
        "clarification_question": None, "suggested_followups": [],
    }


def _run_chat_query(service, retriever_future, messages, conv_id, sync_memory, question, bypass_cache, cache_namespace):
    """Prepare a session's private memory and answer without blocking Streamlit."""
    try:
        if service is None:
            from app.chat_service import ChatService
            from rag.chain import VietLaborRAGChain

            service = ChatService(
                chain=VietLaborRAGChain(hybrid_retriever=retriever_future.result()),
                cache_namespace=cache_namespace,
            )
            sync_memory = True
        if sync_memory:
            service.restore_conversation(messages)
            service._synced_conv_id = conv_id
        response = service.ask(
            question,
            update_memory=True,
            bypass_cache=bypass_cache,
        )
    except Exception as exc:
        response = _chat_error_response(exc)
    return service, response


@st.fragment(run_every=0.5)
def poll_pending_chat_response():
    """Refresh the chat only after the background answer is ready."""
    future = st.session_state.get("pending_chat_future")
    if future is None or not future.done():
        return

    try:
        service, response = future.result()
    except Exception as exc:
        service = None
        response = _chat_error_response(exc)

    if service is not None:
        st.session_state[f"chat_service::{APP_BUILD_VERSION}::{account_id}"] = service
    conv_id = st.session_state.pop("pending_chat_conv_id", None)
    conv_id = conv_id or str(st.session_state.get("active_conv_id") or "")
    if conv_id:
        message_id = session_mgr.append_message(
            conv_id=conv_id,
            role="assistant",
            content=str(response.get("answer", "")),
            structured_data=response,
        )
        st.session_state["typing_msg_id"] = message_id

    started = st.session_state.pop("pending_query_started", None)
    if started is not None and is_authenticated:
        duration = min(3600000, max(0, int((time.perf_counter() - started) * 1000)))
        def save_duration():
            try:
                cloud_accounts.rest("POST", "query_metrics", body={"duration_ms": duration, "success": bool(response.get("citations") or response.get("needs_clarification") or response.get("is_smalltalk"))})
            except AccountError:
                pass
        get_chat_executor(APP_BUILD_VERSION).submit(save_duration)
    st.session_state.pop("pending_chat_future", None)
    st.session_state.pop("pending_query", None)
    st.rerun(scope="app")

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
            service._synced_conv_id = new_c["id"]
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
    st.session_state["bypass_answer_cache"] = True
    st.rerun()


def handle_feedback(action):
    try:
        st.session_state["ui_notice"] = feedback_action(cloud_accounts, _stored_account, session_mgr, action)
    except AccountError as exc:
        st.session_state["ui_notice"] = str(exc)
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

    session_mgr.append_message(
        conv_id=active_id,
        role="user",
        content=content_to_save,
        attachment=msg_attachment,
    )

    full_query = content_to_save
    if extracted_text:
        full_query = (
            f"{content_to_save}\n\n"
            f"--- NỘI DUNG TÀI LIỆU ĐÍNH KÈM ({msg_attachment.get('name') if msg_attachment else 'Văn bản'}) ---\n"
            f"{extracted_text}\n"
            f"--- HẾT NỘI DUNG TÀI LIỆU ---"
        )

    # INSTANT FAST-TRACK FOR SMALLTALK & OFF-TOPIC QUERIES:
    # Answer immediately with 0 delay and NO thinking indicator.
    st_reply = None
    if not extracted_text:
        from app.smalltalk import answer_out_of_scope_fast, answer_smalltalk
        conv_messages = (session_mgr.get_conversation(active_id) or {}).get("messages", [])
        has_hist = len(conv_messages) > 1
        st_reply = answer_smalltalk(content_to_save, has_history=has_hist) or answer_out_of_scope_fast(content_to_save, has_history=has_hist)

    if st_reply is not None:
        st_aid = session_mgr.append_message(
            conv_id=active_id,
            role="assistant",
            content=str(st_reply.get("answer", "")),
            structured_data=st_reply,
        )
        st.session_state["typing_msg_id"] = st_aid
        st.session_state["ui_view"] = "chat"
    else:
        # Only complex legal questions or document review trigger the asynchronous thinking state
        st.session_state["pending_query_started"] = time.perf_counter()
        st.session_state["pending_query"] = full_query
        st.session_state["ui_view"] = "chat"

active_conv = session_mgr.get_conversation(active_id)
messages = (active_conv or {}).get("messages", [])
pending_query = st.session_state.get("pending_query")
view = st.session_state.get("ui_view", "home")
typing_id = str(st.session_state.pop("typing_msg_id", "") or "")
ui_result = render_approved_layout(
    view=view,
    messages=messages,
    conversations=session_mgr.load_conversations(),
    busy=bool(pending_query),
    active_id=active_id,
    notice=st.session_state.pop("ui_notice", ""),
    typing_id=typing_id,
    username=account_username,
    account_id=account_id,
    auth_open=bool(st.session_state.pop("auth_open", False)),
    auth_mode=str(st.session_state.get("auth_mode", "login")),
    auth_error=str(st.session_state.pop("auth_error", "")),
    auth_username=str(st.session_state.get("auth_username", "")),
    role=account_role,
    navigation_ack=str(st.session_state.get("_last_navigation_action_id", "")),
)

# Component events are transient, validated again on the Python boundary.
action = ui_result.get("action") if hasattr(ui_result, "get") else getattr(ui_result, "action", None)
if not pending_query and isinstance(action, dict):
    action_id = action.get("action_id") or f"{action.get('type')}_{action.get('text')}_{action.get('id')}_{action.get('view')}"
    if action_id != st.session_state.get("_last_handled_action_id"):
        st.session_state["_last_handled_action_id"] = action_id
        kind = action.get("type")
        if kind == "navigate" and action.get("view") in {v for v, _, _ in NAVIGATION}:
            st.session_state["ui_view"] = action["view"]
            st.session_state["_last_navigation_action_id"] = action_id
            # Fallback for an event first exposed by the component return value.
            st.rerun()
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
        elif kind == "auth_submit":
            _complete_authentication(action)
        elif kind == "logout":
            account_logout(cloud_accounts)
        elif kind == "portal_route":
            account_route(str(action.get("view", "")), _stored_account, cloud_accounts.config.configured)
        elif kind == "switch":
            requested = str(action.get("id") or "")
            if session_mgr.get_conversation(requested):
                handle_switch_conv(requested)
        elif kind == "regenerate":
            handle_regenerate()
        elif kind == "delete":
            requested = str(action.get("id") or "")
            if requested == "all":
                for conv in session_mgr.load_conversations():
                    session_mgr.delete_conversation(conv["id"])
                new_c = session_mgr.create_conversation("Cuộc trò chuyện mới")
                st.session_state["active_conv_id"] = new_c["id"]
                for state_key, service in list(st.session_state.items()):
                    if state_key.startswith("chat_service::"):
                        service.reset_conversation()
                st.session_state["ui_view"] = "chat"
                st.session_state["ui_notice"] = "Đã xóa toàn bộ lịch sử trò chuyện."
                st.rerun()
            elif requested:
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
            handle_feedback(action)
        elif kind == "general_feedback":
            handle_feedback(action)

# 7. Run RAG inference outside the page-rendering thread so the conversation
# and its thinking indicator remain visible while the local model is working.
if pending_query:
    user_query = str(pending_query)
    from app.smalltalk import answer_smalltalk

    resp_data = answer_smalltalk(user_query, has_history=len(messages) > 1)
    if resp_data is not None:
        new_aid = session_mgr.append_message(
            conv_id=active_id, role="assistant", content=str(resp_data.get("answer", "")), structured_data=resp_data,
        )
        st.session_state["typing_msg_id"] = new_aid
        st.session_state.pop("pending_query", None)
        st.rerun()

    if st.session_state.get("pending_chat_future") is None:
        try:
            st.session_state["chat_service_initialized"] = True
            reset_answer_cache_for_build(APP_BUILD_VERSION)
            chat_service = st.session_state.get(f"chat_service::{APP_BUILD_VERSION}::{account_id}")
            sync_memory = bool(st.session_state.pop("pending_memory_sync", None)) or (
                chat_service is None or getattr(chat_service, "_synced_conv_id", None) != active_id
            )
            _, retriever_future = get_hybrid_retriever_loader(APP_BUILD_VERSION)
            memory_messages = [dict(message) for message in messages]
            if memory_messages and memory_messages[-1].get("role") == "user":
                # The pending question is already stored in chat history; don't
                # replay it as an earlier turn before asking the model about it.
                memory_messages.pop()
            future = get_chat_executor(APP_BUILD_VERSION).submit(
                _run_chat_query,
                chat_service,
                retriever_future,
                memory_messages,
                active_id,
                sync_memory,
                user_query,
                bypass_cache=bool(st.session_state.pop("bypass_answer_cache", False)),
                cache_namespace=account_id,
            )
            st.session_state["pending_chat_future"] = future
            st.session_state["pending_chat_conv_id"] = active_id
        except Exception as exc:
            resp_data = _chat_error_response(exc)
            new_aid = session_mgr.append_message(
                conv_id=active_id, role="assistant", content=str(resp_data.get("answer", "")), structured_data=resp_data,
            )
            st.session_state["typing_msg_id"] = new_aid
            st.session_state.pop("pending_query", None)
            st.rerun()

    poll_pending_chat_response()
