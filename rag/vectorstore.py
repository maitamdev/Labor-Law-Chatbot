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
from contextlib import closing
from pathlib import Path
from typing import Any, List, Optional, Union, cast

import chromadb
from chromadb.config import Settings

from config.settings import CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH
from rag.embeddings import (
    LocalBGEEmbeddings,
    compute_corpus_fingerprint,
    format_retrieval_text,
)

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = CHROMA_INDEX_DIR
DEFAULT_COLLECTION_NAME = "vietlabor_chunks_v3"
DEFAULT_CORPUS_PATH = PRODUCTION_CORPUS_PATH


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
        "status": str(chunk.get("status") or "CURRENT"),
        "scope_tier": str(chunk.get("scope_tier") or "core"),
        "domain": str(chunk.get("domain") or "CORE_LABOR"),
        "amends": str(chunk.get("amends") or ""),
        "amended_by": str(chunk.get("amended_by") or ""),
        "replaces": str(chunk.get("replaces") or ""),
        "replaced_by": str(chunk.get("replaced_by") or ""),
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
        self._client: Optional[ Any ] = None
        self.embedding_model = embedding_model or LocalBGEEmbeddings()

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    @client.setter
    def client(self, value: Any) -> None:
        self._client = value

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

    def _corpus_chunk_count(self) -> int:
        if not self.corpus_path.exists():
            return 0
        total = 0
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    total += 1
        return total

    def _sqlite_chunk_count(self) -> Optional[int]:
        """Reads collection embedding count directly from chroma.sqlite3 without loading HNSW."""
        import sqlite3

        sqlite_path = self.persist_dir / "chroma.sqlite3"
        if not sqlite_path.is_file():
            return 0
        try:
            with closing(sqlite3.connect(sqlite_path.resolve().as_uri() + "?mode=ro", uri=True)) as con:
                row = con.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE segment_id IN ("
                    "SELECT id FROM segments WHERE collection = ("
                    "SELECT id FROM collections WHERE name = ?"
                    "))",
                    (self.collection_name,),
                ).fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.debug(f"SQLite count check fallback: {e}")
            return None

    def is_index_valid(self, strict: bool = False) -> bool:
        """True only when index meta, fingerprint, and collection count match the corpus."""
        del strict  # kept for callers; completeness is always required
        expected = self._corpus_chunk_count()
        if expected == 0:
            return False

        # Fast & safe metadata and SQLite checks BEFORE touching native HNSW segments
        if not self.meta_file.exists():
            return False

        meta = self.load_index_meta()
        if not meta:
            return False

        if meta.get("total_chunks") != expected:
            logger.info(
                "Chroma index meta total_chunks (%s) != corpus (%d).",
                meta.get("total_chunks"),
                expected,
            )
            return False

        current_fp = compute_corpus_fingerprint(
            corpus_path=self.corpus_path,
            model_name=self.embedding_model.model_name,
        )
        if meta.get("fingerprint") != current_fp:
            logger.info("Fingerprint mismatch between corpus and existing index.")
            return False

        sqlite_count = self._sqlite_chunk_count()
        if sqlite_count is not None and sqlite_count != expected:
            logger.info("Chroma SQLite index incomplete: %d / %d chunks.", sqlite_count, expected)
            return False

        try:
            collection = self.get_collection()
            count = collection.count()
        except Exception as e:
            logger.warning(f"Error checking existing collection: {e}")
            return False

        if count == 0:
            logger.info("Chroma collection is empty.")
            return False
        if count != expected:
            logger.info("Chroma index incomplete: %d / %d chunks.", count, expected)
            return False

        return True

    def build_index(
        self,
        force: bool = False,
        batch_size: int = 64,
        show_progress: bool = True,
    ) -> dict[str, Any]:
        """Builds or reuses the ChromaDB vector index from the production corpus."""
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
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
        if not chunks or len({c["chunk_id"] for c in chunks}) != total_chunks:
            raise ValueError("Corpus must contain unique, nonempty chunks")
        logger.info(f"Read {total_chunks} chunks from {self.corpus_path}.")

        previous_meta = self.load_index_meta()
        if previous_meta and previous_meta.get("model_name") != self.embedding_model.model_name:
            logger.warning("Embedding model changed; rebuilding vectors with the new model.")
            force = True
        if force:
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted old collection '{self.collection_name}'.")
            except Exception:
                pass
        collection = self.get_collection()


        # Reuse unchanged vectors. This also makes an interrupted build resumable.
        existing = collection.get(include=["documents", "metadatas"])
        indexed = {
            chunk_id: (document, metadata)
            for chunk_id, document, metadata in zip(
                existing["ids"], existing.get("documents") or [], existing.get("metadatas") or [], strict=True
            )
        }
        desired_ids = {chunk["chunk_id"] for chunk in chunks}
        obsolete = list(indexed.keys() - desired_ids)
        for i in range(0, len(obsolete), batch_size):
            collection.delete(ids=obsolete[i : i + batch_size])

        to_embed = []
        metadata_only = []
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            retrieval_text = str(chunk.get("retrieval_text") or "").strip() or format_retrieval_text(chunk, corpus_path=self.corpus_path)
            metadata = clean_metadata_for_chroma(chunk)
            old = indexed.get(chunk_id)
            if old is None or old[0] != retrieval_text:
                to_embed.append(chunk)
            elif old[1] != metadata:
                metadata_only.append((chunk_id, metadata))

        upsert_step = 500
        for i in range(0, len(metadata_only), upsert_step):
            batch = metadata_only[i : i + upsert_step]
            collection.update(ids=[item[0] for item in batch], metadatas=[item[1] for item in batch])

        logger.info(
            "Index sync: %d unchanged, %d embed, %d metadata-only, %d obsolete.",
            total_chunks - len(to_embed) - len(metadata_only),
            len(to_embed),
            len(metadata_only),
            len(obsolete),
        )
        is_cuda = getattr(self.embedding_model, "device", "cpu") == "cuda"
        embed_step = max(batch_size, 128) if is_cuda else batch_size
        encode_batch = 32 if is_cuda else batch_size
        for i in range(0, len(to_embed), embed_step):
            batch_chunks = to_embed[i : i + embed_step]
            batch_ids = [c["chunk_id"] for c in batch_chunks]
            # Ingestion may preserve a reviewed retrieval representation whose
            # embedding already defines the production index. Reuse it when
            # present; only synthesize text for legacy rows.
            batch_texts = [
                str(c.get("retrieval_text") or "").strip() or format_retrieval_text(c, corpus_path=self.corpus_path)
                for c in batch_chunks
            ]
            batch_metas = [clean_metadata_for_chroma(c) for c in batch_chunks]

            batch_embeddings = self.embedding_model.embed_documents(
                batch_texts,
                batch_size=min(encode_batch, len(batch_texts)),
                show_progress_bar=False,
            )

            collection.upsert(
                ids=batch_ids,
                embeddings=cast(Any, batch_embeddings),
                documents=batch_texts,
                metadatas=cast(Any, batch_metas),
            )
            if show_progress and (
                (i + len(batch_chunks)) % 256 == 0
                or (i + len(batch_chunks)) == len(to_embed)
            ):
                logger.info(f"Indexed {i + len(batch_chunks)}/{len(to_embed)} changed chunks...")

        if collection.count() != total_chunks:
            raise RuntimeError(f"Index incomplete: {collection.count()} / {total_chunks} chunks")

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
        if not query_text.strip() or top_k <= 0:
            return []
        collection = self.get_collection()
        count = collection.count()
        if count == 0:
            raise RuntimeError(
                f"Vector index '{self.collection_name}' is empty. "
                "Run: python scripts/build_index_v3.py --target chroma"
            )
        query_vector = self.embedding_model.embed_query(query_text)

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": min(top_k, count),
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

        for chunk_id, dist, doc, meta in zip(ids, distances, documents, metadatas, strict=True):
            meta = meta or {}
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
