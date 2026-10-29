# -*- coding: utf-8 -*-
"""Apply config/metadata_registry.py fields onto every chunk in the production corpus."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.metadata_registry import get_verified_metadata
from config.settings import PRODUCTION_CORPUS_PATH

_STATUS_MAP = {
    "Còn hiệu lực": "CURRENT",
    "Còn hiệu lực một phần": "PARTIALLY_EFFECTIVE",
    "Hết hiệu lực": "REPEALED",
    "CURRENT": "CURRENT",
    "PARTIALLY_EFFECTIVE": "PARTIALLY_EFFECTIVE",
    "REPEALED": "REPEALED",
}


def _apply_registry(chunk: dict) -> dict:
    doc_id = chunk.get("doc_id") or ""
    reg = get_verified_metadata(doc_id)
    if not reg.get("document_no"):
        return chunk
    status_raw = reg.get("status") or chunk.get("status")
    status = _STATUS_MAP.get(str(status_raw), chunk.get("status") or status_raw)
    for key in (
        "document_no",
        "doc_title",
        "document_type",
        "issuer",
        "signer",
        "effective_from",
        "effective_to",
        "official_source",
        "scope_tier",
        "domain",
        "source_role",
        "amends",
        "amended_by",
        "replaces",
        "replaced_by",
    ):
        val = reg.get(key)
        if val is not None:
            chunk[key] = val
    if status:
        chunk["status"] = status
    chunk["metadata_backfill_at"] = datetime.now(timezone.utc).isoformat()
    return chunk


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill corpus chunk metadata from verified registry")
    parser.add_argument("--corpus", type=Path, default=PRODUCTION_CORPUS_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    corpus = args.corpus.resolve()
    lines = [ln for ln in corpus.read_text(encoding="utf-8").splitlines() if ln.strip()]
    updated = 0
    out_rows: list[str] = []
    for line in lines:
        chunk = json.loads(line)
        before = json.dumps(chunk, sort_keys=True, ensure_ascii=False)
        chunk = _apply_registry(chunk)
        after = json.dumps(chunk, sort_keys=True, ensure_ascii=False)
        if before != after:
            updated += 1
        out_rows.append(json.dumps(chunk, ensure_ascii=False))
    print(f"Chunks: {len(out_rows)}, updated from registry: {updated}")
    if not args.dry_run and updated:
        backup = corpus.with_suffix(".before_metadata_backfill.jsonl")
        if not backup.exists():
            backup.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"Backup: {backup}")
        corpus.write_text("\n".join(out_rows) + "\n", encoding="utf-8")
        print(f"Wrote: {corpus}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
