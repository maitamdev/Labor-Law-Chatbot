# -*- coding: utf-8 -*-
"""
VietLabor AI - UI Formatting Helpers (Phase 6)
"""
from __future__ import annotations

import datetime
import html
from typing import Optional


def format_provision_badge(
    article: Optional[str],
    clause: Optional[str] = None,
    point: Optional[str] = None,
) -> str:
    """Formats canonical provision hierarchy: 'Điều 35 · Khoản 1 · Điểm b'."""
    parts = []
    if article:
        parts.append(f"Điều {article}")
    if clause:
        parts.append(f"Khoản {clause}")
    if point:
        parts.append(f"Điểm {point}")
    return " · ".join(parts) if parts else "Căn cứ luật định"


def format_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """Returns clean HH:MM string."""
    d = dt or datetime.datetime.now()
    return d.strftime("%H:%M")


def format_relative_date(iso_date_str: str) -> str:
    """Formats an ISO timestamp to 'Hôm nay HH:MM', 'Hôm qua HH:MM', or 'DD/MM HH:MM'."""
    try:
        dt = datetime.datetime.fromisoformat(iso_date_str)
        now = datetime.datetime.now()
        if dt.date() == now.date():
            return f"Hôm nay {dt.strftime('%H:%M')}"
        yesterday = now.date() - datetime.timedelta(days=1)
        if dt.date() == yesterday:
            return f"Hôm qua {dt.strftime('%H:%M')}"
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return "Gần đây"
