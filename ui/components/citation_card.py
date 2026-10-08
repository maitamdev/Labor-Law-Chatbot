# -*- coding: utf-8 -*-
"""
VietLabor AI - Compact Citation Card Component (Phase 6)
Matches the approved mockup layout with compact container and expandable statutory basis.
"""
from __future__ import annotations

import html
from urllib.parse import urlparse

import streamlit as st
from typing import Any, Dict

from ui.utils.formatting import format_provision_badge


OFFICIAL_SOURCE_HOSTS = {
    "vanban.chinhphu.vn",
    "datafiles.chinhphu.vn",
    "congbao.chinhphu.vn",
    "congbaocdn.chinhphu.vn",
    "vbpl.vn",
    "vbpl-bientap-gateway.moj.gov.vn",
    "moha.gov.vn",
    "thuvienphapluat.vn",
    "www.thuvienphapluat.vn",
}


def _safe_official_url(value: Any) -> str:
    """Allows only HTTPS links to the configured official legal sources."""
    raw = str(value or "").strip()
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ""
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in OFFICIAL_SOURCE_HOSTS:
        return ""
    return raw


def render_citation_card(citation: Dict[str, Any], key_prefix: str = "") -> None:
    """Renders a clean, compact statutory citation card with 'Xem căn cứ' expander."""
    doc_title = str(citation.get("document_title") or "Bộ luật Lao động 2019")
    doc_number = str(citation.get("document_number") or "")
    article = str(citation.get("article") or "")
    clause = str(citation.get("clause") or "")
    point = str(citation.get("point") or "")
    article_title = str(citation.get("article_title") or "")
    excerpt = str(citation.get("excerpt") or "")
    source_url = _safe_official_url(citation.get("source_url"))
    deep_link_url = _safe_official_url(citation.get("deep_link_url"))

    provision_badge = html.escape(format_provision_badge(article, clause, point))
    safe_doc_title = html.escape(doc_title)
    safe_article_title = html.escape(article_title)

    # Clean Card HTML Header
    card_html = f"""
    <div class="citation-card">
        <div class="citation-doc-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
                <path d="M6 6h10"/>
                <path d="M6 10h10"/>
            </svg>
            <strong>{safe_doc_title}</strong>
        </div>
        <div class="citation-provision-badge">{provision_badge}</div>
        {f'<div class="citation-article-title">{safe_article_title}</div>' if article_title else ''}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Expandable "Xem căn cứ" Detail Drawer
    with st.expander("Xem căn cứ pháp lý chi tiết", icon=":material/menu_book:", expanded=False):
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
                {html.escape(excerpt).replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)

        # Dual Navigation Action Buttons
        art_label = f"Điều {article}" if article else "Điều khoản"
        actions = []
        if deep_link_url:
            btn_title = f"Mở {art_label} (Tự cuộn tới Điều) ↗" if "#dieu_" in deep_link_url else f"Mở {safe_doc_title} (HTML) ↗"
            actions.append(f"""
            <a href="{html.escape(deep_link_url, quote=True)}" target="_blank" rel="noopener noreferrer" class="citation-btn-primary">
                🎯 {btn_title}
            </a>
            """)
        if source_url:
            actions.append(f"""
            <a href="{html.escape(source_url, quote=True)}" target="_blank" rel="noopener noreferrer" class="citation-btn-secondary">
                🏛️ Công Báo Chính Phủ ↗
            </a>
            """)

        if actions:
            st.markdown(f"""
            <div class="citation-actions">
                {''.join(actions)}
            </div>
            """, unsafe_allow_html=True)
