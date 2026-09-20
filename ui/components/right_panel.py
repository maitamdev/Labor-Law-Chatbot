# -*- coding: utf-8 -*-
"""
VietLabor AI - Right Information Panel Component (Phase 6)
Matches the approved mockup with Popular Topics, Main Legal Documents, and Disclaimer.
"""
from __future__ import annotations

import streamlit as st
from typing import Callable, Optional

POPULAR_TOPICS = [
    ("Thử việc", "Thời gian thử việc tối đa theo trình độ?", ":material/badge:"),
    ("Nghỉ việc", "Quy định về thời hạn báo trước khi nghỉ việc?", ":material/logout:"),
    ("Làm thêm giờ", "Số giờ làm thêm tối đa trong một ngày?", ":material/more_time:"),
    ("Tiền lương", "Làm việc vào ban đêm được trả lương thế nào?", ":material/payments:"),
    ("Nghỉ phép", "Số ngày nghỉ phép năm theo thâm niên và công việc?", ":material/event_available:"),
]

MAIN_DOCS = [
    ("Bộ luật Lao động 2019", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx"),
    ("Nghị định 145/2020/NĐ-CP", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-460987.aspx"),
    ("Nghị định 12/2022/NĐ-CP", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx"),
]


def render_right_panel(on_topic_click: Optional[Callable[[str], None]] = None) -> None:
    """Renders the clean, sparse right information panel."""
    st.markdown('<div class="sidebar-section-title">CHỦ ĐỀ PHỔ BIẾN</div>', unsafe_allow_html=True)

    for idx, (label, sample_q, icon) in enumerate(POPULAR_TOPICS):
        btn_col1, btn_col2 = st.columns([0.88, 0.12])
        if st.button(label, icon=icon, key=f"pop_topic_{idx}", use_container_width=True):
            if on_topic_click:
                on_topic_click(sample_q)
            else:
                st.session_state["submitted_query"] = sample_q
                st.rerun()

    st.markdown('<div class="sidebar-section-title" style="margin-top: 24px;">VĂN BẢN CHÍNH</div>', unsafe_allow_html=True)
    for idx, (title, url) in enumerate(MAIN_DOCS):
        st.markdown(f"""
        <a href="{url}" target="_blank" style="text-decoration: none;">
            <div class="right-card-item">
                <span style="display: flex; align-items: center; gap: 8px;">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span>{title}</span>
                </span>
                <span class="right-card-chevron">↗</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

    # Disclaimer Card
    st.markdown("""
    <div class="disclaimer-card">
        <div class="disclaimer-header">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle; margin-right:4px;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            LƯU Ý PHÁP LÝ
        </div>
        <div class="disclaimer-text">
            VietLabor AI hỗ trợ tra cứu thông tin pháp luật lao động từ các văn bản trong cơ sở dữ liệu. Nội dung cung cấp mang tính tham khảo và không thay thế ý kiến tư vấn chuyên môn cho tình huống pháp lý cụ thể.
        </div>
    </div>
    """, unsafe_allow_html=True)
