from __future__ import annotations

import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.metadata_registry import get_verified_metadata
from ingestion.cleaner import TextCleaner
from ingestion.loader import PDFLoader
from ingestion.parser import LegalParser
from ingestion.schemas import LegalChunk

# Set up logging and UTF-8 console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("VietLaborIngestion")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "raw" / "download_manifest.csv"
OUTPUT_JSONL_PATH = PROJECT_ROOT / "data" / "processed" / "legal_documents.jsonl"


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Loads manifest CSV using utf-8-sig to safely handle UTF-8 BOM."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    records = []
    with open(manifest_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def run_pipeline(target_doc_id: str | None = None) -> list[LegalChunk]:
    """Runs ingestion pipeline on core documents marked for RAG inclusion."""
    OUTPUT_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest_rows = load_manifest(MANIFEST_PATH)

    cleaner = TextCleaner()
    all_chunks: list[LegalChunk] = []

    existing_chunks: dict[str, dict[str, Any]] = {}
    if OUTPUT_JSONL_PATH.exists():
        try:
            with open(OUTPUT_JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        c_dict = json.loads(line)
                        existing_chunks[c_dict["chunk_id"]] = c_dict
        except Exception as e:
            logger.warning(f"Không thể đọc chunks cũ từ {OUTPUT_JSONL_PATH.name}: {e}")

    # Filter target docs
    core_docs = [
        r for r in manifest_rows
        if r.get("category") == "core" and r.get("include_in_rag", "").strip().lower() == "true"
    ]

    # Prioritize fast documents first (cached / small), then larger ones
    doc_priority = {
        "TT_10_2020": 1,
        "ND_293_2025": 2,
        "ND_337_2025": 3,
        "TT_08_2026": 4,
        "ND_12_2022": 5,
        "VBHN_18_2026": 6,
        "ND_145_2020": 7,
    }
    core_docs.sort(key=lambda r: doc_priority.get(r.get("id"), 99))

    if target_doc_id:
        core_docs = [r for r in core_docs if r.get("id") == target_doc_id]

    logger.info(f"=== BẮT ĐẦU INGESTION: {len(core_docs)} VĂN BẢN CORE ===")

    for doc_meta in core_docs:
        doc_id = doc_meta["id"]
        doc_title = doc_meta["title"]
        local_rel_path = doc_meta["local_path"]
        pdf_path = PROJECT_ROOT / local_rel_path

        logger.info(f"\n[LOAD] Document: {doc_id} - {doc_title}")
        if not pdf_path.exists():
            logger.error(f"[ERROR] File không tồn tại: {pdf_path}")
            continue

        # 1. Load PDF
        loader = PDFLoader(pdf_path, doc_id=doc_id)
        pages = loader.load()
        logger.info(f"[LOAD] {doc_id} - {len(pages)} pages loaded")

        # 2. Clean Text
        cleaned_pages = []
        total_text_chars = 0
        for p in pages:
            cleaned_p = cleaner.clean_page(p)
            cleaned_pages.append(cleaned_p)
            total_text_chars += len(cleaned_p.text)

        logger.info(f"[CLEAN] {doc_id} - Total characters after cleaning: {total_text_chars}")

        extraction_method = "pdf_text"
        ocr_engine = None
        ocr_model = None

        avg_chars_per_page = total_text_chars / max(1, len(pages))

        if avg_chars_per_page < 100:
            logger.info(
                f"[OCR] {doc_id} - Văn bản có ít text ({total_text_chars} ký tự / {len(pages)} trang = {avg_chars_per_page:.1f} ký tự/trang). "
                f"Đang kích hoạt Local Vietnamese OCR Pipeline..."
            )

            from ingestion.ocr import OCRProcessor
            ocr_proc = OCRProcessor()
            pages = ocr_proc.process_document(
                pdf_path=pdf_path,
                doc_id=doc_id,
                filename=doc_meta.get("filename", pdf_path.name),
            )
            cleaned_pages = [cleaner.clean_page(p) for p in pages]
            total_ocr_chars = sum(len(p.text) for p in cleaned_pages)
            logger.info(f"[OCR] {doc_id} - Hoàn tất OCR: {total_ocr_chars} ký tự trích xuất")
            extraction_method = "local_ocr"
            ocr_engine = "rapidocr-onnxruntime"
            ocr_model = "PP-OCRv4_mobile"

        # 3. Parse Legal Structure with Verified Metadata
        verified = get_verified_metadata(doc_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        parser_meta = {
            "doc_id": doc_id,
            "doc_title": verified.get("doc_title") or doc_title,
            "filename": doc_meta.get("filename", pdf_path.name),
            "document_no": verified.get("document_no"),
            "document_type": verified.get("document_type"),
            "issuer": verified.get("issuer"),
            "signer": verified.get("signer"),
            "effective_from": verified.get("effective_from"),
            "effective_to": verified.get("effective_to"),
            "status": verified.get("status"),
            "official_source": verified.get("official_source") or doc_meta.get("source_page") or doc_meta.get("pdf_url"),
            "extraction_method": extraction_method,
            "ocr_engine": ocr_engine,
            "ocr_model": ocr_model,
            "text_source_url": doc_meta.get("source_page") or doc_meta.get("pdf_url"),
            "extraction_timestamp": now_iso,
        }

        parser = LegalParser(parser_meta)
        chunks = parser.parse_pages(cleaned_pages)


        articles_count = len({c.article_number for c in chunks if c.article_number})
        clauses_count = len({f"{c.article_number}-k{c.clause_number}" for c in chunks if c.clause_number})
        points_count = sum(1 for c in chunks if c.point)

        logger.info(f"[PARSE] {doc_id} - Chunks: {len(chunks)} (Articles: {articles_count}, Clauses: {clauses_count}, Points: {points_count})")
        all_chunks.extend(chunks)

        # Remove old chunks for this doc_id from existing_chunks and add new ones
        existing_chunks = {cid: c for cid, c in existing_chunks.items() if c.get("doc_id") != doc_id}
        for chunk in chunks:
            existing_chunks[chunk.chunk_id] = chunk.model_dump()

        # Incremental save to JSONL
        with open(OUTPUT_JSONL_PATH, mode="w", encoding="utf-8") as f:
            for c_dict in existing_chunks.values():
                f.write(json.dumps(c_dict, ensure_ascii=False) + "\n")
        logger.info(f"[CHECKPOINT] Đã cập nhật {OUTPUT_JSONL_PATH.name} (Hiện có {len(existing_chunks)} chunks tổng cộng)")

    logger.info(f"\n[SAVE] Hoàn tất toàn bộ pipeline. File kết quả: {OUTPUT_JSONL_PATH.relative_to(PROJECT_ROOT)} ({len(existing_chunks)} chunks)")
    return all_chunks


if __name__ == "__main__":
    run_pipeline()
