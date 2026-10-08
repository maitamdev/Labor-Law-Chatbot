"""Refresh the TT 12/2025 source and only its generated corpus chunks.

Source: the full-text publication on the Government's policy portal. This is a
targeted refresh so unrelated Wave 2 documents and the V2 corpus stay untouched.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://xaydungchinhsach.chinhphu.vn/"
    "toan-van-thong-tu-12-2025-tt-bnv-quy-dinh-chi-tiet-mot-so-dieu-cua-luat-bhxh-"
    "ve-bhxh-bat-buoc-11925070415595016.htm"
)
DOC_ID = "TT_12_2025"
RAW_TEXT = (
    ROOT / "data" / "raw" / "extended_wave2" / "social_insurance"
    / "04_12_2025_TT_BNV_Huong_Dan_BHXH.txt"
)
MANIFEST = ROOT / "data" / "raw" / "extended_wave2_manifest.csv"
WAVE2_CORPUS = ROOT / "data" / "processed" / "extended_wave2_documents.jsonl"
V3_CORPUS = ROOT / "data" / "processed" / "legal_documents_v3.jsonl"


def extract_official_text(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.detail-content") or soup.select_one("div.detail-cmain")
    if container is None:
        raise RuntimeError("Could not find the Government article body (detail-content).")

    block_names = {"p", "h1", "h2", "h3", "h4", "li", "tr"}
    lines: list[str] = []
    for node in container.find_all(list(block_names)):
        if node.find_parent(list(block_names)):
            continue
        if node.name == "tr":
            cells = node.find_all(["th", "td"], recursive=False)
            raw = " | ".join(cell.get_text("", strip=False) for cell in cells)
        else:
            raw = node.get_text("", strip=False)
        text = raw.replace("\u200e", "").replace("\u200f", "").replace("\xa0", " ")
        text = re.sub(r"[\t\r\n\u200b]+", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = re.sub(
            r"^(Chương\s+[IVXLCDM]+)(?=[A-ZĂÂĐÊÔƠƯ])",
            r"\1 ",
            text,
            flags=re.IGNORECASE,
        )
        if text and not re.fullmatch(r"[-_\s]{8,}", text):
            lines.append(text)

    body = "\n".join(lines)
    required = (
        "12/2025/TT-BNV",
        "Căn cứ Luật Bảo hiểm xã hội ngày 29 tháng 6 năm 2024",
        "Điều 1.",
        "Điều 21.",
    )
    missing = [marker for marker in required if marker not in body]
    if missing:
        raise RuntimeError(f"Official source text is incomplete; missing: {missing}")
    if "ngày 20 tháng 11 năm 2014" in body:
        raise RuntimeError("Extracted text contains the incorrect 2014-law preamble.")
    return body + "\n"


def atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        Path(temp_name).replace(path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def replace_document_chunks(path: Path, new_chunks: list[dict[str, Any]]) -> None:
    old_records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    retained = [record for record in old_records if record.get("doc_id") != DOC_ID]
    atomic_write_jsonl(path, retained + new_chunks)


def update_manifest(source_text: str, article_numbers: set[str]) -> None:
    rows: list[dict[str, str]] = []
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError("Wave 2 manifest has no header.")

    matching = [row for row in rows if row.get("doc_id") == DOC_ID]
    if len(matching) != 1:
        raise RuntimeError(f"Expected one {DOC_ID} manifest row, got {len(matching)}.")
    numbers = sorted(int(number) for number in article_numbers)
    matching[0].update({
        "official_url": SOURCE_URL,
        "download_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "official_total_articles": str(len(numbers)),
        "ingested_articles": str(len(numbers)),
        "first_ingested_article": str(numbers[0]),
        "last_ingested_article": str(numbers[-1]),
        "specific_article_ranges": f"Điều {numbers[0]}-{numbers[-1]} ({len(numbers)} điều)",
        "corpus_scope": "FULL_TEXT",
    })

    fd, temp_name = tempfile.mkstemp(prefix=f".{MANIFEST.name}.", suffix=".tmp", dir=MANIFEST.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        Path(temp_name).replace(MANIFEST)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> None:
    response = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "VietLabor-AI legal corpus refresh/1.0"},
        timeout=45,
    )
    response.raise_for_status()
    source_text = extract_official_text(response.content)

    # Save the verbatim-derived text before parsing; later preparation runs read
    # this same file instead of regenerating the former six-article summary.
    RAW_TEXT.parent.mkdir(parents=True, exist_ok=True)
    RAW_TEXT.write_text(source_text, encoding="utf-8", newline="\n")

    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from config.metadata_registry import get_verified_metadata
    from ingestion.cleaner import TextCleaner
    from ingestion.parser import LegalParser
    from ingestion.schemas import PageText

    metadata = get_verified_metadata(DOC_ID)
    metadata.update({
        "doc_id": DOC_ID,
        "filename": RAW_TEXT.name,
        "extraction_method": "official_government_html",
        "official_source": SOURCE_URL,
        "text_source_url": SOURCE_URL,
        "scope_tier": "extended_wave2",
        "domain": "SOCIAL_INSURANCE",
        "status": "CURRENT",
    })
    clean_text = TextCleaner().clean_text(source_text)
    page = PageText(doc_id=DOC_ID, filename=RAW_TEXT.name, page_number=1, text=clean_text)
    chunks = [chunk.model_dump() for chunk in LegalParser(doc_metadata=metadata).parse_pages([page])]
    article_numbers = {
        str(chunk["article_number"])
        for chunk in chunks
        if chunk.get("article_number") is not None
    }
    expected_articles = {str(number) for number in range(1, 22)}
    missing_articles = sorted(expected_articles - article_numbers, key=int)
    if missing_articles or article_numbers - expected_articles:
        raise RuntimeError(f"Unexpected TT12 article coverage; missing={missing_articles}, extra={article_numbers - expected_articles}")

    child_sick = next((chunk for chunk in chunks if chunk["chunk_id"] == "TT_12_2025#d5-k3"), None)
    if not child_sick or "từ 2 con trở lên dưới 07 tuổi" not in child_sick["content"]:
        raise RuntimeError("TT12 Article 5 Clause 3 was not parsed from the official source.")

    for path in (WAVE2_CORPUS, V3_CORPUS):
        replace_document_chunks(path, chunks)
    update_manifest(source_text, article_numbers)

    print(
        f"Refreshed {DOC_ID} from Government source: {len(chunks)} chunks, "
        f"Articles 1-21; Art. 5(3) present. Replaced only TT12 rows in both corpora."
    )


if __name__ == "__main__":
    main()
