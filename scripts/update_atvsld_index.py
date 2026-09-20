# -*- coding: utf-8 -*-
"""
VietLabor AI - Update ATVSLĐ Index Script
Replaces old L_84_2015 chunks with enriched Điều 6, 7, 12, 16 in both BM25 and Chroma V3.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

# Ensure workspace root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import chromadb
from rag.bm25_retriever import BM25Retriever
from rag.embeddings import LocalBGEEmbeddings
from rag.vectorstore import clean_metadata_for_chroma, format_retrieval_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("update_atvsld_index")

V3_BM25_DIR = PROJECT_ROOT / "storage" / "bm25_v3"
V3_CHROMA_DIR = PROJECT_ROOT / "storage" / "chroma_v3"
V3_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "legal_documents_v3.jsonl"
WAVE2_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "extended_wave2_documents.jsonl"


def update_indexes():
    t0 = time.time()
    logger.info("=== UPDATING ATVSLĐ CHUNKS IN BM25 & CHROMA V3 ===")

    # 1. Load existing BM25 chunks
    chunks_file = V3_BM25_DIR / "chunks.json"
    with open(chunks_file, "r", encoding="utf-8") as f:
        existing_chunks = json.load(f)

    # Filter out old L_84_2015 chunks
    base_chunks = [c for c in existing_chunks if c.get("doc_id") != "L_84_2015"]
    logger.info(f"Retained {len(base_chunks)} base non-L84 chunks.")

    # Load new L_84_2015 chunks from extended_wave2_documents.jsonl
    with open(WAVE2_CORPUS_PATH, "r", encoding="utf-8") as f:
        new_w2_chunks = [json.loads(line) for line in f if line.strip()]

    new_l84_chunks = [c for c in new_w2_chunks if c.get("doc_id") == "L_84_2015"]
    logger.info(f"Loaded {len(new_l84_chunks)} enriched L_84_2015 chunks.")

    # Combine into full V3 corpus
    all_v3_chunks = base_chunks + new_l84_chunks
    logger.info(f"Total V3 chunks after update: {len(all_v3_chunks)}")

    # Write combined legal_documents_v3.jsonl
    with open(V3_CORPUS_PATH, "w", encoding="utf-8") as f:
        for ch in all_v3_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(all_v3_chunks)} chunks to {V3_CORPUS_PATH}")

    # 2. Rebuild BM25 V3
    logger.info("Rebuilding BM25 V3 index...")
    t_bm25 = time.time()
    retriever = BM25Retriever(persist_dir=V3_BM25_DIR, corpus_path=V3_CORPUS_PATH)
    meta = retriever.build_index(force=True)
    logger.info(f"BM25 V3 rebuilt in {time.time() - t_bm25:.2f}s with {meta.get('total_chunks')} chunks.")

    # 3. Update Chroma V3
    logger.info("Connecting to Chroma V3...")
    client = chromadb.PersistentClient(path=str(V3_CHROMA_DIR))
    col = client.get_collection("vietlabor_chunks_v3")

    # Delete old L_84_2015 chunks
    logger.info("Deleting old L_84_2015 chunks from Chroma V3...")
    old_res = col.get(where={"doc_id": "L_84_2015"}, include=["metadatas"])
    if old_res["ids"]:
        col.delete(ids=old_res["ids"])
        logger.info(f"Deleted {len(old_res['ids'])} old L_84_2015 chunks.")

    # Embed and add new L_84_2015 chunks
    logger.info("Embedding new 76 L_84_2015 chunks...")
    embed_model = LocalBGEEmbeddings()
    l84_texts = [format_retrieval_text(c) for c in new_l84_chunks]
    l84_ids = [c["chunk_id"] for c in new_l84_chunks]
    l84_metas = [clean_metadata_for_chroma(c) for c in new_l84_chunks]

    t_emb = time.time()
    l84_embeddings = embed_model.embed_documents(l84_texts, batch_size=32, show_progress_bar=False)
    logger.info(f"Embedded 76 chunks in {time.time() - t_emb:.2f}s.")

    col.add(
        ids=l84_ids,
        embeddings=l84_embeddings,
        metadatas=l84_metas,
        documents=l84_texts,
    )
    logger.info(f"Added {len(l84_ids)} new L_84_2015 chunks to Chroma V3. Final count: {col.count()}")
    logger.info(f"=== ALL UPDATES COMPLETED SUCCESSFULLY IN {time.time() - t0:.2f}s ===")


if __name__ == "__main__":
    update_indexes()
