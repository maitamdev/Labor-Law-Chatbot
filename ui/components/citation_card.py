# -*- coding: utf-8 -*-
"""
VietLabor AI - Compact Citation Card Component (Phase 6)
Matches the approved mockup layout with compact container and expandable statutory basis.
"""
from __future__ import annotations

import streamlit as st
from typing import Any, Dict

from ui.utils.formatting import format_provision_badge


def render_citation_card(citation: Dict[str, Any], key_prefix: str = "") -> None:
    """Renders a clean, compact statutory citation card with 'Xem căn cứ' expander."""
    doc_title = citation.get("document_title") or "Bộ luật Lao động 2019"
    doc_number = citation.get("document_number") or ""
    article = citation.get("article") or ""
    clause = citation.get("clause") or ""
    point = citation.get("point") or ""
    article_title = citation.get("article_title") or ""
    excerpt = citation.get("excerpt") or ""
    source_url = citation.get("source_url") or ""

    provision_badge = format_provision_badge(article, clause, point)

    # Clean Card HTML Header
    card_html = f"""
    <div class="citation-card">
        <div class="citation-doc-title">
            <span>📘</span> <strong>{doc_title}</strong>
        </div>
        <div class="citation-provision-badge">{provision_badge}</div>
        {f'<div class="citation-article-title">{article_title}</div>' if article_title else ''}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Expandable "Xem căn cứ" Detail Drawer
    with st.expander("📖 Xem căn cứ pháp lý chi tiết", expanded=False):
        if doc_number:
            st.markdown(f"**Văn bản số:** `{doc_number}`")
        if article_title:
            st.markdown(f"**Điều:** {article} ({article_title})")
        if clause or point:
            sub = []
            if clause:
                sub.append(f"Khoản {clause}")
            if point:
                sub.append(f"Điểm {point}")
            st.markdown(f"**Quy định cụ thể:** {' · '.join(sub)}")

        if excerpt:
            st.markdown(f"""
            <div class="citation-excerpt">
                {excerpt}
            </div>
            """, unsafe_allow_html=True)

        if source_url:
            st.markdown(f"""
            <a href="{source_url}" target="_blank" class="citation-link">
                Mở văn bản chính thức ↗
            </a>
            """, unsafe_allow_html=True)
