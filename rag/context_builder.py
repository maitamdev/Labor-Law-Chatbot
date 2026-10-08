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
        max_context_chars: int = 12000,
        max_chunks: int = 10,
        max_per_issue_blocks: int = 4,
        corpus_path: Optional[str] = None,
    ):
        self.max_context_chars = max_context_chars
        self.max_chunks = max_chunks
        self.max_per_issue_blocks = max_per_issue_blocks
        if corpus_path is None:
            if Path("data/processed/legal_documents_v3.jsonl").exists():
                corpus_path = "data/processed/legal_documents_v3.jsonl"
            else:
                corpus_path = "data/processed/legal_documents.jsonl"
        self.corpus_path = corpus_path
        self._ensure_corpus_loaded()

    def _ensure_corpus_loaded(self) -> None:
        """Loads canonical legal documents corpus for hierarchy completion and statutory bridges."""
        if ContextBuilder._corpus_cache is not None and len(ContextBuilder._corpus_cache.get("by_id", {})) >= 3500:
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
        doc_no = meta.get("document_no") or meta.get("doc_id", "")
        doc_title = meta.get("doc_title") or meta.get("document_title") or doc_no
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
        allow_repealed: bool = False,
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

            # 2b. Vocational training obligations (Điều 6k2c + Điều 60)
            training_resp_issue_id = None
            has_training_resp = False
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                pt_val = str(meta.get("point", "")).lower()
                c_text = str(c.get("content", "")).lower()
                if d_id == "VBHN_18_2026":
                    if (a_num == "6" and pt_val == "c") or a_num == "60" or ("đào tạo" in c_text and a_num in ["6", "60"]):
                        has_training_resp = True
                        if i_id:
                            training_resp_issue_id = i_id
                            break

            if has_training_resp:
                target_iid = training_resp_issue_id or "statutory_bridge"
                training_cids = ["VBHN_18_2026#d6-k2-c", "VBHN_18_2026#d60-k1", "VBHN_18_2026#d60-k2"]
                selected_chunks = [(c, i_id) for c, i_id in selected_chunks if not (i_id == target_iid and c.get("chunk_id") in training_cids)]
                for cid in training_cids:
                    seen_cids.discard(cid)
                canonical_resp_chunks = []
                for cid in training_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_resp_chunks.append((b_chk, target_iid))
                        seen_cids.add(cid)
                selected_chunks.extend(canonical_resp_chunks)

            # 2c. Vocational training contract, commitment & cost refund (Điều 62 + Điều 40k3)
            training_contract_issue_id = None
            has_training_contract = False
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                c_text = str(c.get("content", "")).lower()
                if d_id == "VBHN_18_2026":
                    if a_num == "62" or (a_num == "40" and "đào tạo" in c_text):
                        has_training_contract = True
                        if i_id:
                            training_contract_issue_id = i_id
                            break

            if has_training_contract:
                target_iid = training_contract_issue_id or "statutory_bridge"
                contract_cids = ["VBHN_18_2026#d62-k1", "VBHN_18_2026#d62-k2-c", "VBHN_18_2026#d62-k2-d", "VBHN_18_2026#d62-k3", "VBHN_18_2026#d40-k3"]
                selected_chunks = [(c, i_id) for c, i_id in selected_chunks if not (i_id == target_iid and c.get("chunk_id") in contract_cids)]
                for cid in contract_cids:
                    seen_cids.discard(cid)
                canonical_contract_chunks = []
                for cid in contract_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_contract_chunks.append((b_chk, target_iid))
                        seen_cids.add(cid)
                selected_chunks.extend(canonical_contract_chunks)

            # 2d. Statutory Employee Rights Bridge (VBHN_18_2026#d5-k1 toàn văn 7 điểm)
            rights_issue_id = None
            has_employee_rights = False
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                c_text = str(c.get("content", "")).lower()
                if d_id == "VBHN_18_2026" and a_num == "5":
                    if any(k in c_text for k in ["quyền của người lao động", "có các quyền sau đây", "quyền, nghĩa vụ của người lao động"]):
                        has_employee_rights = True
                        if i_id:
                            rights_issue_id = i_id
                            break

            if has_employee_rights:
                target_iid = rights_issue_id or "statutory_bridge"
                d5_k1_chk = self._get_chunk_by_id("VBHN_18_2026#d5-k1")
                if d5_k1_chk:
                    # Remove partial point chunks of Điều 5 for this issue
                    selected_chunks = [(c, i_id) for c, i_id in selected_chunks if not (i_id == target_iid and (c.get("metadata") or c).get("article_number") in [5, "5"])]
                    selected_chunks.insert(0, (d5_k1_chk, target_iid))
                    seen_cids.add("VBHN_18_2026#d5-k1")

            # 2e. Safety Refusal & Discipline / Monetary Fine Bridge
            safety_issue_id = next((
                i_id for c, i_id in selected_chunks
                if str((c.get("metadata") or c).get("doc_id", "")) == "L_84_2015"
                and str((c.get("metadata") or c).get("article_number", "")) == "6"
                and i_id
            ), None)
            has_safety_refusal = safety_issue_id is not None
            if safety_issue_id:
                # Attach the BLLĐ rights bridge to the issue that actually owns
                # the safety-refusal provision, regardless of question order.
                d5_d_chk = self._get_chunk_by_id("VBHN_18_2026#d5-k1-d")
                if d5_d_chk and not any(c.get("chunk_id") == "VBHN_18_2026#d5-k1-d" and i_id == safety_issue_id for c, i_id in selected_chunks):
                    selected_chunks.insert(0, (d5_d_chk, safety_issue_id))
                    seen_cids.add("VBHN_18_2026#d5-k1-d")

            discipline_issue_id = next((
                i_id for c, i_id in selected_chunks
                if i_id and (
                    str((c.get("metadata") or c).get("article_number", "")) in {"124", "127"}
                    or any(k in str(c.get("content", "")).lower() for k in ["kỷ luật", "khiển trách", "cắt lương", "phạt tiền"])
                )
            ), None)
            if has_safety_refusal and discipline_issue_id:
                target_iid = discipline_issue_id
                discipline_cids = ["VBHN_18_2026#d127-k2", "VBHN_18_2026#d124-k1", "L_84_2015#d6-k1-đ", "L_84_2015#d12-k4"]
                for cid in discipline_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        if not any(c.get("chunk_id") == cid and i_id == target_iid for c, i_id in selected_chunks):
                            selected_chunks.append((b_chk, target_iid))
                            seen_cids.add(cid)

            # 2f. Mandatory Social Insurance Bridge (HĐLĐ >= 1 month)
            mand_ins_issue_id = None
            has_mand_ins = False
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                c_text = str(c.get("content", "")).lower()
                if (d_id == "VBHN_18_2026" and a_num == "168") or (d_id == "VBHN_58_2025" and a_num in ["2", "21"]) or ("đóng bảo hiểm" in c_text and "01 tháng" in c_text):
                    has_mand_ins = True
                    if i_id:
                        mand_ins_issue_id = i_id
                        break

            if has_mand_ins:
                target_iid = mand_ins_issue_id or "statutory_bridge"
                # Hard purge d168-k3 from the entire selected_chunks
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if not (c.get("chunk_id") == "VBHN_18_2026#d168-k3" or ((c.get("metadata") or c).get("doc_id") == "VBHN_18_2026" and str((c.get("metadata") or c).get("article_number")) == "168" and str((c.get("metadata") or c).get("clause_number")) == "3"))
                ]
                seen_cids.discard("VBHN_18_2026#d168-k3")

                mand_cids = ["VBHN_18_2026#d168-k1", "VBHN_58_2025#d2-k1-a", "VBHN_58_2025#d21", "ND_283_2026#d44-k3"]
                canonical_mand_chunks = []
                for cid in mand_cids:
                    existing = next((sc[0] for sc in selected_chunks if sc[0].get("chunk_id") == cid), None)
                    b_chk = existing or self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_mand_chunks.append((b_chk, target_iid))
                        seen_cids.add(cid)
                other_chunks = [sc for sc in selected_chunks if sc[1] != target_iid and sc[0].get("chunk_id") not in mand_cids]
                remaining_target = [sc for sc in selected_chunks if sc[1] == target_iid and sc[0].get("chunk_id") not in mand_cids]
                selected_chunks = canonical_mand_chunks + remaining_target + other_chunks

            # 2g. Uninsured Occupational Accident Bridge
            uninsured_issue_id = None
            has_uninsured_acc = False
            for c, i_id in selected_chunks:
                # Must not collide with mand_ins_issue_id if multi-issue exists
                if mand_ins_issue_id and i_id == mand_ins_issue_id and len(set(x[1] for x in selected_chunks if x[1])) > 1:
                    continue
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                c_text = str(c.get("content", "")).lower()
                if (d_id == "L_84_2015" and a_num in ["38", "39"]) or ("không đóng bảo hiểm" in c_text and "tai nạn" in c_text):
                    has_uninsured_acc = True
                    if i_id:
                        uninsured_issue_id = i_id
                        break

            if has_uninsured_acc:
                target_iid = uninsured_issue_id or "statutory_bridge"
                # Hard purge d168-k3 and d45
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if not (c.get("chunk_id") == "VBHN_18_2026#d168-k3" or ((c.get("metadata") or c).get("doc_id") == "L_84_2015" and str((c.get("metadata") or c).get("article_number")) == "45"))
                ]
                seen_cids.discard("VBHN_18_2026#d168-k3")
                seen_cids.discard("L_84_2015#d45")

                uninsured_cids = ["L_84_2015#d39-k4", "L_84_2015#d38-k2", "L_84_2015#d38-k3", "L_84_2015#d38-k4", "ND_283_2026#d44-k3"]
                canonical_uninsured_chunks = []
                for cid in uninsured_cids:
                    existing = next((sc[0] for sc in selected_chunks if sc[0].get("chunk_id") == cid), None)
                    b_chk = existing or self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_uninsured_chunks.append((b_chk, target_iid))
                        seen_cids.add(cid)
                non_target = [sc for sc in selected_chunks if sc[1] != target_iid and sc[0].get("chunk_id") not in uninsured_cids]
                selected_chunks = non_target + canonical_uninsured_chunks

            # 2h. Delayed Wage Payment & Labour Complaint Bridge
            wage_schedule_iid = None
            delayed_wage_iid = None
            complaint_iid = None

            for c, i_id in selected_chunks:
                c_text = str(c.get("content", "")).lower()
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                cid = c.get("chunk_id", "")

                if ("kỳ hạn trả lương" in c_text or "d97" in cid) and not wage_schedule_iid:
                    wage_schedule_iid = i_id
                if ("chậm trả lương" in c_text or "d97-k4" in cid) and not delayed_wage_iid:
                    delayed_wage_iid = i_id
                if ("khiếu nại" in c_text or "tạm ngừng làm việc" in c_text or "nd_24_2018" in cid.lower()) and not complaint_iid:
                    complaint_iid = i_id

            if wage_schedule_iid or delayed_wage_iid or complaint_iid:
                # Purge irrelevant chunks like Điều 99 ngừng việc for delayed wage issues
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if not (c.get("chunk_id", "").startswith("VBHN_18_2026#d99"))
                ]

                # 1. Issue 1: Canonical Article 97 BLLD 2019 (Clauses 1, 2, 3, 4)
                if wage_schedule_iid:
                    target_w_iid = wage_schedule_iid
                    d97_cids = ["VBHN_18_2026#d97-k1", "VBHN_18_2026#d97-k2", "VBHN_18_2026#d97-k3", "VBHN_18_2026#d97-k4"]
                    for cid in d97_cids:
                        if not any(c.get("chunk_id") == cid and i_id == target_w_iid for c, i_id in selected_chunks):
                            b_chk = self._get_chunk_by_id(cid)
                            if b_chk:
                                selected_chunks.append((b_chk, target_w_iid))
                                seen_cids.add(cid)

                # 2. Delayed-wage remedies. Điều 35k2b belongs to a separate
                # termination issue when the employee also asks about quitting.
                if delayed_wage_iid:
                    target_d_iid = delayed_wage_iid
                    d_remedy_cids = ["VBHN_18_2026#d97-k4", "ND_283_2026#d23-k2", "ND_283_2026#d23-k5-a"]
                    for cid in d_remedy_cids:
                        if not any(c.get("chunk_id") == cid and i_id == target_d_iid for c, i_id in selected_chunks):
                            b_chk = self._get_chunk_by_id(cid)
                            if b_chk:
                                selected_chunks.append((b_chk, target_d_iid))
                                seen_cids.add(cid)

                # 3. Issue 3: Labour Complaint (Article 94 Clause 1, ND 24/2018 Articles 5, 7, 27, 10, Article 125 Clause 4)
                if complaint_iid:
                    target_c_iid = complaint_iid
                    complaint_cids = ["VBHN_18_2026#d94-k1", "ND_24_2018#d7", "ND_24_2018#d27", "ND_24_2018#d10", "VBHN_18_2026#d125-k4"]
                    for cid in complaint_cids:
                        if not any(c.get("chunk_id") == cid and i_id == target_c_iid for c, i_id in selected_chunks):
                            b_chk = self._get_chunk_by_id(cid)
                            if b_chk:
                                selected_chunks.append((b_chk, target_c_iid))
                                seen_cids.add(cid)

            # 2i. Contract-formation principles: Article 15 only.  Article 16
            # is a separate information-duty issue and is removed here.
            principles_owner: Optional[str] = None
            principles_raw_owner: Optional[str] = None
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                if (
                    str(meta.get("doc_id", "")) == "VBHN_18_2026"
                    and str(meta.get("article_number", "")) == "15"
                ):
                    principles_raw_owner = i_id
                    principles_owner = i_id or "statutory_bridge"
                    break

            if principles_owner:
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if i_id != principles_raw_owner
                ]
                for cid in ["VBHN_18_2026#d15-k1", "VBHN_18_2026#d15-k2"]:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        selected_chunks.append((b_chk, principles_owner))
                        seen_cids.add(cid)

            # 2j. Starting work before signing: lock the timing rule, legal
            # relationship definition, written form and oral exception.
            contract_timing_owner: Optional[str] = None
            contract_timing_raw_owner: Optional[str] = None
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                cl_num = str(meta.get("clause_number", ""))
                c_text = str(c.get("content", "")).lower()
                if d_id == "VBHN_18_2026" and a_num == "13" and cl_num == "2":
                    contract_timing_raw_owner = i_id
                    contract_timing_owner = i_id or "statutory_bridge"
                    break

            if contract_timing_owner:
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if i_id != contract_timing_raw_owner
                ]
                contract_timing_cids = [
                    "VBHN_18_2026#d13-k2",
                    "VBHN_18_2026#d13-k1",
                    "VBHN_18_2026#d14-k1",
                    "VBHN_18_2026#d14-k2",
                ]
                canonical_contract_timing = []
                for cid in contract_timing_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_contract_timing.append((b_chk, contract_timing_owner))
                        seen_cids.add(cid)
                selected_chunks = canonical_contract_timing + selected_chunks

            # 2k. Workplace violence: replace disciplinary noise with the exact
            # prohibition, immediate-exit right and administrative sanction.
            violence_owner: Optional[str] = None
            violence_raw_owner: Optional[str] = None
            for c, i_id in selected_chunks:
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                cid_str = str(c.get("chunk_id") or "")
                pt_str = str(meta.get("point") or "").lower()
                c_text = str(c.get("content", "")).lower()
                is_violence_rule = (
                    (d_id == "VBHN_18_2026" and a_num == "8" and any(k in c_text for k in ["ngược đãi", "đánh đập"]))
                    or (d_id == "VBHN_18_2026" and a_num == "35" and (pt_str == "c" or cid_str.endswith("#d35-k2-c") or "điểm c" in cid_str))
                    or (d_id == "ND_283_2026" and a_num == "17" and any(k in c_text for k in ["ngược đãi", "đánh đập"]))
                )
                if is_violence_rule:
                    violence_raw_owner = i_id
                    violence_owner = i_id or "statutory_bridge"
                    break

            if violence_owner:
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if i_id != violence_raw_owner
                ]
                violence_cids = [
                    "VBHN_18_2026#d8-k2",
                    "VBHN_18_2026#d35-k2-c",
                    "ND_283_2026#d17-k4",
                    "ND_283_2026#d17-k4-a",
                    "ND_283_2026#d7-k1",
                ]
                canonical_violence_chunks = []
                for cid in violence_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_violence_chunks.append((b_chk, violence_owner))
                        seen_cids.add(cid)
                selected_chunks = canonical_violence_chunks + selected_chunks

            # 2l. De Facto Labor Contract & Prohibited ID Retention Bridge (Điều 13 & Điều 17 BLLĐ 2019)
            de_facto_contract_iid = None
            prohibited_id_iid = None
            dispute_procedure_iids: Set[str] = set()

            for c, i_id in selected_chunks:
                c_text = str(c.get("content", "")).lower()
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))

                if (
                    not contract_timing_owner
                    and ("thỏa thuận bằng tên gọi khác" in c_text or "được coi là hợp đồng lao động" in c_text or (d_id == "VBHN_18_2026" and a_num == "13"))
                    and not de_facto_contract_iid
                ):
                    de_facto_contract_iid = i_id or "statutory_bridge"
                if ("giữ bản chính giấy tờ tùy thân" in c_text or "giấy tờ tùy thân" in c_text or (d_id == "VBHN_18_2026" and a_num == "17") or (d_id == "ND_283_2026" and a_num == "15")) and not prohibited_id_iid:
                    prohibited_id_iid = i_id or "statutory_bridge"
                if d_id == "VBHN_18_2026" and a_num in {"188", "190"} and i_id:
                    dispute_procedure_iids.add(str(i_id))

            if de_facto_contract_iid:
                target_df_iid = de_facto_contract_iid
                # Replace the issue's noisy retrieval tail with the exact legal
                # test and, when litigation is asked, the required procedure.
                selected_chunks = [(c, i_id) for c, i_id in selected_chunks if i_id != target_df_iid]
                d13_cids = ["VBHN_18_2026#d13-k1"]
                if str(target_df_iid) in dispute_procedure_iids:
                    d13_cids.extend([
                        "VBHN_18_2026#d188-k1",
                        "VBHN_18_2026#d188-k1-a",
                        "VBHN_18_2026#d188-k7-b",
                        "VBHN_18_2026#d190-k3",
                    ])
                canonical_df_chunks = []
                for cid in d13_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_df_chunks.append((b_chk, target_df_iid))
                        seen_cids.add(cid)
                selected_chunks = canonical_df_chunks + selected_chunks

            if prohibited_id_iid:
                target_pid_iid = prohibited_id_iid
                selected_chunks = [(c, i_id) for c, i_id in selected_chunks if i_id != target_pid_iid]
                d17_cids = [
                    "VBHN_18_2026#d17-k1",
                    "ND_283_2026#d15-k2",
                    "ND_283_2026#d15-k2-a",
                    "ND_283_2026#d15-k3-d",
                ]
                for cid in d17_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        selected_chunks.append((b_chk, target_pid_iid))
                        seen_cids.add(cid)

            # 2m. Misassigned Work & Unlawful Termination Bridge (Điều 35k2a, Điều 29, Điều 40 BLLĐ 2019)
            misassigned_work_iid = None
            for c, i_id in selected_chunks:
                c_text = str(c.get("content", "")).lower()
                meta = c.get("metadata") or c
                d_id = str(meta.get("doc_id", ""))
                a_num = str(meta.get("article_number", ""))
                cid_str = str(c.get("chunk_id") or "")
                if (
                    (d_id == "VBHN_18_2026" and a_num == "29")
                    or any(k in c_text for k in ["chuyển người lao động làm công việc khác so với hợp đồng", "không được bố trí theo đúng công việc"])
                ) and not misassigned_work_iid:
                    misassigned_work_iid = i_id or "statutory_bridge"
                    break

            if misassigned_work_iid:
                target_mw_iid = misassigned_work_iid
                # Filter out noisy chunks for this issue (especially false 30-day notice d35-k1-b or employer exit d36/d41)
                selected_chunks = [
                    (c, i_id) for c, i_id in selected_chunks
                    if not (i_id == target_mw_iid and (c.get("chunk_id") or "") in ["VBHN_18_2026#d35-k1-b", "VBHN_18_2026#d36-k1-b", "VBHN_18_2026#d41-k1"])
                ]
                mw_cids = [
                    "VBHN_18_2026#d35-k2-a",
                    "VBHN_18_2026#d29-k1",
                    "VBHN_18_2026#d40-k1",
                    "VBHN_18_2026#d40-k2",
                ]
                canonical_mw_chunks = []
                for cid in mw_cids:
                    b_chk = self._get_chunk_by_id(cid)
                    if b_chk:
                        canonical_mw_chunks.append((b_chk, target_mw_iid))
                        seen_cids.add(cid)
                selected_chunks = canonical_mw_chunks + selected_chunks

        # Fair-share ordering: put the first block of every issue before any
        # issue receives its second block. This prevents the final issue in a
        # long scenario from being starved by the character budget.
        if multi_issue_candidates:
            issue_order = list(multi_issue_candidates.keys())
            grouped: Dict[str, List[Tuple[Dict[str, Any], Optional[str]]]] = {
                issue_id: [] for issue_id in issue_order
            }
            ungrouped: List[Tuple[Dict[str, Any], Optional[str]]] = []
            for item in selected_chunks:
                if item[1] in grouped:
                    grouped[str(item[1])].append(item)
                else:
                    ungrouped.append(item)
            fair_order: List[Tuple[Dict[str, Any], Optional[str]]] = []
            max_depth = max((len(items) for items in grouped.values()), default=0)
            for depth in range(max_depth):
                for issue_id in issue_order:
                    if depth < len(grouped[issue_id]):
                        fair_order.append(grouped[issue_id][depth])
            selected_chunks = fair_order + ungrouped

        # Never expose the repealed 12/2022 sanction schedule as present law.
        # Explicit historical lookups may opt in from the chain.
        if not allow_repealed:
            selected_chunks = [
                item for item in selected_chunks
                if (item[0].get("metadata") or item[0]).get("doc_id") != "ND_12_2022"
            ]

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
                "issue_id": issue_id,
                "status": (chk.get("metadata") or chk).get("status", "CURRENT"),
                "rule_type": (chk.get("metadata") or chk).get("rule_type", "GENERAL_RULE"),
                "evidence_roles": (chk.get("metadata") or chk).get("evidence_roles", []),
                "official_source": (chk.get("metadata") or chk).get("official_source", ""),
                "content": block.content,
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
