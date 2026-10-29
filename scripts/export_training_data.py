# -*- coding: utf-8 -*-
"""
VietLabor AI - Export 1,000 QA Dataset for LLM Fine-Tuning (SFT)
Converts data/evaluation/labor_qa_corrected.jsonl (from Google Sheet)
into standard ChatML (OpenAI/Qwen) and Alpaca instruction tuning formats.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data/evaluation/labor_qa_corrected.jsonl"
OUTPUT_DIR = ROOT / "data/training"
CHATML_FILE = OUTPUT_DIR / "vietlabor_sft_1000_chatml.jsonl"
ALPACA_FILE = OUTPUT_DIR / "vietlabor_sft_1000_alpaca.json"

SYSTEM_PROMPT = (
    "Bạn là VietLabor AI — trợ lý tra cứu pháp luật lao động Việt Nam. "
    "Trả lời chính xác, mạch lạc; viện dẫn Điều/Khoản/Nghị định/Thông tư cụ thể. "
    "Xử phạt hành chính lao động: ưu tiên Nghị định 283/2026/NĐ-CP khi còn hiệu lực."
)


def export_sft_datasets():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    records = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} verified QA pairs from {INPUT_FILE.name}")

    # 1. Export ChatML format (for Qwen 2.5 / Unsloth / HuggingFace)
    chatml_count = 0
    with open(CHATML_FILE, "w", encoding="utf-8") as f_out:
        for r in records:
            question = r.get("question", "").strip()
            answer = r.get("answer", "").strip()
            source = r.get("source", "").strip()

            full_answer = answer
            if source and "Căn cứ pháp lý:" not in full_answer:
                full_answer += f"\n\n**Căn cứ pháp lý:**\n{source}"

            payload = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": full_answer},
                ]
            }
            f_out.write(json.dumps(payload, ensure_ascii=False) + "\n")
            chatml_count += 1

        thainguyen_file = OUTPUT_DIR / "vietlabor_thainguyen_situations_chatml.jsonl"
        if thainguyen_file.is_file():
            for line in thainguyen_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    f_out.write(line.strip() + "\n")
                    chatml_count += 1

    print(f"Exported {chatml_count} records to ChatML format: {CHATML_FILE}")


    # 2. Export Alpaca format (for Llama-Factory / Axolotl)
    alpaca_records = []
    for r in records:
        question = r.get("question", "").strip()
        answer = r.get("answer", "").strip()
        source = r.get("source", "").strip()
        full_answer = answer
        if source and "Căn cứ pháp lý:" not in full_answer:
            full_answer += f"\n\n**Căn cứ pháp lý:**\n{source}"

        alpaca_records.append({
            "instruction": question,
            "input": "",
            "output": full_answer,
            "system": SYSTEM_PROMPT,
        })

    with open(ALPACA_FILE, "w", encoding="utf-8") as f_out:
        json.dump(alpaca_records, f_out, ensure_ascii=False, indent=2)

    print(f"Exported {len(alpaca_records)} records to Alpaca format: {ALPACA_FILE}")


if __name__ == "__main__":
    export_sft_datasets()
