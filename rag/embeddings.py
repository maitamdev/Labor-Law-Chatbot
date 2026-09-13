# -*- coding: utf-8 -*-
"""
VietLabor AI - Local Embedding Engine
Provides local dense embeddings using BAAI/bge-m3 with caching,
structure-aware legal retrieval text formatting, and corpus fingerprinting.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
DEFAULT_EMBEDDING_DIM = 1024

_PARENT_CLAUSE_CACHE: Optional[dict[tuple[str, str, str], str]] = None


def get_parent_clause_map(corpus_path: Optional[Union[str, Path]] = None) -> dict[tuple[str, str, str], str]:
    """Builds or returns cached mapping of (doc_id, str(article_number), str(clause_number)) -> parent clause content."""
    global _PARENT_CLAUSE_CACHE
    if _PARENT_CLAUSE_CACHE is not None:
        return _PARENT_CLAUSE_CACHE

    p = Path(corpus_path or "data/processed/legal_documents.jsonl")
    clause_map: dict[tuple[str, str, str], str] = {}
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    item = json.loads(line_str)
                    doc_id = item.get("doc_id", "")
                    art_num = str(item.get("article_number") or "").strip()
                    cl_num = str(item.get("clause_number") or "").strip()
                    pt = item.get("point")
                    # Only pure clauses (not points) act as parent clauses
                    if doc_id and art_num and cl_num and not pt:
                        clause_map[(doc_id, art_num, cl_num)] = (item.get("content") or "").strip()
        except Exception as e:
            logger.warning(f"Error building parent clause map: {e}")

    _PARENT_CLAUSE_CACHE = clause_map
    return _PARENT_CLAUSE_CACHE


def format_retrieval_text(chunk: dict[str, Any], enrich_parent: bool = True) -> str:
    """Enriches raw legal chunk content with hierarchical legal structural context and parent clause text.
    
    Excludes URLs, raw SHA256 hashes, timestamps, and internal flags to maintain
    a pure semantic space for dense retrieval.
    """
    header_parts = []

    doc_title = chunk.get("doc_title") or chunk.get("document_no")
    if doc_title:
        header_parts.append(f"Văn bản: {doc_title}")

    chapter = chunk.get("chapter")
    if chapter:
        header_parts.append(f"Chương: {chapter}")

    art_num = chunk.get("article_number")
    art_title = chunk.get("article_title")
    if art_num and art_title:
        header_parts.append(f"Điều {art_num}: {art_title}")
    elif art_num:
        header_parts.append(f"Điều {art_num}")

    clause_num = chunk.get("clause_number")
    point = chunk.get("point")
    content = (chunk.get("content") or "").strip()

    doc_id = chunk.get("doc_id", "")
    art_str = str(art_num or "").strip()
    cl_str = str(clause_num or "").strip()

    # Look up parent clause text for points if enrichment is requested
    parent_clause_text = ""
    if enrich_parent and point and cl_str:
        pc_map = get_parent_clause_map()
        parent_clause_text = pc_map.get((doc_id, art_str, cl_str), "")

    if clause_num:
        if parent_clause_text:
            header_parts.append(f"Khoản {clause_num}: {parent_clause_text}")
        else:
            header_parts.append(f"Khoản {clause_num}")

    if point:
        header_parts.append(f"Điểm {point}")

    header = " | ".join(header_parts)
    
    if header:
        return f"{header}\nNội dung: {content}"
    return f"Nội dung: {content}"


def compute_corpus_fingerprint(
    corpus_path: Union[str, Path],
    model_name: str = DEFAULT_MODEL_NAME,
    config: Optional[dict[str, Any]] = None,
) -> str:
    """Computes a deterministic SHA256 fingerprint for index versioning."""
    p = Path(corpus_path)
    if not p.exists():
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    corpus_hash = h.hexdigest()

    meta_payload = {
        "corpus_sha256": corpus_hash,
        "model_name": model_name,
        "dimension": DEFAULT_EMBEDDING_DIM,
        "config": config or {},
    }
    encoded = json.dumps(meta_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class LocalBGEEmbeddings:
    """Local dense embedding model wrapper around BAAI/bge-m3."""

    _instance: Optional[LocalBGEEmbeddings] = None
    _model: Optional[SentenceTransformer] = None

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
        normalize_embeddings: bool = True,
        cache_folder: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self.cache_folder = cache_folder
        self._ensure_model_loaded()
    def _ensure_model_loaded(self):
        if LocalBGEEmbeddings._model is None:
            logger.info(f"Loading local embedding model: {self.model_name} on {self.device}...")
            import torch
            if torch.get_num_threads() < 8:
                torch.set_num_threads(min(8, torch.get_num_threads() * 2))
            LocalBGEEmbeddings._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.cache_folder,
            )
            LocalBGEEmbeddings._model.max_seq_length = 1024
            logger.info("Local embedding model loaded successfully.")

    @property
    def model(self) -> SentenceTransformer:
        self._ensure_model_loaded()
        assert LocalBGEEmbeddings._model is not None
        return LocalBGEEmbeddings._model

    @property
    def dimension(self) -> int:
        return DEFAULT_EMBEDDING_DIM

    def embed_documents(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
    ) -> List[List[float]]:
        """Generates dense vector embeddings for a list of documents."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a single query string."""
        embedding = self.model.encode(
            text,
            show_progress_bar=False,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return embedding.tolist()
