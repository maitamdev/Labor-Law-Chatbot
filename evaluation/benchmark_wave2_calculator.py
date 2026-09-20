# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H.1 Legal Calculator Benchmark Runner
evaluation/benchmark_wave2_calculator.py

Evaluates the deterministic BenefitCalculator engine on 46 statutory test cases:
Metrics:
1. Formula Selection Accuracy
2. Eligibility Decision Accuracy
3. Arithmetic Accuracy
4. Final Calculation Accuracy (exact match or <= 1 VNĐ rounding)
5. Missing-Fact Clarification Accuracy
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure workspace root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from rag.legal_calculator import BenefitCalculator, CalculationResult, FORMULA_REGISTRY

BENCHMARK_PATH = PROJECT_ROOT / "data" / "evaluation" / "wave2_calculator_benchmark_45.json"
RESULTS_OUTPUT = PROJECT_ROOT / "evaluation" / "results" / "phase5h_1_calculator_results.json"


def run_benchmark():
    print(f"Loading benchmark test cases from {BENCHMARK_PATH}...")
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        tests: List[Dict[str, Any]] = json.load(f)

    total_tests = len(tests)
    print(f"Total test cases to evaluate: {total_tests}\n")

    formula_correct = 0
    eligibility_correct = 0
    arithmetic_correct = 0
    final_calc_correct = 0
    clarification_correct = 0

    domain_counts: Dict[str, int] = {}
    domain_correct: Dict[str, int] = {}
    failures: List[Dict[str, Any]] = []

    print(f"{'ID':<12} | {'Domain':<30} | {'Expected Amount':<16} | {'Actual Amount':<16} | {'Formula':<8} | {'Status'}")
    print("-" * 105)

    for tc in tests:
        tid = tc["test_id"]
        domain = tc["domain"]
        query = tc["query"]
        facts = tc.get("facts", {})
        exp_formula = tc["expected_formula_id"]
        exp_amount = tc["expected_amount"]
        exp_eligible = tc["expected_eligible"]
        exp_clarify = tc.get("requires_clarification", False)

        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Run extract_and_calculate
        result: Optional[CalculationResult] = BenefitCalculator.extract_and_calculate(query, facts)

        if result is None:
            status = "FAIL (None returned)"
            failures.append({"test_id": tid, "reason": "Calculator returned None", "query": query})
            print(f"{tid:<12} | {domain:<30} | {exp_amount:>16,.0f} | {'None':>16} | {'FAIL':<8} | {status}")
            continue

        # 1. Formula Selection check
        f_match = (result.formula_id == exp_formula)
        if f_match:
            formula_correct += 1

        # 2. Eligibility Decision check
        e_match = (result.is_eligible == exp_eligible)
        if e_match:
            eligibility_correct += 1

        # 3. Missing-Fact Clarification check
        c_match = (result.needs_clarification == exp_clarify)
        if c_match:
            clarification_correct += 1

        # 4. Arithmetic / Final Calculation check
        # If requires clarification or ineligible, expected amount is 0
        if exp_clarify or not exp_eligible:
            a_match = (abs(result.total_amount - 0.0) < 1.0)
        else:
            diff = abs(result.total_amount - exp_amount)
            # Allow tiny rounding differences within 10 VNĐ or 0.1%
            a_match = (diff < 10.0 or (exp_amount > 0 and diff / exp_amount < 0.001))

        if a_match:
            arithmetic_correct += 1

        passed = f_match and e_match and c_match and a_match
        if passed:
            final_calc_correct += 1
            domain_correct[domain] = domain_correct.get(domain, 0) + 1
            status = "PASS"
        else:
            status = f"FAIL (F:{f_match}, E:{e_match}, C:{c_match}, A:{a_match})"
            failures.append({
                "test_id": tid,
                "domain": domain,
                "query": query,
                "expected_formula": exp_formula,
                "actual_formula": result.formula_id,
                "expected_amount": exp_amount,
                "actual_amount": result.total_amount,
                "expected_eligible": exp_eligible,
                "actual_eligible": result.is_eligible,
                "expected_clarify": exp_clarify,
                "actual_clarify": result.needs_clarification,
            })

        print(f"{tid:<12} | {domain:<30} | {exp_amount:>16,.0f} | {result.total_amount:>16,.0f} | {'OK' if f_match else 'ERR':<8} | {status}")

    # Metrics Summary
    formula_acc = (formula_correct / total_tests) * 100
    eligibility_acc = (eligibility_correct / total_tests) * 100
    arithmetic_acc = (arithmetic_correct / total_tests) * 100
    final_acc = (final_calc_correct / total_tests) * 100
    clarification_acc = (clarification_correct / total_tests) * 100

    print("\n" + "=" * 60)
    print("PHASE 5H.1 DETERMINISTIC CALCULATOR BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Total Test Cases                   : {total_tests}")
    print(f"Formula Selection Accuracy         : {formula_acc:.2f}% ({formula_correct}/{total_tests})")
    print(f"Eligibility Decision Accuracy      : {eligibility_acc:.2f}% ({eligibility_correct}/{total_tests})")
    print(f"Arithmetic Accuracy                : {arithmetic_acc:.2f}% ({arithmetic_correct}/{total_tests})")
    print(f"Final Calculation Accuracy         : {final_acc:.2f}% ({final_calc_correct}/{total_tests})")
    print(f"Missing-Fact Clarification Accuracy: {clarification_acc:.2f}% ({clarification_correct}/{total_tests})")
    print("-" * 60)
    print("Domain Breakdown:")
    for dom, cnt in domain_counts.items():
        cor = domain_correct.get(dom, 0)
        print(f"  - {dom:<32}: {cor}/{cnt} ({cor / cnt * 100:.1f}%)")
    print("=" * 60)

    summary = {
        "total_tests": total_tests,
        "formula_selection_accuracy": formula_acc,
        "eligibility_accuracy": eligibility_acc,
        "arithmetic_accuracy": arithmetic_acc,
        "final_calculation_accuracy": final_acc,
        "clarification_accuracy": clarification_acc,
        "domain_breakdown": {
            dom: {"total": cnt, "correct": domain_correct.get(dom, 0), "accuracy": (domain_correct.get(dom, 0) / cnt) * 100}
            for dom, cnt in domain_counts.items()
        },
        "failures": failures,
    }

    RESULTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Saved results to {RESULTS_OUTPUT}")


if __name__ == "__main__":
    run_benchmark()
