# -*- coding: utf-8 -*-
"""
VietLabor AI - Clarification & Quick Reply Chips Component (Phase 6)
Matches the approved mockup with outline blue pill buttons for clarification.
"""
from __future__ import annotations

import streamlit as st
from typing import Callable, List, Optional


def render_clarification_chips(
    chips: List[str],
    message_id: str,
    on_chip_click: Optional[Callable[[str], None]] = None,
) -> None:
    """Renders interactive quick-reply pill buttons in a compact row."""
    if not chips:
        return

    st.markdown('<div style="margin-top: 10px; margin-bottom: 4px;"></div>', unsafe_allow_html=True)
    
    # Render buttons in columns or flex-wrap
    cols = st.columns(len(chips))
    for idx, chip_text in enumerate(chips):
        with cols[idx]:
            btn_key = f"chip_{message_id}_{idx}"
            if st.button(chip_text, key=btn_key, use_container_width=True):
                if on_chip_click:
                    on_chip_click(chip_text)
                else:
                    st.session_state["submitted_query"] = chip_text
                    st.rerun()
