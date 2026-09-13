# -*- coding: utf-8 -*-
"""
VietLabor AI - Vietnamese Tokenizer Benchmark for BM25
Compares Segmented Tokenization (PyVi + legal entities) vs
Whitespace Tokenization (Normalized regex + legal entities).
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import time

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from evaluation.evaluate_retrieval import evaluate_single_query, aggregate_metrics
from rag.bm25_retriever import BM25Retriever

GOLD_DATASET_PATH = Path("data/evaluation/retrieval_gold.json")
TEMP_WS_BM25 = Path("storage/bm25_whitespace")


def benchmark_tokenizer(mode: str, persist_dir: Path, gold_questions: list[dict]):
    print(f"\n--- Testing BM25 with Tokenizer Mode: {mode.upper()} ---")
    retriever = BM25Retriever(persist_dir=persist_dir, tokenizer_mode=mode)
    t0 = time.time()
    meta = retriever.build_index(force=True)
    build_time = time.time() - t0
    print(f"Index built in {build_time:.2f}s ({meta.get('total_chunks')} chunks).")

    query_results = []
    t_start = time.perf_counter()
    for q in gold_questions:
        res = evaluate_single_query(retriever, q, top_k=10)
        query_results.append(res)
    total_eval_time = time.perf_counter() - t_start

    summary = aggregate_metrics(query_results)
    summary["mode"] = mode
    summary["build_time_s"] = build_time
    summary["eval_time_s"] = total_eval_time
    return summary


def main():
    with open(GOLD_DATASET_PATH, "r", encoding="utf-8") as f:
        gold_questions = json.load(f)

    # 1. Benchmark segmented
    summary_seg = benchmark_tokenizer("segmented", Path("storage/bm25"), gold_questions)

    # 2. Benchmark whitespace
    summary_ws = benchmark_tokenizer("whitespace", TEMP_WS_BM25, gold_questions)

    # Cleanup temp index
    if TEMP_WS_BM25.exists():
        shutil.rmtree(TEMP_WS_BM25, ignore_errors=True)

    print("\n" + "=" * 80)
    print("TOKENIZER BENCHMARK RESULTS (BM25)")
    print("=" * 80)
    print(f"{'Tokenizer':<15} | {'Hit@1':<8} | {'Hit@3':<8} | {'Hit@5':<8} | {'MRR':<8} | {'Recall@5':<9} | {'Build Time'}")
    print("-" * 80)
    for s in [summary_seg, summary_ws]:
        print(
            f"{s['mode'].capitalize():<15} | "
            f"{s['hit@1']*100:>6.2f}% | "
            f"{s['hit@3']*100:>6.2f}% | "
            f"{s['hit@5']*100:>6.2f}% | "
            f"{s['mrr']:>8.4f} | "
            f"{s['recall@5']*100:>7.2f}% | "
            f"{s['build_time_s']:>6.2f}s"
        )
    print("=" * 80 + "\n")

    # Save comparison to file
    out_file = Path("evaluation/results/tokenizer_comparison.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"segmented": summary_seg, "whitespace": summary_ws}, f, ensure_ascii=False, indent=2)
    print(f"Saved tokenizer comparison to {out_file}")


if __name__ == "__main__":
    main()
