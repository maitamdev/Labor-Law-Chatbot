# -*- coding: utf-8 -*-
"""
Build national-mode SFT ChatML train/val splits from verified QA bank.

Does NOT merge Can Tho scenario memorization (see rag/anchor_lock_policy.py).
Use outputs with VietLabor_SFT_Qwen25_Colab.ipynb (LoRA on GPU).

Usage:
    python scripts/build_national_sft_train_val.py
    python scripts/build_national_sft_train_val.py --val-ratio 0.1 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

QA_BANK = PROJECT_ROOT / "data" / "evaluation" / "labor_qa_corrected.jsonl"
OUT_DIR = PROJECT_ROOT / "data" / "training"
FULL_CHATML = OUT_DIR / "vietlabor_sft_national_chatml.jsonl"
TRAIN_FILE = OUT_DIR / "vietlabor_sft_national_train.jsonl"
VAL_FILE = OUT_DIR / "vietlabor_sft_national_val.jsonl"
MANIFEST = OUT_DIR / "national_sft_manifest.json"

SYSTEM_PROMPT = (
    "Bạn là VietLabor AI — trợ lý tra cứu pháp luật lao động Việt Nam. "
    "Trả lời ngắn gọn, khách quan; mỗi kết luận phải gắn căn cứ (Điều/Khoản/Nghị định/Thông tư). "
    "Ưu tiên văn bản còn hiệu lực (ví dụ Nghị định 283/2026/NĐ-CP cho xử phạt hành chính lao động, "
    "thay cho Nghị định 12/2022 đã thay thế). Không bịa số tiền, thời hạn hoặc điều luật."
)


def _record(row: dict, idx: int) -> dict:
    question = (row.get("question") or "").strip()
    answer = (row.get("answer") or "").strip()
    source = (row.get("source") or "").strip()
    body = answer
    if source and "Căn cứ pháp lý" not in body and "căn cứ pháp lý" not in body:
        body += f"\n\n**Căn cứ pháp lý:**\n{source}"
    return {
        "id": f"national_qa_{row.get('sheet_row', idx)}",
        "source": "labor_qa_corrected",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": body},
        ],
        "metadata": {"sheet_row": row.get("sheet_row"), "split": None},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-val", type=int, default=80)
    args = parser.parse_args()

    if not QA_BANK.is_file():
        raise FileNotFoundError(QA_BANK)

    rows = []
    with QA_BANK.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    records = [_record(r, i) for i, r in enumerate(rows, 1)]
    rng = random.Random(args.seed)
    rng.shuffle(records)

    n_val = max(args.min_val, int(len(records) * args.val_ratio))
    n_val = min(n_val, len(records) // 5)
    val_set = records[:n_val]
    train_set = records[n_val:]

    for rec in train_set:
        rec["metadata"]["split"] = "train"
    for rec in val_set:
        rec["metadata"]["split"] = "val"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_lines = train_set + val_set
    with FULL_CHATML.open("w", encoding="utf-8") as f:
        for rec in all_lines:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with TRAIN_FILE.open("w", encoding="utf-8") as f:
        for rec in train_set:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with VAL_FILE.open("w", encoding="utf-8") as f:
        for rec in val_set:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "qa_bank": str(QA_BANK),
        "total": len(records),
        "train": len(train_set),
        "val": len(val_set),
        "seed": args.seed,
        "files": {
            "full": str(FULL_CHATML),
            "train": str(TRAIN_FILE),
            "val": str(VAL_FILE),
        },
        "note": "Do not add Can Tho 106 verbatim pairs to this mix for national deployment.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"National SFT: train={len(train_set)} val={len(val_set)} total={len(records)}")
    print(f"  {TRAIN_FILE}")
    print(f"  {VAL_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
