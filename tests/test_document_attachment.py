# -*- coding: utf-8 -*-
"""
Tests for document attachment upload, text extraction, and message rendering.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from ui.utils.document_reader import format_file_size, extract_attachment_text
from ui.components.approved_layout import render_messages
from ui.utils.session import SessionManager


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(2 * 1024 * 1024) == "2.0 MB"


def test_extract_plain_text_attachment():
    raw_text = "Hợp đồng thử việc 3 tháng, lương 80%."
    b64_content = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
    payload = {
        "name": "hop_dong.txt",
        "size": len(raw_text.encode("utf-8")),
        "data": f"data:text/plain;base64,{b64_content}",
    }
    extracted, name, size_str = extract_attachment_text(payload)
    assert name == "hop_dong.txt"
    assert "Hợp đồng thử việc 3 tháng" in extracted
    assert size_str != ""


def test_extract_docx_attachment():
    import docx
    doc = docx.Document()
    doc.add_paragraph("Điều 1: Thời hạn hợp đồng là 24 tháng.")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    b64_content = base64.b64encode(docx_bytes).decode("ascii")
    payload = {
        "name": "hop_dong_lao_dong.docx",
        "size": len(docx_bytes),
        "data": f"data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64_content}",
    }
    extracted, name, size_str = extract_attachment_text(payload)
    assert name == "hop_dong_lao_dong.docx"
    assert "Điều 1: Thời hạn hợp đồng là 24 tháng." in extracted


def test_render_messages_with_attachment_and_xss_protection():
    messages = [
        {
            "id": "u1",
            "role": "user",
            "content": "Rà soát giúp tôi hợp đồng này",
            "attachment": {
                "name": '<script>alert("hack")</script>hop_dong.pdf',
                "size_formatted": "120.5 KB",
                "file_type": ".pdf",
            },
        }
    ]
    rendered = render_messages(messages, False)
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered
    assert "user-attached-file" in rendered
    assert "hop_dong.pdf" in rendered
    assert "120.5 KB" in rendered


def test_session_manager_persists_attachment(tmp_path, monkeypatch):
    test_storage = tmp_path / "chat_history.json"
    monkeypatch.setattr("ui.utils.session.HISTORY_STORAGE_PATH", test_storage)

    sm = SessionManager()
    conv = sm.create_conversation("Kiểm tra tệp đính kèm")
    cid = conv["id"]

    att = {
        "name": "thoa_thuan.docx",
        "size_formatted": "45.0 KB",
        "file_type": ".docx",
    }
    sm.append_message(cid, "user", "Đánh giá thỏa thuận này", attachment=att)

    loaded = sm.get_conversation(cid)
    assert loaded is not None
    msgs = loaded.get("messages", [])
    assert len(msgs) == 1
    assert msgs[0].get("attachment") == att
