# -*- coding: utf-8 -*-
"""
VietLabor AI - Welcome Screen Component (Phase 6)
Renders centered welcome banner and 4 suggested topic cards when conversation is empty.
"""
from __future__ import annotations

import streamlit as st
from typing import Callable, Optional
from ui.utils.branding import get_logo_base64

SUGGESTED_PROMPTS = [
    {
        "icon": ":material/schedule:",
        "title": "Thử việc tối đa bao nhiêu ngày?",
        "subtitle": "Quy định về thời gian thử việc theo từng trình độ chuyên môn kỹ thuật",
    },
    {
        "icon": ":material/description:",
        "title": "Tôi ký hợp đồng 2 năm, muốn nghỉ việc phải báo trước bao lâu?",
        "subtitle": "Thời hạn báo trước khi đơn phương chấm dứt hợp đồng xác định thời hạn",
    },
    {
        "icon": ":material/payments:",
        "title": "Làm thêm ngày lễ được trả lương thế nào?",
        "subtitle": "Mức tiền lương làm thêm giờ vào ngày nghỉ lễ, tết theo luật định",
    },
    {
        "icon": ":material/policy:",
        "title": "Công ty có được giữ bằng đại học bản chính không?",
        "subtitle": "Quy định về các hành vi người sử dụng lao động không được làm khi ký HĐLĐ",
    },
]


def render_welcome_screen(on_card_click: Optional[Callable[[str], None]] = None) -> None:
    """Renders the clean, spacious centered empty-state welcome screen."""
    logo_b64 = get_logo_base64()
    logo_badge = (
        f'<div class="welcome-logo-badge"><img src="data:image/png;base64,{logo_b64}" class="welcome-logo-img" alt="VietLabor AI Logo" /></div>'
        if logo_b64
        else ""
    )

    st.markdown(f"""
    <div class="welcome-container">
        {logo_badge}
        <div class="welcome-title">Bạn cần tra cứu vấn đề lao động nào?</div>
        <div class="welcome-subtitle">
            Tôi có thể hỗ trợ bạn tìm kiếm và giải thích các quy định pháp luật lao động dựa trên văn bản chính thức.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2x2 Suggested Cards Grid
    col1, col2 = st.columns(2, gap="medium")

    for idx, prompt_data in enumerate(SUGGESTED_PROMPTS):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            card_title = prompt_data["title"]

            if st.button(
                card_title,
                icon=prompt_data["icon"],
                key=f"welcome_card_{idx}",
                use_container_width=True,
                help=prompt_data["subtitle"],
            ):
                if on_card_click:
                    on_card_click(card_title)
                else:
                    st.session_state["submitted_query"] = card_title
                    st.rerun()
