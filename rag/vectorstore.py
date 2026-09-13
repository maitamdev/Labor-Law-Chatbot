# -*- coding: utf-8 -*-
"""
VietLabor AI - ChromaDB Vector Store
Manages persistent local vector indexing, metadata roundtrip,
provenance preservation, and corpus fingerprint versioning.
"""
from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb
from chromadb.config import Settings

from rag.embeddings import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_MODEL_NAME,
    LocalBGEEmbeddings,
    compute_corpus_fingerprint,
    format_retrieval_text,
)

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = Path("storage/chroma")
DEFAULT_COLLECTION_NAME = "vietlabor_chunks"
DEFAULT_CORPUS_PATH = Path("data/processed/legal_documents.jsonl")


def clean_metadata_for_chroma(chunk: dict[str, Any]) -> dict[str, Union[str, int, float, bool]]:
    """Sanitizes chunk metadata for ChromaDB compatibility.
    
    Chroma requires primitive values (str, int, float, bool) and rejects None,
    lists, or nested dicts in metadata.
    """
    cleaned: dict[str, Union[str, int, float, bool]] = {
        "chunk_id": str(chunk.get("chunk_id") or ""),
        "doc_id": str(chunk.get("doc_id") or ""),
        "doc_title": str(chunk.get("doc_title") or ""),
        "document_no": str(chunk.get("document_no") or ""),
        "document_type": str(chunk.get("document_type") or ""),
        "issuer": str(chunk.get("issuer") or ""),
        "part": str(chunk.get("part") or ""),
        "chapter": str(chunk.get("chapter") or ""),
        "section": str(chunk.get("section") or ""),
        "article_number": str(chunk.get("article_number") or ""),
        "article_title": str(chunk.get("article_title") or ""),
        "clause_number": str(chunk.get("clause_number") or ""),
        "point": str(chunk.get("point") or ""),
        "source_file": str(chunk.get("source_file") or ""),
        "source_page_start": int(chunk.get("source_page_start") or 0),
        "source_page_end": int(chunk.get("source_page_end") or 0),
        "official_source": str(chunk.get("official_source") or ""),
        "signer": str(chunk.get("signer") or ""),
        "effective_from": str(chunk.get("effective_from") or ""),
        "status": str(chunk.get("status") or ""),
        "content": str(chunk.get("content") or ""),
    }
    return cleaned


class LegalVectorStore:
    """Local persistent ChromaDB vector store for Vietnamese labor law chunks."""

    def __init__(
        self,
        persist_dir: Union[str, Path] = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        corpus_path: Union[str, Path] = DEFAULT_CORPUS_PATH,
        embedding_model: Optional[LocalBGEEmbeddings] = None,
    ):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.corpus_path = Path(corpus_path)
        self.meta_file = self.persist_dir / "index_meta.json"

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_model = embedding_model or LocalBGEEmbeddings()

    def get_collection(self) -> Any:
        """Retrieves or creates the target Chroma collection with cosine distance."""
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def load_index_meta(self) -> Optional[dict[str, Any]]:
        """Loads index metadata if present."""
        if not self.meta_file.exists():
            return None
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read index_meta.json: {e}")
            return None

    def save_index_meta(self, meta: dict[str, Any]) -> None:
        """Persists index metadata to disk."""
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def is_index_valid(self) -> bool:
        """Checks if the existing ChromaDB index matches current corpus fingerprint."""
        if not self.meta_file.exists():
            return False

        meta = self.load_index_meta()
        if not meta:
            return False

        current_fp = compute_corpus_fingerprint(
            corpus_path=self.corpus_path,
            model_name=self.embedding_model.model_name,
        )

        if meta.get("fingerprint") != current_fp:
            logger.info("Fingerprint mismatch between corpus and existing index.")
            return False

        try:
            collection = self.get_collection()
            count = collection.count()
            if count != meta.get("total_chunks"):
                logger.info(f"Chunk count mismatch: index has {count}, meta expected {meta.get('total_chunks')}.")
                return False
            return True
        except Exception as e:
            logger.warning(f"Error checking existing collection: {e}")
            return False

    def build_index(
        self,
        force: bool = False,
        batch_size: int = 64,
        show_progress: bool = True,
    ) -> dict[str, Any]:
        """Builds or reuses the ChromaDB vector index from the production corpus."""
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {self.corpus_path}")

        current_fp = compute_corpus_fingerprint(
            corpus_path=self.corpus_path,
            model_name=self.embedding_model.model_name,
        )

        if not force and self.is_index_valid():
            logger.info("Existing index is valid and up-to-date. Reusing index without re-indexing.")
            meta = self.load_index_meta()
            assert meta is not None
            return meta

        logger.info(f"Building persistent ChromaDB index at {self.persist_dir}...")

        # Read corpus chunks
        chunks: List[dict[str, Any]] = []
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    chunks.append(json.loads(line_str))

        total_chunks = len(chunks)
        logger.info(f"Read {total_chunks} chunks from {self.corpus_path}.")

        # Reset existing collection if it exists
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted old collection '{self.collection_name}'.")
        except Exception:
            pass

        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Batch embed and insert
        logger.info(f"Embedding and inserting {total_chunks} chunks in batches of {batch_size}...")
        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_ids = [c["chunk_id"] for c in batch_chunks]
            batch_texts = [format_retrieval_text(c) for c in batch_chunks]
            batch_metas = [clean_metadata_for_chroma(c) for c in batch_chunks]

            batch_embeddings = self.embedding_model.embed_documents(
                batch_texts,
                batch_size=len(batch_texts),
                show_progress_bar=False,
            )

            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )

            if show_progress and (i + len(batch_chunks)) % 256 == 0 or (i + len(batch_chunks)) == total_chunks:
                logger.info(f"Indexed {i + len(batch_chunks)}/{total_chunks} chunks...")

        # Save metadata
        meta = {
            "fingerprint": current_fp,
            "corpus_path": str(self.corpus_path),
            "collection_name": self.collection_name,
            "model_name": self.embedding_model.model_name,
            "embedding_dim": self.embedding_model.dimension,
            "total_chunks": total_chunks,
            "indexed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.save_index_meta(meta)
        logger.info(f"Index successfully built and verified with {collection.count()} items.")
        return meta

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> List[dict[str, Any]]:
        """Queries the vector index using cosine similarity."""
        collection = self.get_collection()
        query_vector = self.embedding_model.embed_query(query_text)

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        formatted_results: List[dict[str, Any]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return formatted_results

        ids = results["ids"][0]
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)
        documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)

        for chunk_id, dist, doc, meta in zip(ids, distances, documents, metadatas):
            # Chroma returns cosine distance d in [0, 2]. Cosine similarity is 1.0 - d
            sim_score = float(max(0.0, min(1.0, 1.0 - dist)))
            formatted_results.append({
                "chunk_id": chunk_id,
                "score": sim_score,
                "retrieval_text": doc,
                "metadata": meta,
                "content": meta.get("content", ""),
            })

        return formatted_results
