"""Fast lexical triage: rank answer claims least represented in cited law.

This is only a queue for manual review; inference, arithmetic, negation and
paraphrase can all legitimately have low lexical overlap.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from audit_qa_bank import extract_citation_pairs

ROOT = Path(__file__).resolve().parents[1]
STOP = set("người lao động sử dụng công ty doanh nghiệp trường hợp theo quy định của và hoặc là có được phải không thì trong với từ đến cho trên này đó các một hai ba pháp luật hợp đồng điều khoản điểm thời gian cần nếu việc bên mức về năm tháng ngày hiện tại khi như đã sẽ còn cụ thể".split())


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"\w+", text.lower()) if len(word) >= 3 and word not in STOP}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=40)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (ROOT / "data/evaluation/labor_qa_corrected.jsonl").read_text(encoding="utf-8").splitlines()]
    by_article: dict[tuple[str, str], str] = defaultdict(str)
    for line in (ROOT / "data/processed/legal_documents_v3.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("article_number"):
            by_article[(item["doc_id"], str(item["article_number"]))] += " " + item["content"]
    ranked = []
    for row in rows:
        novel = tokens(row["answer"]) - tokens(row["question"])
        if len(novel) < 4:
            continue
        law_tokens = tokens(" ".join(by_article[ref] for ref in extract_citation_pairs(row["source"])))
        overlap = len(novel & law_tokens) / len(novel)
        ranked.append((overlap, row["sheet_row"], sorted(novel - law_tokens)))
    for score, sheet_row, missing in sorted(ranked)[: args.top]:
        print(f"{sheet_row:4d}  overlap={score:.2f}  answer-only={', '.join(missing[:14])}")


if __name__ == "__main__":
    main()
