"""The approved account/admin screens, populated only with authorized data."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from streamlit.components.v2 import component

from app.admin_service import AUDIT_LABELS, VIETNAM_TIME, audit_day, audit_details, audit_search_text
from ui.components.approved_layout import esc, icon, sprite

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
ADMIN_NAV = [
    ("admin-dashboard", "Tổng quan", "home-filled"),
    ("admin-users", "Người dùng", "user"),
    ("admin-documents", "Kho văn bản", "file-text"),
    ("admin-feedback", "Phản hồi", "message-dots"),
    ("admin-operations", "Vận hành AI", "settings"),
    ("admin-audit", "Nhật ký & sao lưu", "clock"),
    ("admin-settings", "Cài đặt & bảo mật", "shield-lock"),
]
PORTAL_VIEWS = {x[0] for x in ADMIN_NAV} | {
    "admin-user-detail",
    "admin-document-add",
    "account-profile",
    "account-privacy",
    "account-password",
    "account-password-success",
    "account-recovery",
    "account-reset-success",
    "account-link-confirm",
    "account-link-error",
    "access-denied",
    "setup",
}


def btn(label, route="", action="", id="", kind="secondary", confirm=""):
    attrs = f'data-route="{esc(route)}"' if route else f'data-action="{esc(action)}"'
    return f'<button type="button" class="btn {esc(kind)}" {attrs} data-id="{esc(id)}" {f"data-confirm={chr(34)}{esc(confirm)}{chr(34)}" if confirm else ""}>{esc(label)}</button>'


def badge(label, tone="neutral"):
    return f'<span class="badge {tone}">{esc(label)}</span>'


def brand(admin=False):
    caption = "KHÔNG GIAN QUẢN TRỊ" if admin else "TRỢ LÝ PHÁP LUẬT LAO ĐỘNG"
    return f'<div class="demo-brand"><span class="brand-mark">{icon("scale")}</span><span>VietLabor<span class="brand-ai">AI</span><small>{caption}</small></span></div>'


def field(label, name, value="", type="text", placeholder="", required=True, extra=""):
    control = f'<input name="{esc(name)}" type="{esc(type)}" value="{esc(value)}" placeholder="{esc(placeholder)}" {"required" if required else ""} {extra}>'
    if type == "password":
        control = f'<span class="portal-password-field">{control}<button type="button" data-reveal="{esc(name)}" aria-label="Hiện mật khẩu">Hiện</button></span>'
    return f'<label class="field"><span>{esc(label)}</span>{control}</label>'


def select(label, name, options, value="", extra=""):
    choices = "".join(
        '<option value="' + esc(v) + '"' + (" selected" if str(v) == str(value) else "") + ">" + esc(t) + "</option>"
        for v, t in options
    )
    return (
        f'<label class="field"><span>{esc(label)}</span><select name="{esc(name)}" {extra}>{choices}</select></label>'
    )


def textarea(label, name, value="", placeholder="", maxlength=4000):
    return f'<label class="field full"><span>{esc(label)}</span><textarea name="{esc(name)}" maxlength="{int(maxlength)}" placeholder="{esc(placeholder)}">{esc(value)}</textarea></label>'


def form(action, body, label="Lưu thay đổi", confirm=""):
    return f'<form data-form="{esc(action)}" {f"data-confirm={chr(34)}{esc(confirm)}{chr(34)}" if confirm else ""}>{body}<p class="form-error" role="alert" hidden></p><div class="align-right"><button type="submit" class="btn primary">{esc(label)}</button></div></form>'


def hidden(name, value):
    return f'<input type="hidden" name="{esc(name)}" value="{esc(value)}">'


def panel(title, subtitle, body, action="", cls=""):
    return f'<section class="panel {cls}"><div class="panel-head"><div><h2>{esc(title)}</h2><p>{esc(subtitle)}</p></div>{action}</div>{body}</section>'


def table(headers, rows, attrs=None):
    body = "".join(
        f"<tr data-search-row {attrs[i] if attrs else ''}>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>"
        for i, row in enumerate(rows)
    )
    if not rows:
        body = (
            f'<tr><td colspan="{len(headers)}"><div class="empty-state">Chưa có dữ liệu trong mục này.</div></td></tr>'
        )
    return (
        '<div class="table-scroll"><table class="data-table"><thead><tr>'
        + "".join(f"<th>{esc(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></div><nav class=\"pagination\" aria-label=\"Phân trang bảng\"><span data-result-count aria-live=\"polite\"></span><div class=\"page-controls\"><button type=\"button\" data-page-turn=\"prev\" aria-label=\"Trang trước\">‹</button><span data-page-label></span><button type=\"button\" data-page-turn=\"next\" aria-label=\"Trang sau\">›</button><label class=\"page-size-label\">Mỗi trang <select data-page-size aria-label=\"Số dòng mỗi trang\"><option value=\"25\">25</option><option value=\"50\">50</option><option value=\"100\">100</option></select></label></div></nav>"
    )


def date(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(VIETNAM_TIME).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return "—"


def notice(text, error=False, success=False):
    return (
        f'<div class="notice {"warning-notice" if error else "success-notice" if success else "subtle"}" role="{"alert" if error else "status"}">{icon("info-circle")}{esc(text)}</div>'
        if text
        else ""
    )


def status(value):
    labels = {
        "active": ("Hoạt động", "success"),
        "blocked": ("Tạm khóa", "danger"),
        "draft": ("Bản nháp", "neutral"),
        "review": ("Chờ duyệt", "warning"),
        "approved": ("Đã duyệt", "success"),
        "indexed": ("Đã lập chỉ mục", "success"),
        "pending": ("Chờ xử lý", "warning"),
        "reviewing": ("Đang xem xét", "warning"),
        "resolved": ("Đã xử lý", "success"),
        "running": ("Đang chạy", "warning"),
        "succeeded": ("Hoàn tất", "success"),
        "failed": ("Cần kiểm tra", "danger"),
    }
    return badge(*labels.get(value, (str(value), "neutral")))


def admin_shell(
    view, profile, title, subtitle, body, actions="", message="", error="", workspace="Không gian quản trị",
    pending_feedback=0,
):
    active = {"admin-user-detail": "admin-users", "admin-document-add": "admin-documents"}.get(view, view)
    nav = "".join(
        f'<button class="admin-nav {"active" if key == active else ""}" data-route="{key}" {"aria-current=page" if key == active else ""}>{icon(glyph)}<span>{label}</span>'
        + (f'<span class="nav-count">{esc(pending_feedback)}</span>' if key == "admin-feedback" and pending_feedback else "")
        + '</button>'
        for key, label, glyph in ADMIN_NAV
    )
    name = profile.get("full_name") or profile.get("email", "")
    initials = "".join(w[0] for w in name.split()[-2:]).upper() or "QT"
    return f"""<div class="admin-app" data-page="{esc(view)}" data-owner="{esc(profile.get("id", ""))}"><aside class="admin-sidebar">{brand(True)}<nav aria-label="Điều hướng quản trị">{nav}</nav><div class="sidebar-bottom"><div class="sidebar-privacy">{icon("lock")}<div><strong>Lịch sử luôn riêng tư</strong><small>Chỉ xem nội dung được chia sẻ</small></div></div><button class="back-ai" data-route="home">{icon("chevron-right")}Trở về trợ lý AI</button><div class="admin-identity"><span class="avatar">{esc(initials)}</span><div><strong>{esc(name)}</strong><small>Quản trị viên</small></div><button data-action="logout" aria-label="Đăng xuất" title="Đăng xuất">{icon("logout")}</button></div></div></aside><button type="button" class="mobile-scrim" data-menu aria-label="Đóng menu" hidden></button><div class="admin-main"><header class="admin-topbar"><button class="menu-toggle" data-menu aria-label="Mở menu" aria-expanded="false">{icon("menu")}</button><div class="breadcrumb">Quản trị <span>/</span><strong>{esc(title)}</strong></div><div class="topbar-end"><button class="btn security-button" data-route="account-profile">{icon("shield-lock")}Bảo mật tài khoản</button><span class="avatar small rose" title="{esc(name)}">{esc(initials)}</span></div></header><main class="admin-content"><div class="page-heading"><div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div><div class="page-actions">{actions}</div></div>{notice(error, True)}{notice(message, success=True)}{body}<footer class="prototype-foot">{icon("lock")}Lịch sử trò chuyện luôn riêng tư. Chỉ xem nội dung được người dùng chủ động chia sẻ.</footer></main></div><div class="portal-progress" role="status" hidden>Đang xử lý yêu cầu…</div></div>"""


def metric(label, value, help, glyph, featured=False):
    formatted = f"{value:,}".replace(",", ".") if isinstance(value, int) else value
    return f'<article class="metric {"featured" if featured else ""}"><div class="metric-label">{esc(label)}<span>{icon(glyph)}</span></div><strong>{esc(formatted)}</strong><small>{esc(help)}</small></article>'


def audit_label(action):
    return AUDIT_LABELS.get(action, action)


def short_id(value):
    value = str(value or "")
    return f'<span class="record-id" title="{esc(value)}">{esc(value[:8]) or "Hệ thống"}</span>'


def dashboard(data):
    stats = data.get("stats", {})
    median = stats.get("median_ms")
    metrics = (
        '<div class="metrics-grid">'
        + metric("Người dùng", stats.get("users", 0), "Tài khoản trong hệ thống", "users", True)
        + metric("Lượt tra cứu", stats.get("queries", 0), "Trong 7 ngày gần đây", "file-search")
        + metric("Phản hồi chờ xử lý", stats.get("pending_feedback", 0), "Cần bạn xem xét", "message-dots")
        + metric(
            "Thời gian trả lời",
            f"{median / 1000:.1f}".replace(".", ",") + " s" if median is not None else "—",
            "Trung vị · số đo thực tế",
            "clock",
        )
        + "</div>"
    )
    days = stats.get("daily", [])
    maximum = max(10, ((max((int(d["count"]) for d in days), default=0) + 4) // 5) * 5)
    bars = "".join(
        f'<div class="chart-column" style="--bar-height:{int(d["count"]) / maximum * 100:.2f}%"><span>{int(d["count"])}</span><div class="chart-bar"></div><small>{esc(str(d["day"])[8:10] + "/" + str(d["day"])[5:7])}</small></div>'
        for d in days
    )
    empty = '<div class="chart-empty"><strong>Chưa có lượt tra cứu</strong><span>Biểu đồ sẽ cập nhật khi tài khoản đăng nhập sử dụng trợ lý.</span></div>' if not any(d["count"] for d in days) else ""
    chart = panel(
        "Hoạt động tra cứu",
        "Lượt sử dụng trong 7 ngày gần đây",
        '<div class="chart-area"><div class="chart-axis" aria-hidden="true">' + ''.join(f'<span>{maximum * (5-i) // 5}</span>' for i in range(6)) + '</div><div class="bar-chart" aria-label="Số lượt tra cứu trong 7 ngày">'
        + bars
        + '</div>' + empty + '</div><div class="chart-caption">' + icon("lock") + 'Chỉ thống kê lượt sử dụng, không thu thập nội dung câu hỏi.</div>',
        action='<span class="chart-legend"><i aria-hidden="true"></i>Lượt tra cứu</span>', cls="activity-panel",
    )
    tasks = "".join(
        f'<button class="task-row" data-route="{route}"><span class="task-icon">{icon(glyph)}</span><span><strong>{esc(title)}</strong><small>{esc(help)}</small></span>{icon("chevron-right")}</button>'
        for title, help, glyph, route in [
            (
                f"{stats.get('pending_feedback', 0)} phản hồi chờ xử lý",
                "Kiểm tra góp ý từ người dùng.",
                "message-dots",
                "admin-feedback",
            ),
            (
                f"{stats.get('pending_documents', 0)} văn bản chờ duyệt",
                "Kiểm tra nguồn và hiệu lực văn bản.",
                "file-text",
                "admin-documents",
            ),
            ("Vận hành hệ thống", "Theo dõi dịch vụ và tác vụ nền.", "settings", "admin-operations"),
        ]
    )
    audits = data.get("admin_audit", [])[:3]
    recent = table(
        ["Thời gian", "Hoạt động", "Đối tượng", "Trạng thái"],
        [[date(a["created_at"]), esc(audit_label(a["action"])), short_id(a.get("target_id", "")), badge("Đã ghi nhận", "success")] for a in audits],
    )
    return (
        metrics
        + '<div class="dashboard-middle">'
        + chart
        + panel("Cần bạn xử lý", "", tasks + '<button class="task-all" data-route="admin-audit">Xem tất cả hoạt động <span>→</span></button>', action=badge("3 mục", "attention-count"), cls="attention-panel")
        + "</div>"
        + panel("Hoạt động gần đây", "Các thay đổi mới nhất trong không gian quản trị", recent, f'<button class="btn text" data-route="admin-audit">Xem nhật ký {icon("external-link")}</button>', cls="recent-panel")
    )


def users_page(data, selected=""):
    users = data.get("profiles", [])
    manage_admins = (data.get("permissions") or {}).get("manage_admins") is True
    filters = (
        '<div class="table-toolbar"><label class="search-box">'
        + icon("search")
        + '<input data-search placeholder="Tìm theo tên hoặc email" aria-label="Tìm người dùng"></label><select data-filter-column="role" aria-label="Lọc vai trò"><option value="">Tất cả vai trò</option><option value="user">Người dùng</option><option value="admin">Quản trị viên</option></select><select data-filter-column="status" aria-label="Lọc trạng thái"><option value="">Tất cả trạng thái</option><option value="active">Hoạt động</option><option value="blocked">Tạm khóa</option></select></div>'
    )
    rows = []
    attrs = []
    for u in users:
        rows.append(
            [
                f'<div class="person"><span class="avatar pale">{esc((u.get("full_name") or "U")[:1])}</span><div><strong>{esc(u.get("full_name"))}</strong><small>{esc(u["email"])}</small></div></div>',
                badge("Quản trị viên" if u["role"] == "admin" else "Người dùng"),
                status(u["status"]),
                badge("Đã xác minh", "success") if u["email_verified"] else badge("Chờ xác minh", "warning"),
                date(u["created_at"]),
                btn("Chi tiết", "admin-user-detail", id=u["id"], kind="table-action"),
            ]
        )
        attrs.append(f'data-role="{esc(u["role"])}" data-status="{esc(u["status"])}"')
    body = panel(
        "Danh sách tài khoản",
        "Thông tin truy cập; không hiển thị lịch sử hoặc tiêu đề chat.",
        filters
        + table(["Người dùng", "Vai trò", "Trạng thái", "Email", "Ngày tham gia", ""], rows, attrs),
    )
    invite = form(
        "admin_invite",
        field("Email quản trị viên mới", "email", type="email", placeholder="quantri@example.com"),
        "Gửi lời mời",
        "Gửi email mời quản trị viên đến địa chỉ này?",
    )
    invite_note = notice("Gửi lời mời cần cấu hình khóa máy chủ Supabase. Hiện bạn vẫn có thể cấp quyền cho tài khoản đã đăng ký trong mục Chi tiết.") if not data.get("can_invite", True) else ""
    if not data.get("can_invite", True):
        invite = btn("Xem tài khoản hiện có", "admin-users")
    if manage_admins:
        body += f'<dialog class="portal-dialog" id="invite-admin" aria-labelledby="invite-title"><header><div><h2 id="invite-title">Mời quản trị viên</h2><p>Người được mời xác minh email và tự đặt mật khẩu.</p></div><button type="button" data-close-dialog aria-label="Đóng">{icon("x")}</button></header>{invite_note}{invite}</dialog>'
    else:
        body += notice("Admin nghiệp vụ chỉ quản lý trạng thái tài khoản người dùng. Cấp quyền và hỗ trợ tài khoản admin thuộc quản trị viên chính.")
    pending_invitations = [
        row for row in data.get("admin_invitations", [])
        if not row.get("cancelled") and not row.get("accepted_at")
        and datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")).astimezone().timestamp() > datetime.now().timestamp()
    ]
    invitation_rows = [
        [
            esc(row["email"]),
            date(row["created_at"]),
            date(row["expires_at"]),
            btn("Hủy lời mời", action="admin_invitation_cancel", id=row["id"], kind="table-action danger-ghost", confirm="Hủy lời mời quản trị viên này?"),
        ]
        for row in pending_invitations
    ]
    invitation_panel = panel(
        "Lời mời quản trị đang chờ",
        "Lời mời hết hạn sau 24 giờ. Chỉ người có đúng địa chỉ email đã xác minh mới nhận được quyền admin.",
        table(["Email", "Gửi lúc", "Hết hạn", ""], invitation_rows)
        if invitation_rows else '<div class="empty-state">Không có lời mời nào đang chờ xác nhận.</div>',
    )
    if manage_admins:
        body += invitation_panel
    if selected:
        user = next((u for u in users if u["id"] == selected), None)
        if user:
            content = (
                hidden("id", user["id"])
                + (select("Vai trò", "role", [("user", "Người dùng"), ("admin", "Quản trị viên")], user["role"])
                   if manage_admins else hidden("role", user["role"]) + badge("Người dùng" if user["role"] == "user" else "Quản trị viên"))
                + select("Trạng thái", "status", [("active", "Hoạt động"), ("blocked", "Tạm khóa")], user["status"])
                + textarea("Lý do thay đổi", "reason", placeholder="Ghi lý do để lưu nhật ký", maxlength=500)
            )
            management = form("admin_account_update", content, confirm="Xác nhận thay đổi quyền hoặc trạng thái tài khoản?") if manage_admins or user["role"] == "user" else notice("Chỉ quản trị viên chính được thay đổi hoặc hỗ trợ tài khoản admin.")
            recovery_button = btn("Gửi liên kết khôi phục", action="admin_reset_user", id=user["id"], confirm="Gửi email khôi phục mật khẩu cho tài khoản này?") if manage_admins or user["role"] == "user" else ""
            body += f'<button type="button" class="drawer-scrim" data-route="admin-users" aria-label="Đóng chi tiết tài khoản"></button><aside class="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="user-detail-title"><div class="drawer-heading"><div><small>Chi tiết tài khoản</small><h2 id="user-detail-title">{esc(user.get("full_name") or user["email"])}</h2></div>{btn("Đóng", "admin-users")}</div><div class="person-profile"><span class="avatar large pale">{esc((user.get("full_name") or "U")[:1])}</span><strong>{esc(user.get("full_name"))}</strong><span>{esc(user["email"])}</span>{status(user["status"])}</div><section class="drawer-section">{management}</section><section class="drawer-section"><h3>Hỗ trợ tài khoản</h3>{recovery_button}<p class="privacy-note">Không xem mật khẩu hoặc lịch sử chat của người dùng.</p></section></aside>'
    return body


def documents_page(data):
    docs = data.get("legal_documents", [])
    filters = (
        '<div class="table-toolbar"><label class="search-box">'
        + icon("search")
        + '<input data-search placeholder="Tìm tên hoặc số hiệu văn bản" aria-label="Tìm văn bản"></label><select data-filter-column="status" aria-label="Lọc văn bản"><option value="">Tất cả trạng thái</option>'
        + "".join(
            f'<option value="{s}">{t}</option>'
            for s, t in [
                ("draft", "Bản nháp"),
                ("review", "Chờ duyệt"),
                ("approved", "Đã duyệt"),
                ("indexed", "Đã lập chỉ mục"),
            ]
        )
        + "</select></div>"
    )
    rows = [
        [
            f'<div class="document-name">{icon("file-description")}<div><strong>{esc(d["title"])}</strong><small>{esc(d["document_no"])}</small></div></div>',
            esc(d["issuer"]),
            status(d["status"]),
            date(d["updated_at"]),
            btn("Kiểm tra", "admin-document-add", id=d["id"], kind="table-action"),
        ]
        for d in docs
    ]
    return (
        '<div class="compact-stats"><span><b>'
        + str(len(docs))
        + "</b> Văn bản quản trị</span><span><b>"
        + str(sum(d["status"] == "indexed" for d in docs))
        + "</b> Đã lập chỉ mục</span></div>"
        + notice(
            "Kho quản trị bổ sung cho bộ văn bản nền tảng hiện có. Duyệt tài liệu và kiểm tra chỉ mục trước khi đưa vào câu trả lời."
        )
        + panel(
            "Danh mục văn bản",
            "Nguồn, metadata và trạng thái xử lý.",
            filters
            + table(
                ["Văn bản", "Cơ quan", "Trạng thái", "Cập nhật", ""],
                rows,
                [f'data-status="{d["status"]}"' for d in docs],
            ),
        )
    )


def document_form(data, selected=""):
    doc = next((d for d in data.get("legal_documents", []) if d["id"] == selected), {})
    body = (
        hidden("id", doc.get("id", "")) + hidden("updated_at", doc.get("updated_at", ""))
        if doc
        else '<label class="sample-upload"><span>Chọn văn bản PDF · tối đa 10 MB</span><input name="document_file" type="file" accept="application/pdf,.pdf" required></label>'
    )
    body += (
        '<div class="form-grid">'
        + field("Tên văn bản", "title", doc.get("title", ""), extra='maxlength="300"')
        + field("Số hiệu", "document_no", doc.get("document_no", ""), required=False)
        + field("Cơ quan ban hành", "issuer", doc.get("issuer", ""))
        + field("Ngày có hiệu lực", "effective_from", doc.get("effective_from") or "", type="date", required=False)
        + field(
            "Đường dẫn nguồn chính thức",
            "source_url",
            doc.get("source_url", ""),
            type="url",
            placeholder="https://congbao.chinhphu.vn/...",
        )
        + select(
            "Hiệu lực đã kiểm tra",
            "validity",
            [
                (v, t)
                for v, t in [
                    ("unverified", "Chưa xác minh"),
                    ("CURRENT", "Còn hiệu lực"),
                    ("PARTIALLY_EFFECTIVE", "Hiệu lực một phần"),
                    ("REPEALED", "Hết hiệu lực"),
                    ("HISTORICAL", "Văn bản lịch sử"),
                ]
            ],
            doc.get("validity", "unverified"),
        )
        + textarea("Ghi chú rà soát", "review_note", doc.get("review_note", ""))
        + "</div>"
    )
    left = panel(
        "Thông tin văn bản",
        "Chỉ nhận bản PDF có lớp văn bản để kiểm tra.",
        f'<div class="portal-form-pad">{form("admin_document_save", body, "Lưu bản nháp / thay đổi")}</div>',
    )
    right = panel(
        "Kiểm tra trước khi duyệt",
        "Lưu thay đổi sẽ yêu cầu duyệt lại văn bản.",
        f'<div class="portal-form-pad">{notice("Kiểm tra nguồn, ngày hiệu lực, văn bản sửa đổi/thay thế và cấu trúc trích xuất.")}<pre class="extracted-preview">{esc(doc.get("preview_text") or "Sau khi lưu PDF, phần trích xuất sẽ hiển thị tại đây.")}</pre>'
        + (
            form(
                "admin_document_approve",
                hidden("id", doc["id"])
                + '<label class="check-label"><input type="checkbox" name="confirmed" required>Tôi đã kiểm tra nguồn, hiệu lực và nội dung văn bản.</label>',
                "Duyệt & lập chỉ mục",
                "Xác nhận duyệt văn bản và tạo tiến trình lập chỉ mục?",
            )
            if doc and doc.get("status") in {"draft", "review"}
            else notice(
                "Văn bản đã được duyệt. Mở mục Vận hành AI để theo dõi hoặc chạy lại lập chỉ mục."
                if doc and doc.get("status") == "approved"
                else "Văn bản đã được lập chỉ mục. Muốn sửa, hãy lưu thay đổi để yêu cầu duyệt lại."
            ) if doc else ""
        )
        + "</div>",
    )
    return '<div class="document-form-grid">' + left + right + "</div>"


def feedback_page(data, selected=""):
    rows = data.get("feedback", [])
    selected = selected or (rows[0]["id"] if rows else "")
    item = next((r for r in rows if r["id"] == selected), None)
    listing = "".join(
        f'<button class="feedback-item {"selected" if r["id"] == selected else ""}" data-route="admin-feedback" data-id="{r["id"]}" data-status="{esc(r["status"])}" data-consent="{str(bool(r["share_consent"])).lower()}"><div><span>#{r["id"][:8]}</span>{status(r["status"])}</div><strong>{esc(r["comment"][:100] or ("Đánh giá tích cực" if r["rating"] == "up" else "Cần xem xét câu trả lời"))}</strong><small>{date(r["created_at"])}</small></button>'
        for r in rows
    )
    if item:
        detail = "<h2>Phản hồi #" + esc(item["id"][:8]) + '</h2><p class="muted">' + date(item["created_at"]) + "</p>"
        if item["share_consent"]:
            detail += f'<div class="reported-question"><small>Câu hỏi được chia sẻ</small><p>{esc(item["question"])}</p></div><div class="reported-answer"><small>Câu trả lời được chia sẻ</small><p>{esc(item["answer"])}</p></div>'
        else:
            detail += notice("Người dùng không chia sẻ nội dung chat. Chỉ có đánh giá và góp ý bên dưới.")
        detail += (
            '<div class="user-comment"><strong>Góp ý</strong><p>'
            + esc(item["comment"] or "Không có ghi chú.")
            + "</p></div>"
            + form(
                "admin_feedback_save",
                hidden("id", item["id"])
                + hidden("privacy_version", item.get("privacy_version", 0))
                + select(
                    "Trạng thái",
                    "status",
                    [("pending", "Chờ xử lý"), ("reviewing", "Đang xem xét"), ("resolved", "Đã xử lý")],
                    item["status"],
                )
                + textarea("Ghi chú quản trị", "admin_note", item["admin_note"]),
            )
        )
        detail += (
            btn("Xuất ca đánh giá", action="admin_feedback_export", id=item["id"]) if item["share_consent"] else ""
        )
    else:
        detail = '<div class="empty-state">Chưa có phản hồi để xử lý.</div>'
    return (
        notice("Chỉ hiển thị đoạn trao đổi người dùng chủ động gửi kèm. Không truy cập toàn bộ lịch sử cá nhân.")
        + '<div class="feedback-workspace"><section class="feedback-list"><div class="feedback-list-title"><h2>Phản hồi người dùng</h2>'
        + badge(len(rows))
        + "</div>"
        + '<div class="feedback-toolbar"><label class="search-box">'
        + icon("search")
        + '<input data-search placeholder="Tìm nội dung phản hồi" aria-label="Tìm phản hồi"></label>'
        + '<div class="feedback-filters"><select data-feedback-status aria-label="Lọc trạng thái phản hồi"><option value="">Tất cả trạng thái</option><option value="pending">Chờ xử lý</option><option value="reviewing">Đang xem xét</option><option value="resolved">Đã xử lý</option></select><select data-feedback-consent aria-label="Lọc quyền chia sẻ"><option value="">Mọi phản hồi</option><option value="true">Có chia sẻ nội dung</option><option value="false">Chỉ đánh giá, góp ý</option></select></div>'
        + '<nav class="feedback-pagination" aria-label="Phân trang phản hồi"><span data-feedback-count aria-live="polite"></span><div class="page-controls"><button type="button" data-feedback-page="prev" aria-label="Phản hồi trước">‹</button><span data-feedback-page-label></span><button type="button" data-feedback-page="next" aria-label="Phản hồi sau">›</button><label class="page-size-label">Mỗi trang <select data-feedback-size aria-label="Số phản hồi mỗi trang"><option value="10">10</option><option value="25">25</option><option value="50">50</option></select></label></div></nav></div>'
        + listing
        + '</section><section class="panel feedback-detail"><div data-feedback-detail-body>'
        + detail
        + '</div><div class="empty-state" data-feedback-detail-empty hidden>Phản hồi đang mở nằm ngoài bộ lọc. Chọn một phản hồi trong danh sách hoặc đổi bộ lọc để tiếp tục.</div></section></div>'
    )


def jobs_table(jobs):
    names = {
        "index": "Cập nhật chỉ mục",
        "health": "Kiểm tra dịch vụ",
        "backup": "Sao lưu nghiệp vụ",
        "restore": "Khôi phục metadata",
    }
    return table(
        ["Tiến trình", "Bắt đầu", "Trạng thái", "Kết quả", ""],
        [
            [
                esc(names.get(j["kind"], j["kind"])),
                date(j["created_at"]),
                status(j["status"]),
                f'<span class="job-result">{esc(job_result(j))}</span>',
                btn("Chạy lại", action="admin_job_retry", id=j["id"]) if j["status"] == "failed" else "—",
            ]
            for j in jobs
        ],
    )


def job_result(job):
    result = str(job.get("result") or "")
    if job.get("kind") == "health" and result:
        try:
            checked = json.loads(result)
            return {"ready": "Mô hình sẵn sàng", "offline": "Chưa kết nối dịch vụ AI", "missing_model": "Chưa tìm thấy mô hình"}.get(checked.get("ollama"), "Đã kiểm tra dịch vụ")
        except (ValueError, AttributeError):
            pass
    return result or {"pending": "Đang chờ xử lý", "running": "Đang thực hiện"}.get(job.get("status"), "Chưa có kết quả")


def operations_page(data):
    from app.admin_jobs import active_index
    from config.settings import OLLAMA_MODEL, OLLAMA_NUM_CTX, OLLAMA_NUM_PREDICT

    stats = data.get("stats", {})
    jobs = data.get("admin_jobs", [])
    health = next((j for j in jobs if j["kind"] == "health" and j["status"] == "succeeded"), None)
    try:
        checked = json.loads(health["result"]) if health else {}
        if not isinstance(checked, dict):
            checked = {}
    except (ValueError, TypeError):
        checked = {}
    modelstate = {"ready": "Sẵn sàng", "missing_model": "Chưa cài mô hình", "offline": "Chưa kết nối"}.get(
        str(checked.get("ollama") or ""), "Chưa kiểm tra"
    )
    cards = panel(
        "Mô hình AI",
        modelstate,
        f'<div class="portal-form-pad"><h3>{esc(OLLAMA_MODEL)}</h3><p class="muted">Context {OLLAMA_NUM_CTX} · Tối đa {OLLAMA_NUM_PREDICT} token</p></div>',
    ) + panel(
        "Kho tri thức",
        "ChromaDB · BM25 · Neo4j",
        f'<div class="portal-form-pad"><strong>{esc((active_index() or {}).get("version", "Bộ chỉ mục v3"))}</strong><p class="muted">Chỉ chuyển phiên bản sau khi xây dựng hoàn tất.</p></div>',
    )

    def ms(key):
        return f"{stats[key] / 1000:.1f} s" if stats.get(key) is not None else "Chưa có số đo"

    cards += panel(
        "Hiệu năng thực tế",
        "7 ngày · tài khoản đăng nhập",
        f'<div class="performance"><span><small>Trung vị</small><strong>{ms("median_ms")}</strong></span><span><small>P95</small><strong>{ms("p95_ms")}</strong></span></div>',
    )
    return (
        '<div class="health-grid">'
        + cards
        + "</div>"
        + panel("Các tác vụ vận hành", "Tiến trình chạy nền; bấm tải lại để cập nhật trạng thái.", jobs_table(jobs))
    )


def audit_page(data, backups):
    audits = data.get("admin_audit", [])
    rows = [
        [date(a["created_at"]), short_id(a.get("actor_id")), esc(audit_label(a["action"])), short_id(a.get("target_id")),
         f'<button class="btn table-action" data-open-dialog="audit-detail-{i}">Chi tiết</button>']
        for i, a in enumerate(audits)
    ]
    options = ''.join(f'<option value="{esc(action)}">{esc(audit_label(action))}</option>' for action in sorted({a["action"] for a in audits}))
    toolbar = f'<div class="table-toolbar audit-toolbar"><label class="search-box">{icon("search")}<input data-search maxlength="200" aria-label="Tìm nhật ký" placeholder="Tìm thao tác hoặc mã đối tượng"></label><select data-filter-column="action" aria-label="Lọc thao tác"><option value="">Tất cả thao tác</option>{options}</select><label class="date-filter">Từ ngày<input type="date" data-date-from aria-label="Nhật ký từ ngày"></label><label class="date-filter">Đến ngày<input type="date" data-date-to aria-label="Nhật ký đến ngày"></label><button class="btn text" data-reset-filters>Xóa bộ lọc</button></div><p class="audit-filter-error" role="alert" hidden>Ngày kết thúc phải từ ngày bắt đầu trở đi.</p>'
    attrs = [f'data-action="{esc(a["action"])}" data-day="{audit_day(a.get("created_at"))}" data-search-text="{esc(audit_search_text(a))}"' for a in audits]
    dialogs = ""
    for i, a in enumerate(audits):
        values = [("Thời gian", date(a["created_at"])), ("Mã sự kiện", a.get("id", "")),
                  ("Người thực hiện", a.get("actor_id") or "Hệ thống"), ("Mã thao tác", a["action"]),
                  ("Đối tượng", a.get("target_id") or "Hệ thống"), *audit_details(a)]
        details = ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in values)
        dialogs += f'<dialog class="portal-dialog audit-detail" id="audit-detail-{i}" aria-labelledby="audit-title-{i}"><header><div><h2 id="audit-title-{i}">{esc(audit_label(a["action"]))}</h2><p>Chi tiết sự kiện quản trị · giờ Việt Nam</p></div><button data-close-dialog aria-label="Đóng chi tiết nhật ký">{icon("x")}</button></header><dl class="audit-properties">{details}</dl><p class="muted">Chỉ hiển thị metadata và lý do quản trị được ghi nhận.</p></dialog>'
    body = panel(
        "Nhật ký hoạt động",
        "Lọc theo giờ Việt Nam. CSV xuất đúng các sự kiện khớp bộ lọc.",
        toolbar + table(["Thời gian", "Người thực hiện", "Thao tác", "Đối tượng", ""], rows, attrs) + dialogs,
        btn("Xuất CSV", action="admin_audit_export"),
        cls="audit-log-panel",
    )
    backupbody = notice(
        "Sao lưu tại đây gồm cấu hình và metadata kho văn bản, không chứa tài khoản hoặc lịch sử chat. PDF gốc được lưu riêng trong Supabase Storage."
    ) + btn("Tạo bản sao lưu", action="admin_backup", kind="primary")
    if backups:
        options = [
            (
                b["id"],
                datetime.fromtimestamp(b["created_at"]).strftime("%d/%m/%Y %H:%M")
                + " · "
                + str(round(b["size"] / 1024))
                + " KB",
            )
            for b in backups
        ]
        backupbody += form(
            "admin_restore",
            select("Chọn bản sao lưu", "backup_id", options)
            + '<label class="check-label"><input type="checkbox" name="confirmed" required>Tôi đã kiểm tra bản sao lưu và đồng ý khôi phục metadata.</label>',
            "Khôi phục metadata",
            "Thao tác sẽ khôi phục cấu hình và đưa văn bản về chờ duyệt. Tiếp tục?",
        )
    else:
        backupbody += '<p class="muted">Chưa có bản sao lưu nghiệp vụ trên máy chủ này.</p>'
    return (
        body
        + panel(
            "Sao lưu & khôi phục",
            "Khôi phục không thay thế tài khoản, lịch sử chat hoặc chỉ mục đang phục vụ.",
            f'<div class="portal-form-pad">{backupbody}</div>',
        )
        + panel(
            "Tiến trình sao lưu",
            "Kết quả và trạng thái thực tế.",
            jobs_table([j for j in data.get("admin_jobs", []) if j["kind"] in {"backup", "restore"}]),
        )
    )


def settings_page(data):
    row = (data.get("app_settings") or [{}])[0]
    dashboard_url = data.get("supabase_dashboard", "")
    template_link = f'<a class="btn" href="{esc(dashboard_url)}/auth/templates" target="_blank" rel="noopener noreferrer">Mở cài đặt email{icon("external-link")}</a>' if dashboard_url else badge("Supabase quản lý")
    smtp_link = f'<a class="btn" href="{esc(dashboard_url)}/auth/smtp" target="_blank" rel="noopener noreferrer">Cấu hình SMTP{icon("external-link")}</a>' if dashboard_url else badge("Cấu hình bên ngoài")
    auth = (
        '<div class="portal-form-pad"><div class="integration-title"><strong>Supabase Auth</strong>'
        + badge("Nhà cung cấp xác thực")
        + '</div><div class="setting-row"><div><strong>Xác minh email & khôi phục mật khẩu</strong><p>Thiết lập tại Supabase → Authentication.</p></div>'
        + template_link
        + '</div><div class="setting-row"><div><strong>Email SMTP</strong><p>Cấu hình và kiểm tra tại Supabase → SMTP Settings.</p></div>'
        + smtp_link
        + "</div>"
        + notice("Không hiển thị khóa máy chủ hoặc mật khẩu SMTP trong giao diện.")
        + "</div>"
    )
    roles = table(
        ["Chức năng", "Người dùng", "Admin nghiệp vụ", "Quản trị chính"],
        [
            ["Lịch sử chat của chính mình", "Có", "Có", "Có"],
            ["Lịch sử chat của người khác", "Không", "Không", "Không"],
            ["Gửi / thu hồi phản hồi của mình", "Có", "Có", "Có"],
            ["Quản lý trạng thái người dùng / văn bản", "Không", "Có", "Có"],
            ["Cấp quyền / quản lý tài khoản admin", "Không", "Không", "Có"],
            ["Đọc đoạn phản hồi còn được chia sẻ", "Không", "Có", "Có"],
            ["Xem mật khẩu hoặc chủ sở hữu phản hồi", "Không", "Không", "Không"],
        ],
    )
    body = (
        '<div class="settings-grid">'
        + panel("Xác thực & email", "Thiết lập do nhà cung cấp xác thực quản lý.", auth)
        + panel("Phân quyền", "Không có đăng ký admin công khai.", roles)
        + "</div>"
    )
    body += panel(
        "Thông tin ứng dụng",
        "Cấu hình tên hiển thị của khu quản trị.",
        f'<div class="portal-form-pad">{form("admin_settings_save", field("Tên ứng dụng", "app_name", row.get("app_name", "VietLaborAI")) + field("Tên khu quản trị", "workspace_name", row.get("workspace_name", "Quản trị VietLaborAI")), "Lưu cấu hình")}</div>',
    )
    return body


def privacy_page(data):
    export = panel("Lịch sử của bạn", "Chỉ xuất và xóa lịch sử thuộc tài khoản đang đăng nhập.",
        '<div class="portal-form-pad">' + btn("Tải lịch sử của tôi", action="account_export_history")
        + '<p class="muted">Tệp tải về có thể chứa thông tin riêng tư bạn đã nhập. Hãy lưu ở nơi an toàn.</p></div>')
    if not data.get("privacy_configured"):
        return export + notice("Chức năng thu hồi và xóa dữ liệu chưa sẵn sàng. Vui lòng thử lại sau.")
    rows = []
    for row in data.get("my_feedback", []):
        controls = (btn("Thu hồi chia sẻ", action="account_feedback_withdraw", id=row["id"], confirm="Xóa đoạn chat đã chia sẻ và ghi chú xử lý trong phản hồi này?") if row.get("share_consent") else badge("Không chia sẻ chat"))
        controls += btn("Xóa phản hồi", action="account_feedback_delete", id=row["id"], kind="danger-ghost", confirm="Xóa phản hồi này khỏi hệ thống? Không thể hoàn tác.")
        rows.append([date(row["created_at"]), esc(row.get("comment") or "Đánh giá câu trả lời"), status(row["status"]), controls])
    shared = panel("Phản hồi bạn đã gửi", "Bạn kiểm soát việc chia sẻ nội dung chat với admin.",
        table(["Thời gian", "Góp ý", "Trạng thái", "Quyền của bạn"], rows)
        + '<p class="muted">Thu hồi xóa đoạn chat và ghi chú xử lý trên hệ thống. Tệp đã được tải về trước đó không thể thu hồi tự động.</p>')
    erase = panel("Xóa toàn bộ lịch sử", "Thao tác chỉ áp dụng cho tài khoản của bạn và không thể hoàn tác.",
        '<div class="portal-form-pad">' + form("account_delete_history",
        '<label class="check-label"><input type="checkbox" name="confirmed" required>Tôi muốn xóa toàn bộ lịch sử trò chuyện của mình.</label>',
        "Xóa lịch sử của tôi", "Xóa toàn bộ lịch sử trò chuyện của bạn? Không thể hoàn tác.") + '</div>')
    return export + shared + erase


def account_page(profile, view, message="", error="", recovery=False, data=None):
    name = profile.get("full_name") or profile.get("email", "")
    if view == "account-privacy":
        content = privacy_page(data or {})
    elif view in {"account-password-success", "account-reset-success"}:
        content = (
            '<div class="account-success">'
            + icon("thumb-up")
            + "<h1>Mật khẩu đã được cập nhật</h1><p>Hãy đăng nhập lại bằng mật khẩu mới.</p>"
            + btn("Quay lại trợ lý AI", "home")
            + "</div>"
        )
    elif view in {"account-password", "account-recovery"}:
        current = (
            ""
            if recovery
            else field(
                "Mật khẩu hiện tại",
                "current_password",
                type="password",
                extra='autocomplete="current-password" maxlength="256"',
            )
        )
        inputs = (
            current
            + field(
                "Mật khẩu mới",
                "password",
                type="password",
                extra='minlength="8" maxlength="256" autocomplete="new-password"',
            )
            + field(
                "Xác nhận mật khẩu mới",
                "confirm_password",
                type="password",
                extra='minlength="8" maxlength="256" autocomplete="new-password"',
            )
        )
        help = "" if recovery else btn("Quên mật khẩu hiện tại?", action="account_send_recovery", kind="text")
        content = panel(
            "Đặt mật khẩu mới" if recovery else "Đổi mật khẩu",
            "Mật khẩu dài từ 8–256 ký tự.",
            f'<div class="portal-form-pad">{form("account_reset_password" if recovery else "account_change_password", inputs, "Lưu mật khẩu mới")}{help}</div>',
        )
    else:
        person = f'<div class="profile-person"><span class="avatar extra rose">{esc("".join(w[0] for w in name.split()[-2:]).upper())}</span><div><h2>{esc(name)}</h2><p>{esc(profile.get("email"))}</p>{badge("Email đã xác minh", "success")}</div></div>'
        content = panel(
            "Hồ sơ cá nhân",
            "Quản lý tên hiển thị và thông tin tài khoản.",
            person
            + '<div class="portal-form-pad">'
            + form("account_update_profile", field("Họ và tên", "full_name", profile.get("full_name", "")), "Lưu hồ sơ")
            + "</div>",
        )
        content += panel(
            "Bảo mật tài khoản",
            "Mật khẩu được xử lý bởi Supabase Auth.",
            '<div class="setting-row"><div><strong>Mật khẩu</strong><p>Cập nhật mật khẩu của tài khoản.</p></div>'
            + btn("Đổi mật khẩu", "account-password")
            + '</div><div class="setting-row"><div><strong>Phiên đăng nhập khác</strong><p>Thu hồi quyền làm mới phiên trên thiết bị khác.</p></div>'
            + btn("Đăng xuất phiên khác", action="account_logout_others", confirm="Thu hồi các phiên đăng nhập khác?")
            + '</div><div class="setting-row"><div><strong>Quyền riêng tư</strong><p>Chỉ bạn có quyền đọc lịch sử chat của mình.</p></div>'
            + btn("Quản lý dữ liệu của tôi", "account-privacy")
            + "</div>",
        )
    back = "admin-dashboard" if profile.get("role") == "admin" else "home"
    if view == "account-privacy":
        back = "account-profile"
    heading = '<div class="page-heading"><div><h1>Tài khoản của bạn</h1><p>Thông tin cá nhân, bảo mật và quyền riêng tư.</p></div></div>' if view == "account-profile" else ""
    return f'<div class="profile-page" data-account-view="{esc(view)}"><header class="profile-header">{brand()}{btn("Quay lại", back)}</header><main class="profile-main">{heading}{notice(error, True)}{notice(message, success=True)}{content}<div class="profile-footer"><p>Không chia sẻ mật khẩu hoặc liên kết khôi phục với người khác.</p>{btn("Đăng xuất", action="logout") if profile else ""}</div></main></div>'


def portal_markup(view, profile=None, data=None, selected="", message="", error="", backups=None, link_type=""):
    profile = profile or {}
    data = data or {}
    if view in {"account-link-confirm", "account-link-error"}:
        if link_type == "recovery":
            title = "Xác nhận đặt lại mật khẩu"
            description = "Bấm tiếp tục để xác minh liên kết. Sau bước này, màn hình nhập mật khẩu mới sẽ mở ra."
            action_label = "Tiếp tục đặt mật khẩu"
        elif link_type == "invite":
            title = "Hoàn tất lời mời VietLaborAI"
            description = "Bấm tiếp tục để xác minh lời mời và tạo mật khẩu cho tài khoản."
            action_label = "Xác minh và tạo mật khẩu"
        else:
            title = "Xác minh email VietLaborAI"
            description = "Bấm tiếp tục để xác minh địa chỉ email và hoàn tất đăng ký."
            action_label = "Xác minh email"
        if view == "account-link-error":
            title = "Liên kết không còn hiệu lực"
            description = "Liên kết có thể đã hết hạn hoặc đã được sử dụng. Hãy quay lại ứng dụng và gửi yêu cầu email mới."
            buttons = btn("Về trợ lý AI", "home", kind="primary")
        else:
            buttons = btn(action_label, action="account_verify_link", kind="primary")
        return (
            '<div class="profile-page"><header class="profile-header">' + brand() + '</header>'
            '<main class="profile-main"><section class="panel">'
            + '<div class="panel-head"><div><h2>' + esc(title) + '</h2><p>' + esc(description) + '</p></div></div>'
            + notice(error, True)
            + '<div class="portal-form-pad">' + buttons + '</div>'
            + '</section><p class="muted">VietLaborAI chỉ xác minh liên kết sau khi bạn bấm nút này.</p></main></div>'
        )
    if view == "setup":
        return (
            '<div class="profile-page"><header class="profile-header">'
            + brand()
            + btn("Về trợ lý AI", "home")
            + '</header><main class="profile-main"><h1>Kết nối Supabase</h1>'
            + notice("Chưa cấu hình Supabase. Chế độ khách vẫn hoạt động.")
            + panel(
                "Thiết lập một lần",
                "Hướng dẫn đầy đủ tại docs/SUPABASE_SETUP.md.",
                '<ol class="setup-steps"><li>Tạo project Supabase và chạy lần lượt các SQL migration trong thư mục supabase/migrations.</li><li>Điền URL và publishable key vào .streamlit/secrets.toml.</li><li>Cấu hình email, đường dẫn xác thực và tài khoản admin đầu tiên.</li><li>Khởi động lại ứng dụng.</li></ol>',
            )
            + "</main></div>"
        )
    if view == "access-denied" or (view.startswith("admin-") and profile.get("role") != "admin"):
        return (
            '<div class="denied-page"><header class="profile-header">'
            + brand()
            + '</header><main><span class="error-code">403</span><h1>Bạn không có quyền truy cập</h1><p>Khu vực này chỉ dành cho quản trị viên.</p>'
            + btn("Về trợ lý AI", "home", kind="primary")
            + "</main></div>"
        )
    if view.startswith("account-"):
        return account_page(profile, view, message, error, view == "account-recovery", data=data)
    builders = {
        "admin-dashboard": lambda: dashboard(data),
        "admin-users": lambda: users_page(data),
        "admin-user-detail": lambda: users_page(data, selected),
        "admin-documents": lambda: documents_page(data),
        "admin-document-add": lambda: document_form(data, selected),
        "admin-feedback": lambda: feedback_page(data, selected),
        "admin-operations": lambda: operations_page(data),
        "admin-audit": lambda: audit_page(data, backups or []),
        "admin-settings": lambda: settings_page(data),
    }
    title = next(
        (label for key, label, _ in ADMIN_NAV if key == view),
        {"admin-user-detail": "Chi tiết tài khoản", "admin-document-add": "Kiểm tra văn bản"}.get(view, "Quản trị"),
    )
    actions = (
        btn("Thêm văn bản", "admin-document-add", kind="primary")
        if view == "admin-documents"
        else btn("Kiểm tra dịch vụ", action="admin_health", kind="primary")
        if view == "admin-operations"
        else ""
    )
    if view in {"admin-users", "admin-user-detail"}:
        actions = f'<button type="button" class="btn primary" data-open-dialog="invite-admin">{icon("plus")}Mời quản trị viên</button>' if (data.get("permissions") or {}).get("manage_admins") is True else ""
    elif view == "admin-dashboard":
        actions = f'<button class="btn primary" data-route="admin-users">{icon("plus")}Quản lý người dùng</button>'
    if view == "admin-document-add":
        actions = btn("Về kho văn bản", "admin-documents")
    settings = (data.get("app_settings") or [{}])[0]
    return admin_shell(
        view,
        profile,
        title,
        "Theo dõi hoạt động và chất lượng trợ lý của bạn." if view == "admin-dashboard" else "Không gian quản trị " + settings.get("app_name", "VietLaborAI"),
        builders.get(view, lambda: "")(),
        f'<button class="btn icon-button" data-action="portal_refresh" aria-label="Tải lại" title="Tải lại">{icon("refresh")}</button>' + actions,
        message,
        error,
        settings.get("workspace_name", "Không gian quản trị"),
        pending_feedback=(data.get("stats") or {}).get("pending_feedback", 0),
    )


@lru_cache(maxsize=1)
def get_portal_surface():
    css = (
        ((FRONTEND / "portal.css").read_text(encoding="utf-8")
         + "\n" + (FRONTEND / "admin.css").read_text(encoding="utf-8"))
        .replace(":root", ":host")
        .replace("'/ui/static/approved-homepage.png'", "'/app/static/approved-homepage.png'")
    )
    return component(
        "vietlabor_account_admin_v5_4",
        html='<div class="portal-mount"></div>',
        css=css,
        js=(FRONTEND / "portal.js").read_text(encoding="utf-8"),
        isolate_styles=True,
    )


def build_client_views(view, profile=None, data=None, backups=None):
    if not profile or not isinstance(profile, dict) or not profile.get("id"):
        return {}
    if view in {
        "account-link-confirm",
        "account-link-error",
        "account-recovery",
        "account-password-success",
        "account-reset-success",
        "setup",
        "access-denied",
    }:
        return {}
    data = data or {}
    backups = backups or []
    views = {}
    for acct_view in ("account-profile", "account-privacy", "account-password"):
        views[acct_view] = portal_markup(view=acct_view, profile=profile, data=data, backups=backups)
    if profile.get("role") == "admin":
        for adm_view in (
            "admin-dashboard",
            "admin-users",
            "admin-documents",
            "admin-document-add",
            "admin-feedback",
            "admin-operations",
            "admin-audit",
            "admin-settings",
        ):
            views[adm_view] = portal_markup(view=adm_view, profile=profile, data=data, backups=backups)
        for u in (data.get("profiles") or [])[:100]:
            uid = u.get("id")
            if uid:
                views[f"admin-user-detail:{uid}"] = portal_markup(
                    view="admin-user-detail", profile=profile, data=data, selected=uid, backups=backups
                )
        for d in (data.get("legal_documents") or [])[:100]:
            did = d.get("id")
            if did:
                views[f"admin-document-add:{did}"] = portal_markup(
                    view="admin-document-add", profile=profile, data=data, selected=did, backups=backups
                )
        for r in (data.get("feedback") or [])[:100]:
            fid = r.get("id")
            if fid:
                views[f"admin-feedback:{fid}"] = portal_markup(
                    view="admin-feedback", profile=profile, data=data, selected=fid, backups=backups
                )
    return views


def render_portal(on_action_change=None, **kwargs):
    download = kwargs.pop("download", None)
    poll_after = kwargs.pop("poll_after", 0)
    form_draft = kwargs.pop("form_draft", None)
    views = build_client_views(
        kwargs.get("view", ""),
        profile=kwargs.get("profile"),
        data=kwargs.get("data"),
        backups=kwargs.get("backups"),
    )
    return get_portal_surface()(
        data={
            "markup": portal_markup(**kwargs),
            "views": views,
            "selected": str(kwargs.get("selected") or ""),
            "download": download,
            "revision": uuid.uuid4().hex,
            "poll_after": poll_after,
            "form_draft": form_draft,
        },
        key="account-admin-portal",
        on_action_change=on_action_change or (lambda: None),
    )


def auth_dialog_markup():
    return f"""<dialog class="auth-dialog" data-mode="login" aria-labelledby="auth-title">
      <button type="button" class="auth-close" data-auth-close aria-label="Đóng đăng nhập">{icon("x")}</button>
      <div class="auth-brand">{sprite(56, 8, 86, 61, "auth-symbol", "VietLaborAI")}<span>VietLabor<span>AI</span></span></div>
      <div class="auth-heading"><h2 id="auth-title">Chào mừng trở lại</h2><p class="auth-description">Đăng nhập để lưu và tiếp tục cuộc trò chuyện.</p></div>
      <form class="auth-form" aria-label="Đăng nhập hoặc tạo tài khoản">
        <div class="auth-register-only auth-name"><label for="vl-auth-name">Họ và tên</label><input id="vl-auth-name" name="full_name" maxlength="100" autocomplete="name" placeholder="Nhập họ và tên"></div>
        <div class="auth-email-fields"><label for="vl-auth-username">Email</label><input id="vl-auth-username" name="username" type="email" autocomplete="email" required maxlength="254" placeholder="ban@example.com"></div>
        <div class="auth-password-fields"><label for="vl-auth-password">Mật khẩu</label><div class="auth-password-field"><input id="vl-auth-password" name="password" type="password" autocomplete="current-password" required maxlength="256" placeholder="Nhập mật khẩu"><button type="button" data-auth-password aria-label="Hiện mật khẩu">Hiện</button></div></div>
        <div class="auth-register-only auth-confirm"><label for="vl-auth-confirm">Nhập lại mật khẩu</label><input id="vl-auth-confirm" name="confirm_password" type="password" autocomplete="new-password" maxlength="256" placeholder="Nhập lại mật khẩu"><small>Ít nhất 8 ký tự. Xác minh email trước khi đăng nhập.</small></div>
        <button type="button" class="auth-forgot auth-login-only" data-auth-mode="forgot">Quên mật khẩu?</button>
        <p class="auth-error" role="alert" hidden></p>
        <div class="auth-sent-only"><div class="auth-mail-mark">{icon("file-text")}</div><p>Nếu email khớp với tài khoản, liên kết khôi phục sẽ được gửi tới hộp thư. Hãy kiểm tra cả thư mục spam.</p></div>
        <button class="auth-submit" type="submit"><span>Đăng nhập</span>{icon("chevron-right")}</button>
      </form>
      <p class="auth-switch auth-login-only">Chưa có tài khoản? <button type="button" data-auth-mode="register">Tạo tài khoản</button></p>
      <p class="auth-switch auth-register-only">Đã có tài khoản? <button type="button" data-auth-mode="login">Đăng nhập</button></p>
      <p class="auth-switch auth-forgot-only"><button type="button" data-auth-mode="login">Quay lại đăng nhập</button></p>
      <p class="auth-switch auth-sent-only"><button type="button" data-auth-mode="forgot">Nhập email khác</button></p>
      <div class="auth-divider"><span>hoặc</span></div><button type="button" class="auth-guest" data-auth-close>Tiếp tục với tư cách khách</button>
      <p class="auth-privacy">Lịch sử riêng cho từng tài khoản. Không có đăng ký admin công khai.</p>
    </dialog>"""
