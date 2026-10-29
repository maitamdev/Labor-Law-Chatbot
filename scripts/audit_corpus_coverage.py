# -*- coding: utf-8 -*-
"""Report corpus coverage vs manifests and retrieval gold."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS = PROJECT_ROOT / "data" / "processed" / "legal_documents_v3.jsonl"
GOLD = PROJECT_ROOT / "data" / "evaluation" / "retrieval_gold.json"


def corpus_doc_ids() -> Counter:
    counts: Counter = Counter()
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            counts[json.loads(line)["doc_id"]] += 1
    return counts


def main() -> int:
    counts = corpus_doc_ids()
    print(f"Corpus: {sum(counts.values())} chunks, {len(counts)} doc_ids")
    manifests = [
        PROJECT_ROOT / "data" / "raw" / "extended" / "extended_manifest.csv",
        PROJECT_ROOT / "data" / "raw" / "extended_wave2_manifest.csv",
        PROJECT_ROOT / "data" / "raw" / "national_labor_wave3_manifest.csv",
    ]
    for mp in manifests:
        if not mp.is_file():
            print(f"\n[SKIP] {mp.name} not found")
            continue
        with mp.open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        ids = {r.get("doc_id") or r.get("id") for r in rows}
        missing = sorted(i for i in ids if i and i not in counts)
        partial = sorted(i for i in ids if i and i in counts)
        print(f"\n{mp.name}: {len(ids)} listed, in corpus {len(partial)}, missing {len(missing)}")
        if missing:
            for mid in missing:
                print(f"  - {mid}")

    if GOLD.is_file():
        data = json.loads(GOLD.read_text(encoding="utf-8"))
        need: set[str] = set()
        for item in data:
            for ev in item.get("expected_evidence", []) or []:
                if isinstance(ev, str) and "#" in ev:
                    need.add(ev.split("#", 1)[0])
        miss = sorted(need - set(counts.keys()))
        print(f"\nretrieval_gold doc_ids: {len(need)}, missing from corpus: {len(miss)}")
        for m in miss[:15]:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
