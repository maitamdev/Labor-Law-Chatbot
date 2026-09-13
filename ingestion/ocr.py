from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import pymupdf
from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]

from ingestion.schemas import PageText

logger = logging.getLogger(__name__)

# Vietnamese vowels with diacritics
VIETNAMESE_DIACRITICS_REGEX = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]",
    re.IGNORECASE,
)

# Standard legal structural markers (including OCR variants)
ARTICLE_REGEX = re.compile(r"\b(?:Điều|ĐIỀU|Dieu|DIEU|Điu|ĐIU)\s+\d+[a-z]?", re.IGNORECASE)
CLAUSE_REGEX = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
POINT_REGEX = re.compile(r"^\s*[a-zđ]\)\s+", re.MULTILINE | re.IGNORECASE)
CHAPTER_REGEX = re.compile(r"\b(?:Chương|CHƯƠNG|Chuong|CHUONG)\s+[IVXLCDM\d]+", re.IGNORECASE)


class OCRProcessor:
    """High-performance local OCR processor using RapidOCR (ONNXRuntime)

    with SHA-256 caching and automated quality gates.
    """

    def __init__(
        self,
        cache_dir: str | Path = "data/processed/ocr",
        render_dpi: int = 150,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.render_dpi = render_dpi
        self._engine = None

    def _get_engine(self) -> RapidOCR:
        if self._engine is None:
            self._engine = RapidOCR(use_cls=False)
        return self._engine

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Calculates SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_cache_path(self, doc_id: str) -> Path:
        return self.cache_dir / f"{doc_id}.jsonl"

    def is_cache_valid(self, doc_id: str, pdf_path: Path) -> bool:
        """Checks if OCR cache exists and matches the source PDF hash and page count."""
        cache_file = self.get_cache_path(doc_id)
        if not cache_file.exists():
            return False

        try:
            current_sha256 = self.compute_sha256(pdf_path)
            with open(cache_file, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    return False
                meta = json.loads(first_line)
                if meta.get("type") != "ocr_manifest":
                    return False
                if meta.get("source_sha256") != current_sha256:
                    return False

                # Check page count
                doc = pymupdf.open(pdf_path)
                expected_pages = len(doc)
                doc.close()

                lines = [line for line in f if line.strip()]
                return len(lines) == expected_pages
        except Exception as e:
            logger.warning("Failed to validate cache for %s: %s", doc_id, e)
            return False

    def load_from_cache(self, doc_id: str, filename: str) -> list[PageText]:
        """Loads cached OCR pages as PageText objects."""
        cache_file = self.get_cache_path(doc_id)
        pages: list[PageText] = []
        with open(cache_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "ocr_manifest":
                    continue
                pages.append(
                    PageText(
                        doc_id=doc_id,
                        filename=filename,
                        page_number=data["page_number"],
                        text=data["text"],
                    )
                )
        return pages

    def check_page_quality(self, text: str, confidence: Optional[float]) -> dict:
        """Checks character count, diacritic ratio, abnormal characters, and legal units."""
        char_count = len(text)
        alpha_chars = [c for c in text if c.isalpha()]
        alpha_count = len(alpha_chars)
        diacritic_matches = VIETNAMESE_DIACRITICS_REGEX.findall(text)
        diacritic_ratio = (len(diacritic_matches) / alpha_count) if alpha_count > 0 else 0.0

        replacement_count = text.count("\ufffd")
        has_articles = len(ARTICLE_REGEX.findall(text))
        has_clauses = len(CLAUSE_REGEX.findall(text))
        has_points = len(POINT_REGEX.findall(text))
        has_chapters = len(CHAPTER_REGEX.findall(text))

        is_suspicious = False
        reasons = []

        if char_count < 30:
            is_suspicious = True
            reasons.append("very_short_text")

        if replacement_count > 5:
            is_suspicious = True
            reasons.append("replacement_characters_found")

        if confidence is not None and confidence < 0.50:
            is_suspicious = True
            reasons.append("low_ocr_confidence")

        return {
            "char_count": char_count,
            "diacritic_ratio": round(diacritic_ratio, 3),
            "articles_detected": has_articles,
            "clauses_detected": has_clauses,
            "points_detected": has_points,
            "chapters_detected": has_chapters,
            "confidence": round(confidence, 3) if confidence is not None else None,
            "quality_status": "manual_review" if is_suspicious else "pass",
            "reasons": reasons,
        }

    def process_document(
        self,
        pdf_path: Path,
        doc_id: str,
        filename: str,
        force_ocr: bool = False,
    ) -> list[PageText]:
        """Runs full OCR pipeline on document with persistent caching and quality checks."""
        pdf_path = Path(pdf_path)

        if not force_ocr and self.is_cache_valid(doc_id, pdf_path):
            logger.info(f"  [CACHE HIT] {doc_id}: Nạp từ {self.get_cache_path(doc_id).name}")
            return self.load_from_cache(doc_id, filename)

        logger.info(f"  [OCR START] {doc_id}: Đang chạy Local OCR (RapidOCR ONNX)...")
        engine = self._get_engine()
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        source_sha256 = self.compute_sha256(pdf_path)

        cache_path = self.get_cache_path(doc_id)
        manifest_record = {
            "type": "ocr_manifest",
            "doc_id": doc_id,
            "filename": filename,
            "total_pages": total_pages,
            "source_sha256": source_sha256,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "ocr_engine": "rapidocr-onnxruntime",
            "ocr_model": "PP-OCRv4_mobile",
            "render_dpi": self.render_dpi,
        }

        pages_extracted: list[PageText] = []
        cached_records = [manifest_record]

        t0 = time.time()
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            pix = page.get_pixmap(dpi=self.render_dpi)
            res, _ = engine(pix.tobytes("png"))

            lines = [r[1] for r in res] if res else []
            scores = [float(r[2]) for r in res] if res else []
            text = "\n".join(lines)
            conf = float(sum(scores) / len(scores)) if scores else None

            quality = self.check_page_quality(text, conf)

            page_record = {
                "doc_id": doc_id,
                "page_number": page_num,
                "text": text,
                "ocr_engine": "rapidocr-onnxruntime",
                "ocr_model": "PP-OCRv4_mobile",
                "confidence": conf,
                "quality": quality,
            }
            cached_records.append(page_record)

            pages_extracted.append(
                PageText(
                    doc_id=doc_id,
                    filename=filename,
                    page_number=page_num,
                    text=text,
                )
            )

            if page_num % 5 == 0 or page_num == total_pages:
                logger.info(f"    Trang {page_num}/{total_pages} hoàn tất...")

        doc.close()
        elapsed = time.time() - t0
        logger.info(f"  [OCR DONE] {doc_id}: {total_pages} trang trong {elapsed:.1f}s ({elapsed/total_pages:.2f}s/trang)")

        # Write to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            for rec in cached_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        return pages_extracted
