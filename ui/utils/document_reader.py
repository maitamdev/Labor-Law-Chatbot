# -*- coding: utf-8 -*-
"""
VietLabor AI - Document Attachment Reader
Extracts text from uploaded PDF, DOCX, DOC, and TXT files for legal review.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Tuple


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

    # 1. DOCX Extraction
    if ext in [".docx", ".doc"]:
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
            # Fallback to text decoding if docx parsing fails
            try:
                extracted_text = file_bytes.decode("utf-8", errors="ignore")
            except Exception:
                extracted_text = f"Không thể đọc tệp văn bản Word: {e}"

    # 2. PDF Extraction
    elif ext == ".pdf":
        try:
            import pymupdf
            pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            pages = []
            for i, page in enumerate(pdf_doc):
                page_text = page.get_text().strip()
                if page_text:
                    pages.append(f"--- Trang {i + 1} ---\n{page_text}")
            extracted_text = "\n\n".join(pages)
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
