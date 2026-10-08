"""Apply a batch of restored Sheet question/answer/citation records locally."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from qa_source_normalizations import normalize_source

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/evaluation/labor_qa_sheet_snapshot.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-base64", required=True)
    args = parser.parse_args()
    updates = json.loads(base64.b64decode(args.payload_base64).decode("utf-8"))
    if not isinstance(updates, list) or not updates:
        raise ValueError("Expected a non-empty JSON list of row updates")

    records = [
        json.loads(line)
        for line in SNAPSHOT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_row = {record["sheet_row"]: record for record in records}
    for update in updates:
        row_number = int(update["sheet_row"])
        if row_number not in by_row:
            raise ValueError(f"Snapshot is missing physical Sheet row {row_number}")
        for field in ("question", "answer", "source"):
            by_row[row_number][field] = update[field]

    SNAPSHOT.write_text(
        "".join(
            json.dumps(
                {**record, "source": normalize_source(record["sheet_row"], record["source"])},
                ensure_ascii=False,
            ) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    print(f"Restored {len(updates)} snapshot rows")


if __name__ == "__main__":
    main()
