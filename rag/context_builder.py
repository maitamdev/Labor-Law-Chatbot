# -*- coding: utf-8 -*-
"""
VietLabor AI - Statutory Context Builder (Phase 5D)
Assembles compact, hierarchically enriched legal evidence blocks labeled with
temporary evidence IDs ([E1], [E2], ...) for the LLM.
Eliminates context omission, dilutive redundant text, and raw chunk-ID hallucination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rag.evidence_mapper import EvidenceBlock, EvidenceMapper

logger = logging.getLogger(__name__)


@dataclass
class FormattedContext:
    """Encapsulates the assembled prompt context and metadata registry."""
    prompt_context: str
    available_chunk_ids: Set[str]
    chunk_metadata_registry: Dict[str, Dict[str, Any]]
    total_chunks_in_context: int
    grouped_articles_count: int
    evidence_blocks: List[EvidenceBlock] = field(default_factory=list)
    evidence_mapper: Optional[EvidenceMapper] = None


class ContextBuilder:
    """Builds compact statutory evidence blocks with temporary Evidence IDs."""

    _corpus_cache: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        max_context_chars: int = 8000,
        max_chunks: int = 10,
        max_per_issue_blocks: int = 4,
        corpus_path: Optional[str] = "data/processed/legal_documents.jsonl",
    ):
        self.max_context_chars = max_context_chars
        self.max_chunks = max_chunks
        self.max_per_issue_blocks = max_per_issue_blocks
        self.corpus_path = corpus_path
        self._ensure_corpus_loaded()

    def _ensure_corpus_loaded(self) -> None:
        """Loads canonical legal documents corpus for hierarchy completion and statutory bridges."""
        if ContextBuilder._corpus_cache is not None:
            return

        corpus_file = Path(self.corpus_path) if self.corpus_path else None
        if not corpus_file or not corpus_file.exists():
            ContextBuilder._corpus_cache = {
                "by_id": {},
                "by_article": {},
                "by_clause": {},
                "clause_parent": {},
            }
            return

        by_id: Dict[str, Dict[str, Any]] = {}
        by_article: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        by_clause: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        clause_parent: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        try:
            with open(corpus_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    cid = item.get("chunk_id", "")
                    doc_id = item.get("doc_id", "")
                    art_num = str(item.get("article_number") or "").strip()
                    cl_num = str(item.get("clause_number") or "").strip()
                    pt = str(item.get("point") or "").strip()

                    by_id[cid] = item

                    if doc_id and art_num:
                        art_key = (doc_id, art_num)
                        if art_key not in by_article:
                            by_article[art_key] = []
                        by_article[art_key].append(item)

                        if cl_num:
                            cl_key = (doc_id, art_num, cl_num)
                            if cl_key not in by_clause:
                                by_clause[cl_key] = []
                            by_clause[cl_key].append(item)

                            if not pt:
                                clause_parent[cl_key] = item

            ContextBuilder._corpus_cache = {
                "by_id": by_id,
                "by_article": by_article,
                "by_clause": by_clause,
                "clause_parent": clause_parent,
            }
        except Exception as e:
            logger.error(f"Error loading corpus in ContextBuilder: {e}")
            ContextBuilder._corpus_cache = {"by_id": {}, "by_article": {}, "by_clause": {}, "clause_parent": {}}

    def _get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        cache = ContextBuilder._corpus_cache or {}
        return cache.get("by_id", {}).get(chunk_id)

    def _get_clause_parent(self, doc_id: str, art_num: str, cl_num: str) -> Optional[Dict[str, Any]]:
        cache = ContextBuilder._corpus_cache or {}
        return cache.get("clause_parent", {}).get((doc_id, str(art_num), str(cl_num)))

    def _create_compact_evidence_block(
        self,
        chunk: Dict[str, Any],
        evidence_idx: int,
        issue_id: Optional[str] = None,
    ) -> EvidenceBlock:
        """Converts a raw chunk into a self-contained, compact statutory evidence block."""
        cid = chunk.get("chunk_id", "")
        meta = chunk.get("metadata") or chunk

        doc_id = meta.get("doc_id", "")
        doc_no = meta.get("document_no", doc_id)
        doc_title = meta.get("doc_title", doc_no)
        art_num = meta.get("article_number")
        art_title = meta.get("article_title", "")
        cl_num = meta.get("clause_number")
        pt = meta.get("point")
        official_src = meta.get("official_source") or meta.get("source_url")
        p_start = meta.get("source_page_start")

        # Compact content assembly:
        # If chunk is a Point (e.g. Điều 35 Khoản 1 Điểm b), attach parent Clause lead-in text directly
        raw_content = chunk.get("content", "").strip()
        unified_content = raw_content

        if pt and cl_num and art_num and doc_id:
            parent_chunk = self._get_clause_parent(doc_id, str(art_num), str(cl_num))
            if parent_chunk:
                parent_text = parent_chunk.get("content", "").strip()
                # If parent lead-in ends with colon, attach
                if parent_text and not raw_content.startswith(parent_text[:30]):
                    unified_content = f"{parent_text}\n{raw_content}"

        return EvidenceBlock(
            evidence_id=f"E{evidence_idx}",
            chunk_id=cid,
            document_no=doc_no,
            document_title=doc_title,
            article_number=int(art_num) if art_num is not None and str(art_num).isdigit() else None,
            article_title=art_title,
            clause_number=int(cl_num) if cl_num is not None and str(cl_num).isdigit() else None,
            point=pt,
            content=unified_content,
            source_url=official_src,
            page_number=int(p_start) if p_start is not None and str(p_start).isdigit() else None,
            issue_id=issue_id,
        )

    def build_context(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        multi_issue_candidates: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        enforce_statutory_bridge: bool = True,
        expand_siblings: bool = True,
    ) -> FormattedContext:
        """Builds organized, compact legal evidence blocks labeled [E1], [E2], ...
        
        Args:
            retrieved_chunks: Global candidate chunks.
            multi_issue_candidates: Optional mapping from issue_id -> candidate chunks for compound queries.
            enforce_statutory_bridge: When True, ensures delegating bridges (e.g. Điều 35k1d BLLĐ for Điều 7 NĐ 145) are attached.
            expand_siblings: When True, expands sibling points under the same statutory clause.
        """
        if not retrieved_chunks and not multi_issue_candidates:
            return FormattedContext(
                prompt_context="[KHÔNG CÓ DỮ LIỆU PHÁP LUẬT NÀO ĐƯỢC TRUY XUẤT]",
                available_chunk_ids=set(),
                chunk_metadata_registry={},
                total_chunks_in_context=0,
                grouped_articles_count=0,
                evidence_blocks=[],
                evidence_mapper=EvidenceMapper(),
            )

        selected_chunks: List[Tuple[Dict[str, Any], Optional[str]]] = []
        seen_cids: Set[str] = set()

        # 1. Per-issue evidence selection if multi-issue compound query
        if multi_issue_candidates:
            for issue_id, candidates in multi_issue_candidates.items():
                issue_count = 0
                issue_pool: List[Dict[str, Any]] = []
                for c in candidates:
                    issue_pool.append(c)
                    if expand_siblings:
                        meta = c.get("metadata") or c
                        doc_id = meta.get("doc_id")
                        art_num = meta.get("article_number")
                        cl_num = meta.get("clause_number")
                        pt = meta.get("point")
                        if doc_id and art_num and cl_num and pt:
                            cl_key = (doc_id, str(art_num), str(cl_num))
                            cache = ContextBuilder._corpus_cache or {}
                            siblings = cache.get("by_clause", {}).get(cl_key, [])
                            for sib in siblings:
                                if sib.get("chunk_id") != c.get("chunk_id"):
                                    issue_pool.append(sib)

                for c in issue_pool:
                    cid = c.get("chunk_id", "")
                    if cid and cid not in seen_cids:
                        seen_cids.add(cid)
                        selected_chunks.append((c, issue_id))
                        issue_count += 1
                        if issue_count >= self.max_per_issue_blocks:
                            break
        else:
            # Single-issue: gather candidates with optional sibling expansion
            candidate_pool: List[Dict[str, Any]] = []
            for c in retrieved_chunks:
                candidate_pool.append(c)
                if expand_siblings:
                    meta = c.get("metadata") or c
                    doc_id = meta.get("doc_id")
                    art_num = meta.get("article_number")
                    cl_num = meta.get("clause_number")
                    pt = meta.get("point")
                    if doc_id and art_num and cl_num and pt:
                        cl_key = (doc_id, str(art_num), str(cl_num))
                        cache = ContextBuilder._corpus_cache or {}
                        siblings = cache.get("by_clause", {}).get(cl_key, [])
                        for sib in siblings:
                            if sib.get("chunk_id") != c.get("chunk_id"):
                                candidate_pool.append(sib)

            for c in candidate_pool:
                cid = c.get("chunk_id", "")
                if cid and cid not in seen_cids:
                    seen_cids.add(cid)
                    selected_chunks.append((c, None))
                    if len(selected_chunks) >= self.max_chunks:
                        break

        # 2. Statutory Bridge & Canonical Provision Pairing:
        # 2a. If Điều 7 NĐ 145 (flight crew) is present, ensure BLLĐ Điều 35k1d is also present!
        if enforce_statutory_bridge:
            has_nd145_d7 = any(
                str((c.get("metadata") or c).get("doc_id", "")) == "ND_145_2020" and
                str((c.get("metadata") or c).get("article_number", "")) == "7"
                for c, _ in selected_chunks
            )
            has_blld_35_1d = any(
                str((c.get("metadata") or c).get("doc_id", "")) == "VBHN_18_2026" and
                str((c.get("metadata") or c).get("article_number", "")) == "35" and
                str((c.get("metadata") or c).get("point", "")).lower() == "d"
                for c, _ in selected_chunks
            )
            if has_nd145_d7 and not has_blld_35_1d:
                bridge_chunk = self._get_chunk_by_id("VBHN_18_2026#d35-k1-d")
                if bridge_chunk:
                    selected_chunks.insert(0, (bridge_chunk, "statutory_bridge"))
                    seen_cids.add("VBHN_18_2026#d35-k1-d")

        # 3. Create Compact Evidence Blocks labeled [E1], [E2], ...
        evidence_blocks: List[EvidenceBlock] = []
        available_ids: Set[str] = set()
        registry: Dict[str, Dict[str, Any]] = {}
        prompt_parts: List[str] = []

        preamble = (
            "DƯỚI ĐÂY LÀ CÁC CĂN CỨ PHÁP LÝ ĐƯỢC CẤP CHO BẠN (ĐƯỢC ĐÁNH MÃ TỪ [E1], [E2], ...):\n"
            "BẠN BẮT BUỘC CHỈ SỬ DỤNG MÃ BẰNG CHỨNG (VÍ DỤ: E1, E2) TRONG CÂU TRẢ LỜI. "
            "TUYỆT ĐỐI KHÔNG TỰ VIẾT LẠI MÃ CHUNK HAY TỰ CHẾ MÃ KHÁC.\n\n"
        )
        current_chars = len(preamble)

        for idx, (chk, issue_id) in enumerate(selected_chunks, start=1):
            block = self._create_compact_evidence_block(chk, len(evidence_blocks) + 1, issue_id)
            block_text = block.format_for_llm()

            # Check character budget (allow at least 2 blocks even if long, ensure strict max_context_chars limit)
            if current_chars + len(block_text) + 42 > self.max_context_chars and len(evidence_blocks) >= 2:
                break

            evidence_blocks.append(block)
            available_ids.add(block.chunk_id)
            registry[block.chunk_id] = {
                "chunk_id": block.chunk_id,
                "evidence_id": block.evidence_id,
                "doc_id": (chk.get("metadata") or chk).get("doc_id", block.document_no),
                "document_no": block.document_no,
                "document_title": block.document_title,
                "article_number": block.article_number,
                "article_title": block.article_title,
                "clause_number": block.clause_number,
                "point": block.point,
                "source_url": block.source_url,
                "page_number": block.page_number,
            }

            # If block has a parent clause chunk, also register parent in available_ids and registry
            meta = chk.get("metadata") or chk
            doc_id = meta.get("doc_id")
            art_num = meta.get("article_number")
            cl_num = meta.get("clause_number")
            pt = meta.get("point")
            if pt and cl_num and art_num and doc_id:
                parent_chunk = self._get_clause_parent(doc_id, str(art_num), str(cl_num))
                if parent_chunk:
                    pid = parent_chunk.get("chunk_id", "")
                    if pid and pid not in available_ids and len(available_ids) < self.max_chunks:
                        available_ids.add(pid)
                        if pid not in registry:
                            pmeta = parent_chunk.get("metadata") or parent_chunk
                            registry[pid] = {
                                "chunk_id": pid,
                                "evidence_id": block.evidence_id,
                                "doc_id": pmeta.get("doc_id", block.document_no),
                                "document_no": block.document_no,
                                "document_title": block.document_title,
                                "article_number": block.article_number,
                                "article_title": block.article_title,
                                "clause_number": block.clause_number,
                                "point": None,
                                "source_url": block.source_url,
                                "page_number": block.page_number,
                            }
            prompt_parts.append(block_text)
            current_chars += len(block_text) + 42

        # 4. Initialize EvidenceMapper
        mapper = EvidenceMapper()
        mapper.register_blocks(evidence_blocks)

        formatted_prompt = (
            "DƯỚI ĐÂY LÀ CÁC CĂN CỨ PHÁP LÝ ĐƯỢC CẤP CHO BẠN (ĐƯỢC ĐÁNH MÃ TỪ [E1], [E2], ...):\n"
            "BẠN BẮT BUỘC CHỈ SỬ DỤNG MÃ BẰNG CHỨNG (VÍ DỤ: E1, E2) TRONG CÂU TRẢ LỜI. "
            "TUYỆT ĐỐI KHÔNG TỰ VIẾT LẠI MÃ CHUNK HAY TỰ CHẾ MÃ KHÁC.\n\n"
            + "\n----------------------------------------\n".join(prompt_parts)
        )

        unique_articles = {
            (b.document_no or "", b.article_number)
            for b in evidence_blocks
            if b.article_number is not None
        }
        grouped_count = len(unique_articles) if unique_articles else len(evidence_blocks)

        return FormattedContext(
            prompt_context=formatted_prompt,
            available_chunk_ids=available_ids,
            chunk_metadata_registry=registry,
            total_chunks_in_context=len(available_ids),
            grouped_articles_count=grouped_count,
            evidence_blocks=evidence_blocks,
            evidence_mapper=mapper,
        )
