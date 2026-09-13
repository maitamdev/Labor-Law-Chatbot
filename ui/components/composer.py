# -*- coding: utf-8 -*-
"""
VietLabor AI - Chat Composer Component (Phase 6)
Renders sticky bottom input field with paper plane send button matching the mockup.
"""
from __future__ import annotations

import streamlit as st
from typing import Optional


def render_composer() -> Optional[str]:
    """Renders the clean bottom sticky input field."""
    # Check if a query was submitted via a chip, card, or topic button
    if "submitted_query" in st.session_state and st.session_state["submitted_query"]:
        q = st.session_state.pop("submitted_query")
        return q

    user_input = st.chat_input(
        placeholder="Hỏi về hợp đồng, lương, thử việc, nghỉ việc...",
        key="main_chat_input",
    )
    return user_input
