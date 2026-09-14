# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G Extended Corpus Ingestion Pipeline
Parses Wave 1 extended documents:
- ND_135_2020 (Tuổi nghỉ hưu - Retirement)
- LVL_74_2025 (Luật Việc làm 74/2025/QH15 - Unemployment Insurance)
- ND_374_2025 (Nghị định 374/2025/NĐ-CP - Unemployment Insurance Guidance)
- ND_219_2025 (Nghị định 219/2025/NĐ-CP - Foreign Workers)

Outputs:
1. data/processed/extended_documents.jsonl (only new extended chunks)
2. data/processed/legal_documents_v2.jsonl (CORE 3,206 chunks + new extended chunks)
LEAVES data/processed/legal_documents.jsonl 100% UNTOUCHED.
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
import sys
from typing import Any, List

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 stdout
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from config.metadata_registry import get_verified_metadata
from ingestion.cleaner import TextCleaner
from ingestion.parser import LegalParser
from ingestion.schemas import LegalChunk, PageText

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_extended_ingestion")

EXTENDED_MANIFEST = PROJECT_ROOT / "data" / "raw" / "extended" / "extended_manifest.csv"
EXTENDED_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "extended"
CORE_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "legal_documents.jsonl"
EXTENDED_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "extended_documents.jsonl"
V2_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "legal_documents_v2.jsonl"


DOC_FILE_MAP = {
    "ND_135_2020": EXTENDED_RAW_DIR / "retirement" / "01_135_2020_ND_CP_Tuoi_Nghi_Huu.txt",
    "LVL_74_2025": EXTENDED_RAW_DIR / "unemployment" / "02_74_2025_QH15_Luat_Viec_Lam.txt",
    "ND_374_2025": EXTENDED_RAW_DIR / "unemployment" / "03_374_2025_ND_CP_Huong_Dan_BHTN.txt",
    "ND_219_2025": EXTENDED_RAW_DIR / "foreign_workers" / "04_219_2025_ND_CP_Lao_Dong_Nuoc_Ngoai.txt",
}


def load_extended_manifest() -> List[dict[str, Any]]:
    if not EXTENDED_MANIFEST.exists():
        raise FileNotFoundError(f"Extended manifest missing: {EXTENDED_MANIFEST}")
    with open(EXTENDED_MANIFEST, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def ingest_document(meta_row: dict[str, Any], cleaner: TextCleaner) -> List[LegalChunk]:
    doc_id = meta_row["doc_id"]
    file_path = DOC_FILE_MAP.get(doc_id)
    if not file_path or not file_path.exists():
        raise FileNotFoundError(f"Source file not found for {doc_id}: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    cleaned_text = cleaner.clean_text(raw_text)

    # Wrap into PageText representation
    page_text = PageText(
        doc_id=doc_id,
        filename=file_path.name,
        page_number=1,
        text=cleaned_text,
    )

    full_meta = get_verified_metadata(doc_id)
    full_meta.update({
        "doc_id": doc_id,
        "filename": file_path.name,
        "extraction_method": "official_digital_text",
        "scope_tier": meta_row.get("scope_tier", "extended"),
        "domain": meta_row.get("domain", "UNKNOWN"),
        "status": meta_row.get("status", "CURRENT"),
        "amends": meta_row.get("amends"),
        "amended_by": meta_row.get("amended_by"),
        "replaces": meta_row.get("replaces"),
        "replaced_by": meta_row.get("replaced_by"),
        "official_source": meta_row.get("official_url"),
    })

    parser = LegalParser(doc_metadata=full_meta)
    chunks = parser.parse_pages([page_text])
    logger.info(f"Parsed {doc_id}: {len(chunks)} chunks produced.")
    return chunks


def main():
    logger.info("=== STARTING PHASE 5G EXTENDED INGESTION PIPELINE ===")
    manifest_rows = load_extended_manifest()
    cleaner = TextCleaner()

    all_extended_chunks: List[LegalChunk] = []

    for row in manifest_rows:
        doc_id = row["doc_id"]
        logger.info(f"Processing extended document: {doc_id} ({row['title']})...")
        chunks = ingest_document(row, cleaner)
        all_extended_chunks.extend(chunks)

    # 1. Write extended_documents.jsonl
    logger.info(f"Writing {len(all_extended_chunks)} chunks to {EXTENDED_PROCESSED_JSONL}...")
    with open(EXTENDED_PROCESSED_JSONL, "w", encoding="utf-8") as f:
        for chunk in all_extended_chunks:
            f.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

    # 2. Build combined legal_documents_v2.jsonl (CORE + EXTENDED)
    logger.info(f"Merging CORE from {CORE_PROCESSED_JSONL} with EXTENDED into {V2_PROCESSED_JSONL}...")
    core_count = 0
    with open(V2_PROCESSED_JSONL, "w", encoding="utf-8") as f_out:
        # Read core chunks and make sure scope_tier and domain are present
        if CORE_PROCESSED_JSONL.exists():
            with open(CORE_PROCESSED_JSONL, "r", encoding="utf-8") as f_in:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    c = json.loads(line)
                    if "scope_tier" not in c:
                        c["scope_tier"] = "core"
                    if "domain" not in c:
                        c["domain"] = "CORE_LABOR"
                    if "status" not in c:
                        c["status"] = "CURRENT"
                    f_out.write(json.dumps(c, ensure_ascii=False) + "\n")
                    core_count += 1
        else:
            logger.warning("CORE processed file not found! Generating V2 with extended only.")

        for chunk in all_extended_chunks:
            f_out.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

    total_v2 = core_count + len(all_extended_chunks)
    logger.info(f"=== INGESTION SUCCESS: Core Chunks: {core_count} | Extended Chunks: {len(all_extended_chunks)} | Total V2 Chunks: {total_v2} ===")


if __name__ == "__main__":
    main()
