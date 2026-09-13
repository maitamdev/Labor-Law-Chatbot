# -*- coding: utf-8 -*-
"""
VietLabor AI - Right Information Panel Component (Phase 6)
Matches the approved mockup with Popular Topics, Main Legal Documents, and Disclaimer.
"""
from __future__ import annotations

import streamlit as st
from typing import Callable, Optional

POPULAR_TOPICS = [
    ("👤", "Thử việc", "Thời gian thử việc tối đa theo trình độ?"),
    ("📝", "Nghỉ việc", "Quy định về thời hạn báo trước khi nghỉ việc?"),
    ("🕒", "Làm thêm giờ", "Số giờ làm thêm tối đa trong một ngày?"),
    ("💰", "Tiền lương", "Làm việc vào ban đêm được trả lương thế nào?"),
    ("📅", "Nghỉ phép", "Số ngày nghỉ phép năm theo thâm niên và công việc?"),
]

MAIN_DOCS = [
    ("📖", "Bộ luật Lao động 2019", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx"),
    ("📄", "Nghị định 145/2020/NĐ-CP", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-460987.aspx"),
    ("📄", "Nghị định 12/2022/NĐ-CP", "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx"),
]


def render_right_panel(on_topic_click: Optional[Callable[[str], None]] = None) -> None:
    """Renders the clean, sparse right information panel."""
    st.markdown('<div class="sidebar-section-title">CHỦ ĐỀ PHỔ BIẾN</div>', unsafe_allow_html=True)

    for idx, (icon, label, sample_q) in enumerate(POPULAR_TOPICS):
        btn_col1, btn_col2 = st.columns([0.88, 0.12])
        if st.button(f"{icon}  {label}", key=f"pop_topic_{idx}", use_container_width=True):
            if on_topic_click:
                on_topic_click(sample_q)
            else:
                st.session_state["submitted_query"] = sample_q
                st.rerun()

    st.markdown('<div class="sidebar-section-title" style="margin-top: 24px;">VĂN BẢN CHÍNH</div>', unsafe_allow_html=True)
    for idx, (icon, title, url) in enumerate(MAIN_DOCS):
        st.markdown(f"""
        <a href="{url}" target="_blank" style="text-decoration: none;">
            <div class="right-card-item">
                <span>{icon} {title}</span>
                <span class="right-card-chevron">↗</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

    # Disclaimer Card
    st.markdown("""
    <div class="disclaimer-card">
        <div class="disclaimer-header">
            <span>ℹ</span> LƯU Ý
        </div>
        <div class="disclaimer-text">
            VietLabor AI hỗ trợ tra cứu thông tin pháp luật lao động từ các văn bản trong cơ sở dữ liệu. Nội dung cung cấp mang tính tham khảo và không thay thế ý kiến tư vấn chuyên môn cho tình huống pháp lý cụ thể.
        </div>
    </div>
    """, unsafe_allow_html=True)
