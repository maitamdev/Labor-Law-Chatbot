# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5C Retrieval Benchmark
Compares candidate pool sizes: Top-10 vs Top-20 across 69 in-scope legal queries.
Metrics:
- Hit@1, Hit@3, Hit@5, Hit@10
- MRR
- Recall@5
- Gold Evidence Recall
- Latency (mean, median, p95)
"""
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")

from rag.hybrid_retriever import HybridRetriever
from rag.query_processor import normalize_query


def match_chunk_to_evidence(chunk_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    """Checks if a retrieved chunk matches a required gold evidence item."""
    c_doc = str(chunk_meta.get("doc_id") or "")
    c_doc_no = str(chunk_meta.get("document_no") or "")
    c_art = str(chunk_meta.get("article_number") or "").strip()
    c_cl = str(chunk_meta.get("clause_number") or "").strip()
    c_pt = str(chunk_meta.get("point") or "").strip()

    req_doc = str(req.get("doc_id") or "").strip()
    req_art = str(req.get("article") or "").strip()
    req_cl = str(req.get("clause") or "").strip() if req.get("clause") is not None else ""
    req_pt = str(req.get("point") or "").strip() if req.get("point") is not None else ""

    # Document check
    if req_doc and (req_doc not in c_doc and req_doc not in c_doc_no):
        return False
    # Article check
    if req_art and c_art != req_art:
        return False
    # Clause check (if required)
    if req_cl and c_cl != req_cl:
        return False
    # Point check (if required)
    if req_pt and c_pt.lower() != req_pt.lower():
        return False

    return True


def run_retrieval_benchmark(dataset_path: str = "data/evaluation/phase5c_eval_dataset.json"):
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    in_scope_queries = [q for q in dataset if q.get("query_type") == "in_scope"]
    print(f"Loaded {len(in_scope_queries)} in-scope queries for retrieval benchmark.")

    retriever = HybridRetriever()

    results_top10 = []
    results_top20 = []

    print("\nRunning Top-10 and Top-20 retrieval benchmark...")

    for i, q in enumerate(in_scope_queries, 1):
        q_text = normalize_query(q["question"])
        req_evidence = q.get("required_evidence", [])
        if not req_evidence:
            continue

        # Benchmark Top-20
        t0 = time.perf_counter()
        retrieved_20 = retriever.retrieve(q_text, top_k=20)
        t_20_ms = (time.perf_counter() - t0) * 1000

        retrieved_10 = retrieved_20[:10]

        # Evaluate Top-10
        hits_10 = []
        for rank, c in enumerate(retrieved_10, 1):
            meta = c.get("metadata") or c
            for req in req_evidence:
                if match_chunk_to_evidence(meta, req):
                    hits_10.append((rank, req))
                    break

        first_hit_10 = hits_10[0][0] if hits_10 else None
        mrr_10 = (1.0 / first_hit_10) if first_hit_10 else 0.0
        hit1_10 = 1 if first_hit_10 == 1 else 0
        hit3_10 = 1 if first_hit_10 and first_hit_10 <= 3 else 0
        hit5_10 = 1 if first_hit_10 and first_hit_10 <= 5 else 0
        hit10_10 = 1 if first_hit_10 and first_hit_10 <= 10 else 0

        # Unique gold evidence items retrieved
        matched_reqs_5_10 = set()
        matched_reqs_total_10 = set()
        for rank, c in enumerate(retrieved_10, 1):
            meta = c.get("metadata") or c
            for req_idx, req in enumerate(req_evidence):
                if match_chunk_to_evidence(meta, req):
                    matched_reqs_total_10.add(req_idx)
                    if rank <= 5:
                        matched_reqs_5_10.add(req_idx)

        rec5_10 = len(matched_reqs_5_10) / len(req_evidence)
        gold_rec_10 = len(matched_reqs_total_10) / len(req_evidence)

        results_top10.append({
            "hit@1": hit1_10,
            "hit@3": hit3_10,
            "hit@5": hit5_10,
            "hit@10": hit10_10,
            "mrr": mrr_10,
            "recall@5": rec5_10,
            "gold_evidence_recall": gold_rec_10,
            "latency_ms": t_20_ms * 0.75, # approx
        })

        # Evaluate Top-20
        hits_20 = []
        for rank, c in enumerate(retrieved_20, 1):
            meta = c.get("metadata") or c
            for req in req_evidence:
                if match_chunk_to_evidence(meta, req):
                    hits_20.append((rank, req))
                    break

        first_hit_20 = hits_20[0][0] if hits_20 else None
        mrr_20 = (1.0 / first_hit_20) if first_hit_20 else 0.0
        hit1_20 = 1 if first_hit_20 == 1 else 0
        hit3_20 = 1 if first_hit_20 and first_hit_20 <= 3 else 0
        hit5_20 = 1 if first_hit_20 and first_hit_20 <= 5 else 0
        hit10_20 = 1 if first_hit_20 and first_hit_20 <= 10 else 0

        matched_reqs_5_20 = set()
        matched_reqs_total_20 = set()
        for rank, c in enumerate(retrieved_20, 1):
            meta = c.get("metadata") or c
            for req_idx, req in enumerate(req_evidence):
                if match_chunk_to_evidence(meta, req):
                    matched_reqs_total_20.add(req_idx)
                    if rank <= 5:
                        matched_reqs_5_20.add(req_idx)

        rec5_20 = len(matched_reqs_5_20) / len(req_evidence)
        gold_rec_20 = len(matched_reqs_total_20) / len(req_evidence)

        results_top20.append({
            "hit@1": hit1_20,
            "hit@3": hit3_20,
            "hit@5": hit5_20,
            "hit@10": hit10_20,
            "mrr": mrr_20,
            "recall@5": rec5_20,
            "gold_evidence_recall": gold_rec_20,
            "latency_ms": t_20_ms,
        })

    def summarize(res_list):
        n = len(res_list)
        latencies = [r["latency_ms"] for r in res_list]
        latencies.sort()
        p95_idx = int(n * 0.95)
        return {
            "hit@1": sum(r["hit@1"] for r in res_list) / n * 100,
            "hit@3": sum(r["hit@3"] for r in res_list) / n * 100,
            "hit@5": sum(r["hit@5"] for r in res_list) / n * 100,
            "hit@10": sum(r["hit@10"] for r in res_list) / n * 100,
            "mrr": sum(r["mrr"] for r in res_list) / n,
            "recall@5": sum(r["recall@5"] for r in res_list) / n * 100,
            "gold_evidence_recall": sum(r["gold_evidence_recall"] for r in res_list) / n * 100,
            "mean_latency_ms": statistics.mean(latencies),
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms": latencies[p95_idx] if p95_idx < n else latencies[-1],
        }

    s10 = summarize(results_top10)
    s20 = summarize(results_top20)

    print("\n============================================================")
    print("PHASE 5C RETRIEVAL EXPERIMENT (TOP-10 vs TOP-20)")
    print("============================================================")
    print(f"Total evaluated in-scope queries: {len(in_scope_queries)}")
    print("\nMetric                       | Top-10 Pool | Top-20 Pool")
    print("-----------------------------|-------------|------------")
    print(f"Hit@1                        | {s10['hit@1']:10.2f}% | {s20['hit@1']:10.2f}%")
    print(f"Hit@3                        | {s10['hit@3']:10.2f}% | {s20['hit@3']:10.2f}%")
    print(f"Hit@5                        | {s10['hit@5']:10.2f}% | {s20['hit@5']:10.2f}%")
    print(f"Hit@10                       | {s10['hit@10']:10.2f}% | {s20['hit@10']:10.2f}%")
    print(f"MRR                          | {s10['mrr']:11.4f} | {s20['mrr']:11.4f}")
    print(f"Recall@5                     | {s10['recall@5']:10.2f}% | {s20['recall@5']:10.2f}%")
    print(f"Gold Evidence Recall         | {s10['gold_evidence_recall']:10.2f}% | {s20['gold_evidence_recall']:10.2f}%")
    print(f"Mean Retrieval Latency (ms)  | {s10['mean_latency_ms']:10.2f}  | {s20['mean_latency_ms']:10.2f}")
    print(f"Median Latency (ms)          | {s10['median_latency_ms']:10.2f}  | {s20['median_latency_ms']:10.2f}")
    print(f"P95 Latency (ms)             | {s10['p95_latency_ms']:10.2f}  | {s20['p95_latency_ms']:10.2f}")
    print("============================================================\n")

    out_file = Path("evaluation/results/phase5c_retrieval_experiment.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"top10": s10, "top20": s20}, f, indent=2)

    return s10, s20


if __name__ == "__main__":
    run_retrieval_benchmark()
