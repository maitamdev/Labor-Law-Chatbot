# -*- coding: utf-8 -*-
"""Unit test suite for document attachment reader functions."""
import base64
from ui.utils.document_reader import format_file_size, extract_attachment_text


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert "KB" in format_file_size(2048)
    assert "MB" in format_file_size(2 * 1024 * 1024)


def test_extract_plain_text_attachment():
    raw_text = "HỢP ĐỒNG LAO ĐỘNG\nĐiều 1: Công việc"
    b64_data = "data:text/plain;base64," + base64.b64encode(raw_text.encode('utf-8')).decode('utf-8')
    payload = {
        "name": "hop_dong.txt",
        "size": len(raw_text.encode('utf-8')),
        "type": "text/plain",
        "data": b64_data
    }
    extracted, name, size_str = extract_attachment_text(payload)
    assert name == "hop_dong.txt"
    assert "Điều 1: Công việc" in extracted


def test_extract_empty_or_invalid():
    text, name, size = extract_attachment_text(None)
    assert text == ""
    assert name == ""
