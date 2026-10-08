# -*- coding: utf-8 -*-
"""
VietLabor AI - Retrieval ablation study.

Compares retrieval configurations on the gold set (data/evaluation/retrieval_gold.json):

    bm25          BM25s lexical only
    dense         BGE-M3 + ChromaDB only
    hybrid        BM25 + Dense fused with RRF (HybridRetriever)
    hybrid_graph  Hybrid + Neo4j GUIDES/PENALIZES expansion (HybridGraphRetriever)
    hybrid_norm   Hybrid after the chain's query normalization (colloquial → statutory terms)

Metrics (article level, i.e. (doc_id, article) pairs, which is what citations use):
    Hit@k       share of questions with at least one relevant article in the top k
    Recall@k    mean share of relevant articles found in the top k
    MRR@k       mean reciprocal rank of the first relevant article
    ChunkR@k    mean share of gold chunk ids found (prefix match for clause chunks)

Unavailable components are reported, not faked: if the BGE-M3 weights fail to
load, "dense" is marked N/A and "hybrid" silently equals BM25 (flagged in the
report); if Neo4j is offline "hybrid_graph" equals "hybrid" (flagged).

Usage:
    python scripts/evaluate_ablation.py
    python scripts/evaluate_ablation.py --configs bm25 hybrid --limit 50 --k 5 10
    python scripts/evaluate_ablation.py --out reports/ablation_retrieval.md --csv reports/ablation.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import logging
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("ablation")

ArticleKey = Tuple[str, str]
DEFAULT_GOLD = PROJECT_ROOT / "data" / "evaluation" / "retrieval_gold.json"
ALL_CONFIGS = ("bm25", "dense", "hybrid", "hybrid_graph", "hybrid_norm")
_CHUNK_ARTICLE_RE = re.compile(r"^(?P<doc>[^#]+)#d(?P<art>\d+)")


# --------------------------------------------------------------------------- #
# Gold set + metric helpers (pure functions, unit-tested)
# --------------------------------------------------------------------------- #

def article_from_chunk_id(chunk_id: str) -> Optional[ArticleKey]:
    match = _CHUNK_ARTICLE_RE.match(chunk_id or "")
    return (match.group("doc"), match.group("art")) if match else None


def gold_articles(item: Dict[str, Any]) -> Set[ArticleKey]:
    """Relevant (doc_id, article) pairs; chunk ids are the most precise source."""
    pairs = {a for a in (article_from_chunk_id(c) for c in item.get("relevant_chunk_ids") or []) if a}
    if pairs:
        return pairs
    docs = item.get("relevant_documents") or []
    arts = [str(a) for a in item.get("relevant_articles") or []]
    if len(docs) == 1:
        return {(docs[0], a) for a in arts}
    return set()  # ambiguous doc/article pairing → not scorable at article level


def retrieved_article(chunk: Dict[str, Any]) -> Optional[ArticleKey]:
    meta = chunk.get("metadata") or {}
    doc_id = meta.get("doc_id") or chunk.get("doc_id")
    art = str(meta.get("article_number") or chunk.get("article_number") or "").strip()
    if doc_id and art:
        return (str(doc_id), art)
    return article_from_chunk_id(str(chunk.get("chunk_id") or ""))


def chunk_matches(retrieved_id: str, gold_id: str) -> bool:
    return retrieved_id == gold_id or retrieved_id.startswith(gold_id + "-")


def score_query(
    retrieved: Sequence[Dict[str, Any]],
    gold_arts: Set[ArticleKey],
    gold_chunks: Sequence[str],
    ks: Sequence[int],
) -> Dict[str, float]:
    ranked_articles: List[Optional[ArticleKey]] = [retrieved_article(c) for c in retrieved]
    ranked_ids = [str(c.get("chunk_id") or "") for c in retrieved]
    out: Dict[str, float] = {}
    for k in ks:
        top_arts = {a for a in ranked_articles[:k] if a}
        found = gold_arts & top_arts
        out[f"hit@{k}"] = 1.0 if found else 0.0
        out[f"recall@{k}"] = len(found) / len(gold_arts) if gold_arts else 0.0
        if gold_chunks:
            hit_chunks = [g for g in gold_chunks if any(chunk_matches(r, g) for r in ranked_ids[:k])]
            out[f"chunk_recall@{k}"] = len(hit_chunks) / len(gold_chunks)
        first = next((i for i, a in enumerate(ranked_articles[:k], start=1) if a in gold_arts), None)
        out[f"mrr@{k}"] = 1.0 / first if first else 0.0
    return out


def aggregate(rows: Iterable[Dict[str, float]]) -> Dict[str, float]:
    rows = list(rows)
    if not rows:
        return {}
    keys = sorted({k for r in rows for k in r})
    return {k: statistics.fmean(r.get(k, 0.0) for r in rows) for k in keys}


# --------------------------------------------------------------------------- #
# Retriever construction
# --------------------------------------------------------------------------- #

def build_retrievers(configs: Sequence[str]) -> Tuple[Dict[str, Callable[[str, int], List[Dict[str, Any]]]], Dict[str, str]]:
    from config.settings import BM25_INDEX_DIR, CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH
    from rag.bm25_retriever import BM25Retriever

    notes: Dict[str, str] = {}
    bm25 = BM25Retriever(persist_dir=BM25_INDEX_DIR, corpus_path=PRODUCTION_CORPUS_PATH)

    dense = None
    dense_ok = False
    if any(c in configs for c in ("dense", "hybrid", "hybrid_graph")):
        try:
            from rag.dense_retriever import DenseRetriever
            from rag.vectorstore import LegalVectorStore

            dense = DenseRetriever(vectorstore=LegalVectorStore(
                persist_dir=CHROMA_INDEX_DIR, collection_name="vietlabor_chunks_v3",
                corpus_path=PRODUCTION_CORPUS_PATH,
            ))
            if not dense.vectorstore.is_index_valid(strict=False):
                raise RuntimeError("Chroma index incomplete or stale")
            dense.retrieve("thời gian thử việc", top_k=1)  # forces model load
            dense_ok = True
        except Exception as exc:
            notes["dense"] = f"N/A - dense unavailable ({type(exc).__name__}: {str(exc)[:120]})"
            notes["hybrid"] = "dense unavailable → equals BM25 only"

    fns: Dict[str, Callable[[str, int], List[Dict[str, Any]]]] = {}
    if "bm25" in configs:
        fns["bm25"] = lambda q, k: bm25.retrieve(q, top_k=k)
    if "dense" in configs and dense_ok:
        fns["dense"] = lambda q, k: dense.retrieve(q, top_k=k)
    if "hybrid" in configs:
        from rag.hybrid_retriever import HybridRetriever

        hybrid = HybridRetriever(bm25_retriever=bm25, dense_retriever=dense) if dense else HybridRetriever(bm25_retriever=bm25)
        hybrid.dense_ready = dense_ok
        fns["hybrid"] = lambda q, k: hybrid.retrieve(q, top_k=k)
    if "hybrid_graph" in configs:
        from rag.hybrid_graph_retriever import HybridGraphRetriever

        graph = (HybridGraphRetriever(bm25_retriever=bm25, dense_retriever=dense)
                 if dense else HybridGraphRetriever(bm25_retriever=bm25))
        graph.dense_ready = dense_ok
        if not graph.graph_available:
            notes["hybrid_graph"] = "Neo4j offline/disabled → equals hybrid"
        # Graph additions are appended beyond top_k; cut to k for a fair comparison.
        fns["hybrid_graph"] = lambda q, k: graph.retrieve(q, top_k=k)[:k]
    if "hybrid_norm" in configs:
        from rag.hybrid_retriever import HybridRetriever
        from rag.query_processor import normalize_colloquial_vietnamese, normalize_query
        from rag.query_rewriter import AdaptiveQueryRewriter

        norm_hybrid = HybridRetriever(bm25_retriever=bm25, dense_retriever=dense) if dense else HybridRetriever(bm25_retriever=bm25)
        norm_hybrid.dense_ready = dense_ok
        expander = AdaptiveQueryRewriter(llm_manager=None)

        def _normalized(q: str, k: int) -> List[Dict[str, Any]]:
            nq = expander.rewrite_deterministic(normalize_colloquial_vietnamese(normalize_query(q)))
            return norm_hybrid.retrieve(nq, top_k=k)

        fns["hybrid_norm"] = _normalized
    return fns, notes


# --------------------------------------------------------------------------- #
# Runner + report
# --------------------------------------------------------------------------- #

def run_ablation(
    gold: Sequence[Dict[str, Any]],
    retrievers: Dict[str, Callable[[str, int], List[Dict[str, Any]]]],
    ks: Sequence[int],
) -> Dict[str, Dict[str, Any]]:
    max_k = max(ks)
    scorable = [g for g in gold if gold_articles(g)]
    results: Dict[str, Dict[str, Any]] = {}
    for name, fn in retrievers.items():
        rows, latencies, by_type = [], [], {}
        for item in scorable:
            t0 = time.perf_counter()
            try:
                retrieved = fn(item["question"], max_k)
            except Exception as exc:
                logger.warning("%s failed on %s: %s", name, item.get("question_id"), exc)
                retrieved = []
            latencies.append((time.perf_counter() - t0) * 1000)
            row = score_query(retrieved, gold_articles(item), item.get("relevant_chunk_ids") or [], ks)
            rows.append(row)
            by_type.setdefault(item.get("query_type") or "other", []).append(row)
        results[name] = {
            "n": len(rows),
            "metrics": aggregate(rows),
            "latency_ms": statistics.fmean(latencies) if latencies else 0.0,
            "by_type": {t: aggregate(r) | {"n": len(r)} for t, r in sorted(by_type.items())},
        }
        logger.info("%s done (%d queries)", name, len(rows))
    return results


def render_markdown(results: Dict[str, Dict[str, Any]], notes: Dict[str, str], ks: Sequence[int], n_total: int) -> str:
    main_k = max(ks)
    cols = [f"hit@{k}" for k in ks] + [f"recall@{k}" for k in ks] + [f"mrr@{main_k}", f"chunk_recall@{main_k}"]
    lines = [
        "# VietLabor AI - Retrieval Ablation",
        "",
        f"- Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"- Gold set: `data/evaluation/retrieval_gold.json` ({n_total} questions; "
        f"{next(iter(results.values()))['n'] if results else 0} scorable, out-of-scope skipped)",
        "- Metrics are article-level ((doc_id, Điều) pairs) except ChunkR.",
        "",
        "| Config | " + " | ".join(c.replace("_", " ") for c in cols) + " | ms/query |",
        "|---" * (len(cols) + 2) + "|",
    ]
    for name in ALL_CONFIGS:
        if name not in results:
            if name in notes:
                lines.append(f"| {name} | " + " | ".join("N/A" for _ in cols) + " | - |")
            continue
        m = results[name]["metrics"]
        vals = " | ".join(f"{m.get(c, 0.0):.3f}" for c in cols)
        lines.append(f"| {name} | {vals} | {results[name]['latency_ms']:.0f} |")
    if notes:
        lines += ["", "**Notes**", ""] + [f"- `{k}`: {v}" for k, v in notes.items()]
    lines += ["", f"## Hit@{main_k} by query type", "", "| Config | " + " | ".join(
        sorted({t for r in results.values() for t in r["by_type"]})) + " |"]
    types = sorted({t for r in results.values() for t in r["by_type"]})
    lines.append("|---" * (len(types) + 1) + "|")
    for name, res in results.items():
        cells = []
        for t in types:
            bt = res["by_type"].get(t)
            cells.append(f"{bt.get(f'hit@{main_k}', 0.0):.2f} (n={bt['n']})" if bt else "-")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_csv(results: Dict[str, Dict[str, Any]], path: Path) -> None:
    keys = sorted({k for r in results.values() for k in r["metrics"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["config", "n", "latency_ms", *keys])
        for name, res in results.items():
            writer.writerow([name, res["n"], f"{res['latency_ms']:.1f}", *[f"{res['metrics'].get(k, 0.0):.4f}" for k in keys]])


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--configs", nargs="+", choices=ALL_CONFIGS, default=list(ALL_CONFIGS))
    parser.add_argument("--k", nargs="+", type=int, default=[5, 10])
    parser.add_argument("--limit", type=int, default=0, help="evaluate only the first N questions")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "ablation_retrieval.md")
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    if args.limit:
        gold = gold[: args.limit]
    ks = sorted(set(args.k))

    retrievers, notes = build_retrievers(args.configs)
    results = run_ablation(gold, retrievers, ks)
    report = render_markdown(results, notes, ks, n_total=len(gold))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    if args.csv:
        write_csv(results, args.csv)
    try:
        print(report)
    except UnicodeEncodeError:
        import sys
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(report.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
