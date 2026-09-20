# -*- coding: utf-8 -*-
"""
VietLabor AI - Left Sidebar Component (Phase 6)
Matches the approved mockup with Brand Logo, New Chat button, Chat History, and Search Topics.
"""
from __future__ import annotations

import streamlit as st
from typing import Any, Callable, Dict, List, Optional

from ui.utils.branding import get_logo_base64
from ui.utils.session import SessionManager

SEARCH_TOPICS = [
    ("Hợp đồng lao động", ":material/description:", [
        "Có mấy loại hợp đồng lao động theo BLLĐ 2019?",
        "Hợp đồng thử việc dưới 1 tháng có được áp dụng không?",
        "Hết hạn hợp đồng mà tiếp tục làm việc thì xử lý thế nào?",
    ]),
    ("Thử việc", ":material/badge:", [
        "Công ty bắt tôi thử việc 3 tháng có đúng không?",
        "Lương trong thời gian thử việc tối thiểu là bao nhiêu?",
        "Thời gian thử việc tối đa đối với trình độ đại học?",
    ]),
    ("Tiền lương", ":material/payments:", [
        "Làm việc vào ban đêm được trả thêm bao nhiêu % lương?",
        "Công ty chậm trả lương bao lâu thì phải đền bù?",
        "Mức khấu trừ tiền lương tối đa là bao nhiêu %?",
    ]),
    ("Thời giờ làm việc", ":material/schedule:", [
        "Thời giờ làm việc bình thường tối đa bao nhiêu giờ trong một tuần?",
        "Ca làm việc ban đêm được tính từ mấy giờ đến mấy giờ?",
    ]),
    ("Làm thêm giờ", ":material/more_time:", [
        "Số giờ làm thêm tối đa trong một ngày là bao nhiêu?",
        "Làm thêm ngày nghỉ lễ được trả bao nhiêu % tiền lương?",
        "Công ty có được ép nhân viên làm thêm giờ không?",
    ]),
    ("Nghỉ phép", ":material/event_available:", [
        "Người lao động làm việc 1 năm được bao nhiêu ngày phép?",
        "Thôi việc mà chưa nghỉ hết phép năm có được thanh toán tiền không?",
        "Nghỉ kết hôn được nghỉ mấy ngày nguyên lương?",
    ]),
    ("Nghỉ việc & chấm dứt HĐLĐ", ":material/logout:", [
        "Tôi ký hợp đồng 2 năm, muốn nghỉ việc phải báo trước bao lâu?",
        "Hợp đồng dưới 12 tháng nghỉ việc báo trước mấy ngày?",
        "Sau khi nghỉ việc bao nhiêu ngày thì công ty phải thanh toán tiền?",
    ]),
    ("Kỷ luật lao động", ":material/gavel:", [
        "Có bao nhiêu hình thức xử lý kỷ luật lao động?",
        "Tự ý bỏ việc bao nhiêu ngày thì công ty được sa thải?",
        "Công ty có được phạt tiền thay cho xử lý kỷ luật không?",
    ]),
]


def render_sidebar(
    session_mgr: SessionManager,
    active_conv_id: Optional[str],
    on_new_chat: Callable[[], None],
    on_switch_conv: Callable[[str], None],
    on_topic_select: Optional[Callable[[str], None]] = None,
) -> None:
    """Renders the left navigation sidebar matching the mockup."""
    with st.sidebar:
        # 1. Brand Logo Header
        logo_b64 = get_logo_base64()
        if logo_b64:
            logo_markup = f'<img src="data:image/png;base64,{logo_b64}" class="brand-logo-img" alt="VietLabor AI Logo" />'
        else:
            logo_markup = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>
                    <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>
                    <path d="M7 21h10"/>
                    <path d="M12 3v18"/>
                    <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>
                </svg>"""

        st.markdown(f"""
        <div class="brand-header">
            <div class="brand-logo-box">
                {logo_markup}
            </div>
            <div>
                <div class="brand-text-title">VietLabor AI</div>
                <div class="brand-text-subtitle">Trợ lý pháp luật lao động</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. "+ Cuộc trò chuyện mới" Primary Action Button
        st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
        if st.button("Cuộc trò chuyện mới", icon=":material/add:", key="btn_new_chat", use_container_width=True):
            on_new_chat()
        st.markdown('</div>', unsafe_allow_html=True)

        # 3. LỊCH SỬ TRÒ CHUYỆN (Real session history)
        st.markdown('<div class="sidebar-section-title">LỊCH SỬ TRÒ CHUYỆN</div>', unsafe_allow_html=True)
        conversations = session_mgr.load_conversations()

        if not conversations:
            st.markdown('<div style="font-size: 13px; color: #94A3B8; padding: 4px 8px;">Chưa có lịch sử trò chuyện</div>', unsafe_allow_html=True)
        else:
            for conv in conversations[:10]:
                cid = conv["id"]
                ctitle = conv.get("title") or "Cuộc trò chuyện"
                ctime = conv.get("display_time") or "Gần đây"
                is_active = (cid == active_conv_id)

                # Render active or inactive button
                btn_type = "primary" if is_active else "secondary"
                btn_label = ctitle
                if len(btn_label) > 28:
                    btn_label = btn_label[:26] + "..."

                col_item, col_del = st.columns([0.85, 0.15])
                with col_item:
                    if st.button(
                        btn_label,
                        icon=":material/chat_bubble_outline:",
                        key=f"conv_{cid}",
                        type=btn_type,
                        use_container_width=True,
                        help=f"{ctitle} ({ctime})",
                    ):
                        on_switch_conv(cid)
                with col_del:
                    if st.button("×", key=f"del_{cid}", help="Xóa cuộc trò chuyện"):
                        session_mgr.delete_conversation(cid)
                        st.rerun()

        # 4. CHỦ ĐỀ TRA CỨU (Search Topics with Suggested Questions)
        st.markdown('<div class="sidebar-section-title" style="margin-top: 26px;">CHỦ ĐỀ TRA CỨU</div>', unsafe_allow_html=True)

        for t_idx, (topic_name, icon_name, sample_questions) in enumerate(SEARCH_TOPICS):
            with st.expander(topic_name, icon=icon_name, expanded=False):
                for q_idx, sample_q in enumerate(sample_questions):
                    if st.button(sample_q, key=f"topic_{t_idx}_q_{q_idx}", use_container_width=True):
                        if on_topic_select:
                            on_topic_select(sample_q)
                        else:
                            st.session_state["submitted_query"] = sample_q
                            st.rerun()
