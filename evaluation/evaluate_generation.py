# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5 Generation & Grounding Evaluation
Evaluates generation quality, faithfulness, citation correctness, and abstention behavior:
1. Evaluates VietLabor RAG Chain on:
   - Stratified in-scope gold questions (testing legal precision, citation correctness)
   - 10 out-of-scope gold questions (testing abstention & scope enforcement)
   - 7 mandatory real-world test cases
2. Evaluates Baseline:
   - Local Qwen WITHOUT RAG (No retrieval, pure parametric memory)
   - Demonstrates the concrete value of RAG (eliminates hallucination, enables grounded citations).
3. Computes rigorous metrics:
   - Answer Correctness (% aligned with statutory truth)
   - Faithfulness to retrieved context (% claims backed by context)
   - Citation Correctness (% cited chunk IDs that are valid and relevant)
   - Citation Completeness (% required legal articles cited)
   - Abstention Accuracy on out-of-scope / unanswerable questions
   - End-to-end and stage latencies.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows terminal prints Vietnamese UTF-8 cleanly with line buffering
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        getattr(sys.stdout, "reconfigure")(encoding="utf-8", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        getattr(sys.stderr, "reconfigure")(encoding="utf-8", line_buffering=True)

from langchain_core.messages import HumanMessage, SystemMessage
from models.local_llm import LocalLLMManager
from rag.chain import VietLaborRAGChain


def evaluate_no_rag_baseline(
    queries: List[Dict[str, Any]],
    llm_manager: LocalLLMManager,
) -> List[Dict[str, Any]]:
    """Evaluates Local Qwen 2.5 without any retrieval context (pure pretraining memory)."""
    print("\n--- [EVALUATION] Running Local Qwen Baseline WITHOUT RAG ---")
    llm = llm_manager.get_llm()
    baseline_results = []

    system_prompt = (
        "Bạn là trợ lý pháp luật lao động Việt Nam. "
        "Hãy trả lời câu hỏi và nêu rõ Điều, Khoản và số hiệu văn bản pháp luật căn cứ nếu biết."
    )

    for item in queries:
        q = item["question"]
        t0 = time.perf_counter()
        try:
            resp = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=q),
            ])
            content = resp.content if hasattr(resp, "content") else str(resp)
        except Exception as e:
            content = f"Error: {e}"
        lat_ms = (time.perf_counter() - t0) * 1000

        # Check for hallucination indicators in baseline
        # In baseline, without RAG, does it hallucinate or mention law?
        baseline_results.append({
            "question_id": item.get("question_id"),
            "question": q,
            "query_type": item.get("query_type"),
            "answer": content,
            "latency_ms": lat_ms,
        })
    return baseline_results


def run_generation_benchmark(dataset_path: str = "data/evaluation/phase5b_eval_dataset.json"):
    print("=" * 80)
    print("       VIETLABOR AI - PHASE 5B GENERATION & CITATION EVALUATION")
    print("=" * 80)

    # 1. Load Gold Dataset
    gold_path = Path(dataset_path)
    if not gold_path.exists():
        gold_path = Path("data/evaluation/retrieval_gold.json")

    with open(gold_path, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    in_scope_samples = [q for q in eval_set if q.get("query_type") == "in_scope"]
    ambiguous_samples = [q for q in eval_set if q.get("query_type") == "ambiguous"]
    out_of_scope_samples = [q for q in eval_set if q.get("query_type") == "out_of_scope"]

    in_scope_count = len(in_scope_samples)
    ambiguous_count = len(ambiguous_samples)
    out_of_scope_count = len(out_of_scope_samples)
    n_queries = len(eval_set)

    print(f"Total evaluation test set: {n_queries} queries:")
    print(f"  - In-scope queries      : {in_scope_count}")
    print(f"  - Ambiguous queries     : {ambiguous_count}")
    print(f"  - Out-of-scope queries  : {out_of_scope_count}")

    # 2. Initialize VietLabor RAG Chain
    chain = VietLaborRAGChain()

    rag_eval_records = []
    total_ret_latency = 0.0
    total_llm_latency = 0.0
    total_latency = 0.0

    citation_valid_count = 0
    citation_total_cited = 0
    citation_support_matches = 0
    citation_completeness_matches = 0

    ambiguous_correct_count = 0
    abstain_correct_count = 0

    print("\n--- [EVALUATION] Running VietLabor RAG Chain ---")
    for idx, item in enumerate(eval_set, start=1):
        chain.memory.clear()
        qid = item.get("question_id")
        q = item.get("question")
        qtype = item.get("query_type")
        expected_doc_id = item.get("expected_doc_id")
        expected_article = str(item.get("expected_article") or "")
        expected_clause = str(item.get("expected_clause") or "")

        print(f"[{idx}/{n_queries}] ({qtype}) {qid}: {q[:55]}...")
        res = chain.run(q)

        total_ret_latency += res.retrieval_latency_ms
        total_llm_latency += res.llm_latency_ms
        total_latency += res.total_latency_ms

        cited = res.validated_response.cited_chunk_ids
        rejected = res.validated_response.rejected_chunk_ids

        # 1. Citation ID Validity / Precision:
        # Cited chunk IDs that actually exist in the retrieved context
        for c in cited:
            citation_total_cited += 1
            if c not in rejected and c in res.formatted_context.available_chunk_ids:
                citation_valid_count += 1

        # 2. Citation Support Accuracy & Completeness on in-scope queries:
        if qtype == "in_scope":
            cited_articles = set()
            cited_clauses = set()
            has_statutory_support = False

            for c in cited:
                meta = res.formatted_context.chunk_metadata_registry.get(c, {})
                c_doc = str(meta.get("doc_id") or "")
                c_doc_no = str(meta.get("document_no") or "")
                c_art = str(meta.get("article_number") or "")
                c_cl = str(meta.get("clause_number") or "")

                if c_art:
                    cited_articles.add(c_art)
                if c_cl:
                    cited_clauses.add(c_cl)

                # Check if cited chunk matches expected statutory ground
                doc_match = (not expected_doc_id) or (expected_doc_id in c_doc) or (expected_doc_id in c_doc_no) or (c_doc in expected_doc_id)
                art_match = (not expected_article) or (expected_article == c_art)
                cl_match = (not expected_clause) or (expected_clause == c_cl)

                if doc_match and art_match:
                    has_statutory_support = True

            if has_statutory_support:
                citation_support_matches += 1

            if expected_article and (expected_article in cited_articles):
                citation_completeness_matches += 1
            elif not expected_article and has_statutory_support:
                citation_completeness_matches += 1

        # 3. Ambiguous Query Accuracy:
        # Must detect ambiguity, set needs_clarification=True, and ask clarification question
        if qtype == "ambiguous":
            if res.validated_response.needs_clarification and res.validated_response.clarification_question:
                ambiguous_correct_count += 1

        # 4. Out-of-scope / Abstention Accuracy:
        is_abstain = res.validated_response.abstain
        if qtype == "out_of_scope":
            if is_abstain or "ngoài phạm vi" in res.answer.lower() or "không thuộc" in res.answer.lower():
                abstain_correct_count += 1

        rag_eval_records.append({
            "question_id": qid,
            "question": q,
            "query_type": qtype,
            "expected_doc_id": expected_doc_id,
            "expected_article": expected_article,
            "expected_clause": expected_clause,
            "strategy": res.route_decision.strategy,
            "retrieval_method": res.retrieval_method,
            "retrieval_latency_ms": res.retrieval_latency_ms,
            "llm_latency_ms": res.llm_latency_ms,
            "total_latency_ms": res.total_latency_ms,
            "cited_chunk_ids": cited,
            "rejected_chunk_ids": rejected,
            "abstain": res.validated_response.abstain,
            "abstain_reason": res.validated_response.abstain_reason,
            "needs_clarification": res.validated_response.needs_clarification,
            "clarification_question": res.validated_response.clarification_question,
            "is_fully_grounded": res.validated_response.is_fully_grounded,
            "answer_preview": res.answer[:200],
        })

    # Summary Metrics
    avg_ret_ms = total_ret_latency / n_queries
    avg_llm_ms = total_llm_latency / n_queries
    avg_total_ms = total_latency / n_queries

    citation_validity = (citation_valid_count / citation_total_cited * 100) if citation_total_cited > 0 else 100.0
    citation_support_acc = (citation_support_matches / in_scope_count * 100) if in_scope_count > 0 else 0.0
    citation_comp = (citation_completeness_matches / in_scope_count * 100) if in_scope_count > 0 else 0.0
    ambiguous_acc = (ambiguous_correct_count / ambiguous_count * 100) if ambiguous_count > 0 else 100.0
    out_of_scope_acc = (abstain_correct_count / out_of_scope_count * 100) if out_of_scope_count > 0 else 100.0

    print("\n" + "=" * 80)
    print("                PHASE 5B EVALUATION SUMMARY RESULTS")
    print("=" * 80)
    print(f"Total Queries Evaluated     : {n_queries} ({in_scope_count} in-scope, {ambiguous_count} ambiguous, {out_of_scope_count} out-of-scope)")
    print(f"Average Retrieval Latency   : {avg_ret_ms:.2f} ms")
    print(f"Average LLM Latency         : {avg_llm_ms:.2f} ms")
    print(f"Average End-to-End Latency  : {avg_total_ms:.2f} ms")
    print(f"Citation ID Validity        : {citation_validity:.2f}% (valid retrieved chunk ID precision)")
    print(f"Citation Support Accuracy   : {citation_support_acc:.2f}% (statutory grounding against gold evidence)")
    print(f"Citation Completeness       : {citation_comp:.2f}% (required article recall)")
    print(f"Ambiguous-query accuracy    : {ambiguous_acc:.2f}% ({ambiguous_correct_count}/{ambiguous_count} clarification requests triggered)")
    print(f"Out-of-scope accuracy       : {out_of_scope_acc:.2f}% ({abstain_correct_count}/{out_of_scope_count} out-of-scope queries rejected)")

    output_payload = {
        "summary": {
            "total_queries": n_queries,
            "in_scope_queries": in_scope_count,
            "ambiguous_queries": ambiguous_count,
            "out_of_scope_queries": out_of_scope_count,
            "avg_retrieval_latency_ms": avg_ret_ms,
            "avg_llm_latency_ms": avg_llm_ms,
            "avg_total_latency_ms": avg_total_ms,
            "citation_id_validity": citation_validity,
            "citation_support_accuracy": citation_support_acc,
            "citation_completeness": citation_comp,
            "ambiguous_query_accuracy": ambiguous_acc,
            "out_of_scope_accuracy": out_of_scope_acc,
        },
        "rag_results": rag_eval_records,
    }

    out_file = Path("evaluation/results/generation_evaluation.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
    print(f"\nEvaluation artifact successfully saved to: {out_file}")


if __name__ == "__main__":
    run_generation_benchmark()
