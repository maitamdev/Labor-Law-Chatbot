# -*- coding: utf-8 -*-
"""
VietLabor AI - Deterministic RAG Chain (Phase 5D)
Orchestrates the grounded legal question-answering workflow:
1. Input question normalization (Unicode NFC, whitespace, safe punctuation).
2. Short-term conversational context resolution (anaphora, contract terms, active facts).
3. Deterministic query routing (Actor-aware, Legal intent, Exact reference vs Hybrid).
4. Multi-issue decomposition for compound questions (IssueDecomposer).
5. Vocabulary divergence expansion (QueryExpander).
6. Multi-issue parallel/independent Hybrid retrieval.
7. Compact statutory context construction with temporary Evidence IDs ([E1], [E2], ...).
8. Local Qwen inference via Ollama (localhost:11434).
9. Structured JSON parsing into LegalAnswer with findings and evidence_ids.
10. Deterministic mapping to canonical chunk IDs via EvidenceMapper.
11. Rigorous citation validation and canonical metadata citation rendering.

STRICTLY DETERMINISTIC WORKFLOW. ZERO AGENTS / ZERO MULTI-AGENT / ZERO LANGGRAPH.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from models.local_llm import LocalLLMManager
from rag.bm25_retriever import BM25Retriever
from rag.context_builder import ContextBuilder, FormattedContext
from rag.evidence_selector import EvidenceSelector, EvidenceSelectionResult
from rag.hybrid_retriever import HybridRetriever
from rag.issue_decomposer import IssueDecomposer
from rag.legal_issue_parser import LegalIssue, LegalIssueParser
from rag.material_premise_gate import MaterialPremiseGate, PremiseGateResult
from rag.output_validator import LegalAnswer, OutputValidator, ValidatedResponse
from rag.prompts import SYSTEM_PROMPT, build_user_prompt
from rag.query_expander import QueryExpander
from rag.query_processor import normalize_query, normalize_colloquial_vietnamese
from rag.query_router import QueryRouter, RouteDecision

logger = logging.getLogger(__name__)


@dataclass
class Turn:
    """A single conversational turn."""
    user_query: str
    assistant_response: str
    facts: Dict[str, str] = field(default_factory=dict)


class ConversationMemory:
    """Short-term conversational state tracker with statutory premise extraction and state refinement."""

    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
        self.history: List[Turn] = []
        self.accumulated_facts: Dict[str, str] = {}
        self.inferred_states: Dict[str, str] = {}

    def add_turn(self, user_query: str, assistant_response: str) -> None:
        """Stores a turn and extracts active statutory facts, overriding prior inferences."""
        extracted = self._extract_facts(user_query)
        self.accumulated_facts.update(extracted)
        turn = Turn(user_query=user_query, assistant_response=assistant_response, facts=extracted)
        self.history.append(turn)
        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def _extract_facts(self, text: str) -> Dict[str, str]:
        """Extracts factual premises relevant to labor statutes and relationship states."""
        facts: Dict[str, str] = {}
        t = text.lower()

        # Contract duration / type (only when referring to employment contract, not probation duration)
        m_contract = re.search(r"(dưới\s*)?(\d+)\s*(năm|tháng)", t)
        if m_contract and ("hợp đồng" in t or "hđ" in t or "ký" in t or "nghỉ việc" in t or "thời hạn" in t) and "thử việc" not in t:
            prefix = "dưới " if m_contract.group(1) else ""
            facts["contract_term"] = f"{prefix}{m_contract.group(2)} {m_contract.group(3)}"
        if "không xác định thời hạn" in t or "vô thời hạn" in t:
            facts["contract_term"] = "không xác định thời hạn"
        if "xác định thời hạn" in t and "không" not in t:
            facts["contract_term_type"] = "xác định thời hạn"

        # Topic identification
        if "thử việc" in t or "làm thử" in t:
            facts["topic"] = "thử việc"
            facts["relationship_type"] = "PROBATION"
            facts["probation_status"] = "IN_PROBATION"
            if any(k in t for k in ["thực ra là thử việc", "công ty bảo thử việc", "thử việc trước khi ký"]):
                facts["probation_clarified"] = "thử việc trước khi ký hợp đồng"
                # Explicit probation overrides prior internship assumptions
                if "school_program" in self.accumulated_facts:
                    del self.accumulated_facts["school_program"]
                if "de_facto_employee" in self.accumulated_facts:
                    del self.accumulated_facts["de_facto_employee"]

        if "nghỉ việc" in t or "thôi việc" in t or "đơn phương" in t:
            facts["action"] = "chấm dứt hợp đồng"
        if "lương" in t or "chậm lương" in t:
            facts["topic"] = "tiền lương"
        if "làm thêm" in t or "tăng ca" in t:
            facts["topic"] = "làm thêm giờ"

        # Position / Qualification level
        if any(k in t for k in ["đại học", "cao đẳng", "kỹ sư", "cử nhân", "lập trình viên", "chuyên viên"]):
            facts["qualification"] = "cao đẳng trở lên"
        elif any(k in t for k in ["trung cấp", "công nhân kỹ thuật", "nghiệp vụ", "trung cấp nghề"]):
            facts["qualification"] = "trung cấp"
        elif any(k in t for k in ["người quản lý", "giám đốc", "tổng giám đốc", "chủ tịch"]):
            facts["qualification"] = "người quản lý doanh nghiệp"
        elif any(k in t for k in ["lao động phổ thông", "tạp vụ", "bảo vệ"]):
            facts["qualification"] = "công việc khác"

        # Special occupation
        if any(k in t for k in ["tổ lái", "tàu bay", "phi công", "tiếp viên hàng không", "thuyền viên"]):
            facts["special_occupation"] = "ngành nghề đặc thù"

        # Factual relationship classification (Phase 5F)
        if any(k in t for k in ["chương trình của trường", "giấy giới thiệu", "thỏa thuận thực tập", "nhà trường", "đồ án"]):
            facts["relationship_type"] = "INTERNSHIP"
            facts["internship_type"] = "SCHOOL_PROGRAM"
            facts["school_program"] = "chương trình nhà trường có giấy giới thiệu"
            facts["topic"] = "thực tập"
            if "de_facto_employee" in self.accumulated_facts:
                del self.accumulated_facts["de_facto_employee"]

        if any(k in t for k in [
            "công ty tự tuyển", "như nhân viên", "8 tiếng", "8 giờ", "chấm công",
            "giao việc như nhân viên", "quản lý trực tiếp", "kpi", "làm việc cố định"
        ]):
            facts["relationship_type"] = "EMPLOYMENT"
            facts["employment_status"] = "ACTUAL_EMPLOYEE"
            facts["de_facto_employee"] = "làm việc như nhân viên có chấm công quản lý"
            facts["topic"] = "quan hệ lao động thực tế"
            if "school_program" in self.accumulated_facts:
                del self.accumulated_facts["school_program"]

        return facts

    def resolve_context(self, current_query: str) -> str:
        """Resolves follow-up queries by appending active conversational facts if needed."""
        norm_q = current_query.strip()
        if not self.history:
            return norm_q

        supplements = []
        q_lower = norm_q.lower()

        # Merge facts from previous turns and current query
        current_facts = self._extract_facts(current_query)
        effective_facts = {**self.accumulated_facts, **current_facts}

        # If previous turn established school internship
        if effective_facts.get("relationship_type") == "INTERNSHIP" and effective_facts.get("school_program"):
            if "thực tập" not in q_lower:
                supplements.append("thực tập sinh theo chương trình nhà trường tiền lương phụ cấp")

        # If previous turn established de facto employment
        elif effective_facts.get("relationship_type") == "EMPLOYMENT" and effective_facts.get("de_facto_employee"):
            if "quan hệ lao động" not in q_lower and "điều 13" not in q_lower:
                supplements.append("quan hệ lao động thực tế Điều 13 Khoản 1 BLLĐ tiền lương nhân viên")

        # If previous turn was about probation and user provides position/qualification
        elif effective_facts.get("topic") == "thử việc" or effective_facts.get("relationship_type") == "PROBATION":
            if "thử việc" not in q_lower:
                if effective_facts.get("payment_issue") or any("lương" in t.user_query.lower() for t in self.history):
                    supplements.append("thời gian thử việc tiền lương thử việc Điều 25 Điều 26 BLLĐ")
                else:
                    supplements.append("thời gian thử việc Điều 25 BLLĐ")
            if "qualification" in effective_facts and effective_facts["qualification"] not in q_lower:
                supplements.append(effective_facts["qualification"])

        # If previous turn was about contract termination and user provides contract term or occupation
        if effective_facts.get("action") == "chấm dứt hợp đồng":
            if "nghỉ việc" not in q_lower and "chấm dứt" not in q_lower:
                supplements.append("thời hạn báo trước khi nghỉ việc")
            if "contract_term" in effective_facts and "hợp đồng" not in q_lower:
                supplements.append(f"hợp đồng {effective_facts['contract_term']}")
            if effective_facts.get("special_occupation") and "đặc thù" not in q_lower:
                supplements.append("ngành nghề công việc đặc thù tổ lái tàu bay")

        if supplements:
            return f"{norm_q} ({', '.join(supplements)})"
        return norm_q

    def has_clarification_facts(self) -> bool:
        """Checks whether the user has already provided specific facts resolving ambiguity."""
        return bool(
            self.accumulated_facts.get("qualification")
            or self.accumulated_facts.get("contract_term")
            or self.accumulated_facts.get("school_program")
            or self.accumulated_facts.get("de_facto_employee")
            or self.accumulated_facts.get("probation_clarified")
        )

    def get_history_summary(self) -> str:
        """Formats recent history for LLM prompt context."""
        if not self.history:
            return "Không có lịch sử trước đó."
        lines = []
        for i, turn in enumerate(self.history, start=1):
            lines.append(f"Lượt {i}:")
            lines.append(f"  Người dùng: {turn.user_query}")
            short_resp = turn.assistant_response[:200] + "..." if len(turn.assistant_response) > 200 else turn.assistant_response
            lines.append(f"  VietLabor AI: {short_resp}")
        return "\n".join(lines)

    def clear(self):
        """Clears conversation state."""
        self.history.clear()
        self.accumulated_facts.clear()
        self.inferred_states.clear()


@dataclass
class ChainExecutionResult:
    """Comprehensive result object holding answer, provenance, and diagnostic metrics."""
    query: str
    normalized_query: str
    resolved_query: str
    route_decision: RouteDecision
    retrieval_method: str
    retrieved_chunks: List[Dict[str, Any]]
    formatted_context: FormattedContext
    raw_llm_output: str
    validated_response: ValidatedResponse
    retrieval_latency_ms: float
    llm_latency_ms: float
    total_latency_ms: float
    selection_latency_ms: float = 0.0
    locked_chunk_ids: List[str] = field(default_factory=list)

    @property
    def answer(self) -> str:
        return self.validated_response.final_answer

    @property
    def cited_chunk_ids(self) -> List[str]:
        return self.validated_response.cited_chunk_ids


class VietLaborRAGChain:
    """Deterministic LangChain-based RAG pipeline for VietLabor AI (Phase 5E)."""

    def __init__(
        self,
        hybrid_retriever: Optional[HybridRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        llm_manager: Optional[LocalLLMManager] = None,
        top_k: int = 20,
        max_context_chars: int = 8000,
        max_chunks: int = 10,
        max_per_issue_blocks: int = 4,
        index_version: str = "v2",
    ):
        self.top_k = top_k
        self.index_version = index_version
        self.router = QueryRouter()
        self.decomposer = IssueDecomposer()
        self.issue_parser = LegalIssueParser(router=self.router)
        self.evidence_selector = EvidenceSelector()
        self.expander = QueryExpander()
        self.context_builder = ContextBuilder(
            max_context_chars=max_context_chars,
            max_chunks=max_chunks,
            max_per_issue_blocks=max_per_issue_blocks,
        )
        self.validator = OutputValidator()
        self.memory = ConversationMemory(max_turns=3)
        self.premise_gate = MaterialPremiseGate()

        # Initialize or reuse retrievers
        if hybrid_retriever is not None:
            self.hybrid_retriever = hybrid_retriever
            self.bm25_retriever = hybrid_retriever.bm25_retriever
        elif bm25_retriever is not None:
            self.bm25_retriever = bm25_retriever
            self.hybrid_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                index_version=index_version,
            )
        else:
            self.hybrid_retriever = HybridRetriever(index_version=index_version)
            self.bm25_retriever = self.hybrid_retriever.bm25_retriever

        # Local LLM manager
        self.llm_manager = llm_manager or LocalLLMManager()

    # -------------------------------------------------------------------------
    # Out-of-scope response message (DRY: used in run() and tests)
    # -------------------------------------------------------------------------
    _OOS_MESSAGE = (
        "Câu hỏi của bạn không thuộc phạm vi tư vấn của pháp luật lao động Việt Nam "
        "(ví dụ: hôn nhân gia đình, đất đai, hình sự, giao thông, thuế doanh nghiệp, kiện đòi nợ, thủ tục doanh nghiệp, sở hữu trí tuệ). "
        "VietLabor AI chỉ hỗ trợ tra cứu các quy định về quan hệ lao động, tiền lương, "
        "hợp đồng, kỷ luật, bảo hiểm và thời giờ làm việc theo Bộ luật Lao động và các văn bản hướng dẫn thi hành."
    )

    # -------------------------------------------------------------------------
    # Private pipeline stage methods
    # -------------------------------------------------------------------------

    def _handle_empty_query(self, question: str) -> ChainExecutionResult:
        """Stage 0: Return early for empty/whitespace-only queries."""
        empty_resp = ValidatedResponse(
            raw_answer="Vui lòng nhập câu hỏi của bạn.",
            final_answer="Vui lòng nhập câu hỏi của bạn.",
            legal_findings=[],
            cited_chunk_ids=[],
            rejected_chunk_ids=[],
            formatted_citations="",
            needs_clarification=False,
            clarification_question=None,
            abstain=True,
            abstain_reason="Empty query",
            is_fully_grounded=True,
        )
        return ChainExecutionResult(
            query=question,
            normalized_query="",
            resolved_query="",
            route_decision=RouteDecision(strategy="hybrid", reason="Empty"),
            retrieval_method="None",
            retrieved_chunks=[],
            formatted_context=self.context_builder.build_context([]),
            raw_llm_output="",
            validated_response=empty_resp,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            total_latency_ms=0.0,
        )

    def _handle_out_of_scope(
        self, question: str, norm_q: str, resolved_q: str, route_decision: RouteDecision,
    ) -> ChainExecutionResult:
        """Stage 1: Return early for queries outside labor law scope."""
        oos_resp = ValidatedResponse(
            raw_answer=self._OOS_MESSAGE,
            final_answer=self._OOS_MESSAGE,
            legal_findings=[],
            cited_chunk_ids=[],
            rejected_chunk_ids=[],
            formatted_citations="",
            needs_clarification=False,
            clarification_question=None,
            abstain=True,
            abstain_reason=route_decision.reason,
            is_fully_grounded=True,
        )
        return ChainExecutionResult(
            query=question,
            normalized_query=norm_q,
            resolved_query=resolved_q,
            route_decision=route_decision,
            retrieval_method="None (Out-of-scope Abstained)",
            retrieved_chunks=[],
            formatted_context=self.context_builder.build_context([]),
            raw_llm_output="",
            validated_response=oos_resp,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            total_latency_ms=0.0,
        )

    def _handle_premise_gate(
        self,
        question: str,
        norm_q: str,
        resolved_q: str,
        route_decision: RouteDecision,
        premise_result: "PremiseGateResult",
        update_memory: bool,
        t0: float,
    ) -> ChainExecutionResult:
        """Stage 2: Return clarification when MaterialPremiseGate detects missing facts."""
        clarify_text = premise_result.clarification_question or "Vui lòng cung cấp thêm thông tin chi tiết."
        clarify_resp = ValidatedResponse(
            raw_answer=clarify_text,
            final_answer=clarify_text,
            legal_findings=[],
            cited_chunk_ids=[],
            rejected_chunk_ids=[],
            formatted_citations="",
            needs_clarification=True,
            clarification_question=clarify_text,
            clarification_options=premise_result.clarification_options,
            abstain=False,
            is_fully_grounded=True,
        )
        if update_memory:
            self.memory.add_turn(user_query=norm_q, assistant_response=clarify_text)
        t_end = time.perf_counter()
        return ChainExecutionResult(
            query=question,
            normalized_query=norm_q,
            resolved_query=resolved_q,
            route_decision=route_decision,
            retrieval_method="None (Material Premise Gate Clarification)",
            retrieved_chunks=[],
            formatted_context=self.context_builder.build_context([]),
            raw_llm_output="",
            validated_response=clarify_resp,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            total_latency_ms=(t_end - t0) * 1000,
            selection_latency_ms=0.0,
            locked_chunk_ids=[],
        )

    def _retrieve_and_select(
        self,
        norm_q: str,
        resolved_q: str,
        route_decision: RouteDecision,
        premise_result: "PremiseGateResult",
    ) -> Dict[str, Any]:
        """Stage 3: Decompose, retrieve, filter, and select+lock canonical evidence.

        Returns a dict with keys:
            retrieval_method, combined_candidate_chunks, locked_chunks,
            locked_chunk_ids, multi_issue_locked, decomposed_issues,
            retrieval_latency_ms, selection_latency_ms.
        """
        # --- 3a. Issue Decomposition ---
        t_ret_start = time.perf_counter()
        query_for_retrieval = route_decision.augmented_query or resolved_q
        decomposed_issues = self.decomposer.decompose(resolved_q)

        multi_issue_candidates: Dict[str, List[Dict[str, Any]]] = {}
        combined_candidate_chunks: List[Dict[str, Any]] = []
        retrieval_method = "Hybrid RRF (BM25 + BGE-M3)"

        is_domestic = any(k in resolved_q.lower() for k in ["giúp việc", "người giúp việc", "gia đình"])

        # --- 3b. Retrieval ---
        if route_decision.is_exact_reference():
            retrieval_method = "BM25 Lexical (Exact Reference)"
            raw_retrieved = self.bm25_retriever.retrieve(query_for_retrieval, top_k=self.top_k)
            if route_decision.detected_article is not None:
                art_target = str(route_decision.detected_article)
                matching = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) == art_target]
                non_matching = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) != art_target]
                combined_candidate_chunks = (matching + non_matching)[: self.top_k]
            else:
                combined_candidate_chunks = raw_retrieved[: self.top_k]
        else:
            # Multi-issue or single-issue Hybrid retrieval
            if len(decomposed_issues) > 1:
                retrieval_method = "Multi-Issue Hybrid RRF (BM25 + BGE-M3)"
                for iss in decomposed_issues:
                    issue_retrieved = self.hybrid_retriever.retrieve(iss.retrieval_query, top_k=self.top_k // 2 + 5)

                    # Filter domestic worker provisions unless question is about domestic workers
                    if not is_domestic:
                        issue_retrieved = [c for c in issue_retrieved if str(c.get("metadata", {}).get("article_number")) not in ["161", "162", "165"]]

                    # If intent is SUBSTANTIVE_RULE, prioritize BLLĐ substantive provisions over NĐ 12 sanctions
                    if route_decision.legal_intent == "SUBSTANTIVE_RULE":
                        blld_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                        other_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") != "VBHN_18_2026" and c.get("metadata", {}).get("doc_id") != "ND_12_2022"]
                        sanction_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") == "ND_12_2022"]
                        issue_retrieved = blld_cands + other_cands + sanction_cands

                    multi_issue_candidates[iss.issue_id] = issue_retrieved
                    for c in issue_retrieved:
                        if c not in combined_candidate_chunks:
                            combined_candidate_chunks.append(c)
            else:
                # Single-issue Hybrid retrieval with Actor-aware filtering
                single_query = decomposed_issues[0].retrieval_query if decomposed_issues else query_for_retrieval
                raw_retrieved = self.hybrid_retriever.retrieve(single_query, top_k=50)

                # Prioritize substantive rules over sanctions if intent is SUBSTANTIVE_RULE
                if route_decision.legal_intent == "SUBSTANTIVE_RULE":
                    blld_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                    other_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") != "VBHN_18_2026" and c.get("metadata", {}).get("doc_id") != "ND_12_2022"]
                    sanction_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") == "ND_12_2022"]
                    raw_retrieved = blld_cands + other_cands + sanction_cands

                # Actor-aware and statutory intent filtering
                if route_decision.intent == "termination_notice":
                    is_domestic = any(k in resolved_q.lower() for k in ["giúp việc", "người giúp việc", "gia đình"])
                    candidates = raw_retrieved
                    if not is_domestic:
                        candidates = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) not in ["162", "89"]]

                    if route_decision.actor == "EMPLOYER":
                        # Prioritize Điều 36 (NSDLĐ đơn phương chấm dứt)
                        d36_chunks = [c for c in candidates if str(c.get("metadata", {}).get("article_number")) == "36"]
                        other_chunks = [c for c in candidates if str(c.get("metadata", {}).get("article_number")) != "36" and str(c.get("metadata", {}).get("article_number")) != "35"]
                        combined_candidate_chunks = (d36_chunks + other_chunks)[: 35]
                    elif route_decision.is_special_occupation:
                        # Special occupation -> prioritize NĐ 145 Điều 7 + BLLĐ Điều 35k1d
                        d7_chunks = [c for c in candidates if c.get("metadata", {}).get("doc_id") == "ND_145_2020" and str(c.get("metadata", {}).get("article_number")) == "7"]
                        d35_special = [
                            c for c in candidates
                            if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"
                            and str(c.get("metadata", {}).get("article_number")) == "35"
                        ]
                        other_chunks = [c for c in candidates if c not in d7_chunks and c not in d35_special]
                        combined_candidate_chunks = (d7_chunks + d35_special + other_chunks)[: 35]
                    else:
                        # General employee -> prioritize BLLĐ Điều 35, exclude NĐ 145 Điều 7
                        d35_chunks = [c for c in candidates if str(c.get("metadata", {}).get("article_number")) == "35"]
                        other_blld = [
                            c for c in candidates
                            if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"
                            and str(c.get("metadata", {}).get("article_number")) not in ["113", "29", "33", "36", "40", "162", "89"]
                            and c not in d35_chunks
                        ]
                        combined_candidate_chunks = (d35_chunks + other_blld)[: 35]
                elif route_decision.legal_intent == "SUBSTANTIVE_RULE" and any(k in resolved_q.lower() for k in ["đặt cọc", "thế chấp", "giữ bằng", "giấy tờ tùy thân", "căn cước"]):
                    # Prioritize substantive prohibition (BLLĐ Điều 17)
                    d17_chunks = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) == "17" and c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                    other_chunks = [c for c in raw_retrieved if c not in d17_chunks]
                    combined_candidate_chunks = (d17_chunks + other_chunks)[: 35]
                else:
                    combined_candidate_chunks = raw_retrieved[: 35]

        # Enforce forbidden provisions from premise gate (prevent premature statutory anchoring)
        if premise_result.forbidden_provisions:
            combined_candidate_chunks = [
                c for c in combined_candidate_chunks
                if not any(fb in c.get("chunk_id", "") for fb in premise_result.forbidden_provisions)
            ]

        t_ret_end = time.perf_counter()
        retrieval_latency_ms = (t_ret_end - t_ret_start) * 1000

        # --- 3c. Evidence Selection & Locking ---
        t_sel_start = time.perf_counter()
        locked_chunks: List[Dict[str, Any]] = []
        locked_chunk_ids: List[str] = []
        multi_issue_locked: Dict[str, List[Dict[str, Any]]] = {}

        if len(decomposed_issues) > 1:
            for iss in decomposed_issues:
                parsed_iss = self.issue_parser.parse(
                    query=iss.retrieval_query,
                    issue_id=iss.issue_id,
                    context_facts=self.memory.accumulated_facts,
                )
                cands = multi_issue_candidates.get(iss.issue_id, combined_candidate_chunks)
                sel_res = self.evidence_selector.select_evidence(parsed_iss, cands)
                issue_locked = [sc.raw_chunk for sc in sel_res.locked_evidence_blocks]
                multi_issue_locked[iss.issue_id] = issue_locked
                for sc in sel_res.locked_evidence_blocks:
                    if sc.chunk_id not in locked_chunk_ids:
                        locked_chunk_ids.append(sc.chunk_id)
                        locked_chunks.append(sc.raw_chunk)
        else:
            current_turn_facts = self.memory._extract_facts(norm_q)
            effective_facts = {**self.memory.accumulated_facts, **current_turn_facts}
            parsed_iss = self.issue_parser.parse(
                query=resolved_q,
                issue_id="ISSUE_1",
                context_facts=effective_facts,
            )
            sel_res = self.evidence_selector.select_evidence(parsed_iss, combined_candidate_chunks)
            locked_chunks = [sc.raw_chunk for sc in sel_res.locked_evidence_blocks]
            locked_chunk_ids = list(sel_res.selected_chunk_ids)

        t_sel_end = time.perf_counter()
        selection_latency_ms = (t_sel_end - t_sel_start) * 1000

        return {
            "retrieval_method": retrieval_method,
            "combined_candidate_chunks": combined_candidate_chunks,
            "locked_chunks": locked_chunks,
            "locked_chunk_ids": locked_chunk_ids,
            "multi_issue_locked": multi_issue_locked,
            "decomposed_issues": decomposed_issues,
            "retrieval_latency_ms": retrieval_latency_ms,
            "selection_latency_ms": selection_latency_ms,
        }

    def _generate_and_validate(
        self,
        norm_q: str,
        resolved_q: str,
        route_decision: RouteDecision,
        premise_result: "PremiseGateResult",
        locked_chunks: List[Dict[str, Any]],
        locked_chunk_ids: List[str],
        multi_issue_locked: Dict[str, List[Dict[str, Any]]],
        decomposed_issues: list,
    ) -> Dict[str, Any]:
        """Stage 4: Build context, invoke LLM, parse JSON, validate citations.

        Returns a dict with keys:
            context, raw_llm_output, validated_resp, locked_chunk_ids, llm_latency_ms.
        """
        # Build compact statutory evidence blocks ONLY from locked evidence
        context = self.context_builder.build_context(
            retrieved_chunks=locked_chunks,
            multi_issue_candidates=multi_issue_locked if len(decomposed_issues) > 1 else None,
            enforce_statutory_bridge=True,
            expand_siblings=False,
        )

        # Synchronize statutory bridges added by ContextBuilder into locked_chunk_ids
        for cid in context.available_chunk_ids:
            if cid not in locked_chunk_ids and any(k in cid for k in ["d35-k1-d", "ND_145_2020#d7"]):
                locked_chunk_ids.append(cid)

        # Construct Prompt
        conv_summary = self.memory.get_history_summary()
        user_prompt = build_user_prompt(
            query=norm_q,
            context_str=context.prompt_context,
            history_summary=conv_summary,
            needs_clarification_hint=route_decision.needs_clarification,
            clarification_reason_hint=route_decision.clarification_reason or "",
            decomposed_issues=decomposed_issues if len(decomposed_issues) > 1 else None,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        # Invoke Local Qwen LLM
        t_llm_start = time.perf_counter()
        llm: Any = self.llm_manager.get_llm()
        llm_response = llm.invoke(messages)
        if hasattr(llm_response, "content"):
            content_val = llm_response.content
            raw_llm_output: str = content_val if isinstance(content_val, str) else str(content_val)
        else:
            raw_llm_output = str(llm_response)
        t_llm_end = time.perf_counter()
        llm_latency_ms = (t_llm_end - t_llm_start) * 1000

        # Parse structured JSON output
        parsed_answer: LegalAnswer = self.validator.parse_llm_json(raw_llm_output)

        # Enforce clarification flag only if query was ambiguous AND no clarification facts exist in memory
        user_has_facts = self.memory.has_clarification_facts()
        if user_has_facts and premise_result.is_sufficient:
            # User provided explicit facts and premise is now sufficient -> MUST ANSWER, DO NOT CLARIFY AGAIN
            parsed_answer.needs_clarification = False
            parsed_answer.clarification_question = None
        elif route_decision.needs_clarification and not user_has_facts and not parsed_answer.needs_clarification and not parsed_answer.abstain:
            parsed_answer.needs_clarification = True
            if not parsed_answer.clarification_question:
                parsed_answer.clarification_question = route_decision.clarification_reason or (
                    "Bạn đang thử việc ở vị trí/công việc nào? "
                    "Nếu biết, hãy cho tôi biết vị trí đó yêu cầu trình độ chuyên môn ở mức nào: "
                    "người quản lý doanh nghiệp, cao đẳng trở lên, trung cấp/kỹ thuật hay nhóm công việc khác?"
                )

        # Validate citations & Backend Citation Ownership using EvidenceMapper
        validated_resp: ValidatedResponse = self.validator.validate_and_format(
            legal_answer=parsed_answer,
            available_chunk_ids=context.available_chunk_ids,
            chunk_registry=context.chunk_metadata_registry,
            evidence_mapper=context.evidence_mapper,
            locked_chunk_ids=locked_chunk_ids,
        )

        return {
            "context": context,
            "raw_llm_output": raw_llm_output,
            "validated_resp": validated_resp,
            "locked_chunk_ids": locked_chunk_ids,
            "llm_latency_ms": llm_latency_ms,
        }

    # -------------------------------------------------------------------------
    # Public orchestrator
    # -------------------------------------------------------------------------

    def run(
        self,
        question: str,
        update_memory: bool = True,
    ) -> ChainExecutionResult:
        """Executes the full deterministic RAG pipeline.

        Pipeline stages:
            0. Normalize input → early return if empty.
            1. Route → early return if out-of-scope.
            2. Material Premise Gate → early return if clarification needed.
            3. Retrieve & Select → decompose, retrieve, filter, score, lock evidence.
            4. Generate & Validate → build context, invoke LLM, parse JSON, validate citations.

        Args:
            question: Raw user question string.
            update_memory: Whether to commit this turn to short-term memory.

        Returns:
            ChainExecutionResult with validated legal answer and full telemetry.
        """
        t0 = time.perf_counter()

        # Stage 0: Normalize
        norm_q = normalize_query(question)
        if not norm_q:
            return self._handle_empty_query(question)

        colloquial_q = normalize_colloquial_vietnamese(norm_q)
        resolved_q = self.memory.resolve_context(colloquial_q)

        # Stage 1: Route
        route_decision = self.router.route(resolved_q)
        if route_decision.strategy == "out_of_scope":
            return self._handle_out_of_scope(question, norm_q, resolved_q, route_decision)

        # Stage 2: Material Premise Gate
        current_turn_facts = self.memory._extract_facts(colloquial_q)
        effective_facts = {**self.memory.accumulated_facts, **current_turn_facts}
        parsed_issue_gate = self.issue_parser.parse(
            query=resolved_q, issue_id="ISSUE_1", context_facts=effective_facts,
        )
        premise_result = self.premise_gate.evaluate(parsed_issue_gate, context_facts=effective_facts)

        if premise_result.needs_clarification:
            return self._handle_premise_gate(
                question, norm_q, resolved_q, route_decision, premise_result, update_memory, t0,
            )

        # Stage 3: Retrieve & Select
        ret_sel = self._retrieve_and_select(norm_q, resolved_q, route_decision, premise_result)

        # Stage 4: Generate & Validate
        gen_val = self._generate_and_validate(
            norm_q, resolved_q, route_decision, premise_result,
            ret_sel["locked_chunks"], ret_sel["locked_chunk_ids"],
            ret_sel["multi_issue_locked"], ret_sel["decomposed_issues"],
        )

        # Commit to short-term conversation state
        if update_memory:
            self.memory.add_turn(
                user_query=norm_q,
                assistant_response=gen_val["validated_resp"].final_answer,
            )

        t_end = time.perf_counter()

        return ChainExecutionResult(
            query=question,
            normalized_query=norm_q,
            resolved_query=resolved_q,
            route_decision=route_decision,
            retrieval_method=ret_sel["retrieval_method"],
            retrieved_chunks=ret_sel["combined_candidate_chunks"],
            formatted_context=gen_val["context"],
            raw_llm_output=gen_val["raw_llm_output"],
            validated_response=gen_val["validated_resp"],
            retrieval_latency_ms=ret_sel["retrieval_latency_ms"],
            llm_latency_ms=gen_val["llm_latency_ms"],
            total_latency_ms=(t_end - t0) * 1000,
            selection_latency_ms=ret_sel["selection_latency_ms"],
            locked_chunk_ids=gen_val["locked_chunk_ids"],
        )
