# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5C Generation & Evidence Support Benchmark
Evaluates:
- Citation ID Validity
- Citation Support Accuracy
- Citation Completeness
- Ambiguous-query Accuracy
- Out-of-scope Accuracy
- Mandatory critical cases A, B, C
- Multi-evidence compound queries
- Telemetry & Latencies
"""
import json
import logging
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8')
sys.path.insert(0, ".")

from rag.chain import VietLaborRAGChain
from rag.output_validator import OutputValidator


def match_chunk_to_evidence(chunk_meta: Dict[str, Any], req: Dict[str, Any]) -> bool:
    """Checks if a chunk metadata matches an expected legal evidence item."""
    c_doc = str(chunk_meta.get("doc_id") or "")
    c_doc_no = str(chunk_meta.get("document_no") or "")
    c_art = str(chunk_meta.get("article_number") or "").strip()
    c_cl = str(chunk_meta.get("clause_number") or "").strip()
    c_pt = str(chunk_meta.get("point") or "").strip()

    req_doc = str(req.get("doc_id") or "").strip()
    req_art = str(req.get("article") or "").strip()
    req_cl = str(req.get("clause") or "").strip() if req.get("clause") is not None else ""
    req_pt = str(req.get("point") or "").strip() if req.get("point") is not None else ""

    # Check doc match
    if req_doc and (req_doc not in c_doc and req_doc not in c_doc_no):
        return False
    # Check article match
    if req_art and c_art != req_art:
        return False
    # Check clause match if specified
    if req_cl and c_cl != req_cl:
        return False
    # Check point match if specified
    if req_pt and c_pt.lower() != req_pt.lower():
        return False

    return True


def run_generation_benchmark(dataset_path: str = "data/evaluation/phase5c_eval_dataset.json"):
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} evaluation items from {dataset_path}.")

    chain = VietLaborRAGChain()

    in_scope_items = [q for q in dataset if q["query_type"] == "in_scope"]
    ambiguous_items = [q for q in dataset if q["query_type"] == "ambiguous"]
    oos_items = [q for q in dataset if q["query_type"] == "out_of_scope"]

    print(f"Dataset breakdown: In-scope = {len(in_scope_items)}, Ambiguous = {len(ambiguous_items)}, Out-of-scope = {len(oos_items)}")

    # 1. Evaluate In-Scope Queries
    in_scope_results = []
    failed_in_scope = []

    retrieval_latencies = []
    llm_latencies = []
    total_latencies = []

    total_valid_citation_ids = 0
    total_cited_ids_count = 0

    total_supported_evidence_items = 0
    total_required_evidence_items = 0

    fully_supported_questions = 0

    print("\n--- Running In-Scope Benchmark ---")
    for i, item in enumerate(in_scope_items, 1):
        qid = item["id"]
        q_text = item["question"]
        req_evidence = item.get("required_evidence", [])

        chain.memory.clear()
        t0 = time.perf_counter()
        res = chain.run(q_text, update_memory=False)
        dur = time.perf_counter() - t0

        retrieval_latencies.append(res.retrieval_latency_ms)
        llm_latencies.append(res.llm_latency_ms)
        total_latencies.append(res.total_latency_ms)

        cited_cids = res.validated_response.cited_chunk_ids
        rejected_cids = res.validated_response.rejected_chunk_ids
        all_emitted_cids = cited_cids + rejected_cids

        # Citation ID Validity:
        # Every cited ID must belong to context registry
        valid_in_context = [cid for cid in cited_cids if cid in res.formatted_context.available_chunk_ids]
        if all_emitted_cids:
            total_valid_citation_ids += len(valid_in_context)
            total_cited_ids_count += len(all_emitted_cids)

        # Multi-evidence support and completeness
        supported_req_indices = set()
        missing_reqs = []

        for req_idx, req in enumerate(req_evidence):
            matched = False
            for cid in cited_cids:
                meta = res.formatted_context.chunk_metadata_registry.get(cid, {})
                if match_chunk_to_evidence(meta, req):
                    matched = True
                    break
            if matched:
                supported_req_indices.add(req_idx)
            else:
                missing_reqs.append(req)

        num_req = len(req_evidence)
        num_supp = len(supported_req_indices)

        total_supported_evidence_items += num_supp
        total_required_evidence_items += num_req

        q_complete = (num_supp == num_req) and (num_req > 0)
        q_supported = (num_supp > 0)

        if q_complete:
            fully_supported_questions += 1

        is_fail = not q_complete

        # Failure diagnosis if failed
        fail_record = None
        if is_fail:
            # Determine failure type
            # Check if gold was retrieved
            gold_in_candidates = any(
                any(match_chunk_to_evidence(c.get("metadata") or c, req) for req in missing_reqs)
                for c in res.retrieved_chunks
            )
            gold_in_context = any(
                any(match_chunk_to_evidence(res.formatted_context.chunk_metadata_registry.get(cid, {}), req) for req in missing_reqs)
                for cid in res.formatted_context.available_chunk_ids
            )

            if not gold_in_candidates:
                failure_type = "RETRIEVAL_MISS"
            elif not gold_in_context:
                failure_type = "CONTEXT_OMISSION"
            elif len(cited_cids) > 0:
                failure_type = "WRONG_CITATION_SELECTION"
            else:
                failure_type = "GENERATION_REASONING"

            fail_record = {
                "question_id": qid,
                "question": q_text,
                "expected_evidence": req_evidence,
                "retrieval_method": res.retrieval_method,
                "retrieved_top_k": [
                    {
                        "rank": r + 1,
                        "chunk_id": c.get("chunk_id"),
                        "doc_id": c.get("metadata", {}).get("doc_id"),
                        "article": c.get("metadata", {}).get("article_number"),
                        "clause": c.get("metadata", {}).get("clause_number"),
                        "point": c.get("metadata", {}).get("point"),
                        "score": c.get("score") or c.get("rrf_score"),
                    }
                    for r, c in enumerate(res.retrieved_chunks[:10])
                ],
                "selected_context": list(res.formatted_context.available_chunk_ids),
                "final_answer": res.answer[:250],
                "cited_chunk_ids": cited_cids,
                "missing_gold_evidence": missing_reqs,
                "failure_type": failure_type,
            }
            failed_in_scope.append(fail_record)

        in_scope_results.append({
            "id": qid,
            "question": q_text,
            "cited_chunk_ids": cited_cids,
            "num_required": num_req,
            "num_supported": num_supp,
            "is_complete": q_complete,
            "is_supported": q_supported,
            "answer_preview": res.answer[:150],
        })

        status_sym = "✅ PASS" if q_complete else "❌ FAIL"
        print(f"[{i:02d}/{len(in_scope_items)}] {status_sym} {qid}: {q_text[:50]}... (Evidence: {num_supp}/{num_req})")

    # 2. Evaluate Ambiguous Queries
    print("\n--- Running Ambiguous Queries Benchmark ---")
    ambiguous_passed = 0
    for i, item in enumerate(ambiguous_items, 1):
        chain.memory.clear()
        res = chain.run(item["question"], update_memory=False)
        passed = (res.validated_response.needs_clarification is True) and (not res.validated_response.abstain)
        if passed:
            ambiguous_passed += 1
        sym = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{i:02d}/{len(ambiguous_items)}] {sym} {item['id']}: {item['question'][:50]} (needs_clarify={res.validated_response.needs_clarification})")

    # 3. Evaluate Out-of-Scope Queries
    print("\n--- Running Out-of-Scope Queries Benchmark ---")
    oos_passed = 0
    for i, item in enumerate(oos_items, 1):
        chain.memory.clear()
        res = chain.run(item["question"], update_memory=False)
        passed = (res.validated_response.abstain is True) and (len(res.validated_response.cited_chunk_ids) == 0)
        if passed:
            oos_passed += 1
        sym = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{i:02d}/{len(oos_items)}] {sym} {item['id']}: {item['question'][:50]} (abstained={res.validated_response.abstain})")

    # Calculate overall metrics
    n_in = len(in_scope_items)
    n_amb = len(ambiguous_items)
    n_oos = len(oos_items)

    citation_id_validity = (total_valid_citation_ids / total_cited_ids_count * 100) if total_cited_ids_count > 0 else 100.0
    citation_support_accuracy = (fully_supported_questions / n_in * 100) if n_in > 0 else 0.0
    citation_completeness = (total_supported_evidence_items / total_required_evidence_items * 100) if total_required_evidence_items > 0 else 0.0

    amb_accuracy = (ambiguous_passed / n_amb * 100) if n_amb > 0 else 0.0
    oos_accuracy = (oos_passed / n_oos * 100) if n_oos > 0 else 0.0

    retrieval_latencies.sort()
    llm_latencies.sort()
    total_latencies.sort()
    p95_idx = int(n_in * 0.95)

    summary = {
        "dataset": {
            "total": len(dataset),
            "in_scope": n_in,
            "ambiguous": n_amb,
            "out_of_scope": n_oos,
        },
        "metrics": {
            "citation_id_validity": {
                "valid": total_valid_citation_ids,
                "total": total_cited_ids_count,
                "percentage": citation_id_validity,
            },
            "citation_support_accuracy": {
                "passed_questions": fully_supported_questions,
                "total_questions": n_in,
                "percentage": citation_support_accuracy,
            },
            "citation_completeness": {
                "supported_evidence_items": total_supported_evidence_items,
                "total_required_evidence_items": total_required_evidence_items,
                "percentage": citation_completeness,
            },
            "ambiguous_accuracy": {
                "passed": ambiguous_passed,
                "total": n_amb,
                "percentage": amb_accuracy,
            },
            "out_of_scope_accuracy": {
                "passed": oos_passed,
                "total": n_oos,
                "percentage": oos_accuracy,
            },
        },
        "latencies": {
            "retrieval": {
                "mean_ms": statistics.mean(retrieval_latencies),
                "median_ms": statistics.median(retrieval_latencies),
                "p95_ms": retrieval_latencies[p95_idx] if p95_idx < n_in else retrieval_latencies[-1],
            },
            "llm": {
                "mean_ms": statistics.mean(llm_latencies),
                "median_ms": statistics.median(llm_latencies),
                "p95_ms": llm_latencies[p95_idx] if p95_idx < n_in else llm_latencies[-1],
            },
            "total": {
                "mean_ms": statistics.mean(total_latencies),
                "median_ms": statistics.median(total_latencies),
                "p95_ms": total_latencies[p95_idx] if p95_idx < n_in else total_latencies[-1],
            },
        },
        "failed_in_scope_queries": failed_in_scope,
    }

    out_file = Path("evaluation/results/phase5c_generation_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n============================================================")
    print("PHASE 5C GENERATION & CITATION BENCHMARK RESULTS")
    print("============================================================")
    print(f"Citation ID Validity       : {total_valid_citation_ids}/{total_cited_ids_count} = {citation_id_validity:.2f}%")
    print(f"Citation Support Accuracy  : {fully_supported_questions}/{n_in} = {citation_support_accuracy:.2f}%")
    print(f"Citation Completeness      : {total_supported_evidence_items}/{total_required_evidence_items} = {citation_completeness:.2f}%")
    print(f"Ambiguous-query Accuracy   : {ambiguous_passed}/{n_amb} = {amb_accuracy:.2f}%")
    print(f"Out-of-scope Accuracy      : {oos_passed}/{n_oos} = {oos_accuracy:.2f}%")
    print("------------------------------------------------------------")
    print(f"Mean Retrieval Latency     : {summary['latencies']['retrieval']['mean_ms']:.2f} ms")
    print(f"Mean LLM Latency           : {summary['latencies']['llm']['mean_ms']:.2f} ms")
    print(f"Mean Total Latency         : {summary['latencies']['total']['mean_ms']:.2f} ms")
    print(f"Failed In-Scope Queries    : {len(failed_in_scope)}")
    print("============================================================\n")

    return summary


if __name__ == "__main__":
    run_generation_benchmark()
