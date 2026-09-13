# -*- coding: utf-8 -*-
"""
VietLabor AI - Corpus Indexing Script
Builds and verifies local persistent ChromaDB and BM25 indexes
for the production legal corpus.
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

from rag.bm25_retriever import BM25Retriever
from rag.vectorstore import LegalVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_index")


def main():
    parser = argparse.ArgumentParser(description="Build VietLabor AI local retrieval indexes.")
    parser.add_argument("--force", action="store_true", help="Force rebuild of indexes even if fingerprint matches.")
    parser.add_argument("--target", choices=["all", "chroma", "bm25"], default="all", help="Target index to build.")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for vector embedding.")
    args = parser.parse_args()

    logger.info("=== STARTING INDEX BUILD PROCESS ===")
    t_start = time.time()

    # 1. Build BM25 index
    if args.target in ("all", "bm25"):
        logger.info("Building / verifying BM25 lexical index...")
        bm25_retriever = BM25Retriever()
        t0 = time.time()
        bm25_meta = bm25_retriever.build_index(force=args.force)
        logger.info(f"BM25 index ready in {time.time() - t0:.2f}s: {bm25_meta.get('total_chunks')} chunks.")

    # 2. Build ChromaDB index
    if args.target in ("all", "chroma"):
        logger.info("Building / verifying ChromaDB dense vector index...")
        vectorstore = LegalVectorStore()
        t0 = time.time()
        chroma_meta = vectorstore.build_index(force=args.force, batch_size=args.batch_size)
        logger.info(f"ChromaDB index ready in {time.time() - t0:.2f}s: {chroma_meta.get('total_chunks')} chunks.")

    total_time = time.time() - t_start
    logger.info(f"=== ALL REQUESTED INDEXES BUILT IN {total_time:.2f}s ===")


if __name__ == "__main__":
    main()
