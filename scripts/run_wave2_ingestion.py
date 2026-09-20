# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Extended Wave 2 Corpus Ingestion Pipeline
Parses Wave 2 documents:
- Social Insurance (BHXH):
  * VBHN_58_2025 (Luật BHXH hợp nhất 58/VBHN-VPQH)
  * ND_158_2025 (NĐ 158/2025/NĐ-CP - BHXH bắt buộc)
  * ND_159_2025 (NĐ 159/2025/NĐ-CP - BHXH tự nguyện)
  * TT_12_2025 (TT 12/2025/TT-BNV - Hướng dẫn BHXH)
  * ND_176_2025 (NĐ 176/2025/NĐ-CP - Trợ cấp hưu trí xã hội)
- Occupational Safety & Accident/Disease (ATVSLĐ / TNLĐ-BNN):
  * L_84_2015 (Luật ATVSLĐ 84/2015/QH13)
  * ND_39_2016 (NĐ 39/2016/NĐ-CP - Hướng dẫn Luật ATVSLĐ)
  * VBHN_04_BNV_2026 (04/VBHN-BNV - Bảo hiểm TNLĐ-BNN)
  * VBHN_05_BNV_2026 (05/VBHN-BNV - Mức đóng quỹ TNLĐ-BNN)
  * VBHN_06_BNV_2026 (06/VBHN-BNV - Chế độ TNLĐ-BNN)

Outputs:
1. data/processed/extended_wave2_documents.jsonl (only new Wave 2 chunks)
2. data/processed/legal_documents_v3.jsonl (V2 3,344 chunks + new Wave 2 chunks)
LEAVES data/processed/legal_documents.jsonl and legal_documents_v2.jsonl 100% UNTOUCHED.
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
logger = logging.getLogger("run_wave2_ingestion")

WAVE2_MANIFEST = PROJECT_ROOT / "data" / "raw" / "extended_wave2_manifest.csv"
RAW_W2_DIR = PROJECT_ROOT / "data" / "raw" / "extended_wave2"
V2_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "legal_documents_v2.jsonl"
WAVE2_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "extended_wave2_documents.jsonl"
V3_PROCESSED_JSONL = PROJECT_ROOT / "data" / "processed" / "legal_documents_v3.jsonl"

DOC_FILE_MAP = {
    "VBHN_58_2025": RAW_W2_DIR / "social_insurance" / "01_58_VBHN_VPQH_2025_Bao_Hiem_Xa_Hoi.txt",
    "ND_158_2025": RAW_W2_DIR / "social_insurance" / "02_158_2025_ND_CP_BHXH_Bat_Buoc.txt",
    "ND_159_2025": RAW_W2_DIR / "social_insurance" / "03_159_2025_ND_CP_BHXH_Tu_Nguyen.txt",
    "TT_12_2025": RAW_W2_DIR / "social_insurance" / "04_12_2025_TT_BNV_Huong_Dan_BHXH.txt",
    "ND_176_2025": RAW_W2_DIR / "social_insurance" / "05_176_2025_ND_CP_Tro_Cap_Huu_Tri_Xa_Hoi.txt",
    "L_84_2015": RAW_W2_DIR / "occupational_safety" / "06_84_2015_QH13_An_Toan_Ve_Sinh_Lao_Dong.txt",
    "ND_39_2016": RAW_W2_DIR / "occupational_safety" / "07_39_2016_ND_CP_Thi_Hanh_Luat_ATVSLD.txt",
    "VBHN_04_BNV_2026": RAW_W2_DIR / "occupational_safety" / "08_04_VBHN_BNV_2026_Bao_Hiem_TNLD_BNN.txt",
    "VBHN_05_BNV_2026": RAW_W2_DIR / "occupational_safety" / "09_05_VBHN_BNV_2026_Muc_Dong_Quy_TNLD_BNN.txt",
    "VBHN_06_BNV_2026": RAW_W2_DIR / "occupational_safety" / "10_06_VBHN_BNV_2026_Che_Do_TNLD_BNN.txt",
}


def load_wave2_manifest() -> List[dict[str, Any]]:
    if not WAVE2_MANIFEST.exists():
        raise FileNotFoundError(f"Wave 2 manifest missing: {WAVE2_MANIFEST}")
    with open(WAVE2_MANIFEST, "r", encoding="utf-8-sig") as f:
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
        "scope_tier": meta_row.get("scope_tier", "extended_wave2"),
        "domain": meta_row.get("domain", "UNKNOWN"),
        "status": meta_row.get("status", "CURRENT"),
        "amends": meta_row.get("amends"),
        "amended_by": meta_row.get("amended_by"),
        "replaces": meta_row.get("replaces"),
        "replaced_by": meta_row.get("replaced_by"),
        "source_role": meta_row.get("source_role", full_meta.get("source_role", "FRAMEWORK_LAW")),
        "official_source": meta_row.get("official_url"),
    })

    parser = LegalParser(doc_metadata=full_meta)
    chunks = parser.parse_pages([page_text])
    logger.info(f"Parsed {doc_id}: {len(chunks)} chunks produced.")
    return chunks


def main():
    logger.info("=== STARTING PHASE 5H WAVE 2 INGESTION PIPELINE ===")
    manifest_rows = load_wave2_manifest()
    cleaner = TextCleaner()

    all_wave2_chunks: List[LegalChunk] = []

    for row in manifest_rows:
        doc_id = row["doc_id"]
        logger.info(f"Processing Wave 2 document: {doc_id} ({row['title']})...")
        chunks = ingest_document(row, cleaner)
        all_wave2_chunks.extend(chunks)

    # 1. Write extended_wave2_documents.jsonl
    logger.info(f"Writing {len(all_wave2_chunks)} chunks to {WAVE2_PROCESSED_JSONL}...")
    with open(WAVE2_PROCESSED_JSONL, "w", encoding="utf-8") as f:
        for chunk in all_wave2_chunks:
            f.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

    # 2. Build combined legal_documents_v3.jsonl (V2 + Wave 2)
    logger.info(f"Merging V2 from {V2_PROCESSED_JSONL} with Wave 2 into {V3_PROCESSED_JSONL}...")
    v2_count = 0
    with open(V3_PROCESSED_JSONL, "w", encoding="utf-8") as f_out:
        if V2_PROCESSED_JSONL.exists():
            with open(V2_PROCESSED_JSONL, "r", encoding="utf-8") as f_in:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    c = json.loads(line)
                    f_out.write(json.dumps(c, ensure_ascii=False) + "\n")
                    v2_count += 1
        else:
            logger.warning("V2 processed file not found! Generating V3 with Wave 2 only.")

        for chunk in all_wave2_chunks:
            f_out.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")

    logger.info(f"=== INGESTION SUMMARY ===")
    logger.info(f"V2 Chunks: {v2_count}")
    logger.info(f"Wave 2 Chunks: {len(all_wave2_chunks)}")
    logger.info(f"V3 Total Chunks: {v2_count + len(all_wave2_chunks)}")
    logger.info("Done!")


if __name__ == "__main__":
    main()
