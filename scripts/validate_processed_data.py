from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Ensure UTF-8 output in Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "raw" / "download_manifest.csv"
JSONL_PATH = PROJECT_ROOT / "data" / "processed" / "legal_documents.jsonl"


def validate():
    if not JSONL_PATH.exists():
        print(f"[ERROR] File không tồn tại: {JSONL_PATH}")
        sys.exit(1)

    # 1. Load manifest IDs and core documents
    manifest_doc_ids = set()
    core_manifest_ids = set()
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_id = row["id"]
                manifest_doc_ids.add(doc_id)
                if row.get("category") == "core" and row.get("include_in_rag", "").strip().lower() == "true":
                    core_manifest_ids.add(doc_id)

    # 2. Read and validate JSONL
    total_chunks = 0
    empty_chunks = 0
    duplicate_ids: list[str] = []
    seen_ids = set()
    duplicate_contents: list[str] = []
    seen_contents = set()
    missing_metadata_chunks = 0
    suspicious_chunks: list[dict] = []
    
    docs_processed = set()
    pages_processed: set[tuple[str, int]] = set()
    articles_detected = set()
    clauses_detected = set()
    points_detected = 0

    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total_chunks += 1

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Dòng {line_num} lỗi cú pháp JSON: {e}")
                sys.exit(1)

            chunk_id = data.get("chunk_id", "")
            content = data.get("content", "")
            doc_id = data.get("doc_id", "")
            doc_title = data.get("doc_title", "")
            source_file = data.get("source_file", "")
            p_start = data.get("source_page_start", 0)
            p_end = data.get("source_page_end", 0)

            # Check duplicate ID
            if chunk_id in seen_ids:
                duplicate_ids.append(chunk_id)
            seen_ids.add(chunk_id)

            # Check empty content
            if not content.strip():
                empty_chunks += 1

            # Check duplicate content (within same clause/point)
            art_id = str(data.get("article_number") or "none")
            clause_id = str(data.get("clause_number") or "none")
            point_id = str(data.get("point") or "none")
            content_key = (doc_id, art_id, clause_id, point_id, content.strip())
            if content_key in seen_contents:
                duplicate_contents.append(chunk_id)
            seen_contents.add(content_key)

            # Check required metadata
            if not doc_id or not doc_title or not source_file or not data.get("document_no") or not data.get("issuer") or not data.get("status"):
                missing_metadata_chunks += 1

            # Check doc_id in manifest
            if manifest_doc_ids and doc_id not in manifest_doc_ids:
                suspicious_chunks.append({
                    "chunk_id": chunk_id,
                    "reason": f"doc_id '{doc_id}' không có trong manifest."
                })

            # Check page numbers
            if p_start <= 0 or p_end <= 0 or p_start > p_end:
                suspicious_chunks.append({
                    "chunk_id": chunk_id,
                    "reason": f"Khoảng trang không hợp lệ: {p_start} -> {p_end}"
                })

            # Check length anomalies (allow short legal clauses/points such as 'e) Đình công;' or '4. Sa thải.')
            is_legal_point_or_clause = bool(data.get("point") or data.get("clause_number"))
            min_length = 5 if is_legal_point_or_clause else 15
            if len(content.strip()) < min_length:
                suspicious_chunks.append({
                    "chunk_id": chunk_id,
                    "reason": f"Nội dung quá ngắn ({len(content.strip())} chars): '{content.strip()}'"
                })
            elif len(content.strip()) > 12000:
                suspicious_chunks.append({
                    "chunk_id": chunk_id,
                    "reason": f"Nội dung quá dài ({len(content.strip())} chars)"
                })

            # Track structural stats
            docs_processed.add(doc_id)
            for p in range(p_start, p_end + 1):
                pages_processed.add((doc_id, p))

            art_num = data.get("article_number")
            if art_num:
                articles_detected.add((doc_id, art_num))

            clause_num = data.get("clause_number")
            if art_num and clause_num:
                clauses_detected.add((doc_id, art_num, clause_num))

            if data.get("point"):
                points_detected += 1

    # Check core coverage
    core_processed_count = len(core_manifest_ids.intersection(docs_processed))
    total_core_count = len(core_manifest_ids)

    if core_processed_count < total_core_count:
        rag_readiness = f"NOT READY FOR RAG ({core_processed_count}/{total_core_count} core documents processed, {total_core_count - core_processed_count} pending text recovery)"
        result = "REVIEW (Incomplete Core Corpus)"
    elif empty_chunks > 0 or duplicate_ids or missing_metadata_chunks > 0:
        rag_readiness = "NOT READY FOR RAG (Validation Failed)"
        result = "FAIL"
    elif suspicious_chunks or duplicate_contents:
        rag_readiness = "NOT READY FOR RAG (Suspicious items found)"
        result = "REVIEW"
    else:
        rag_readiness = "READY FOR RAG"
        result = "PASS"

    print("\n==============================")
    print("VIETLABOR INGESTION VALIDATION")
    print("==============================")
    print(f"Core documents total: {total_core_count}")
    print(f"Core docs processed : {core_processed_count} / {total_core_count}")
    print(f"Total pages         : {len(pages_processed)}")
    print(f"Total chunks        : {total_chunks}")
    print(f"Articles detected   : {len(articles_detected)}")
    print(f"Clauses detected    : {len(clauses_detected)}")
    print(f"Points detected     : {points_detected}")
    print()
    print(f"Empty chunks        : {empty_chunks}")
    print(f"Duplicate IDs       : {len(duplicate_ids)}")
    print(f"Duplicate content   : {len(duplicate_contents)}")
    print(f"Missing metadata    : {missing_metadata_chunks}")
    print(f"Suspicious chunks   : {len(suspicious_chunks)}")
    print()
    print(f"Result              : {result}")
    print(f"RAG Readiness       : {rag_readiness}")
    print("==============================\n")

    if suspicious_chunks:
        print("Chi tiết các chunk cần rà soát (tối đa 5):")
        for s in suspicious_chunks[:5]:
            print(f" - [{s['chunk_id']}]: {s['reason']}")
        print()

    return result == "PASS"


if __name__ == "__main__":
    validate()
