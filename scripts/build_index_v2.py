# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5G Indexing Script (V2)
Builds and verifies local persistent ChromaDB and BM25 indexes
for the expanded legal corpus (CORE 3,206 + EXTENDED Wave 1 = 3,344 chunks).
Stores indexes in:
- storage/bm25_v2/
- storage/chroma_v2/
Preserves original storage/bm25/ and storage/chroma/ as rollback baseline.
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
logger = logging.getLogger("build_index_v2")

V2_CORPUS_PATH = workspace_root / "data" / "processed" / "legal_documents_v2.jsonl"
V2_BM25_DIR = workspace_root / "storage" / "bm25_v2"
V2_CHROMA_DIR = workspace_root / "storage" / "chroma_v2"


def main():
    parser = argparse.ArgumentParser(description="Build VietLabor AI V2 retrieval indexes (Core + Extended Wave 1).")
    parser.add_argument("--force", action="store_true", help="Force rebuild of indexes even if fingerprint matches.")
    parser.add_argument("--target", choices=["all", "chroma", "bm25"], default="all", help="Target index to build.")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for vector embedding.")
    args = parser.parse_args()

    logger.info("=== STARTING V2 INDEX BUILD PROCESS ===")
    logger.info(f"Corpus: {V2_CORPUS_PATH}")
    logger.info(f"BM25 V2 Target: {V2_BM25_DIR}")
    logger.info(f"Chroma V2 Target: {V2_CHROMA_DIR}")
    t_start = time.time()

    # 1. Build BM25 V2 index
    if args.target in ("all", "bm25"):
        logger.info("Building / verifying BM25 V2 lexical index...")
        bm25_retriever = BM25Retriever(persist_dir=V2_BM25_DIR, corpus_path=V2_CORPUS_PATH)
        t0 = time.time()
        bm25_meta = bm25_retriever.build_index(force=args.force)
        logger.info(f"BM25 V2 index ready in {time.time() - t0:.2f}s: {bm25_meta.get('total_chunks')} chunks.")

    # 2. Build ChromaDB V2 index
    if args.target in ("all", "chroma"):
        logger.info("Building / verifying ChromaDB V2 dense vector index...")
        vectorstore = LegalVectorStore(
            persist_dir=V2_CHROMA_DIR,
            collection_name="vietlabor_chunks_v2",
            corpus_path=V2_CORPUS_PATH,
        )
        t0 = time.time()
        chroma_meta = vectorstore.build_index(force=args.force, batch_size=args.batch_size)
        logger.info(f"ChromaDB V2 index ready in {time.time() - t0:.2f}s: {chroma_meta.get('total_chunks')} chunks.")

    total_time = time.time() - t_start
    logger.info(f"=== ALL REQUESTED V2 INDEXES BUILT IN {total_time:.2f}s ===")


if __name__ == "__main__":
    main()
