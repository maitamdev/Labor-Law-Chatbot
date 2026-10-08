# -*- coding: utf-8 -*-
"""
VietLabor AI - Fast Chroma V2 Builder
Transfers pre-computed embeddings for 3,206 unchanged CORE chunks from storage/chroma/
and computes BGE-M3 embeddings ONLY for the 203 new EXTENDED chunks.
Builds the complete 3,409-chunk collection 'vietlabor_chunks_v2' in ~1-2 minutes instead of 45 minutes on CPU.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Sequence, cast

workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import chromadb
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
logger = logging.getLogger("build_chroma_v2_fast")

CHROMA_V1_DIR = workspace_root / "storage" / "chroma"
CHROMA_V2_DIR = workspace_root / "storage" / "chroma_v2"
V2_CORPUS_PATH = workspace_root / "data" / "processed" / "legal_documents_v2.jsonl"
EXTENDED_CORPUS_PATH = workspace_root / "data" / "processed" / "extended_documents.jsonl"


def build_fast_v2():
    t_start = time.time()
    logger.info("=== FAST CHROMA V2 BUILD STARTING ===")

    # 1. Read Core Embeddings from V1 Chroma
    logger.info(f"Reading precomputed Core chunks from {CHROMA_V1_DIR}...")
    v1_client = chromadb.PersistentClient(path=str(CHROMA_V1_DIR))
    v1_col = v1_client.get_collection("vietlabor_chunks")
    core_count = v1_col.count()
    logger.info(f"V1 collection has {core_count} chunks.")

    core_data = v1_col.get(include=["embeddings", "metadatas", "documents"])
    core_ids = core_data["ids"]
    core_embeddings = core_data["embeddings"]
    core_metadatas = core_data["metadatas"]
    core_documents = core_data["documents"]
    assert core_embeddings is not None, "V1 Chroma returned no embeddings"
    assert core_metadatas is not None, "V1 Chroma returned no metadatas"
    assert core_documents is not None, "V1 Chroma returned no documents"
    logger.info(f"Loaded {len(core_ids)} Core embeddings from V1 Chroma in {time.time() - t_start:.2f}s.")

    # 2. Read and embed only Extended chunks
    logger.info(f"Loading extended chunks from {EXTENDED_CORPUS_PATH}...")
    ext_chunks: List[Dict[str, Any]] = []
    with open(EXTENDED_CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ext_chunks.append(json.loads(line))
    logger.info(f"Found {len(ext_chunks)} extended chunks to embed.")

    ext_ids = [c["chunk_id"] for c in ext_chunks]
    ext_texts = [format_retrieval_text(c) for c in ext_chunks]
    ext_metas = [clean_metadata_for_chroma(c) for c in ext_chunks]

    logger.info("Loading BGE-M3 embedding model...")
    embed_model = LocalBGEEmbeddings()
    logger.info(f"Embedding {len(ext_chunks)} extended chunks...")
    t_emb = time.time()
    ext_embeddings = embed_model.embed_documents(ext_texts, batch_size=32, show_progress_bar=True)
    logger.info(f"Embedded {len(ext_chunks)} chunks in {time.time() - t_emb:.2f}s.")

    # 3. Create fresh V2 collection
    logger.info(f"Connecting to V2 Chroma at {CHROMA_V2_DIR}...")
    CHROMA_V2_DIR.mkdir(parents=True, exist_ok=True)
    v2_client = chromadb.PersistentClient(path=str(CHROMA_V2_DIR))

    try:
        v2_client.delete_collection("vietlabor_chunks_v2")
        logger.info("Deleted existing 'vietlabor_chunks_v2' collection.")
    except Exception:
        pass

    v2_col = v2_client.create_collection(
        name="vietlabor_chunks_v2",
        metadata={"hnsw:space": "cosine"},
    )

    # 4. Insert Core chunks in batches
    batch_size = 500
    logger.info("Inserting Core chunks into V2 collection...")
    for i in range(0, len(core_ids), batch_size):
        end = min(i + batch_size, len(core_ids))
        v2_col.add(
            ids=core_ids[i:end],
            embeddings=core_embeddings[i:end].tolist() if hasattr(core_embeddings[i:end], "tolist") else core_embeddings[i:end],
            metadatas=core_metadatas[i:end],
            documents=core_documents[i:end],
        )

    # 5. Insert Extended chunks
    logger.info("Inserting Extended chunks into V2 collection...")
    v2_col.add(
        ids=ext_ids,
        embeddings=cast(Any, ext_embeddings),
        metadatas=cast(Any, ext_metas),
        documents=ext_texts,
    )

    total_inserted = v2_col.count()
    logger.info(f"Successfully verified total count in V2 Chroma: {total_inserted} chunks.")

    # 6. Save index_meta.json
    fingerprint = compute_corpus_fingerprint(
        corpus_path=V2_CORPUS_PATH,
        model_name=embed_model.model_name,
    )
    meta = {
        "fingerprint": fingerprint,
        "corpus_path": str(V2_CORPUS_PATH),
        "collection_name": "vietlabor_chunks_v2",
        "model_name": embed_model.model_name,
        "embedding_dim": 1024,
        "total_chunks": total_inserted,
        "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    }
    meta_path = CHROMA_V2_DIR / "index_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Saved V2 metadata to {meta_path}.")
    logger.info(f"=== FAST V2 CHROMA BUILD COMPLETE IN {time.time() - t_start:.2f}s (Total: {total_inserted} chunks) ===")


if __name__ == "__main__":
    build_fast_v2()
