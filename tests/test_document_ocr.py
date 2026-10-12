# -*- coding: utf-8 -*-
"""Scanned-PDF attachments (image only, no text layer) must go through OCR."""
from __future__ import annotations

import base64

import pymupdf
import pytest

from ui.utils import document_reader
from ui.utils.document_reader import extract_attachment_text


def _payload(name: str, data: bytes) -> dict:
    return {
        "name": name,
        "size": len(data),
        "data": "data:application/octet-stream;base64," + base64.b64encode(data).decode("ascii"),
    }


def _scanned_pdf(text: str) -> bytes:
    """Renders text to an image and embeds only the image in a new PDF."""
    src = pymupdf.open()
    page = src.new_page(width=420, height=160)
    page.insert_text((20, 80), text, fontsize=22)
    png = page.get_pixmap(dpi=200).tobytes("png")
    src.close()

    scanned = pymupdf.open()
    out_page = scanned.new_page(width=420, height=160)
    out_page.insert_image(out_page.rect, stream=png)
    data = scanned.tobytes()
    scanned.close()
    return data


def test_scanned_pdf_has_no_text_layer():
    doc = pymupdf.open(stream=_scanned_pdf("CONTRACT 24 MONTHS"), filetype="pdf")
    assert doc[0].get_text().strip() == ""


def test_scanned_pdf_is_read_with_ocr():
    pytest.importorskip("rapidocr_onnxruntime")
    extracted, name, _ = extract_attachment_text(_payload("scan.pdf", _scanned_pdf("CONTRACT 24 MONTHS")))
    assert name == "scan.pdf"
    assert "OCR" in extracted
    assert "24" in extracted
    assert "CONTRACT" in extracted.upper()


def test_ocr_page_cap(monkeypatch):
    calls = []
    monkeypatch.setattr(document_reader, "MAX_OCR_PAGES", 1)
    monkeypatch.setattr(document_reader, "_ocr_page", lambda page: calls.append(1) or "noi dung")
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    extracted, _, _ = extract_attachment_text(_payload("blank.pdf", doc.tobytes()))
    assert len(calls) == 1
    assert "Bỏ qua 2 trang" in extracted


def test_legacy_doc_is_rejected_cleanly():
    extracted, _, _ = extract_attachment_text(_payload("old.doc", b"\xd0\xcf\x11\xe0binary"))
    assert ".docx" in extracted
    assert "\x00" not in extracted
