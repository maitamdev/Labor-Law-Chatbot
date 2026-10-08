# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Indexing Script (V3)
Builds and verifies local persistent ChromaDB and BM25 indexes for the
authoritative production corpus.

Stores indexes in:
- storage/bm25_v3/
- storage/chroma_v3/

Older indexes are left untouched. A valid v3 index is reused unless --force is
provided; a forced build derives every record from the production corpus so it
cannot silently omit post-v2 additions.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from rag.bm25_retriever import BM25Retriever
from rag.vectorstore import LegalVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_index_v3")

V3_CORPUS_PATH = workspace_root / "data" / "processed" / "legal_documents_v3.jsonl"
V3_BM25_DIR = workspace_root / "storage" / "bm25_v3"
V3_CHROMA_DIR = workspace_root / "storage" / "chroma_v3"


def build_bm25_v3(force: bool = False):
    logger.info("Building / verifying BM25 V3 lexical index...")
    bm25_retriever = BM25Retriever(persist_dir=V3_BM25_DIR, corpus_path=V3_CORPUS_PATH)
    t0 = time.time()
    bm25_meta = bm25_retriever.build_index(force=force)
    logger.info(f"BM25 V3 index ready in {time.time() - t0:.2f}s: {bm25_meta.get('total_chunks')} chunks.")


def build_chroma_v3(force: bool = False):
    t_start = time.time()
    logger.info("Building / verifying Chroma V3 semantic index...")
    store = LegalVectorStore(
        persist_dir=V3_CHROMA_DIR,
        collection_name="vietlabor_chunks_v3",
        corpus_path=V3_CORPUS_PATH,
    )
    meta = store.build_index(force=force)
    logger.info(
        "Chroma V3 index ready in %.2fs: %s chunks.",
        time.time() - t_start,
        meta.get("total_chunks"),
    )


def main():
    parser = argparse.ArgumentParser(description="Build VietLabor AI V3 retrieval indexes (Core + Wave 1 + Wave 2).")
    parser.add_argument("--force", action="store_true", help="Force rebuild of indexes.")
    parser.add_argument("--target", choices=["all", "chroma", "bm25"], default="all", help="Target index.")
    args = parser.parse_args()

    logger.info("=== STARTING V3 INDEX BUILD PROCESS ===")
    t_start = time.time()

    if args.target in ("all", "bm25"):
        build_bm25_v3(force=args.force)

    if args.target in ("all", "chroma"):
        build_chroma_v3(force=args.force)

    logger.info(f"=== ALL V3 INDEXES BUILT IN {time.time() - t_start:.2f}s ===")


if __name__ == "__main__":
    main()
