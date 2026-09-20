# -*- coding: utf-8 -*-
"""
VietLabor AI - Cross-Encoder Reranker
Optimizes candidate precision after BM25 + Dense Hybrid retrieval (RRF)
using Cross-Encoder models (e.g., Alibaba-NLP/gte-multilingual-reranker-base or BAAI/bge-reranker-base).
Includes GPU detection, batching, caching, and graceful fallback.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

logger = logging.getLogger(__name__)

DEFAULT_RERANKER_MODEL = os.environ.get(
    "RERANKER_MODEL_NAME", "Alibaba-NLP/gte-multilingual-reranker-base"
)


class CrossEncoderReranker:
    """Cross-Encoder Reranker for Vietnamese legal chunk re-scoring.
    
    Cross-encoders take (query, document) pairs simultaneously into the Transformer,
    allowing full cross-attention between legal query terms and statutory clauses.
    This delivers much higher precision than bi-encoder cosine similarity alone.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        device: Optional[str] = None,
        max_length: int = 512,
        batch_size: int = 16,
        enabled: bool = True,
    ):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.enabled = enabled
        self._model = None
        self._initialized = False

        if device is not None:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _resolve_local_model_path(self, model_name: str) -> Optional[str]:
        """Checks if the model snapshot is already available in local HF cache."""
        if os.path.isdir(model_name):
            return model_name

        sanitized = "models--" + model_name.replace("/", "--")
        hf_home = os.environ.get("HF_HOME")
        search_dirs = []
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
                valid_snapshots = [
                    s for s in snapshots
                    if os.path.isfile(os.path.join(s, "config.json"))
                    or os.path.isfile(os.path.join(s, "modules.json"))
                ]
                if valid_snapshots:
                    valid_snapshots.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    return valid_snapshots[0]
        return None

    def load_model(self) -> bool:
        """Loads the CrossEncoder model with graceful fallback."""
        if self._initialized:
            return self._model is not None

        if not self.enabled:
            logger.info("CrossEncoderReranker is disabled via configuration.")
            self._initialized = True
            return False

        try:
            from sentence_transformers import CrossEncoder

            local_snap = self._resolve_local_model_path(self.model_name)
            target = local_snap if local_snap else self.model_name
            
            logger.info(
                f"Loading CrossEncoderReranker ({target}) on {self.device}..."
            )
            t0 = time.perf_counter()

            # Attempt local files first if offline or snapshot exists
            try:
                self._model = CrossEncoder(
                    target,
                    max_length=self.max_length,
                    device=self.device,
                    local_files_only=bool(local_snap),
                )
            except Exception as e_local:
                logger.warning(
                    f"Local load for reranker {target} failed: {e_local}. "
                    f"Attempting standard load..."
                )
                self._model = CrossEncoder(
                    self.model_name,
                    max_length=self.max_length,
                    device=self.device,
                )

            t1 = time.perf_counter()
            logger.info(f"CrossEncoderReranker loaded successfully in {t1 - t0:.2f}s.")
            self._initialized = True
            return True
        except Exception as exc:
            logger.warning(
                f"Could not load CrossEncoder model ({self.model_name}): {exc}. "
                "Retaining hybrid RRF ranking without reranking."
            )
            self._model = None
            self._initialized = True
            return False

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Reranks candidate legal chunks by cross-encoder score.
        
        Args:
            query: User's legal question or resolved query.
            candidates: List of chunk dictionaries from retrieval stage.
            top_k: Maximum number of top chunks to return. If None, returns all candidates sorted.
            
        Returns:
            Reranked list of candidate dictionaries with 'rerank_score' attached.
        """
        if not candidates:
            return []

        clean_query = query.strip() if query else ""
        if not clean_query:
            return candidates[:top_k] if top_k else candidates

        if not self._initialized:
            self.load_model()

        if self._model is None:
            # Fallback: maintain original ordering
            return candidates[:top_k] if top_k else candidates

        try:
            # Construct text pairs: (query, passage)
            pairs: List[Tuple[str, str]] = []
            for c in candidates:
                # Include document and article title in passage text for richer cross-attention
                meta = c.get("metadata", {})
                doc_title = meta.get("doc_title", "")
                art_num = meta.get("article_number", "")
                art_title = meta.get("article_title", "")
                content = c.get("content", "")

                prefix = ""
                if art_num and art_title:
                    prefix = f"Điều {art_num}. {art_title}\n"
                elif art_num:
                    prefix = f"Điều {art_num}\n"
                if doc_title:
                    prefix = f"[{doc_title}] " + prefix

                passage_text = prefix + content
                pairs.append((clean_query, passage_text))

            # Run batch prediction
            scores = self._model.predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )

            # Assign rerank scores and sort
            scored_candidates = []
            for i, chunk in enumerate(candidates):
                c_copy = dict(chunk)
                score = float(scores[i])
                c_copy["rerank_score"] = score
                c_copy["initial_score"] = c_copy.get("score", 0.0)
                # Primary ranking becomes the reranker score
                c_copy["score"] = score
                scored_candidates.append(c_copy)

            # Sort descending by rerank_score
            scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

            return scored_candidates[:top_k] if top_k else scored_candidates

        except Exception as e:
            logger.warning(f"Error during cross-encoder reranking: {e}. Falling back to initial ranking.")
            return candidates[:top_k] if top_k else candidates
