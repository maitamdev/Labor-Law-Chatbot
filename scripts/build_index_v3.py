# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Indexing Script (V3)
Builds and verifies local persistent ChromaDB and BM25 indexes
for the expanded legal corpus V3 (CORE + Wave 1 + Wave 2 = 3,747 chunks).

Stores indexes in:
- storage/bm25_v3/
- storage/chroma_v3/

Preserves storage/bm25, storage/chroma, storage/bm25_v2, storage/chroma_v2 100% UNTOUCHED.
Fast Chroma builder reuses precomputed embeddings from V2 Chroma and only computes
BGE-M3 embeddings for the 338 new Wave 2 chunks (~1-2 minutes).
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, cast

# Ensure workspace root is in sys.path
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import chromadb
from rag.bm25_retriever import BM25Retriever
from rag.embeddings import LocalBGEEmbeddings
from rag.vectorstore import (
    clean_metadata_for_chroma,
    compute_corpus_fingerprint,
    format_retrieval_text,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_index_v3")

V3_CORPUS_PATH = workspace_root / "data" / "processed" / "legal_documents_v3.jsonl"
WAVE2_CORPUS_PATH = workspace_root / "data" / "processed" / "extended_wave2_documents.jsonl"
V3_BM25_DIR = workspace_root / "storage" / "bm25_v3"
V3_CHROMA_DIR = workspace_root / "storage" / "chroma_v3"
V2_CHROMA_DIR = workspace_root / "storage" / "chroma_v2"


def build_bm25_v3(force: bool = False):
    logger.info("Building / verifying BM25 V3 lexical index...")
    bm25_retriever = BM25Retriever(persist_dir=V3_BM25_DIR, corpus_path=V3_CORPUS_PATH)
    t0 = time.time()
    bm25_meta = bm25_retriever.build_index(force=force)
    logger.info(f"BM25 V3 index ready in {time.time() - t0:.2f}s: {bm25_meta.get('total_chunks')} chunks.")


def build_chroma_v3_fast():
    t_start = time.time()
    logger.info("=== FAST CHROMA V3 BUILD STARTING ===")

    # 1. Read V2 Chunks and Embeddings from V2 Chroma
    logger.info(f"Reading precomputed V2 chunks from {V2_CHROMA_DIR}...")
    v2_client = chromadb.PersistentClient(path=str(V2_CHROMA_DIR))
    v2_col = v2_client.get_collection("vietlabor_chunks_v2")
    v2_count = v2_col.count()
    logger.info(f"V2 collection has {v2_count} chunks.")

    v2_data = v2_col.get(include=["embeddings", "metadatas", "documents"])
    v2_ids = v2_data["ids"]
    v2_embeddings = v2_data["embeddings"]
    v2_metadatas = v2_data["metadatas"]
    v2_documents = v2_data["documents"]
    assert v2_embeddings is not None, "V2 Chroma returned no embeddings"
    assert v2_metadatas is not None, "V2 Chroma returned no metadatas"
    assert v2_documents is not None, "V2 Chroma returned no documents"
    logger.info(f"Loaded {len(v2_ids)} V2 embeddings in {time.time() - t_start:.2f}s.")

    # 2. Read and embed only Wave 2 chunks
    logger.info(f"Loading Wave 2 chunks from {WAVE2_CORPUS_PATH}...")
    w2_chunks: List[Dict[str, Any]] = []
    with open(WAVE2_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                w2_chunks.append(json.loads(line))
    logger.info(f"Found {len(w2_chunks)} Wave 2 chunks to embed.")

    w2_ids = [c["chunk_id"] for c in w2_chunks]
    w2_texts = [format_retrieval_text(c) for c in w2_chunks]
    w2_metas = [clean_metadata_for_chroma(c) for c in w2_chunks]

    logger.info("Loading BGE-M3 embedding model...")
    embed_model = LocalBGEEmbeddings()
    logger.info(f"Embedding {len(w2_chunks)} Wave 2 chunks...")
    t_emb = time.time()
    w2_embeddings = embed_model.embed_documents(w2_texts, batch_size=32, show_progress_bar=True)
    logger.info(f"Embedded {len(w2_chunks)} Wave 2 chunks in {time.time() - t_emb:.2f}s.")

    # 3. Create fresh V3 collection
    logger.info(f"Connecting to V3 Chroma at {V3_CHROMA_DIR}...")
    V3_CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    v3_client = chromadb.PersistentClient(path=str(V3_CHROMA_DIR))

    try:
        v3_client.delete_collection("vietlabor_chunks_v3")
        logger.info("Deleted existing 'vietlabor_chunks_v3' collection.")
    except Exception:
        pass

    v3_col = v3_client.create_collection(
        name="vietlabor_chunks_v3",
        metadata={"hnsw:space": "cosine"},
    )

    # 4. Insert V2 chunks in batches
    batch_size = 500
    for i in range(0, len(v2_ids), batch_size):
        end_idx = min(i + batch_size, len(v2_ids))
        v3_col.add(
            ids=v2_ids[i:end_idx],
            embeddings=v2_embeddings[i:end_idx],
            metadatas=v2_metadatas[i:end_idx],
            documents=v2_documents[i:end_idx],
        )
        logger.info(f"Inserted V2 chunks {i} to {end_idx}...")

    # 5. Insert Wave 2 chunks in batches
    for i in range(0, len(w2_ids), batch_size):
        end_idx = min(i + batch_size, len(w2_ids))
        v3_col.add(
            ids=w2_ids[i:end_idx],
            embeddings=cast(Any, w2_embeddings[i:end_idx]),
            metadatas=cast(Any, w2_metas[i:end_idx]),
            documents=w2_texts[i:end_idx],
        )
        logger.info(f"Inserted Wave 2 chunks {i} to {end_idx}...")

    final_count = v3_col.count()
    logger.info(f"V3 Chroma collection 'vietlabor_chunks_v3' now has {final_count} items.")

    # 6. Write Fingerprint
    fingerprint = compute_corpus_fingerprint(V3_CORPUS_PATH)
    meta = {
        "corpus_fingerprint": fingerprint,
        "built_at": time.time(),
        "total_chunks": final_count,
        "collection_name": "vietlabor_chunks_v3",
        "embedding_model": "BAAI/bge-m3",
    }
    with open(V3_CHROMA_DIR / "fingerprint.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"=== FAST CHROMA V3 BUILD COMPLETE IN {time.time() - t_start:.2f}s ===")


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
        build_chroma_v3_fast()

    logger.info(f"=== ALL V3 INDEXES BUILT IN {time.time() - t_start:.2f}s ===")


if __name__ == "__main__":
    main()
