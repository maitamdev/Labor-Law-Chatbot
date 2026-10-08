"""Resumable, source-grounded *triage* of the 1,000 QA answers.

This is an AI review queue, not a legal verification certificate. Every FAIL
or UNCLEAR requires human inspection against the cited official source before
editing the Sheet or using an answer as training data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_PATH = ROOT / "data/evaluation/labor_qa_corrected.jsonl"
ANCHOR_PATH = ROOT / "data/processed/qa_question_anchors.jsonl"
CORPUS_PATH = ROOT / "data/processed/legal_documents_v3.jsonl"
OUTPUT_PATH = ROOT / "data/evaluation/labor_qa_semantic_review.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def evidence_for(row: dict, anchors: dict[int, dict], corpus: dict[tuple[str, str], list[dict]]) -> list[dict]:
    query_tokens = words(row["question"] + " " + row["answer"])
    selected: list[dict] = []
    for ref in anchors[row["sheet_row"]]["law_anchors"]:
        chunks = corpus.get((ref["doc_id"], str(ref["article_number"])), [])
        by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
        ranked = sorted(
            chunks,
            key=lambda c: (
                len(words(c.get("content", "")) & query_tokens),
                bool(c.get("clause_number")),
            ),
            reverse=True,
        )
        chosen = ranked[:5]
        article_id = f"{ref['doc_id']}#d{ref['article_number']}"
        if article_id in by_id:
            selected.append(by_id[article_id])
        for chunk in chosen:
            clause = chunk.get("clause_number")
            if clause:
                parent_id = f"{article_id}-k{clause}"
                if parent_id in by_id:
                    selected.append(by_id[parent_id])
            selected.append(chunk)
    seen: set[str] = set()
    unique = []
    for chunk in selected:
        if chunk["chunk_id"] not in seen:
            unique.append(chunk)
            seen.add(chunk["chunk_id"])
    return unique


def review_one(row: dict, evidence: list[dict], model: str, timeout: int) -> dict:
    excerpts = []
    remaining = 9000
    for chunk in evidence:
        if remaining <= 0:
            break
        content = chunk.get("content", "")[: min(remaining, 1200)]
        excerpts.append(f"[{chunk['chunk_id']}] {content}")
        remaining -= len(content)
    prompt = (
        "Bạn là người RÀ SOÁT, không phải người trả lời câu hỏi. Kiểm tra từng khẳng định "
        "pháp lý trong ĐÁP ÁN chỉ dựa trên TRÍCH LUẬT dưới đây. Không dùng trí nhớ ngoài. "
        "Kiểm tra đặc biệt con số, thời hạn, điều kiện, ngoại lệ, hiệu lực, chủ thể và phạm vi. "
        "Nếu trích luật thiếu đoạn cần thiết, ghi UNCLEAR; không đoán. "
        "Chỉ ghi PASS nếu mọi khẳng định quan trọng đều được hỗ trợ. "
        "Chỉ ghi FAIL nếu có mâu thuẫn rõ ràng; trích nguyên văn ngắn và chunk_id. "
        "Trả JSON với khóa verdict (PASS/FAIL/UNCLEAR), reason, disputed_claim, "
        "supporting_chunk_ids (mảng chuỗi), missing_evidence (chuỗi).\n\n"
        f"CÂU HỎI: {row['question']}\nĐÁP ÁN: {row['answer']}\n\n"
        "TRÍCH LUẬT (có thể chưa đầy đủ):\n" + "\n".join(excerpts)
    )
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 360},
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    try:
        assessment = json.loads(result["response"])
    except (json.JSONDecodeError, KeyError):
        assessment = {"verdict": "UNCLEAR", "reason": "Model did not return parseable JSON", "raw_response": result.get("response", "")[:600]}
    if assessment.get("verdict") not in {"PASS", "FAIL", "UNCLEAR"}:
        assessment["verdict"] = "UNCLEAR"
    if assessment["verdict"] == "FAIL" and any(
        phrase in str(assessment.get("reason", "")).lower()
        for phrase in ("thiếu đoạn", "không cung cấp", "thiếu thông tin", "không đủ thông tin")
    ):
        assessment["verdict"] = "UNCLEAR"
    return {
        "sheet_row": row["sheet_row"],
        "review_type": "AI_TRIAGE_NOT_VERIFIED",
        "verdict": assessment["verdict"],
        "assessment": assessment,
        "provided_chunk_ids": [chunk["chunk_id"] for chunk in evidence],
        "model": model,
        "elapsed_seconds": round(result.get("total_duration", 0) / 1e9, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Rows to triage in this run; 0 means all remaining rows (slow)")
    parser.add_argument("--start-row", type=int, default=5)
    parser.add_argument("--rows", help="Comma-separated Sheet row numbers to prioritize")
    parser.add_argument("--rerun", action="store_true", help="Append a fresh assessment even when row has an earlier result")
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    rows = read_jsonl(QA_PATH)
    anchors = {row["sheet_row"]: row for row in read_jsonl(ANCHOR_PATH)}
    corpus: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for chunk in read_jsonl(CORPUS_PATH):
        if chunk.get("article_number"):
            corpus[(chunk["doc_id"], str(chunk["article_number"]))].append(chunk)
    reviewed = {row["sheet_row"] for row in read_jsonl(OUTPUT_PATH)} if OUTPUT_PATH.exists() else set()
    requested = {int(value.strip()) for value in args.rows.split(",")} if args.rows else None
    pending = [
        row for row in rows
        if row["sheet_row"] >= args.start_row
        and (args.rerun or row["sheet_row"] not in reviewed)
        and (requested is None or row["sheet_row"] in requested)
    ]
    if args.limit > 0:
        pending = pending[: args.limit]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("a", encoding="utf-8") as output:
        for idx, row in enumerate(pending, 1):
            try:
                evidence = evidence_for(row, anchors, corpus)
                result = review_one(row, evidence, args.model, args.timeout)
            except Exception as exc:
                result = {"sheet_row": row["sheet_row"], "review_type": "AI_TRIAGE_NOT_VERIFIED", "verdict": "UNCLEAR", "error": str(exc)}
            output.write(json.dumps(result, ensure_ascii=False) + "\n")
            output.flush()
            print(f"[{idx}/{len(pending)}] row {row['sheet_row']}: {result['verdict']} ({result.get('elapsed_seconds', 0)}s)", flush=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
