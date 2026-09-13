# -*- coding: utf-8 -*-
"""
VietLabor AI - Evidence Mapper
Assigns temporary evidence IDs ([E1], [E2], ...) to context blocks and
deterministically maps model evidence selections back to canonical chunk IDs
and official citation metadata.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import re


@dataclass
class EvidenceBlock:
    """A compact statutory evidence block presented to the LLM."""
    evidence_id: str  # E.g. "E1", "E2"
    chunk_id: str     # Canonical chunk ID, e.g. "VBHN_18_2026#d35-k1-b"
    document_no: str  # E.g. "18/VBHN-VPQH"
    document_title: str
    article_number: Optional[int] = None
    article_title: Optional[str] = None
    clause_number: Optional[int] = None
    point: Optional[str] = None
    content: str = ""
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    issue_id: Optional[str] = None

    def format_for_llm(self) -> str:
        """Formats the evidence block with statutory hierarchy and content."""
        if self.issue_id:
            m_iss = re.match(r"issue_(\d+)", self.issue_id, re.IGNORECASE)
            if m_iss:
                parts = [f"[{self.evidence_id}] (Căn cứ cho Vấn đề {m_iss.group(1)})"]
            else:
                parts = [f"[{self.evidence_id}]"]
        else:
            parts = [f"[{self.evidence_id}]"]
        
        # Statutory header
        header_parts = [self.document_title or self.document_no]
        if self.article_number is not None:
            art_str = f"Điều {self.article_number}"
            if self.article_title:
                art_str += f" ({self.article_title})"
            header_parts.append(art_str)
        if self.clause_number is not None:
            header_parts.append(f"Khoản {self.clause_number}")
        if self.point:
            header_parts.append(f"Điểm {self.point}")

        parts.append(" - ".join(header_parts))
        parts.append(f"Nội dung: {self.content.strip()}")
        return "\n".join(parts)


@dataclass
class EvidenceMappingResult:
    """Result of mapping LLM-selected evidence tokens back to canonical chunks."""
    valid_evidence_ids: List[str] = field(default_factory=list)
    invalid_evidence_ids: List[str] = field(default_factory=list)
    canonical_chunk_ids: List[str] = field(default_factory=list)
    mapped_metadata: List[Dict[str, Any]] = field(default_factory=list)
    formatted_citations: str = ""
    raw_validity_rate: float = 1.0


class EvidenceMapper:
    """Manages the lifecycle of temporary evidence IDs and deterministic citation formatting."""

    EVIDENCE_ID_PATTERN = re.compile(r"\bE(\d+)\b", re.IGNORECASE)

    def __init__(self):
        self._registry: Dict[str, EvidenceBlock] = {}
        self._chunk_to_eid: Dict[str, str] = {}

    def register_blocks(self, blocks: List[EvidenceBlock]) -> None:
        """Registers active evidence blocks for a generation turn."""
        self._registry.clear()
        self._chunk_to_eid.clear()
        for b in blocks:
            norm_eid = b.evidence_id.upper()
            self._registry[norm_eid] = b
            self._chunk_to_eid[b.chunk_id] = norm_eid

    @property
    def available_evidence_ids(self) -> Set[str]:
        return set(self._registry.keys())

    def get_block_by_id(self, evidence_id: str) -> Optional[EvidenceBlock]:
        return self._registry.get(evidence_id.upper())

    def get_evidence_id_by_chunk(self, chunk_id: str) -> Optional[str]:
        return self._chunk_to_eid.get(chunk_id)

    def resolve_token(self, token: str) -> Optional[str]:
        """Resolves an evidence ID token (e.g. 'E1' or '[E1]') to canonical chunk ID."""
        if not token or not isinstance(token, str):
            return None
        clean_tok = token.strip().strip("[]").upper()
        block = self._registry.get(clean_tok)
        return block.chunk_id if block else None

    def is_valid_evidence_id(self, token: str) -> bool:
        """Returns True if the token corresponds to an active registered evidence block."""
        if not token or not isinstance(token, str):
            return False
        clean_tok = token.strip().strip("[]").upper()
        return clean_tok in self._registry

    def format_citation_label(self, evidence_id: str) -> str:
        """Formats a single citation label for an evidence block."""
        block = self.get_block_by_id(evidence_id)
        if not block:
            return ""
        meta = {
            "document_no": block.document_no,
            "document_title": block.document_title,
            "article_number": block.article_number,
            "clause_number": block.clause_number,
            "point": block.point,
        }
        res = self.format_citations_from_metadata([meta])
        # Strip preamble if present
        return res.replace("\n\nCĂN CỨ PHÁP LÝ:\n", "").lstrip("- ").strip()

    def map_evidence_tokens(self, tokens: List[str]) -> EvidenceMappingResult:
        """Maps a list of candidate evidence tokens (e.g. ['E1', 'E2', 'E99']) to canonical chunks.
        
        Extracts valid tokens, rejects hallucinations, maps to canonical chunk IDs,
        and generates official legal citations deterministically.
        """
        valid_eids: List[str] = []
        invalid_eids: List[str] = []
        canonical_cids: List[str] = []
        mapped_meta: List[Dict[str, Any]] = []

        seen_eids: Set[str] = set()

        for tok in tokens:
            if not tok or not isinstance(tok, str):
                continue
            # Normalize e.g. " [E1] " or "e1" -> "E1"
            clean_tok = tok.strip().strip("[]").upper()
            if clean_tok in seen_eids:
                continue
            seen_eids.add(clean_tok)

            if clean_tok in self._registry:
                block = self._registry[clean_tok]
                valid_eids.append(clean_tok)
                if block.chunk_id not in canonical_cids:
                    canonical_cids.append(block.chunk_id)
                    mapped_meta.append({
                        "chunk_id": block.chunk_id,
                        "document_no": block.document_no,
                        "document_title": block.document_title,
                        "article_number": block.article_number,
                        "article_title": block.article_title,
                        "clause_number": block.clause_number,
                        "point": block.point,
                        "source_url": block.source_url,
                        "page_number": block.page_number,
                    })
            else:
                invalid_eids.append(clean_tok)

        total_tokens = len(valid_eids) + len(invalid_eids)
        validity_rate = (len(valid_eids) / total_tokens) if total_tokens > 0 else 1.0

        # Build canonical formatted citations string
        formatted = self.format_citations_from_metadata(mapped_meta)

        return EvidenceMappingResult(
            valid_evidence_ids=valid_eids,
            invalid_evidence_ids=invalid_eids,
            canonical_chunk_ids=canonical_cids,
            mapped_metadata=mapped_meta,
            formatted_citations=formatted,
            raw_validity_rate=validity_rate,
        )

    def format_citations_from_metadata(self, metadata_list: List[Dict[str, Any]]) -> str:
        """Deterministically formats official citations based strictly on canonical metadata."""
        if not metadata_list:
            return ""

        # Group provisions by document and article
        lines = ["\n\nCĂN CỨ PHÁP LÝ:"]
        seen_citations: Set[str] = set()

        for m in metadata_list:
            doc_name = m.get("document_title") or m.get("document_no") or "Văn bản pháp luật"
            art = m.get("article_number")
            cl = m.get("clause_number")
            pt = m.get("point")
            url = m.get("source_url")
            page = m.get("page_number")

            prov_parts = []
            if art is not None:
                prov_parts.append(f"Điều {art}")
            if cl is not None:
                prov_parts.append(f"Khoản {cl}")
            if pt:
                prov_parts.append(f"Điểm {pt}")

            if prov_parts:
                prov_str = ", ".join(prov_parts)
                cite_components = [doc_name, prov_str]
            else:
                cite_components = [doc_name]

            cite_label = " – ".join(cite_components)

            # Add source link and page if available
            link_parts = []
            if url:
                link_parts.append(url)
            if page:
                link_parts.append(f"Trang {page}")

            if link_parts:
                full_citation = f"- {cite_label} [{', '.join(link_parts)}]"
            else:
                full_citation = f"- {cite_label}"

            if full_citation not in seen_citations:
                seen_citations.add(full_citation)
                lines.append(full_citation)

        return "\n".join(lines)

    def replace_evidence_tokens_in_text(self, text: str) -> str:
        """Replaces technical evidence tokens like [E1], (E1) with user-friendly statutory citations."""
        if not text or not isinstance(text, str):
            return text

        def _repl(m: re.Match) -> str:
            eid_num = m.group(1) or m.group(2)
            norm_eid = f"E{eid_num}".upper()
            block = self.get_block_by_id(norm_eid)
            if not block:
                return ""

            doc_title = block.document_title or "Bộ luật Lao động 2019"
            if "bộ luật lao động" in doc_title.lower():
                doc_short = "Bộ luật Lao động 2019"
            elif "nghị định 145" in doc_title.lower():
                doc_short = "Nghị định 145/2020/NĐ-CP"
            elif "nghị định 12" in doc_title.lower():
                doc_short = "Nghị định 12/2022/NĐ-CP"
            else:
                doc_short = doc_title

            parts = []
            if block.point:
                parts.append(f"Điểm {block.point}")
            if block.clause_number is not None:
                parts.append(f"Khoản {block.clause_number}")
            if block.article_number is not None:
                parts.append(f"Điều {block.article_number}")

            if parts:
                return f"{' '.join(parts)} {doc_short}"
            return doc_short

        # Match [E1], [E2], (E1), (E2)
        pattern = re.compile(r"\[\s*E(\d+)\s*\]|\(\s*E(\d+)\s*\)", re.IGNORECASE)
        res = pattern.sub(_repl, text)
        return res
