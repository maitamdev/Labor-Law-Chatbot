# -*- coding: utf-8 -*-
"""
Ingest PDFs listed in national_labor_wave3_manifest.csv into legal_documents_v3.jsonl.

Uses text-layer PDF extraction first; falls back to RapidOCR when the PDF is scanned.
After ingest, rebuild indexes: python scripts/build_index_v3.py --force
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.metadata_registry import get_verified_metadata
from config.settings import PRODUCTION_CORPUS_PATH
from ingestion.cleaner import TextCleaner
from ingestion.diacritic_restorer import LegalDiacriticRestorer
from ingestion.loader import PDFLoader
from ingestion.ocr import VIETNAMESE_DIACRITICS_REGEX, OCRProcessor
from ingestion.parser import LegalParser
from ingestion.schemas import PageText

MANIFEST = PROJECT_ROOT / "data" / "raw" / "national_labor_wave3_manifest.csv"
MIN_CHARS_PER_PAGE = 120


def _existing_doc_ids(corpus: Path) -> set[str]:
    ids: set[str] = set()
    if not corpus.is_file():
        return ids
    for line in corpus.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["doc_id"])
    return ids


def _load_pages(pdf_path: Path, doc_id: str, force_ocr: bool) -> list:
    loader = PDFLoader(pdf_path, doc_id=doc_id)
    pages = loader.load()
    total_chars = sum(len(p.text or "") for p in pages)
    avg = total_chars / max(1, len(pages))
    if force_ocr or avg < MIN_CHARS_PER_PAGE:
        ocr = OCRProcessor()
        pages = ocr.process_document(pdf_path, doc_id, pdf_path.name, force_ocr=False)

    cleaner = TextCleaner()
    restorer = LegalDiacriticRestorer()
    cleaned_pages: list[PageText] = []
    for p in pages:
        cp = cleaner.clean_page(p)
        txt = cp.text or ""
        alpha_cnt = sum(1 for ch in txt if ch.isalpha())
        diac_cnt = len(VIETNAMESE_DIACRITICS_REGEX.findall(txt))
        if alpha_cnt > 20 and (diac_cnt / alpha_cnt) < 0.08:
            txt = restorer.restore_text(txt)
        cleaned_pages.append(
            PageText(
                doc_id=cp.doc_id,
                filename=cp.filename,
                page_number=cp.page_number,
                text=txt,
            )
        )
    return cleaned_pages



def _chunk_to_jsonl_row(chunk) -> dict:
    row = chunk.model_dump()
    title = row.get("article_title") or ""
    body = row.get("content") or ""
    row["retrieval_text"] = f"{title}\n{body}".strip()
    return row


def ingest_row(row: dict, corpus: Path, replace: bool) -> int:
    doc_id = row["doc_id"]
    rel = (row.get("pdf_relative_path") or "").strip()
    if not rel:
        print(f"[SKIP] {doc_id}: no pdf_relative_path (download first)")
        return 0
    pdf_path = (PROJECT_ROOT / rel).resolve()
    if not pdf_path.is_file():
        print(f"[SKIP] {doc_id}: missing PDF {pdf_path}")
        return 0

    existing = _existing_doc_ids(corpus)
    if doc_id in existing and not replace:
        print(f"[SKIP] {doc_id}: already in corpus (use --replace)")
        return 0

    reg = get_verified_metadata(doc_id)
    meta = {
        **reg,
        "doc_id": doc_id,
        "filename": pdf_path.name,
        "extraction_method": "pdf_text",
        "text_source_url": row.get("official_url") or reg.get("official_source"),
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if row.get("domain"):
        meta["domain"] = row["domain"]
    if row.get("status"):
        meta["status"] = row["status"]

    pages = _load_pages(pdf_path, doc_id, force_ocr=False)
    chunks = LegalParser(meta).parse_pages(pages)
    if not chunks:
        print(f"[WARN] {doc_id}: parser produced 0 chunks")
        return 0

    lines = []
    if corpus.is_file():
        lines = [ln for ln in corpus.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if replace and doc_id in existing:
        lines = [ln for ln in lines if json.loads(ln).get("doc_id") != doc_id]

    new_lines = [json.dumps(_chunk_to_jsonl_row(c), ensure_ascii=False) for c in chunks]
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text("\n".join(lines + new_lines) + "\n", encoding="utf-8")
    print(f"[OK] {doc_id}: +{len(new_lines)} chunks from {pdf_path.name}")
    return len(new_lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--corpus", type=Path, default=PRODUCTION_CORPUS_PATH)
    parser.add_argument("--doc-id", action="append", help="Only ingest these doc_id values")
    parser.add_argument("--replace", action="store_true", help="Replace existing doc_id chunks")
    args = parser.parse_args()

    with args.manifest.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if args.doc_id:
        allow = set(args.doc_id)
        rows = [r for r in rows if r.get("doc_id") in allow]

    total = 0
    for row in rows:
        total += ingest_row(row, args.corpus.resolve(), args.replace)
    print(f"Done. Added {total} chunks. Rebuild BM25/Chroma: python scripts/build_index_v3.py --force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
