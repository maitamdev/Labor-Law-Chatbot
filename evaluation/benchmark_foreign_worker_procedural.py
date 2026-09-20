# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G.2 Foreign Worker Procedural Benchmark (15 Queries)
Tests retrieval and evidence selection on the complete 18-article NĐ 219/2025/NĐ-CP:
- Work permit dossiers (Điều 11, Điều 13, Điều 15)
- Application procedures & deadlines (Điều 10, Điều 13, Điều 16)
- Re-issuance cases & procedures (Điều 12, Điều 13)
- Extension conditions & procedures (Điều 14, Điều 15, Điều 16)
- Revocation & deportation (Điều 17)
- Demand reporting & exemptions (Điều 4, Điều 5, Điều 6, Điều 7)

Verifies:
1. Procedural questions retrieve NĐ 219 procedural provisions (NOT just broad BLLĐ).
2. Hit@1, Hit@3, Hit@5 and Gold Article Recall.
3. Citation support accuracy.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Dict, List, Set

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from rag.query_router import QueryRouter
from rag.evidence_selector import EvidenceSelector
from rag.hybrid_retriever import HybridRetriever
from rag.legal_issue_parser import LegalIssueParser
from rag.evidence_sufficiency_validator import EvidenceSufficiencyValidator

logging.basicConfig(level=logging.WARNING)


def evaluate_fw_procedural(
    dataset_path: str = "data/evaluation/foreign_worker_procedural_15.json",
    index_version: str = "v2",
) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    retriever = HybridRetriever(index_version=index_version)
    router = QueryRouter()
    selector = EvidenceSelector()
    issue_parser = LegalIssueParser()

    total = len(queries)
    hit1 = 0
    hit3 = 0
    hit5 = 0
    procedural_nd219_count = 0
    recalls = []
    latencies = []
    results = []

    print("=" * 80)
    print(f"RUNNING FOREIGN WORKER PROCEDURAL BENCHMARK ({total} QUERIES)")
    print(f"Index version: {index_version} (testing complete 18-article NĐ 219/2025)")
    print("=" * 80)

    validator = EvidenceSufficiencyValidator()
    sufficient_count = 0
    supported_count = 0

    for idx, item in enumerate(queries, 1):
        qid = item["id"]
        q_type = item.get("type", "exact")
        q_text = item["question"]
        gold_articles = set(str(a) for a in item.get("gold_articles", []))
        gold_chunks = set(item.get("gold_chunks", []))
        is_proc = item.get("is_procedural", True)

        t0 = time.perf_counter()
        route = router.route(q_text)
        parsed_issue = issue_parser.parse(
            query=q_text,
            issue_id=f"ISSUE_{idx}",
            context_facts={},
        )
        parsed_issue.domain = route.domain

        candidates = retriever.retrieve(q_text, top_k=15)
        sel_result = selector.select_evidence(
            issue=parsed_issue,
            candidate_chunks=candidates,
        )

        lat_ms = (time.perf_counter() - t0) * 1000
        latencies.append(lat_ms)

        locked_blocks = sel_result.locked_evidence_blocks
        locked_cids = list(sel_result.selected_chunk_ids)

        retrieved_ids = [c["chunk_id"] for c in candidates[:5]]
        retrieved_arts = [
            str(c.get("metadata", {}).get("article_number") or c.get("article_number") or "").strip()
            for c in candidates[:5]
        ]

        # Top ranks in retrieved
        h1 = (len(retrieved_ids) > 0 and (retrieved_ids[0] in gold_chunks or retrieved_arts[0] in gold_articles)) or \
             any(retrieved_ids[0].startswith(f"ND_219_2025#d{a}") for a in gold_articles)
        h3 = any(cid in gold_chunks or art in gold_articles or any(cid.startswith(f"ND_219_2025#d{a}") for a in gold_articles)
                 for cid, art in zip(retrieved_ids[:3], retrieved_arts[:3]))
        h5 = any(cid in gold_chunks or art in gold_articles or any(cid.startswith(f"ND_219_2025#d{a}") for a in gold_articles)
                 for cid, art in zip(retrieved_ids[:5], retrieved_arts[:5]))

        if h1:
            hit1 += 1
        if h3:
            hit3 += 1
        if h5:
            hit5 += 1

        # Check if procedural question successfully retrieved and locked NĐ 219 provisions
        has_nd219 = any("ND_219" in cid for cid in locked_cids) or any("ND_219" in cid for cid in retrieved_ids[:3])
        if is_proc and has_nd219:
            procedural_nd219_count += 1

        # Evidence Sufficiency Validation
        val_res = validator.validate(
            question=q_text,
            question_specificity=parsed_issue.question_specificity,
            locked_chunks=locked_blocks,
        )
        is_sufficient = val_res.is_legally_sufficient
        if is_sufficient:
            sufficient_count += 1
        if locked_cids:
            supported_count += 1

        # Recall of gold articles
        matched_gold_arts = set()
        for art in retrieved_arts[:5]:
            if art in gold_articles:
                matched_gold_arts.add(art)
        rec = len(matched_gold_arts) / len(gold_articles) if gold_articles else (1.0 if h5 else 0.0)
        recalls.append(rec)

        status_str = "PASS" if is_sufficient else ("WARN" if h5 else "FAIL")
        print(f"[{idx:>2}/{total}] {qid:<12} ({q_type:<15}) | H@1: {int(h1)} H@3: {int(h3)} | NĐ219: {locked_cids} | Sufficiency: {val_res.overall_status} | Status: {status_str}")

        results.append({
            "id": qid,
            "type": q_type,
            "question": q_text,
            "gold_articles": list(gold_articles),
            "hit1": bool(h1),
            "hit3": bool(h3),
            "hit5": bool(h5),
            "retrieved_top5": retrieved_ids[:5],
            "locked_chunk_ids": locked_cids,
            "has_nd219": bool(has_nd219),
            "sufficiency_status": val_res.overall_status,
            "is_legally_sufficient": is_sufficient,
            "latency_ms": lat_ms,
        })

    summary = {
        "total_queries": total,
        "correct_article_top1": round(hit1 / total * 100, 2),
        "correct_article_top3": round(hit3 / total * 100, 2),
        "correct_article_top5": round(hit5 / total * 100, 2),
        "final_citation_sufficiency": round(sufficient_count / total * 100, 2),
        "final_answer_support": round(supported_count / total * 100, 2),
        "procedural_nd219_compliance_rate": round(procedural_nd219_count / total * 100, 2),
        "mean_article_recall": round(statistics.mean(recalls) * 100, 2),
        "mean_latency_ms": round(statistics.mean(latencies), 1),
        "details": results,
    }

    out_file = Path("evaluation/results/foreign_worker_procedural_benchmark_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY:")
    print(f"Correct Article Top-1:                 {summary['correct_article_top1']}%")
    print(f"Correct Article Top-3:                 {summary['correct_article_top3']}%")
    print(f"Correct Article Top-5:                 {summary['correct_article_top5']}%")
    print(f"Final Citation Sufficiency:            {summary['final_citation_sufficiency']}% (Target: >= 90%)")
    print(f"Final Answer Support:                  {summary['final_answer_support']}%")
    print(f"NĐ 219 Procedural Compliance Rate:     {summary['procedural_nd219_compliance_rate']}%")
    print(f"Mean Article Recall:                   {summary['mean_article_recall']}%")
    print(f"Mean Latency:                          {summary['mean_latency_ms']}ms")
    print(f"Saved results to: {out_file}")
    print("=" * 80)
    return summary


if __name__ == "__main__":
    evaluate_fw_procedural()
