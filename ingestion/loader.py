from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from ingestion.schemas import PageText

logger = logging.getLogger(__name__)


class PDFLoader:
    """Loads a PDF file page by page using PyMuPDF (fitz) into a list of PageText models."""

    def __init__(self, file_path: str | Path, doc_id: Optional[str] = None):
        self.file_path = Path(file_path).resolve()
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")
        self.doc_id = doc_id or self.file_path.stem
        self.filename = self.file_path.name

    def load(self) -> list[PageText]:
        """Extract text from each page, preserving 1-indexed page numbers and empty pages."""
        pages: list[PageText] = []
        try:
            logger.info(f"[LOAD] Opening PDF: {self.filename} ({self.file_path})")
            doc = fitz.open(self.file_path)
            total_pages = len(doc)
            logger.info(f"[LOAD] {self.doc_id} - Total pages: {total_pages}")

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page = doc[page_idx]
                    # PyMuPDF get_text preserves UTF-8 Unicode
                    text = page.get_text("text")
                    pages.append(
                        PageText(
                            doc_id=self.doc_id,
                            filename=self.filename,
                            page_number=page_num,
                            text=text,
                        )
                    )
                except Exception as page_err:
                    logger.warning(
                        f"[LOAD] Error reading page {page_num} in {self.filename}: {page_err}. Keeping as empty text."
                    )
                    pages.append(
                        PageText(
                            doc_id=self.doc_id,
                            filename=self.filename,
                            page_number=page_num,
                            text="",
                        )
                    )

            doc.close()
            logger.info(f"[LOAD] Successfully extracted {len(pages)} pages from {self.filename}")
            return pages

        except Exception as e:
            logger.error(f"[ERROR] Failed to load PDF {self.file_path}: {e}")
            raise RuntimeError(f"Error loading PDF {self.file_path}: {e}") from e
