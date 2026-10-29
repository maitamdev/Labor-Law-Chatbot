# -*- coding: utf-8 -*-
"""
VietLabor AI - Document Attachment Reader
Extracts text from uploaded PDF, DOCX, DOC, and TXT files for legal review.
"""
from __future__ import annotations

import base64
import io
import logging
import threading
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# A page with less extractable text than this is treated as a scanned image.
MIN_TEXT_LAYER_CHARS = 20
# OCR costs ~1-2 s/page on CPU; cap it so one upload cannot stall the chat.
MAX_OCR_PAGES = 10
OCR_RENDER_DPI = 200

_ocr_engine: Optional[Any] = None
_ocr_lock = threading.Lock()


def _get_ocr_engine() -> Optional[Any]:
    """Lazily loads the local RapidOCR engine; returns None if unavailable."""
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]
                _ocr_engine = RapidOCR(use_cls=False)
            except Exception as exc:  # pragma: no cover - depends on local install
                logger.warning("RapidOCR unavailable, scanned PDFs cannot be read: %s", exc)
                return None
        return _ocr_engine


def _ocr_page(page: Any) -> str:
    """Runs OCR on one PyMuPDF page and returns recognized lines."""
    engine = _get_ocr_engine()
    if engine is None:
        return ""
    pix = page.get_pixmap(dpi=OCR_RENDER_DPI)
    result, _ = engine(pix.tobytes("png"))
    return "\n".join(r[1] for r in result) if result else ""


def format_file_size(size_bytes: int) -> str:
    """Format byte count into human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def extract_attachment_text(attachment: dict) -> Tuple[str, str, str]:
    """
    Extract readable text from a client attachment payload.
    
    Args:
        attachment: dict with keys: 'name', 'size', 'type', 'data'
        
    Returns:
        tuple of (extracted_text, filename, size_string)
    """
    if not isinstance(attachment, dict):
        return "", "", ""

    filename = str(attachment.get("name") or "tài_liệu").strip()
    size = int(attachment.get("size") or 0)
    size_str = format_file_size(size)
    raw_data = str(attachment.get("data") or "")

    if not raw_data:
        return "", filename, size_str

    # Handle base64 data URLs
    file_bytes = b""
    if raw_data.startswith("data:"):
        try:
            _, b64_part = raw_data.split(",", 1)
            file_bytes = base64.b64decode(b64_part)
        except Exception:
            file_bytes = b""
    else:
        try:
            file_bytes = base64.b64decode(raw_data)
        except Exception:
            file_bytes = raw_data.encode("utf-8", errors="replace")

    ext = Path(filename).suffix.lower()
    extracted_text = ""

    # 1. DOCX Extraction (legacy binary .doc is not supported by python-docx;
    # decoding its bytes would feed binary garbage to the model)
    if ext == ".doc":
        extracted_text = (
            "Không đọc được tệp Word định dạng cũ (.doc). "
            "Vui lòng lưu lại dưới dạng .docx hoặc .pdf rồi tải lên lại."
        )
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            parts = []
            for p in doc.paragraphs:
                pt = p.text.strip()
                if pt:
                    parts.append(pt)
            for table in doc.tables:
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        parts.append(" | ".join(row_texts))
            extracted_text = "\n\n".join(parts)
        except Exception as e:
            extracted_text = f"Không thể đọc tệp văn bản Word: {e}"

    # 2. PDF Extraction: text layer first, OCR fallback for scanned pages
    elif ext == ".pdf":
        try:
            import pymupdf
            pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            pages = []
            ocr_pages = 0
            skipped_ocr = 0
            for i, page in enumerate(pdf_doc.pages()):
                page_text = page.get_text().strip()
                if len(page_text) < MIN_TEXT_LAYER_CHARS:
                    if ocr_pages < MAX_OCR_PAGES:
                        ocr_text = _ocr_page(page).strip()
                        ocr_pages += 1
                        if ocr_text:
                            page_text = ocr_text
                    else:
                        skipped_ocr += 1
                if page_text:
                    pages.append(f"--- Trang {i + 1} ---\n{page_text}")
            pdf_doc.close()
            extracted_text = "\n\n".join(pages)
            if ocr_pages:
                extracted_text = (
                    f"[Lưu ý: {ocr_pages} trang là ảnh scan, nội dung được nhận dạng bằng OCR và có thể sai chính tả.]\n\n"
                    + extracted_text
                )
            if skipped_ocr:
                extracted_text += f"\n\n[... Bỏ qua {skipped_ocr} trang scan vượt giới hạn OCR {MAX_OCR_PAGES} trang ...]"
            if not extracted_text.strip():
                extracted_text = "Không trích xuất được nội dung từ tệp PDF (tệp rỗng hoặc ảnh scan không nhận dạng được)."
        except Exception as e:
            extracted_text = f"Không thể đọc tệp PDF: {e}"

    # 3. Plain text / Markdown
    else:
        for enc in ["utf-8", "utf-16", "cp1258", "latin-1"]:
            try:
                extracted_text = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

    # Cap text length to avoid token explosion (max ~15,000 characters)
    max_chars = 15000
    if len(extracted_text) > max_chars:
        extracted_text = (
            extracted_text[:max_chars]
            + f"\n\n[... Văn bản quá dài, đã cắt bớt {len(extracted_text) - max_chars} ký tự tiếp theo ...]"
        )

    return extracted_text.strip(), filename, size_str
