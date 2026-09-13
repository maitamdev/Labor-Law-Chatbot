# -*- coding: utf-8 -*-
"""
VietLabor AI - CLI Retrieval Search & Debug Tool
Enables interactive or one-shot querying across BM25, Dense, and Hybrid retrieval.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from rag.bm25_retriever import BM25Retriever
from rag.dense_retriever import DenseRetriever
from rag.hybrid_retriever import HybridRetriever


def display_results(results: list[dict], query: str, method: str):
    print(f"\n{'='*70}")
    print(f"SEARCH RESULTS: [{method.upper()}] (Total: {len(results)})")
    print(f"Query: \"{query}\"")
    print(f"{'='*70}")

    if not results:
        print("No matching chunks retrieved.")
        return

    for rank, r in enumerate(results, start=1):
        meta = r.get("metadata", {})
        doc = meta.get("document_no") or meta.get("doc_id") or "N/A"
        doc_title = meta.get("doc_title") or ""
        art = meta.get("article_number") or ""
        art_title = meta.get("article_title") or ""
        clause = meta.get("clause_number") or ""
        point = meta.get("point") or ""
        score = r.get("score", 0.0)

        art_display = f"Điều {art}" if art else "N/A"
        if art_title:
            art_display += f" ({art_title})"
        clause_display = f"Khoản {clause}" if clause else ""
        if point:
            clause_display += f" Điểm {point}"

        print(f"\n--- Rank {rank} | Score: {score:.4f} ---")
        print(f"Chunk ID : {r.get('chunk_id')}")
        print(f"Văn bản  : {doc} - {doc_title}")
        print(f"Điều     : {art_display}")
        if clause_display:
            print(f"Khoản/Điểm: {clause_display.strip()}")

        if method == "hybrid":
            bm25_r = r.get("bm25_rank")
            dense_r = r.get("dense_rank")
            print(f"Fusion   : BM25 Rank: {bm25_r if bm25_r else 'None'} | Dense Rank: {dense_r if dense_r else 'None'}")

        content = r.get("content", "").strip()
        preview = content[:250] + "..." if len(content) > 250 else content
        preview = "\n  ".join(preview.splitlines())
        print(f"Nội dung :\n  {preview}")

    print(f"\n{'='*70}\n")


def run_search(query: str, method: str, top_k: int):
    method = method.lower()
    if method == "bm25":
        retriever = BM25Retriever()
        results = retriever.retrieve(query, top_k=top_k)
    elif method == "dense":
        retriever = DenseRetriever()
        results = retriever.retrieve(query, top_k=top_k)
    elif method == "hybrid":
        retriever = HybridRetriever()
        results = retriever.retrieve(query, top_k=top_k)
    else:
        raise ValueError(f"Unknown method: {method}. Choose bm25, dense, or hybrid.")

    display_results(results, query, method)


def main():
    parser = argparse.ArgumentParser(description="VietLabor AI Retrieval Search CLI")
    parser.add_argument("--query", "-q", type=str, default="", help="Search query string.")
    parser.add_argument(
        "--method", "-m", choices=["bm25", "dense", "hybrid"], default="hybrid",
        help="Retrieval method (bm25, dense, hybrid). Default: hybrid."
    )
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results to retrieve. Default: 5.")
    args = parser.parse_args()

    if args.query:
        run_search(args.query, args.method, args.top_k)
        return

    print("VietLabor AI Interactive Retrieval CLI")
    print(f"Method: {args.method} | Top-K: {args.top_k}")
    print("Type 'exit' or 'quit' to terminate.\n")

    while True:
        try:
            user_input = input("Nhập câu hỏi tra cứu: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break
            run_search(user_input, args.method, args.top_k)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    main()
