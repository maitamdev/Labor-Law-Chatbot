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
import os
from pathlib import Path
from typing import Any, List, Optional, Union

# Enforce 100% offline mode for Hugging Face Hub (zero external network requests, zero warnings, zero progress bars)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

FALLBACK_MODEL_NAME = "BAAI/bge-m3"


def _detect_default_embedding_model() -> str:
    """Detects available local embedding model.
    Prioritizes explicit environment variable, then checks local cache for AITeamVN/Vietnamese_Embedding_v2,
    and cleanly falls back to BAAI/bge-m3 if not downloaded yet.
    """
    explicit = os.environ.get("EMBEDDING_MODEL_NAME")
    if explicit:
        return explicit
    try:
        aiteam_path = LocalBGEEmbeddings._resolve_local_model_path("AITeamVN/Vietnamese_Embedding_v2")
        if os.path.isdir(aiteam_path):
            return "AITeamVN/Vietnamese_Embedding_v2"
    except Exception:
        pass
    return FALLBACK_MODEL_NAME


DEFAULT_MODEL_NAME = _detect_default_embedding_model()
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

    @staticmethod
    def _resolve_local_model_path(model_name: str, cache_folder: Optional[str] = None) -> str:
        """Resolves local snapshot directory for model to guarantee 100% offline loading without HF Hub checks."""
        if os.path.isdir(model_name):
            return model_name

        sanitized = "models--" + model_name.replace("/", "--")
        search_dirs = []
        if cache_folder and os.path.isdir(cache_folder):
            search_dirs.append(cache_folder)

        hf_home = os.environ.get("HF_HOME")
        if hf_home and os.path.isdir(hf_home):
            search_dirs.append(os.path.join(hf_home, "hub"))
        search_dirs.append(os.path.expanduser("~/.cache/huggingface/hub"))

        for base in search_dirs:
            snap_dir = os.path.join(base, sanitized, "snapshots")
            if os.path.isdir(snap_dir):
                snapshots = [
                    os.path.join(snap_dir, s)
                    for s in os.listdir(snap_dir)
                    if os.path.isdir(os.path.join(snap_dir, s))
                ]
                # Filter for valid SentenceTransformer snapshots (must contain modules.json)
                valid_snapshots = [
                    s for s in snapshots if os.path.isfile(os.path.join(s, "modules.json"))
                ]
                if not valid_snapshots:
                    valid_snapshots = [
                        s for s in snapshots if os.path.isfile(os.path.join(s, "config.json"))
                    ]
                if valid_snapshots:
                    valid_snapshots.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    return valid_snapshots[0]

        return model_name

    def _ensure_model_loaded(self):
        if LocalBGEEmbeddings._model is None:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

            target_path = self._resolve_local_model_path(self.model_name, self.cache_folder)

            # If target model path is not a local folder on disk, seamlessly use verified fallback
            if not os.path.isdir(target_path) and self.model_name != FALLBACK_MODEL_NAME:
                fallback_path = self._resolve_local_model_path(FALLBACK_MODEL_NAME, self.cache_folder)
                if os.path.isdir(fallback_path):
                    logger.info(f"Primary model '{self.model_name}' not cached locally; seamlessly using local model: {fallback_path}")
                    target_path = fallback_path

            logger.info(f"Loading local embedding model: {target_path} on {self.device}...")
            import torch
            if torch.get_num_threads() < 8:
                torch.set_num_threads(min(8, torch.get_num_threads() * 2))
            try:
                LocalBGEEmbeddings._model = SentenceTransformer(
                    target_path,
                    device=self.device,
                    cache_folder=self.cache_folder,
                    local_files_only=True,
                )
            except Exception as e:
                # Attempt to fall back to BAAI/bge-m3
                fallback_path = self._resolve_local_model_path(FALLBACK_MODEL_NAME, self.cache_folder)
                logger.info(f"Falling back to local model: {fallback_path}...")
                try:
                    LocalBGEEmbeddings._model = SentenceTransformer(
                        fallback_path,
                        device=self.device,
                        cache_folder=self.cache_folder,
                        local_files_only=True,
                    )
                except Exception as e2:
                    logger.warning(f"Local fallback {fallback_path} failed: {e2}. Attempting standard load...")
                    LocalBGEEmbeddings._model = SentenceTransformer(
                        FALLBACK_MODEL_NAME,
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
