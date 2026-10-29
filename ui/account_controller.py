"""Streamlit account and admin routing; authorization stays on the server."""

from __future__ import annotations

import csv
import io
import json
import logging
from urllib.parse import urlsplit

import streamlit as st

from app.accounts import AccountError, Accounts
from app.admin_service import AdminService, audit_details, filter_audits, safe_id, submit_feedback
from config.supabase import SupabaseConfig
from ui.components.account_portal import PORTAL_VIEWS, render_portal
from ui.utils.cloud_history import SupabaseSessionManager

logger = logging.getLogger(__name__)


def accounts_client():
    if "_accounts_client" not in st.session_state:
        st.session_state["_accounts_client"] = Accounts(SupabaseConfig.load())
    return st.session_state["_accounts_client"]


def resolve_account(client):
    # Custom email templates carry a one-time token_hash, not a password or a
    # reusable refresh token. Stage it for an explicit user click instead of
    # verifying on page load; mail-security scanners often prefetch links.
    token_hash = str(st.query_params.get("token_hash", ""))
    link_type = str(st.query_params.get("type", ""))
    if token_hash:
        for key in ("token_hash", "type"):
            if key in st.query_params:
                del st.query_params[key]
        st.session_state["_pending_auth_token_hash"] = token_hash
        st.session_state["_pending_auth_link_type"] = link_type
        st.session_state["portal_view"] = "account-link-confirm"
        st.rerun()
    if client.session:
        try:
            return client.identity()
        except AccountError as exc:
            client.session.clear()
            st.session_state.pop("_cloud_history", None)
            st.session_state["ui_notice"] = str(exc)
    return None


def history_manager(client, profile):
    manager = st.session_state.get("_cloud_history")
    if manager is None or manager.owner_id != profile["id"]:
        manager = SupabaseSessionManager(client, profile["id"])
        st.session_state["_cloud_history"] = manager
    manager.synchronize_privacy()
    return manager


def logout(client):
    try:
        client.logout()
    except AccountError:
        client.session.clear()
    for key in list(st.session_state):
        del st.session_state[key]
    st.rerun()


def authenticate_action(client, action, guest_history):
    mode = str(action.get("mode", "login"))
    email = str(action.get("username", "")).strip()
    try:
        if mode == "register":
            message = client.signup(
                email,
                str(action.get("password", "")),
                str(action.get("full_name", "")),
                str(action.get("confirm_password", "")),
            )
            st.session_state.update(auth_open=True, auth_mode="verify-sent", ui_notice=message)
        elif mode == "forgot":
            client.recover(email)
            st.session_state.update(auth_open=True, auth_mode="reset-sent")
        elif mode == "login":
            profile = client.login(email, str(action.get("password", "")))
            destination = history_manager(client, profile)
            imported = destination.import_conversations(guest_history.load_conversations())
            active = imported.get(st.session_state.get("active_conv_id", ""))
            if active:
                st.session_state["active_conv_id"] = active
            for key in list(st.session_state):
                if key.startswith("chat_service::") or key in {
                    "guest_history_manager",
                    "pending_query",
                    "pending_chat_future",
                    "pending_chat_conv_id",
                }:
                    del st.session_state[key]
            st.session_state["portal_view"] = "admin-dashboard" if profile["role"] == "admin" else ""
            st.session_state["ui_notice"] = "Đã đăng nhập. Lịch sử được lưu riêng cho tài khoản của bạn."
        else:
            raise AccountError("Yêu cầu xác thực không hợp lệ.")
    except AccountError as exc:
        st.session_state.update(
            auth_open=True, auth_mode=mode if mode in {"login", "register", "forgot"} else "login", auth_error=str(exc)
        )
    st.session_state["auth_username"] = email[:254]
    st.rerun()


def route(view, profile, configured=True, selected="", *, rerun=True):
    allowed = PORTAL_VIEWS | {"home", "chat"}
    if view not in allowed:
        return
    if view in {"home", "chat"}:
        st.session_state["portal_view"] = ""
        st.session_state["ui_view"] = view
    elif view.startswith("admin-"):
        st.session_state["portal_view"] = view if profile and profile["role"] == "admin" else "access-denied"
    elif (
        view.startswith("account-")
        and not profile
        and view not in {"account-reset-success", "account-password-success"}
    ):
        st.session_state["portal_view"] = "setup" if not configured else "access-denied"
    else:
        st.session_state["portal_view"] = view
    st.session_state["portal_selected"] = str(selected or "")
    if rerun:
        st.rerun()


def dispatch_portal(client, profile, action, *, rerun_on_route=True):
    kind = action.get("type")
    fields = action.get("fields") or {}
    if not isinstance(fields, dict):
        raise AccountError("Dữ liệu biểu mẫu không hợp lệ.")
    if kind == "portal_route":
        route(
            str(action.get("view", "")),
            profile,
            client.config.configured,
            action.get("id", ""),
            rerun=rerun_on_route,
        )
        return
    if kind == "logout":
        logout(client)
    if kind == "portal_refresh":
        return
    if kind == "account_verify_link":
        token_hash = st.session_state.pop("_pending_auth_token_hash", "")
        link_type = st.session_state.pop("_pending_auth_link_type", "")
        verifier = Accounts(client.config)
        try:
            verifier.verify_email_link(token_hash, link_type)
        except AccountError as exc:
            st.session_state["portal_view"] = "account-link-error"
            st.session_state["portal_error"] = str(exc)
            return
        if link_type in {"recovery", "invite"}:
            st.session_state["_recovery_client"] = verifier
            st.session_state["_recovery_type"] = link_type
            st.session_state["portal_view"] = "account-recovery"
        else:
            verifier.logout()
            st.session_state["portal_view"] = ""
            st.session_state["auth_open"] = True
            st.session_state["auth_mode"] = "login"
            st.session_state["ui_notice"] = "Email đã được xác minh. Bạn có thể đăng nhập."
        return
    if kind == "account_reset_password":
        verifier = st.session_state.get("_recovery_client")
        if verifier is None:
            raise AccountError("Liên kết khôi phục đã hết hạn. Hãy gửi yêu cầu mới.")
        verifier.change_password(
            None, str(fields.get("password", "")), str(fields.get("confirm_password", "")), recovery=True
        )
        if st.session_state.get("_recovery_type") == "invite":
            verifier.rpc("accept_administrator_invitation")
        verifier.logout()
        st.session_state.pop("_recovery_client", None)
        st.session_state.pop("_recovery_type", None)
        client.session.clear()
        st.session_state["portal_view"] = "account-reset-success"
        return
    if not profile:
        raise AccountError("Bạn cần đăng nhập để tiếp tục.")
    if kind == "account_update_profile":
        client.identity()
        client.update_name(str(fields.get("full_name", "")))
    elif kind == "account_change_password":
        client.change_password(
            str(fields.get("current_password", "")),
            str(fields.get("password", "")),
            str(fields.get("confirm_password", "")),
        )
        client.logout()
        st.session_state.pop("_cloud_history", None)
        st.session_state["portal_view"] = "account-password-success"
    elif kind == "account_logout_others":
        client.identity()
        client.logout("others")
    elif kind == "account_send_recovery":
        client.recover(client.identity()["email"])
    elif kind == "account_export_history":
        trusted = client.identity()
        rows = client.rows("conversations", select="id,payload", filters={"owner_id":"eq." + trusted["id"]}, order="updated_at.desc")
        st.session_state["portal_download"] = {"name":"lich-su-cua-toi.json", "mime":"application/json",
            "content":json.dumps({"conversations":[row["payload"] for row in rows]},ensure_ascii=False,indent=2)}
    elif kind == "account_delete_history":
        trusted = client.identity()
        if fields.get("confirmed") is not True:
            raise AccountError("Cần xác nhận trước khi xóa lịch sử của bạn.")
        client.rpc("delete_my_conversations")
        from app.answer_cache import clear_namespace
        clear_namespace(trusted["id"])
        for key in list(st.session_state):
            if key.startswith("chat_service::") or key.startswith("pending_") or key in {"_cloud_history","active_conv_id","typing_msg_id","submitted_query","submitted_attachment"}:
                st.session_state.pop(key, None)
    elif kind in {"account_feedback_withdraw", "account_feedback_delete"}:
        client.identity()
        client.rpc("withdraw_my_feedback_consent" if kind == "account_feedback_withdraw" else "delete_my_feedback",
                   {"feedback_id":safe_id(action.get("id", ""))})
    elif kind.startswith("admin_"):
        client.require_admin()
        service = AdminService(client)
        if kind == "admin_account_update":
            service.account_update(fields)
        elif kind == "admin_invite":
            client.invite_admin(str(fields.get("email", "")))
        elif kind == "admin_invitation_cancel":
            service.cancel_invitation(action.get("id", ""))
        elif kind == "admin_reset_user":
            rows = client.rows("profiles", filters={"id": "eq." + safe_id(action.get("id"))})
            if not rows:
                raise AccountError("Không tìm thấy tài khoản.")
            if rows[0]["role"] == "admin":
                client.require_security_admin()
            client.recover(rows[0]["email"])
        elif kind == "admin_document_save":
            st.session_state["portal_selected"] = service.document_save(fields, action.get("upload"))
        elif kind == "admin_document_approve":
            job = service.approve_document(fields.get("id"), fields.get("confirmed"))
            from app.admin_jobs import launch

            launch(client, job)
            st.session_state["portal_view"] = "admin-operations"
        elif kind == "admin_feedback_save":
            service.review_feedback(fields)
        elif kind == "admin_feedback_export":
            rows = client.rows("feedback", select="id,share_consent,question,answer,comment,admin_note",
                               filters={"id": "eq." + safe_id(action.get("id"))})
            if not rows or not rows[0]["share_consent"]:
                raise AccountError("Phản hồi không có nội dung được chia sẻ.")
            row = rows[0]
            st.session_state["portal_download"] = {
                "name": "feedback-case-" + row["id"] + ".json",
                "mime": "application/json",
                "content": json.dumps(
                    {
                        "question": row["question"],
                        "reported_answer": row["answer"],
                        "comment": row["comment"],
                        "admin_note": row["admin_note"],
                        "source": "user_shared_feedback",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        elif kind == "admin_settings_save":
            service.save_settings(fields)
        elif kind in {"admin_health", "admin_backup", "admin_restore"}:
            if kind == "admin_restore" and fields.get("confirmed") is not True:
                raise AccountError("Cần xác nhận bản sao lưu trước khi khôi phục.")
            job = service.enqueue(
                {"admin_health": "health", "admin_backup": "backup", "admin_restore": "restore"}[kind],
                payload={"backup_id": fields.get("backup_id")} if kind == "admin_restore" else None,
            )
            from app.admin_jobs import launch

            launch(client, job)
        elif kind == "admin_job_retry":
            from app.admin_jobs import launch

            launch(client, str(action.get("id", "")))
        elif kind == "admin_audit_export":
            rows = filter_audits(client.rows("admin_audit"), action.get("filters"))
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Thời gian", "Người thực hiện", "Thao tác", "Đối tượng", "Chi tiết"])
            for row in rows:
                # Prevent spreadsheet formulas when the CSV is opened in Excel.
                writer.writerow(
                    [
                        ("'" + str(v)) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v
                        for v in [row["created_at"], row["actor_id"] or "", row["action"], row["target_id"],
                                  "; ".join(label + ": " + value for label, value in audit_details(row))]
                    ]
                )
            st.session_state["portal_download"] = {
                "name": "nhat-ky-quan-tri.csv",
                "mime": "text/csv;charset=utf-8",
                "content": "\ufeff" + output.getvalue(),
            }
        else:
            raise AccountError("Thao tác quản trị không hợp lệ.")
    else:
        raise AccountError("Thao tác không được hỗ trợ.")


def _capture_portal_action():
    """Queue browser events before the script rerun starts loading page data."""
    state = st.session_state.get("account-admin-portal", {})
    action = state.get("action") if isinstance(state, dict) else None
    if isinstance(action, dict):
        st.session_state["_pending_portal_action"] = dict(action)


def _handle_portal_action(client, profile, action, *, before_render=False):
    if not isinstance(action, dict):
        return False
    action_id = action.get("action_id")
    if not action_id or action_id == st.session_state.get("_last_portal_action"):
        return False
    st.session_state["_last_portal_action"] = action_id
    st.session_state.pop("portal_error", None)
    st.session_state.pop("portal_notice", None)
    st.session_state.pop("_portal_form_draft", None)
    cur_view = str(action.get("current_view") or "")
    if cur_view in PORTAL_VIEWS and action.get("type") != "portal_route":
        st.session_state["portal_view"] = cur_view
        if "current_id" in action:
            st.session_state["portal_selected"] = str(action.get("current_id") or "")
    messages = {
        "portal_refresh": "Dữ liệu đã được cập nhật.",
        "admin_account_update": "Đã cập nhật quyền và trạng thái tài khoản.",
        "admin_invite": "Đã gửi lời mời quản trị viên qua email.",
        "admin_invitation_cancel": "Đã hủy lời mời quản trị viên.",
        "admin_reset_user": "Đã gửi liên kết khôi phục qua email.",
        "admin_document_save": "Đã lưu văn bản. Kiểm tra nội dung trước khi duyệt.",
        "admin_document_approve": "Đã duyệt văn bản và tạo tác vụ lập chỉ mục.",
        "admin_feedback_save": "Đã lưu kết quả xử lý phản hồi.",
        "account_export_history": "Đã chuẩn bị bản xuất lịch sử của chính bạn.",
        "account_delete_history": "Đã xóa lịch sử trò chuyện của bạn trên hệ thống.",
        "account_feedback_withdraw": "Đã thu hồi và xóa đoạn chat đã chia sẻ trong phản hồi này.",
        "account_feedback_delete": "Đã xóa phản hồi của bạn.",
        "admin_settings_save": "Đã lưu cài đặt ứng dụng.",
        "admin_health": "Đã tạo tác vụ kiểm tra dịch vụ.",
        "admin_backup": "Đã tạo tác vụ sao lưu.",
        "admin_restore": "Đã tạo tác vụ khôi phục metadata.",
        "admin_job_retry": "Đã gửi yêu cầu chạy lại tác vụ.",
        "account_update_profile": "Đã cập nhật hồ sơ cá nhân.",
        "account_logout_others": "Đã thu hồi quyền làm mới phiên trên thiết bị khác.",
        "account_send_recovery": "Đã gửi yêu cầu khôi phục. Hãy kiểm tra hộp thư.",
    }
    try:
        dispatch_portal(client, profile, action, rerun_on_route=not before_render)
        if action.get("type") in messages and not action.get("background"):
            st.session_state["portal_notice"] = messages[action["type"]]
    except (AccountError, OSError, ValueError) as exc:
        st.session_state["portal_error"] = (
            str(exc) if isinstance(exc, AccountError)
            else "Không thực hiện được thao tác. Kiểm tra dữ liệu và thử lại."
        )
        fields = action.get("fields")
        if isinstance(fields, dict):
            st.session_state["_portal_form_draft"] = {
                "kind": action.get("type"),
                "fields": {key: value for key, value in fields.items() if "password" not in key.lower()},
            }
    except Exception:
        logger.exception("Unexpected error handling admin portal action %s", action.get("type", "unknown"))
        st.session_state["portal_error"] = "Đã xảy ra lỗi khi xử lý yêu cầu. Tải lại trang rồi thử lại."
    if not before_render:
        st.rerun()
    return True


def render_account_portal(client, profile):
    acted = _handle_portal_action(
        client,
        profile,
        st.session_state.pop("_pending_portal_action", None),
        before_render=True,
    )
    if acted and profile and client.session:
        try:
            profile = client.identity()
        except AccountError:
            pass
    view = st.session_state.get("portal_view", "")
    if not view:
        return
    if view not in PORTAL_VIEWS:
        st.session_state["portal_view"] = ""
        return
    if view == "account-recovery" and not st.session_state.get("_recovery_client"):
        view = "access-denied"
    elif (
        view.startswith("account-")
        and not profile
        and view not in {
            "account-recovery",
            "account-link-confirm",
            "account-link-error",
            "account-password-success",
            "account-reset-success",
        }
    ):
        view = "access-denied"
    data = {}
    error = st.session_state.pop("portal_error", "")
    if profile and profile.get("role") == "admin" and (view.startswith("admin-") or view in {"account-profile", "account-privacy", "account-password"}):
        try:
            data = AdminService(client).load(view, preload_all=True)
            if not (data.get("permissions") or {}).get("configured"):
                error = "Cần chạy migration 202610240003 trong Supabase để bật đầy đủ các giới hạn quyền riêng tư. Quyền cấp admin đang bị khóa."
            if view in {"admin-operations", "admin-audit"}:
                from app.admin_jobs import resume_jobs

                resume_jobs(client, profile, data.get("admin_jobs", []))
        except AccountError as exc:
            error = str(exc)
        except Exception:
            logger.exception("Unexpected error loading admin view %s", view)
            error = "Không tải được dữ liệu trang này. Hãy thử tải lại; nếu lỗi lặp lại, kiểm tra log máy chủ."
    elif view.startswith("admin-"):
        view = "access-denied"
    elif view in {"account-profile", "account-privacy", "account-password"} and profile:
        try:
            client.identity()
            data["my_feedback"] = client.rpc("my_feedback") or []
            data["privacy_configured"] = True
        except AccountError as exc:
            data["privacy_configured"] = False
            if view == "account-privacy":
                error = str(exc)
    data["can_invite"] = bool(client.config.service_key) and (data.get("permissions") or {}).get("manage_admins") is True
    hostname = urlsplit(client.config.url).hostname or ""
    if hostname.endswith(".supabase.co"):
        data["supabase_dashboard"] = "https://supabase.com/dashboard/project/" + hostname.split(".")[0]
    from app.admin_jobs import list_backups

    result = render_portal(
        view=view,
        profile=profile,
        data=data,
        link_type=st.session_state.get("_pending_auth_link_type", ""),
        selected=st.session_state.get("portal_selected", ""),
        message=st.session_state.pop("portal_notice", ""),
        error=error,
        backups=list_backups() if profile and profile.get("role") == "admin" else [],
        download=st.session_state.pop("portal_download", None),
        on_action_change=_capture_portal_action,
        form_draft=st.session_state.pop("_portal_form_draft", None),
        poll_after=5000 if view in {"admin-operations", "admin-audit"} and any(j.get("status") in {"pending", "running"} for j in data.get("admin_jobs", [])) else 0,
    )
    action = result.get("action") if hasattr(result, "get") else getattr(result, "action", None)
    _handle_portal_action(client, profile, action, before_render=False)
    st.stop()


def feedback_action(client, profile, manager, action):
    if not profile:
        raise AccountError("Vui lòng đăng nhập để gửi phản hồi và theo dõi yêu cầu.")
    conversation = manager.get_conversation(str(st.session_state.get("active_conv_id", ""))) or {}
    messages = conversation.get("messages", [])
    msg_id = str(action.get("id", ""))
    selected = next(
        ((i, m) for i, m in enumerate(messages) if m.get("id") == msg_id and m.get("role") == "assistant"), None
    )
    question = answer = ""
    if selected:
        index, message = selected
        question = next((m.get("content", "") for m in reversed(messages[:index]) if m.get("role") == "user"), "")
        answer = message.get("content", "")
    elif action.get("type") == "feedback":
        raise AccountError("Không tìm thấy câu trả lời trong cuộc trò chuyện của bạn.")
    consent = action.get("share_consent") is True and selected is not None
    submit_feedback(
        client,
        rating=action.get("rating", "down"),
        comment=action.get("comment") or action.get("text", ""),
        question=question,
        answer=answer,
        share_consent=bool(consent),
    )
    if selected:
        manager.set_message_feedback(conversation["id"], msg_id, action["rating"])
    return "Đã gửi phản hồi." + (
        " Đã chia sẻ đoạn bạn chọn." if consent else " Nội dung chat không được gửi cho admin."
    )
