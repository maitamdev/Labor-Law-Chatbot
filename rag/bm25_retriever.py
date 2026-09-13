# -*- coding: utf-8 -*-
"""
VietLabor AI - BM25 Lexical Retriever
Provides fast local BM25 indexing and retrieval using bm25s,
featuring Unicode-compliant Vietnamese legal entity preservation
(document numbers, Điều/Khoản, percentages, monetary amounts).
Supports both segmented and whitespace tokenization for benchmarking.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union
import unicodedata

import bm25s
from pyvi import ViTokenizer

from rag.embeddings import format_retrieval_text

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = Path("storage/bm25")
DEFAULT_CORPUS_PATH = Path("data/processed/legal_documents.jsonl")


def tokenize_legal_vietnamese(text: str, mode: str = "segmented") -> List[str]:
    """Tokenizes Vietnamese legal text while strictly preserving legal syntax.
    
    Preserves:
    - Document numbers: e.g. 145/2020/NĐ-CP, 18/VBHN-VPQH, 45/2019/QH14
    - Articles & clauses: 'Điều 25' -> 'điều_25', 'điều', '25'; 'Khoản 1' -> 'khoản_1', 'khoản', '1'
    - Percentages: 150%, 50%, 100%
    - Monetary amounts / dotted numbers: 5.310.000, 75.000.000
    - Vietnamese compound words (when mode == "segmented")
    """
    if not text:
        return []

    # 1. Normalize Unicode NFKC & lowercase
    norm_text = unicodedata.normalize("NFKC", text).lower()

    # 2. Protect document numbers (e.g. 145/2020/nđ-cp, 18/vbhn-vpqh)
    doc_nums = re.findall(r"[a-zà-ỹ0-9]+(?:/[a-zà-ỹ0-9\-_]+)+", norm_text)
    placeholder_map: Dict[str, str] = {}
    for i, dn in enumerate(doc_nums):
        placeholder = f"__docnum_{i}__"
        placeholder_map[placeholder] = dn
        norm_text = norm_text.replace(dn, placeholder)

    # 3. Protect percentages (e.g. 150%, 200%)
    percents = re.findall(r"\d+(?:[.,]\d+)?%", norm_text)
    for i, pc in enumerate(percents):
        placeholder = f"__percent_{i}__"
        placeholder_map[placeholder] = pc
        norm_text = norm_text.replace(pc, placeholder)

    # 4. Protect formatted numbers (e.g. 5.310.000)
    nums = re.findall(r"\d+(?:\.\d+)+", norm_text)
    for i, nm in enumerate(nums):
        placeholder = f"__num_{i}__"
        placeholder_map[placeholder] = nm
        norm_text = norm_text.replace(nm, placeholder)

    # 5. Expand article and clause markers for dual matching:
    # 'điều 25' -> 'điều_25 điều 25'
    norm_text = re.sub(r"\bđiều\s+(\d+)\b", r"điều_\1 điều \1", norm_text)
    norm_text = re.sub(r"\bkhoản\s+(\d+)\b", r"khoản_\1 khoản \1", norm_text)
    norm_text = re.sub(r"\bđiểm\s+([a-zđ])\b", r"điểm_\1 điểm \1", norm_text)

    # 6. Apply segmentation if requested
    if mode == "segmented":
        processed_text = ViTokenizer.tokenize(norm_text)
    else:
        processed_text = norm_text

    # 7. Restore protected entities
    for placeholder, original in placeholder_map.items():
        processed_text = processed_text.replace(placeholder, original)

    # 8. Token extraction regex
    # Matches:
    # - doc numbers: 145/2020/nđ-cp
    # - dotted numbers: 5.310.000
    # - percentages: 150%
    # - compound/simple words: điều_25, thời_gian, luật, 25
    pattern = r"[a-zà-ỹ0-9]+(?:/[a-zà-ỹ0-9\-_]+)+|\d+(?:\.\d+)+|\d+(?:[.,]\d+)?%|[a-zà-ỹ0-9_]+"
    tokens = re.findall(pattern, processed_text)

    return tokens


class BM25Retriever:
    """Local BM25 lexical retriever using bm25s."""

    def __init__(
        self,
        persist_dir: Union[str, Path] = DEFAULT_PERSIST_DIR,
        corpus_path: Union[str, Path] = DEFAULT_CORPUS_PATH,
        tokenizer_mode: str = "segmented",
    ):
        self.persist_dir = Path(persist_dir)
        self.corpus_path = Path(corpus_path)
        self.tokenizer_mode = tokenizer_mode
        self.meta_file = self.persist_dir / "index_meta.json"
        self.chunks_file = self.persist_dir / "chunks.json"

        self.retriever: Optional[bm25s.BM25] = None
        self.chunks_data: List[dict[str, Any]] = []

    def compute_fingerprint(self) -> str:
        """Computes deterministic SHA256 fingerprint for the BM25 index."""
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {self.corpus_path}")

        h = hashlib.sha256()
        with open(self.corpus_path, "rb") as f:
            while block := f.read(65536):
                h.update(block)
        corpus_hash = h.hexdigest()

        meta_payload = {
            "corpus_sha256": corpus_hash,
            "engine": "bm25s",
            "tokenizer_mode": self.tokenizer_mode,
        }
        encoded = json.dumps(meta_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def is_index_valid(self) -> bool:
        """Checks if the stored BM25 index exists and matches the corpus fingerprint."""
        if not self.meta_file.exists() or not self.chunks_file.exists():
            return False

        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            current_fp = self.compute_fingerprint()
            if meta.get("fingerprint") != current_fp:
                return False
            return True
        except Exception:
            return False

    def build_index(self, force: bool = False) -> dict[str, Any]:
        """Builds or reuses the BM25 index from the production corpus."""
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {self.corpus_path}")

        if not force and self.is_index_valid():
            logger.info("BM25 index fingerprint matches. Loading existing index.")
            self.load_index()
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Building BM25 index (mode={self.tokenizer_mode}) at {self.persist_dir}...")

        # Read corpus chunks
        chunks: List[dict[str, Any]] = []
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    chunks.append(json.loads(line_str))

        total_chunks = len(chunks)
        tokenized_corpus: List[List[str]] = []
        simplified_chunks: List[dict[str, Any]] = []

        for c in chunks:
            retrieval_text = format_retrieval_text(c)
            tokens = tokenize_legal_vietnamese(retrieval_text, mode=self.tokenizer_mode)
            tokenized_corpus.append(tokens)
            simplified_chunks.append({
                "chunk_id": c["chunk_id"],
                "doc_id": c.get("doc_id", ""),
                "doc_title": c.get("doc_title", ""),
                "document_no": c.get("document_no", ""),
                "article_number": str(c.get("article_number") or ""),
                "article_title": c.get("article_title") or "",
                "clause_number": str(c.get("clause_number") or ""),
                "point": str(c.get("point") or ""),
                "source_page_start": c.get("source_page_start", 0),
                "source_page_end": c.get("source_page_end", 0),
                "official_source": c.get("official_source", ""),
                "content": c.get("content", ""),
                "retrieval_text": retrieval_text,
            })

        # Initialize and index BM25
        retriever = bm25s.BM25()
        retriever.index(tokenized_corpus)

        # Save BM25 index to directory
        retriever.save(str(self.persist_dir))

        # Save chunk metadata
        with open(self.chunks_file, "w", encoding="utf-8") as f:
            json.dump(simplified_chunks, f, ensure_ascii=False)

        current_fp = self.compute_fingerprint()
        meta = {
            "fingerprint": current_fp,
            "engine": "bm25s",
            "tokenizer_mode": self.tokenizer_mode,
            "total_chunks": total_chunks,
            "indexed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self.retriever = retriever
        self.chunks_data = simplified_chunks
        logger.info(f"BM25 index successfully built for {total_chunks} chunks.")
        return meta

    def load_index(self) -> None:
        """Loads existing BM25 index and chunk metadata from disk."""
        if self.retriever is not None and self.chunks_data:
            return

        if not self.is_index_valid():
            self.build_index()
            return

        logger.info(f"Loading BM25 index from {self.persist_dir}...")
        self.retriever = bm25s.BM25.load(str(self.persist_dir), load_corpus=False)
        with open(self.chunks_file, "r", encoding="utf-8") as f:
            self.chunks_data = json.load(f)
        logger.info(f"BM25 index loaded ({len(self.chunks_data)} chunks).")

    def retrieve(self, query: str, top_k: int = 5) -> List[dict[str, Any]]:
        """Retrieves top-k relevant chunks using BM25 scoring."""
        clean_query = query.strip() if query else ""
        if not clean_query:
            return []

        if self.retriever is None or not self.chunks_data:
            self.load_index()

        assert self.retriever is not None

        query_tokens = tokenize_legal_vietnamese(clean_query, mode=self.tokenizer_mode)
        if not query_tokens:
            return []

        actual_k = min(top_k, len(self.chunks_data))
        docs, scores = self.retriever.retrieve([query_tokens], k=actual_k, show_progress=False)

        results: List[dict[str, Any]] = []
        if len(docs) == 0:
            return results

        doc_indices = docs[0]
        score_values = scores[0]

        for doc_idx, score in zip(doc_indices, score_values):
            idx = int(doc_idx)
            chunk_info = self.chunks_data[idx]
            results.append({
                "chunk_id": chunk_info["chunk_id"],
                "score": float(score),
                "content": chunk_info["content"],
                "retrieval_text": chunk_info["retrieval_text"],
                "metadata": {
                    "doc_id": chunk_info["doc_id"],
                    "doc_title": chunk_info["doc_title"],
                    "document_no": chunk_info["document_no"],
                    "article_number": chunk_info["article_number"],
                    "article_title": chunk_info["article_title"],
                    "clause_number": chunk_info["clause_number"],
                    "point": chunk_info["point"],
                    "source_page_start": chunk_info["source_page_start"],
                    "source_page_end": chunk_info["source_page_end"],
                    "official_source": chunk_info["official_source"],
                }
            })

        return results
