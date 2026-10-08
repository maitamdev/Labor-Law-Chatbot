from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

# Ensure UTF-8 output in Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REPORT_PATH = PROCESSED_DIR / "pdf_audit_report.json"
MANUAL_REVIEW_PATH = PROCESSED_DIR / "manual_review.json"

TEXT_THRESHOLD = 20  # Characters below this are considered empty or metadata-only


def audit_single_pdf(file_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    filename = file_path.name
    doc = fitz.open(file_path)
    total_pages = len(doc)
    
    char_counts: list[int] = []
    empty_pages: list[int] = []
    text_pages: list[int] = []
    suspected_scanned: list[int] = []
    manual_review_items: list[dict[str, Any]] = []

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]
        raw_text = page.get_text("text")
        text = (raw_text if isinstance(raw_text, str) else str(raw_text)).strip()
        num_chars = len(text)
        char_counts.append(num_chars)

        images = page.get_images()

        if num_chars >= TEXT_THRESHOLD:
            text_pages.append(page_num)
        else:
            empty_pages.append(page_num)
            if images:
                suspected_scanned.append(page_num)
                manual_review_items.append({
                    "filename": filename,
                    "file_path": str(file_path.relative_to(PROJECT_ROOT)),
                    "page": page_num,
                    "char_count": num_chars,
                    "has_images": len(images),
                    "reason": "Trang chứa ảnh nhưng không có text layer (nghi ngờ scan)."
                })
            else:
                manual_review_items.append({
                    "filename": filename,
                    "file_path": str(file_path.relative_to(PROJECT_ROOT)),
                    "page": page_num,
                    "char_count": num_chars,
                    "has_images": 0,
                    "reason": "Trang hoàn toàn trống không có text và không có ảnh."
                })

    doc.close()

    total_characters = sum(char_counts)
    pages_with_text = len(text_pages)
    empty_text_pages = len(empty_pages)
    avg_chars = round(total_characters / total_pages, 2) if total_pages > 0 else 0
    min_chars = min(char_counts) if char_counts else 0
    max_chars = max(char_counts) if char_counts else 0

    # Determine status
    if pages_with_text == total_pages and min_chars >= TEXT_THRESHOLD:
        status = "ok"
    elif pages_with_text == 0 or (pages_with_text / total_pages) < 0.3:
        status = "likely_scanned"
    else:
        status = "mixed_or_suspicious"

    audit_entry = {
        "filename": filename,
        "relative_path": str(file_path.relative_to(PROJECT_ROOT)),
        "total_pages": total_pages,
        "pages_with_text": pages_with_text,
        "empty_text_pages": empty_text_pages,
        "total_characters": total_characters,
        "average_characters_per_page": avg_chars,
        "min_chars_page": min_chars,
        "max_chars_page": max_chars,
        "suspected_scanned_pages": len(suspected_scanned),
        "suspected_scanned_page_numbers": suspected_scanned,
        "extraction_status": status,
    }

    return audit_entry, manual_review_items


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    pdf_files = sorted(RAW_DIR.rglob("*.pdf"))
    print(f"=== BẮT ĐẦU AUDIT {len(pdf_files)} FILE PDF TRONG data/raw/ ===")

    all_reports: list[dict[str, Any]] = []
    all_manual_reviews: list[dict[str, Any]] = []

    header = f"{'Filename':<45} | {'Pages':<6} | {'Text':<6} | {'Empty':<6} | {'Avg Chars':<10} | {'Status':<16}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for pdf_path in pdf_files:
        report, reviews = audit_single_pdf(pdf_path)
        all_reports.append(report)
        all_manual_reviews.extend(reviews)
        print(
            f"{report['filename']:<45} | "
            f"{report['total_pages']:<6} | "
            f"{report['pages_with_text']:<6} | "
            f"{report['empty_text_pages']:<6} | "
            f"{report['average_characters_per_page']:<10} | "
            f"{report['extraction_status']:<16}"
        )

    print("-" * len(header))

    # Save reports
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    print(f"[REPORT] Đã lưu báo cáo audit: {REPORT_PATH.relative_to(PROJECT_ROOT)}")

    with open(MANUAL_REVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(all_manual_reviews, f, ensure_ascii=False, indent=2)
    print(f"[REVIEW] Đã lưu danh sách trang scan/trống cần rà soát: {MANUAL_REVIEW_PATH.relative_to(PROJECT_ROOT)} ({len(all_manual_reviews)} trang)")

    # Overall Summary
    total_files = len(all_reports)
    ok_files = sum(1 for r in all_reports if r["extraction_status"] == "ok")
    scanned_files = sum(1 for r in all_reports if r["extraction_status"] == "likely_scanned")
    suspicious_files = sum(1 for r in all_reports if r["extraction_status"] == "mixed_or_suspicious")

    print("\n==============================")
    print("TỔNG KẾT AUDIT PDF")
    print("==============================")
    print(f"Tổng số PDF kiểm tra        : {total_files}")
    print(f"PDF có text layer chuẩn (ok) : {ok_files}")
    print(f"PDF nghi ngờ scan/ít text   : {scanned_files}")
    print(f"PDF hỗn hợp (suspicious)    : {suspicious_files}")
    print(f"Tổng trang cần manual review : {len(all_manual_reviews)}")
    print("==============================\n")


if __name__ == "__main__":
    main()
