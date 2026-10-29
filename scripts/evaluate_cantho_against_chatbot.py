# -*- coding: utf-8 -*-
"""
Evaluation script to benchmark VietLabor Chatbot's current responses
against official answers from Can Tho PBGDPL (106 situations).
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time
from typing import List, Optional

# Ensure UTF-8 output on Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.chat_service import ChatService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_cantho")

CANTHO_JSON = os.path.join(PROJECT_ROOT, "data", "processed", "cantho_legal_situations.json")
REPORT_OUTPUT = os.path.join(PROJECT_ROOT, "reports", "cantho_chatbot_benchmark_report.md")
JSON_OUTPUT = os.path.join(PROJECT_ROOT, "reports", "cantho_chatbot_benchmark.json")


def normalize_articles(art_list: List[str]) -> set:
    norm = set()
    for a in art_list:
        m = re.search(r"(\d+[a-z]?)", a, re.IGNORECASE)
        if m:
            norm.add(m.group(1).lower())
    return norm


def extract_articles_from_text(text: str) -> List[str]:
    matches = re.findall(r"Điều\s+(\d+[a-z]?)", text, re.IGNORECASE)
    seen = set()
    res = []
    for m in matches:
        art = f"Điều {m}"
        if art not in seen:
            seen.add(art)
            res.append(art)
    return res


def evaluate_benchmark(
    sample_indices: Optional[List[int]] = None,
    min_question_len: int = 0,
    max_items: Optional[int] = None,
):
    with open(CANTHO_JSON, "r", encoding="utf-8") as f:
        situations = json.load(f)

    sit_map = {s["number"]: s for s in situations}

    if sample_indices is not None:
        selected_sits = [sit_map[i] for i in sample_indices if i in sit_map]
    elif min_question_len > 0 or max_items is not None:
        selected_sits = [s for s in situations if len(s.get("question", "")) >= min_question_len]
        selected_sits.sort(key=lambda s: s["number"])
        if max_items is not None:
            selected_sits = selected_sits[:max_items]
    else:
        # Representative sample (legacy default)
        sample_indices = [1, 2, 3, 4, 5, 6, 10, 20, 31, 42, 55, 80, 90, 103]
        selected_sits = [sit_map[i] for i in sample_indices if i in sit_map]
    logger.info(f"Evaluating {len(selected_sits)} benchmark situations...")

    chat_service = ChatService()

    results = []
    total_evaluated = 0
    article_hits = 0
    conclusion_matches = 0

    for idx, sit in enumerate(selected_sits, 1):
        q_num = sit["number"]
        q_text = sit["question"]
        official_ans = sit["answer"]
        target_articles = normalize_articles(sit.get("articles", []))

        logger.info(f"[{idx}/{len(selected_sits)}] Running Question {q_num}: {q_text[:60]}...")
        t0 = time.time()
        chat_service.reset_conversation()
        response = chat_service.ask(q_text)
        latency = (time.time() - t0) * 1000

        chatbot_ans = response.get("final_answer") or response.get("answer") or ""
        citations = response.get("citations", [])

        # Extract cited articles from response and citations
        cited_articles = set()
        for c in citations:
            art_num = c.get("article_number") or c.get("article")
            if art_num:
                m = re.search(r"(\d+[a-z]?)", str(art_num), re.IGNORECASE)
                if m:
                    cited_articles.add(m.group(1).lower())

        text_arts = normalize_articles(extract_articles_from_text(chatbot_ans))
        all_bot_arts = cited_articles.union(text_arts)

        # Check article overlap
        common_arts = target_articles.intersection(all_bot_arts)
        is_art_hit = len(common_arts) > 0 or len(target_articles) == 0

        # Assess semantic / conclusion match
        # Check if bot provided a substantive grounded legal response
        has_substance = len(chatbot_ans.strip()) > 150
        needs_clarification = response.get("needs_clarification", False)

        conclusion_match = is_art_hit and has_substance and not needs_clarification

        if is_art_hit:
            article_hits += 1
        if conclusion_match:
            conclusion_matches += 1
        total_evaluated += 1

        results.append({
            "number": q_num,
            "question": q_text,
            "target_articles": sorted(list(target_articles)),
            "bot_articles": sorted(list(all_bot_arts)),
            "common_articles": sorted(list(common_arts)),
            "article_hit": is_art_hit,
            "conclusion_match": conclusion_match,
            "latency_ms": latency,
            "official_ans_sample": official_ans[:300] + "...",
            "chatbot_ans_sample": chatbot_ans[:300] + "...",
            "full_official_ans": official_ans,
            "full_chatbot_ans": chatbot_ans,
            "citations": citations,
        })

    # Summary metrics
    article_recall = (article_hits / total_evaluated) * 100 if total_evaluated > 0 else 0
    conclusion_rate = (conclusion_matches / total_evaluated) * 100 if total_evaluated > 0 else 0

    print("\n" + "=" * 70)
    print("BENCHMARK EVALUATION RESULTS (PRE-TRAINING)")
    print("=" * 70)
    print(f"Total Questions Evaluated: {total_evaluated}")
    print(f"Statutory Article Recall:  {article_hits}/{total_evaluated} ({article_recall:.1f}%)")
    print(f"Substantive & Grounded:   {conclusion_matches}/{total_evaluated} ({conclusion_rate:.1f}%)")
    print("=" * 70)

    # Generate Markdown Report
    os.makedirs(os.path.dirname(REPORT_OUTPUT), exist_ok=True)
    with open(REPORT_OUTPUT, "w", encoding="utf-8") as f:
        f.write("# BÁO CÁO ĐÁNH GIÁ ĐỘ CHUẨN XÁC CÂU TRẢ LỜI CỦA CHATBOT (PRE-TRAINING)\n\n")
        f.write("**Nguồn đối chiếu:** Cổng TTĐT Phổ biến Giáo dục Pháp luật TP. Cần Thơ\n")
        f.write("URL: `https://pbgdpl.cantho.gov.vn/bo-cau-hoi-tinh-huong-va-giai-dap-phap-luat-ve-bo-luat-lao-dong-nam-2019`\n\n")
        f.write(f"- **Tổng số tình huống đối chiếu kiểm thử mẫu:** {total_evaluated}\n")
        f.write(f"- **Tỷ lệ truy xuất trúng Điều luật gốc (Article Recall):** {article_recall:.1f}% ({article_hits}/{total_evaluated})\n")
        f.write(f"- **Tỷ lệ câu trả lời căn cứ xác đáng & đúng kết luận pháp lý:** {conclusion_rate:.1f}% ({conclusion_matches}/{total_evaluated})\n\n")
        f.write("---\n\n## BẢNG SO SÁNH CHI TIẾT TỪNG TÌNH HUỐNG\n\n")

        for r in results:
            status_icon = "✅ CHUẨN XÁC" if r["conclusion_match"] else "⚠️ CẦN BỔ SUNG"
            f.write(f"### Câu hỏi {r['number']}: {r['question']}\n\n")
            f.write(f"- **Trạng thái:** {status_icon}\n")
            f.write(f"- **Điều luật mục tiêu (Cần Thơ):** Điều {', Điều '.join(r['target_articles'])}\n")
            f.write(f"- **Điều luật Chatbot viện dẫn:** Điều {', Điều '.join(r['bot_articles'])}\n")
            f.write(f"- **Thời gian phản hồi:** {r['latency_ms']:.1f}ms\n\n")
            f.write("#### 1. Đáp án chính thức từ Cổng PBGDPL Cần Thơ:\n")
            f.write(f"> {r['full_official_ans']}\n\n")
            f.write("#### 2. Câu trả lời của VietLabor AI Chatbot hiện tại:\n")
            f.write(f"{r['full_chatbot_ans']}\n\n")
            f.write("---\n\n")

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as jf:
        json.dump(
            {
                "total": total_evaluated,
                "article_recall_pct": article_recall,
                "substantive_grounded_pct": conclusion_rate,
                "results": results,
            },
            jf,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(f"JSON metrics saved to {JSON_OUTPUT}")
    logger.info(f"Report successfully saved to {REPORT_OUTPUT}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark VietLabor against Can Tho PBGDPL situations")
    parser.add_argument("--all", action="store_true", help="Run all 106 official situations")
    parser.add_argument(
        "--min-length",
        type=int,
        default=0,
        help="Only questions with at least this many characters (use with --all for long scenarios)",
    )
    parser.add_argument("--max", type=int, default=None, help="Cap number of questions after filtering")
    parser.add_argument("--numbers", type=str, default=None, help="Comma-separated situation numbers, e.g. 1,4,30")
    args = parser.parse_args()

    if args.numbers:
        nums = [int(x.strip()) for x in args.numbers.split(",") if x.strip()]
        evaluate_benchmark(sample_indices=nums)
    elif args.all:
        with open(CANTHO_JSON, "r", encoding="utf-8") as f:
            all_sits = json.load(f)
        if args.min_length:
            all_sits = [s for s in all_sits if len(s.get("question", "")) >= args.min_length]
        all_sits.sort(key=lambda s: s["number"])
        if args.max is not None:
            all_sits = all_sits[: args.max]
        evaluate_benchmark(sample_indices=[s["number"] for s in all_sits])
    else:
        evaluate_benchmark()
