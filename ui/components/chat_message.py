# -*- coding: utf-8 -*-
"""
VietLabor AI - Chat Message Component (Phase 6)
Renders User bubbles and Assistant cards adhering to the approved mockup.
"""
from __future__ import annotations

import html
import streamlit as st
from typing import Any, Callable, Dict, Optional

from ui.components.citation_card import render_citation_card
from ui.components.clarification import render_clarification_chips


def render_user_message(content: str, timestamp: str = "") -> None:
    """Renders user query in a right-aligned light blue bubble."""
    escaped_content = html.escape(content).replace("\n", "<br>")
    time_html = f'<div class="user-msg-time">{html.escape(timestamp)}</div>' if timestamp else ""
    user_html = f'<div class="user-msg-wrapper"><div class="user-msg-bubble">{escaped_content}</div>{time_html}</div>'
    st.markdown(user_html, unsafe_allow_html=True)


def render_assistant_message(
    msg: Dict[str, Any],
    on_chip_click: Optional[Callable[[str], None]] = None,
) -> None:
    """Renders assistant answer card with avatar, findings, citations, and clarification chips."""
    content = msg.get("content", "")
    timestamp = msg.get("timestamp", "")
    msg_id = msg.get("id", "msg")
    data = msg.get("structured_data", {})

    citations = data.get("citations", [])
    needs_clarification = data.get("needs_clarification", False)
    followups = data.get("suggested_followups", [])

    # Layout with left avatar icon and right message container
    col_avatar, col_content = st.columns([0.06, 0.94], gap="small")

    with col_avatar:
        st.markdown("""
        <div class="assistant-avatar">⚖</div>
        """, unsafe_allow_html=True)

    with col_content:
        # Render the full structured advisory answer
        st.markdown(content)

        # Render deduplicated statutory citations if present
        if citations and not needs_clarification:
            st.markdown("**Căn cứ pháp lý:**")
            seen_cids = set()
            unique_citations = []
            for c in citations:
                cid = c.get("chunk_id")
                if cid and cid not in seen_cids:
                    seen_cids.add(cid)
                    unique_citations.append(c)
                elif not cid:
                    unique_citations.append(c)

            for c_idx, c in enumerate(unique_citations):
                render_citation_card(c, key_prefix=f"{msg_id}_c{c_idx}")

        # Render clarification quick-reply chips if clarification is needed
        if needs_clarification and followups:
            render_clarification_chips(
                chips=followups,
                message_id=msg_id,
                on_chip_click=on_chip_click,
            )

        if timestamp:
            st.markdown(f'<div class="assistant-msg-time">{html.escape(timestamp)}</div>', unsafe_allow_html=True)
