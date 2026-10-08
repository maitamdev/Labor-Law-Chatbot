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
from typing import Any, Callable, Dict, List, Optional, Set

from langchain_core.messages import HumanMessage, SystemMessage

from models.local_llm import LocalLLMManager
from config.settings import LLM_FOLLOWUP_REWRITE, RAG_MAX_CONTEXT_CHARS, RAG_MAX_CONTEXT_CHUNKS
from rag.bm25_retriever import BM25Retriever
from rag.case_analyzer import CaseAnalysisResult, CaseAnalyzer
from rag.context_builder import ContextBuilder, FormattedContext
from rag.evidence_completeness import EvidenceCompletenessGate, EvidenceCompletenessResult
from rag.evidence_selector import EvidenceSelector, EvidenceSelectionResult
from rag.conversational import SmalltalkReply, detect_smalltalk
from rag.followup_rewriter import FollowupRewriter, looks_like_followup
from rag.hybrid_graph_retriever import HybridGraphRetriever
from rag.hybrid_retriever import HybridRetriever
from rag.streaming import extract_partial_json_string
from rag.issue_decomposer import IssueDecomposer
from rag.legal_calculator import BenefitCalculator, CalculationResult
from rag.legal_issue_parser import LegalIssue, LegalIssueParser
from rag.material_premise_gate import MaterialPremiseGate, PremiseGateResult
from rag.output_validator import LegalAnswer, LegalFinding, OutputValidator, ValidatedResponse, format_answer_markdown
from rag.prompts import SYSTEM_PROMPT, build_user_prompt
from rag.qa_anchor import QuestionLawAnchorIndex
from rag.query_expander import QueryExpander
from rag.query_processor import normalize_query, normalize_colloquial_vietnamese
from rag.query_rewriter import AdaptiveQueryRewriter, RelevanceGrader
from rag.query_router import QueryRouter, RouteDecision
from rag.retirement_age import AGE_EVIDENCE_IDS, grounded_answer as grounded_retirement_age_answer, request_details as retirement_age_request
from rag.voluntary_insurance_support import SUPPORT_EVIDENCE_IDS, grounded_answer as grounded_support_answer, is_support_question
from rag.foreign_worker_multisite import MULTISITE_EVIDENCE_IDS, grounded_answer as grounded_multisite_answer, is_multisite_filing_question
from rag.workplace_lockout import LOCKOUT_EVIDENCE_IDS, grounded_workplace_lockout_answer, standalone_lockout_rule_request

logger = logging.getLogger(__name__)

# Callback types used by the UI for real-time feedback.
StageCallback = Callable[[str, str], None]   # (stage_key, human_label)
TokenCallback = Callable[[str], None]        # full draft answer so far


def _safe_emit(callback: Optional[Callable[..., None]], *args: Any) -> None:
    """UI callbacks must never break the legal pipeline."""
    if callback is None:
        return
    try:
        callback(*args)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("UI callback failed: %s", exc)


@dataclass
class Turn:
    """A single conversational turn."""
    user_query: str
    assistant_response: str
    facts: Dict[str, str] = field(default_factory=dict)


DOMAIN_PRIMARY_DOCS: Dict[str, Set[str]] = {
    "SOCIAL_INSURANCE": {"VBHN_58_2025", "ND_158_2025", "ND_159_2025", "TT_12_2025", "ND_176_2025"},
    "OCCUPATIONAL_SAFETY": {"L_84_2015", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026", "ND_39_2016", "ND_44_2016", "TT_24_2022", "ND_129_2025"},
    "OCCUPATIONAL_ACCIDENT_DISEASE": {"L_84_2015", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026", "ND_39_2016", "ND_129_2025"},
    "UNEMPLOYMENT_INSURANCE": {"LVL_74_2025", "LUAT_74_2025", "ND_374_2025"},
    "FOREIGN_WORKER": {"ND_219_2025", "VBHN_18_2026"},
    "RETIREMENT": {"ND_135_2020", "VBHN_18_2026", "VBHN_58_2025"},
    "CORE_LABOR": {"VBHN_18_2026", "ND_145_2020", "LUAT_113_2025", "ND_168_2026"},
    "MATERNITY": {"VBHN_18_2026", "LUAT_113_2025", "ND_168_2026", "VBHN_58_2025"},
    "COLLECTIVE_LABOR": {"VBHN_18_2026", "VBHN_90_2025", "ND_145_2020", "ND_129_2025"},
    "EMPLOYMENT_SERVICE": {"LVL_74_2025", "ND_318_2025", "ND_352_2025"},
    "CROSS_DOMAIN": {"VBHN_58_2025", "L_84_2015", "LVL_74_2025", "LUAT_74_2025", "VBHN_18_2026", "ND_158_2025", "VBHN_06_BNV_2026", "ND_135_2020", "ND_374_2025"},
}

EVIDENCE_ROLE_RETRIEVAL_HINTS: Dict[str, str] = {
    "OVERTIME_CONSENT": "Điều 107 Khoản 2 Điểm a sự đồng ý của người lao động làm thêm giờ",
    "OVERTIME_LIMIT": "Điều 107 Khoản 2 Điểm b giới hạn số giờ làm thêm trong ngày tháng năm",
    "BONUS_RULE": "Điều 104 Bộ luật Lao động quy chế thưởng căn cứ kết quả sản xuất kinh doanh mức độ hoàn thành công việc",
    "PROHIBITED_MONETARY_DISCIPLINE": "Điều 127 Khoản 2 cấm phạt tiền cắt lương thay xử lý kỷ luật",
    "WAGE_PAYMENT_RULE": "Điều 94 Điều 97 nguyên tắc kỳ hạn trả lương",
    "DELAYED_WAGE_REMEDY": "Điều 97 Khoản 4 trả lương chậm từ 15 ngày tiền lãi",
    "EMPLOYEE_NOTICE_REQUIREMENT": "Điều 35 Khoản 1 thời hạn báo trước của người lao động",
    "EMPLOYEE_NO_NOTICE_EXCEPTION": "Điều 35 Khoản 2 người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước",
    "EMPLOYEE_NO_NOTICE_FOR_MISASSIGNED_WORK": "Điều 35 Khoản 2 Điểm a người lao động không được bố trí theo đúng công việc địa điểm làm việc được nghỉ không cần báo trước Điều 29",
    "WORK_REASSIGNMENT_LIMITS": "Điều 29 Bộ luật Lao động chuyển người lao động làm công việc khác so với hợp đồng lao động",
    "EMPLOYEE_UNLAWFUL_TERMINATION_LIABILITY": "Điều 40 nghĩa vụ người lao động đơn phương chấm dứt trái pháp luật",
    "INDIVIDUAL_LABOUR_DISPUTE_PROCEDURE": "Điều 188 và Điều 190 Bộ luật Lao động thủ tục hòa giải quyền yêu cầu Tòa án và thời hiệu tranh chấp lao động cá nhân",
    "EMPLOYER_MISTREATMENT_PROHIBITION": "Điều 8 Khoản 2 Bộ luật Lao động cấm ngược đãi người lao động",
    "EMPLOYEE_NO_NOTICE_FOR_MISTREATMENT": "Điều 35 Khoản 2 Điểm c người lao động bị người sử dụng lao động đánh đập được nghỉ không cần báo trước",
    "EMPLOYER_MISTREATMENT_SANCTION": "Điều 17 Khoản 4 Điểm a Nghị định 283/2026 xử phạt người sử dụng lao động ngược đãi người lao động",
    "PRE_WORK_CONTRACT_REQUIREMENT": "Điều 13 Khoản 2 trước khi nhận người lao động vào làm việc phải giao kết hợp đồng lao động",
    "EMPLOYMENT_RELATIONSHIP_DEFINITION": "Điều 13 Khoản 1 việc làm có trả công và chịu quản lý được coi là hợp đồng lao động",
    "WRITTEN_CONTRACT_FORM": "Điều 14 Khoản 1 hợp đồng lao động phải bằng văn bản hoặc thông điệp dữ liệu",
    "ORAL_CONTRACT_EXCEPTION": "Điều 14 Khoản 2 hợp đồng dưới 01 tháng có thể giao kết bằng lời nói trừ trường hợp luật định",
    "FORMATION_EQUALITY_GOOD_FAITH": "Điều 15 Khoản 1 nguyên tắc tự nguyện bình đẳng thiện chí hợp tác và trung thực khi giao kết hợp đồng lao động",
    "FORMATION_FREEDOM_LIMITS": "Điều 15 Khoản 2 tự do giao kết nhưng không trái pháp luật thỏa ước lao động tập thể và đạo đức xã hội",
    "MULTIPLE_CONTRACTS_PERMISSION": "Điều 19 Khoản 1 Bộ luật Lao động người lao động có thể giao kết nhiều hợp đồng lao động với nhiều người sử dụng lao động",
    "TERMINATION_SEVERANCE_ALLOWANCE": "Điều 46 Bộ luật Lao động và Điều 8 Nghị định 145/2020 trợ cấp thôi việc người lao động làm việc thường xuyên từ đủ 12 tháng trở lên",
    "PROHIBITED_ACTS_IDENTIFICATION": "Điều 17 Khoản 1 Bộ luật Lao động nghiêm cấm giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ của người lao động Điều 15 Nghị định 283/2026",
    "PREGNANCY_DISMISSAL_PROHIBITION": "Điều 37 Khoản 3 Điều 137 Khoản 3 Bộ luật Lao động người sử dụng lao động không được sa thải hoặc đơn phương chấm dứt hợp đồng lao động đối với lao động nữ mang thai nuôi con dưới 12 tháng tuổi",
    "UNINSURED_ACCIDENT_SUBSTITUTION": "Điều 39 Khoản 4 và Điều 38 Luật An toàn vệ sinh lao động người sử dụng lao động chưa đóng bảo hiểm tai nạn lao động phải bồi thường thanh toán chi phí y tế tiền lương",
    "EMPLOYER_MEDICAL_RESPONSIBILITY": "Điều 38 Khoản 1 Khoản 2 Luật An toàn vệ sinh lao động thanh toán chi phí y tế chi phí đồng chi trả cho người lao động bị tai nạn lao động",
    "EMPLOYER_WAGE_RESPONSIBILITY": "Điều 38 Khoản 3 Luật An toàn vệ sinh lao động trả đủ tiền lương cho người lao động bị tai nạn lao động trong thời gian điều trị",
    "EMPLOYER_ACCIDENT_COMPENSATION": "Điều 38 Khoản 4 Khoản 5 Luật An toàn vệ sinh lao động bồi thường cho người lao động bị tai nạn lao động không do lỗi của người lao động",
    "EMPLOYEE_NO_NOTICE_FOR_UNPAID_WAGE": "Điều 35 Khoản 2 Điểm b Bộ luật Lao động người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước khi không được trả đủ lương hoặc trả lương không đúng thời hạn",
    "TERMINATION_SETTLEMENT_OBLIGATION": "Điều 48 Khoản 1 Khoản 3 Bộ luật Lao động trách nhiệm khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội trả lại sổ bảo hiểm trong thời hạn 14 ngày làm việc",
    "EMPLOYER_TRAINING_OBLIGATION": "Điều 61 Điều 62 Bộ luật Lao động học nghề tập nghề hợp đồng đào tạo nghề không phải hợp đồng lao động",
    "WAGE_DEDUCTION_LIMIT": "Điều 102 Bộ luật Lao động khấu trừ tiền lương người sử dụng lao động chỉ được khấu trừ bồi thường thiệt hại tài sản Điều 129",
    "UNDERPAYMENT_SANCTION": "Điều 17 Nghị định 12/2022 Điều 23 Nghị định 283/2026 xử phạt vi phạm tiền lương trả không đủ tiền lương khấu trừ tiền lương trái quy định buộc trả đủ tiền lương và tiền lãi",
    "DISPUTE_RESOLUTION_PROCEDURE": "Điều 188 Bộ luật Lao động hòa giải viên lao động giải quyết tranh chấp lao động cá nhân về tiền lương khởi kiện Tòa án nhân dân",
}


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

        if any(k in t for k in ["sổ bảo hiểm", "trả sổ", "chốt sổ"]):
            facts["topic"] = "trả sổ bảo hiểm khi chấm dứt hợp đồng"
            facts["action"] = "chấm dứt hợp đồng"
        elif "nghỉ việc" in t or "thôi việc" in t or "đơn phương" in t:
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
        if any(k in q_lower for k in ["sổ bảo hiểm", "trả sổ", "chốt sổ"]):
            supplements.append("thời hạn trả lại sổ bảo hiểm xã hội khi chấm dứt hợp đồng Điều 48 Khoản 1 Khoản 3")
        elif effective_facts.get("action") == "chấm dứt hợp đồng":
            if "nghỉ việc" not in q_lower and "chấm dứt" not in q_lower and not any(k in q_lower for k in ["sổ", "bảo hiểm", "lương"]):
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
    case_analysis: Optional[CaseAnalysisResult] = None
    evidence_completeness: Optional[EvidenceCompletenessResult] = None
    suggestions: List[str] = field(default_factory=list)
    graph_expanded_chunk_ids: List[str] = field(default_factory=list)
    # Standalone question produced by the LLM follow-up rewriter (None if unused).
    followup_rewrite: Optional[str] = None

    @property
    def is_smalltalk(self) -> bool:
        return self.route_decision.strategy == "smalltalk"

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
        max_context_chars: int = RAG_MAX_CONTEXT_CHARS,
        max_chunks: int = RAG_MAX_CONTEXT_CHUNKS,
        max_per_issue_blocks: int = 4,
        index_version: str = "v3",
    ):
        self.top_k = top_k
        self.index_version = index_version
        self.router = QueryRouter()
        self.decomposer = IssueDecomposer()
        self.issue_parser = LegalIssueParser(router=self.router)
        self.evidence_selector = EvidenceSelector()
        self.case_analyzer = CaseAnalyzer()
        self.evidence_gate = EvidenceCompletenessGate()
        self.expander = QueryExpander()
        self.context_builder = ContextBuilder(
            max_context_chars=max_context_chars,
            max_chunks=max_chunks,
            max_per_issue_blocks=max_per_issue_blocks,
        )
        self.validator = OutputValidator()
        self.memory = ConversationMemory(max_turns=3)
        self.premise_gate = MaterialPremiseGate()
        self.qa_anchor_index = QuestionLawAnchorIndex()

        # Initialize or reuse retrievers
        # Default retriever is the Hybrid GraphRAG engine (BM25 + Dense + Neo4j).
        # When Neo4j is disabled/offline it returns exactly the BM25+Dense RRF
        # result, so behaviour degrades gracefully.
        if hybrid_retriever is not None:
            self.hybrid_retriever = hybrid_retriever
            self.bm25_retriever = hybrid_retriever.bm25_retriever
        elif bm25_retriever is not None:
            self.bm25_retriever = bm25_retriever
            self.hybrid_retriever = HybridGraphRetriever(
                bm25_retriever=bm25_retriever,
                index_version=index_version,
            )
        else:
            self.hybrid_retriever = HybridGraphRetriever(index_version=index_version)
            self.bm25_retriever = self.hybrid_retriever.bm25_retriever

        # Local LLM manager
        self.llm_manager = llm_manager or LocalLLMManager()

        # Self-reflective relevance grading and adaptive query rewriter
        self.grader = RelevanceGrader()
        self.query_rewriter = AdaptiveQueryRewriter(llm_manager=self.llm_manager)
        # Conversational follow-up rewriter ("Còn vùng III thì sao?" -> standalone).
        self.followup_rewriter = FollowupRewriter(
            llm_manager=self.llm_manager, enabled=LLM_FOLLOWUP_REWRITE,
        )

    def _resolve_followup(self, colloquial_q: str, on_stage: Optional[StageCallback] = None) -> tuple[str, Optional[str]]:
        """Returns (resolved_query, llm_standalone_or_None).

        The LLM rewrite (if any) replaces the user's wording, while the
        rule-based statutory hints from ConversationMemory are still appended
        so existing fact-driven retrieval boosts keep working.
        """
        regex_resolved = self.memory.resolve_context(colloquial_q)
        if not self.memory.history:
            return regex_resolved, None
        rewrite = None
        try:
            if self.followup_rewriter.enabled and looks_like_followup(colloquial_q, True):
                _safe_emit(on_stage, "analyze", "Đang hiểu câu hỏi nối tiếp từ ngữ cảnh trước…")
                rewrite = self.followup_rewriter.rewrite(colloquial_q, self.memory.history)
        except Exception as exc:  # never let an auxiliary step break the turn
            logger.warning("Follow-up rewriter failed: %s", exc)
            rewrite = None
        if rewrite is None:
            return regex_resolved, None
        suffix = regex_resolved[len(colloquial_q.strip()):] if regex_resolved.startswith(colloquial_q.strip()) else ""
        return f"{rewrite.standalone}{suffix}", rewrite.standalone

    def _repair_role_coverage(
        self,
        issue: LegalIssue,
        selection: EvidenceSelectionResult,
        candidates: List[Dict[str, Any]],
    ) -> tuple[EvidenceSelectionResult, List[Dict[str, Any]]]:
        """Retries retrieval once when required evidence roles are uncovered."""
        required = list(getattr(issue, "required_evidence_roles", None) or [])
        covered: Set[str] = set()
        for block in selection.locked_evidence_blocks:
            covered.update(getattr(block, "evidence_roles", None) or [])
        missing = [role for role in required if role not in covered]
        hints = [EVIDENCE_ROLE_RETRIEVAL_HINTS[role] for role in missing if role in EVIDENCE_ROLE_RETRIEVAL_HINTS]
        if not hints:
            return selection, candidates

        retry_query = f"{issue.raw_query} {' '.join(hints)}"
        retry_chunks = self.hybrid_retriever.retrieve(retry_query, top_k=50)
        merged: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for chunk in retry_chunks + candidates:
            cid = str(chunk.get("chunk_id") or "")
            if cid and cid not in seen:
                seen.add(cid)
                merged.append(chunk)

        repaired = self.evidence_selector.select_evidence(issue, merged)
        repaired_covered: Set[str] = set()
        for block in repaired.locked_evidence_blocks:
            repaired_covered.update(getattr(block, "evidence_roles", None) or [])
        if len(repaired_covered.intersection(required)) >= len(covered.intersection(required)):
            return repaired, merged
        return selection, candidates

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

    @property
    def graph_enabled(self) -> bool:
        """True when the Neo4j knowledge graph is live in the retrieval pipeline."""
        return bool(getattr(self.hybrid_retriever, "graph_available", False))

    def _handle_smalltalk(self, question: str, norm_q: str, reply: SmalltalkReply, t0: float) -> ChainExecutionResult:
        """Stage 0b: Answer greetings/thanks/identity instantly (no retrieval, no LLM).

        Small talk is intentionally NOT written to memory so that legal facts
        from earlier turns keep driving follow-up resolution.
        """
        resp = ValidatedResponse(
            raw_answer=reply.answer,
            final_answer=reply.answer,
            legal_findings=[],
            cited_chunk_ids=[],
            rejected_chunk_ids=[],
            formatted_citations="",
            needs_clarification=False,
            clarification_question=None,
            abstain=False,
            is_fully_grounded=True,
        )
        return ChainExecutionResult(
            query=question,
            normalized_query=norm_q,
            resolved_query=norm_q,
            route_decision=RouteDecision(
                strategy="smalltalk", reason=f"Conversational: {reply.intent}", intent=reply.intent,
                domain="CONVERSATION", target_domains=["CONVERSATION"],
            ),
            retrieval_method="None (Conversational fast-track)",
            retrieved_chunks=[],
            formatted_context=self.context_builder.build_context([]),
            raw_llm_output="",
            validated_response=resp,
            retrieval_latency_ms=0.0,
            llm_latency_ms=0.0,
            total_latency_ms=(time.perf_counter() - t0) * 1000,
            suggestions=list(reply.suggestions),
        )

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
        case_analysis = self.case_analyzer.analyze(resolved_q, decomposed_issues)

        multi_issue_candidates: Dict[str, List[Dict[str, Any]]] = {}
        combined_candidate_chunks: List[Dict[str, Any]] = []
        retrieval_method = "Hybrid RRF (BM25 + BGE-M3)"

        is_domestic = any(k in resolved_q.lower() for k in ["giúp việc", "người giúp việc", "gia đình"])

        # --- 3b. Retrieval ---
        if route_decision.is_exact_reference():
            doc_no = (route_decision.detected_doc_no or "").lower()

            def doc_matches(c):
                meta = c.get("metadata", {})
                c_doc = str(meta.get("doc_id", "")).lower()
                c_no = str(meta.get("document_no", "")).lower()
                if doc_no and (doc_no in c_doc or doc_no in c_no):
                    return True
                for num_key in ["58", "158", "159", "176", "84", "39", "04", "05", "06", "18", "145", "135", "74", "374", "219", "283", "318", "352", "113", "168", "90", "99"]:
                    if doc_no and num_key in doc_no and num_key in c_doc:
                        return True
                return False

            if route_decision.detected_article is not None:
                retrieval_method = "BM25 Lexical (Exact Reference)"
                raw_retrieved = self.bm25_retriever.retrieve(query_for_retrieval, top_k=50)
                art_target = str(route_decision.detected_article)
                exact_art_doc = [
                    c for c in raw_retrieved
                    if str(c.get("metadata", {}).get("article_number")) == art_target and doc_matches(c)
                ]
                art_only = [
                    c for c in raw_retrieved
                    if str(c.get("metadata", {}).get("article_number")) == art_target and c not in exact_art_doc
                ]
                other_chunks = [
                    c for c in raw_retrieved
                    if c not in exact_art_doc and c not in art_only
                ]
                combined_candidate_chunks = (exact_art_doc + art_only + other_chunks)[: self.top_k]
            else:
                retrieval_method = "Hybrid Document Lookup"
                raw_retrieved = self.hybrid_retriever.retrieve(query_for_retrieval, top_k=50)
                doc_matching = [c for c in raw_retrieved if doc_matches(c)]
                other_chunks = [c for c in raw_retrieved if c not in doc_matching]
                combined_candidate_chunks = (doc_matching + other_chunks)[: self.top_k]
            combined_candidate_chunks = self.qa_anchor_index.enrich(
                resolved_q, combined_candidate_chunks
            )[: self.top_k]
        else:
            # Multi-issue or single-issue Hybrid retrieval
            if len(decomposed_issues) > 1:
                retrieval_method = "Multi-Issue Hybrid RRF (BM25 + BGE-M3)"
                for iss in decomposed_issues:
                    issue_retrieved = self.hybrid_retriever.retrieve(iss.retrieval_query, top_k=self.top_k // 2 + 5)
                    issue_retrieved = self.qa_anchor_index.enrich(
                        iss.raw_issue_text or iss.retrieval_query, issue_retrieved
                    )

                    # Filter domestic worker provisions unless question is about domestic workers
                    if not is_domestic:
                        issue_retrieved = [c for c in issue_retrieved if str(c.get("metadata", {}).get("article_number")) not in ["161", "162", "165"]]

                    # If intent is SUBSTANTIVE_RULE, prioritize canonical substantive provisions over sanctions
                    issue_dom = getattr(iss, "domain", route_decision.domain)
                    issue_pri_docs = DOMAIN_PRIMARY_DOCS.get(issue_dom, DOMAIN_PRIMARY_DOCS.get(route_decision.domain, {"VBHN_18_2026"}))
                    if route_decision.legal_intent == "SUBSTANTIVE_RULE":
                        pri_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") in issue_pri_docs]
                        other_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") not in issue_pri_docs and c.get("metadata", {}).get("doc_id") != "ND_12_2022"]
                        sanction_cands = [c for c in issue_retrieved if c.get("metadata", {}).get("doc_id") == "ND_12_2022"]
                        issue_retrieved = pri_cands + other_cands + sanction_cands

                    multi_issue_candidates[iss.issue_id] = issue_retrieved
                    for c in issue_retrieved:
                        if c not in combined_candidate_chunks:
                            combined_candidate_chunks.append(c)
            else:
                # Single-issue Hybrid retrieval with Actor-aware filtering
                single_query = decomposed_issues[0].retrieval_query if decomposed_issues else query_for_retrieval
                raw_retrieved = self.hybrid_retriever.retrieve(single_query, top_k=50)
                raw_retrieved = self.qa_anchor_index.enrich(resolved_q, raw_retrieved)

                # Prioritize substantive rules over sanctions if intent is SUBSTANTIVE_RULE
                primary_docs = DOMAIN_PRIMARY_DOCS.get(route_decision.domain, {"VBHN_18_2026"})

                # Self-reflective Relevance Grading & Adaptive Query Rewriting (ViLeXa CRAG style)
                grade_res = self.grader.grade(
                    single_query,
                    raw_retrieved,
                    primary_docs=primary_docs,
                    expected_intent=route_decision.legal_intent,
                )
                if not grade_res.is_relevant:
                    rewritten_query = self.query_rewriter.rewrite(
                        single_query,
                        domain=route_decision.domain,
                        reason=grade_res.reason,
                    )
                    if rewritten_query != single_query:
                        logger.info(f"Self-reflective query rewrite: '{single_query}' -> '{rewritten_query}' (Reason: {grade_res.reason})")
                        retry_retrieved = self.hybrid_retriever.retrieve(rewritten_query, top_k=50)
                        if retry_retrieved:
                            seen_cids = {c["chunk_id"] for c in retry_retrieved}
                            raw_retrieved = retry_retrieved + [c for c in raw_retrieved if c["chunk_id"] not in seen_cids]

                if route_decision.legal_intent == "SUBSTANTIVE_RULE":
                    pri_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") in primary_docs]
                    other_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") not in primary_docs and c.get("metadata", {}).get("doc_id") != "ND_12_2022"]
                    sanction_cands = [c for c in raw_retrieved if c.get("metadata", {}).get("doc_id") == "ND_12_2022"]
                    raw_retrieved = pri_cands + other_cands + sanction_cands

                # Actor-aware and statutory intent filtering (strictly for CORE_LABOR contract termination)
                if route_decision.intent == "termination_notice" and route_decision.domain == "CORE_LABOR":
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
                        is_misassigned = any(k in resolved_q.lower() for k in [
                            "không được bố trí đúng", "không bố trí đúng", "công việc khác", "làm bốc vác",
                            "bốc vác", "kiến nghị bố trí công việc", "không đúng thỏa thuận", "không đúng hợp đồng",
                            "chuyển làm việc khác", "điều 29",
                        ])
                        has_unlawful_or_comp = any(k in resolved_q.lower() for k in ["bồi thường", "trái pháp luật", "trái luật"])
                        excluded_arts = ["113", "33", "36", "162", "89"] if (is_misassigned or has_unlawful_or_comp) else ["113", "29", "33", "36", "40", "162", "89"]
                        other_blld = [
                            c for c in candidates
                            if c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"
                            and str(c.get("metadata", {}).get("article_number")) not in excluded_arts
                            and c not in d35_chunks
                        ]
                        combined_candidate_chunks = (d35_chunks + other_blld)[: 35]
                elif route_decision.legal_intent == "SUBSTANTIVE_RULE" and any(k in resolved_q.lower() for k in ["đặt cọc", "thế chấp", "giữ bằng", "giấy tờ tùy thân", "căn cước"]):
                    # Prioritize substantive prohibition (BLLĐ Điều 17)
                    d17_chunks = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) == "17" and c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                    other_chunks = [c for c in raw_retrieved if c not in d17_chunks]
                    combined_candidate_chunks = (d17_chunks + other_chunks)[: 35]
                elif any(k in resolved_q.lower() for k in [
                    "nhiều hợp đồng", "nhiều hđlđ", "2 hợp đồng", "hai hợp đồng", "3 hợp đồng",
                    "nhận thêm việc", "làm thêm việc", "làm thêm cho", "nhận thêm công việc",
                    "ký thêm hợp đồng", "ký thêm hđlđ", "làm cho 2 công ty", "làm cho hai công ty",
                    "làm việc cho nhiều", "làm ở nhiều nơi", "làm nhiều nơi", "làm song song",
                    "ký kết hợp đồng lao động với các cơ sở", "ký hợp đồng với các cơ sở",
                    "ký hợp đồng với nhiều công ty", "đồng thời làm việc", "làm việc cho người sử dụng lao động khác",
                ]):
                    # Prioritize Điều 19 BLLĐ (Giao kết nhiều hợp đồng lao động)
                    d19_chunks = [c for c in raw_retrieved if str(c.get("metadata", {}).get("article_number")) == "19" and c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"]
                    for req_cid, req_cl in [("VBHN_18_2026#d19-k1", "1"), ("VBHN_18_2026#d19-k2", "2")]:
                        if not any(c.get("chunk_id") == req_cid for c in d19_chunks):
                            try:
                                coll = self.hybrid_retriever.dense_retriever.vectorstore.get_collection()
                                fetched = coll.get(ids=[req_cid])
                                if fetched and fetched.get("ids"):
                                    d19_chunks.append({
                                        "chunk_id": req_cid,
                                        "content": fetched["documents"][0],
                                        "metadata": fetched["metadatas"][0],
                                        "doc_id": "VBHN_18_2026",
                                        "article_number": "19",
                                        "clause_number": req_cl,
                                        "article_title": "Giao kết nhiều hợp đồng lao động",
                                        "document_title": "Bộ luật Lao động 2019",
                                        "document_no": "18/VBHN-VPQH",
                                        "score": 1.0,
                                    })
                            except Exception:
                                pass
                    d19_chunks.sort(key=lambda x: str(x.get("metadata", {}).get("clause_number") or x.get("clause_number") or ""))
                    other_chunks = [c for c in raw_retrieved if c not in d19_chunks]
                    combined_candidate_chunks = (d19_chunks + other_chunks)[: 35]
                else:
                    combined_candidate_chunks = raw_retrieved[: 35]

        # Enforce forbidden provisions from premise gate (prevent premature statutory anchoring)
        if premise_result and premise_result.forbidden_provisions:
            combined_candidate_chunks = [
                c for c in combined_candidate_chunks
                if not any(fb in c.get("chunk_id", "") for fb in premise_result.forbidden_provisions)
            ]

        # A workplace lockout during a strike is not contract termination.
        # The general selector otherwise overweights Article 36 merely because
        # it also mentions the employer and the workplace.
        lockout_query = standalone_lockout_rule_request(resolved_q)
        if lockout_query:
            combined_candidate_chunks = [
                c for c in combined_candidate_chunks
                if not (
                    c.get("metadata", {}).get("doc_id") == "VBHN_18_2026"
                    and str(c.get("metadata", {}).get("article_number")) == "36"
                )
            ]
        lockout_chunks = (
            self.qa_anchor_index.lookup_chunk_ids(LOCKOUT_EVIDENCE_IDS)
            if lockout_query and len(decomposed_issues) <= 1 else []
        )

        t_ret_end = time.perf_counter()
        retrieval_latency_ms = (t_ret_end - t_ret_start) * 1000

        # --- 3c. Evidence Selection & Locking ---
        t_sel_start = time.perf_counter()
        locked_chunks: List[Dict[str, Any]] = []
        locked_chunk_ids: List[str] = []
        multi_issue_locked: Dict[str, List[Dict[str, Any]]] = {}
        selection_results: Dict[str, EvidenceSelectionResult] = {}

        if len(lockout_chunks) == len(LOCKOUT_EVIDENCE_IDS):
            retrieval_method = "Verified Workplace Lockout Provisions"
            locked_chunks = lockout_chunks
            locked_chunk_ids = [c["chunk_id"] for c in lockout_chunks]
            issue_id = decomposed_issues[0].issue_id if decomposed_issues else "issue_1"
            multi_issue_locked[issue_id] = list(locked_chunks)
            combined_candidate_chunks = lockout_chunks + [
                c for c in combined_candidate_chunks if c.get("chunk_id") not in set(locked_chunk_ids)
            ]
        elif route_decision.is_exact_reference() and len(combined_candidate_chunks) > 0:
            matched_anchor = self.qa_anchor_index.matching_question(resolved_q)
            reviewed_ids = set(matched_anchor.get("reviewed_chunk_ids", [])) if matched_anchor else set()
            reviewed_chunks = [c for c in combined_candidate_chunks if c["chunk_id"] in reviewed_ids]
            locked_chunks = reviewed_chunks if reviewed_chunks else combined_candidate_chunks[:3]
            locked_chunk_ids = [c["chunk_id"] for c in locked_chunks]
            issue_id = decomposed_issues[0].issue_id if decomposed_issues else "issue_1"
            multi_issue_locked[issue_id] = list(locked_chunks)
        elif len(decomposed_issues) > 1:
            for iss in decomposed_issues:
                # Parse the focused question for its legal topic. Parse the
                # enriched text separately and inherit only factual qualifiers;
                # otherwise phrases such as "đi làm thêm" contaminate a
                # contract-classification issue with overtime law.
                parse_q = iss.raw_issue_text or iss.retrieval_query
                parsed_iss = self.issue_parser.parse(
                    query=parse_q,
                    issue_id=iss.issue_id,
                    context_facts=self.memory.accumulated_facts,
                    forced_domain=getattr(iss, "domain", None),
                )
                if iss.retrieval_query and iss.retrieval_query != parse_q:
                    contextual = self.issue_parser.parse(
                        query=iss.retrieval_query,
                        issue_id=iss.issue_id,
                        context_facts=self.memory.accumulated_facts,
                        forced_domain=getattr(iss, "domain", None),
                    )
                    factual_prefixes = ("contract_", "special_occupation_notice")
                    for qualifier in contextual.qualifiers:
                        if qualifier.startswith(factual_prefixes) and qualifier not in parsed_iss.qualifiers:
                            parsed_iss.qualifiers.append(qualifier)
                    if parsed_iss.actor == "UNKNOWN" and contextual.actor != "UNKNOWN":
                        parsed_iss.actor = contextual.actor
                    parsed_iss.material_facts.update(contextual.material_facts)
                if getattr(iss, "legal_event", "UNKNOWN") != "UNKNOWN":
                    parsed_iss.legal_event = iss.legal_event
                if getattr(iss, "legal_events", []):
                    parsed_iss.legal_events = iss.legal_events
                if getattr(iss, "required_evidence_roles", []):
                    parsed_iss.required_evidence_roles = list(dict.fromkeys(iss.required_evidence_roles))

                cands = multi_issue_candidates.get(iss.issue_id, combined_candidate_chunks)
                sel_res = self.evidence_selector.select_evidence(parsed_iss, cands)
                sel_res, repaired_candidates = self._repair_role_coverage(parsed_iss, sel_res, cands)
                multi_issue_candidates[iss.issue_id] = repaired_candidates
                existing_candidate_ids = {c.get("chunk_id") for c in combined_candidate_chunks}
                for repaired_chunk in repaired_candidates:
                    if repaired_chunk.get("chunk_id") not in existing_candidate_ids:
                        combined_candidate_chunks.append(repaired_chunk)
                        existing_candidate_ids.add(repaired_chunk.get("chunk_id"))
                selection_results[iss.issue_id] = sel_res
                issue_locked = [sc.raw_chunk for sc in sel_res.locked_evidence_blocks]
                multi_issue_locked[iss.issue_id] = issue_locked
                for sc in sel_res.locked_evidence_blocks:
                    if sc.chunk_id not in locked_chunk_ids:
                        locked_chunk_ids.append(sc.chunk_id)
                        locked_chunks.append(sc.raw_chunk)
        else:
            current_turn_facts = self.memory._extract_facts(norm_q)
            effective_facts = {**self.memory.accumulated_facts, **current_turn_facts}
            issue_id = decomposed_issues[0].issue_id if decomposed_issues else "issue_1"
            parsed_iss = self.issue_parser.parse(
                query=resolved_q,
                issue_id=issue_id,
                context_facts=effective_facts,
            )
            if decomposed_issues:
                first_iss = decomposed_issues[0]
                if getattr(first_iss, "legal_event", "UNKNOWN") != "UNKNOWN":
                    parsed_iss.legal_event = first_iss.legal_event
                if getattr(first_iss, "legal_events", []):
                    parsed_iss.legal_events = first_iss.legal_events
                if getattr(first_iss, "required_evidence_roles", []):
                    parsed_iss.required_evidence_roles = list(dict.fromkeys(first_iss.required_evidence_roles))

            sel_res = self.evidence_selector.select_evidence(parsed_iss, combined_candidate_chunks)
            sel_res, combined_candidate_chunks = self._repair_role_coverage(
                parsed_iss, sel_res, combined_candidate_chunks,
            )
            selection_results[issue_id] = sel_res
            locked_chunks = [sc.raw_chunk for sc in sel_res.locked_evidence_blocks]
            locked_chunk_ids = list(sel_res.selected_chunk_ids)
            multi_issue_locked[issue_id] = list(locked_chunks)

        t_sel_end = time.perf_counter()
        selection_latency_ms = (t_sel_end - t_sel_start) * 1000

        return {
            "retrieval_method": retrieval_method,
            "combined_candidate_chunks": combined_candidate_chunks,
            "locked_chunks": locked_chunks,
            "locked_chunk_ids": locked_chunk_ids,
            "multi_issue_locked": multi_issue_locked,
            "decomposed_issues": decomposed_issues,
            "case_analysis": case_analysis,
            "selection_results": selection_results,
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
        case_analysis: CaseAnalysisResult,
        selection_results: Dict[str, EvidenceSelectionResult],
        calculation_result: Optional[CalculationResult] = None,
        on_token: Optional[TokenCallback] = None,
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
            allow_repealed=("12/2022" in resolved_q or "nghị định 12" in resolved_q.lower()),
        )

        # Synchronize statutory bridges added by ContextBuilder into locked_chunk_ids
        for cid in context.available_chunk_ids:
            if cid not in locked_chunk_ids:
                locked_chunk_ids.append(cid)

        # The completeness gate evaluates the exact blocks that survived the
        # context budget, not merely the larger retrieval pool.
        context_issue_map: Dict[str, List[Dict[str, Any]]] = {
            str(getattr(issue, "issue_id", f"issue_{idx}")): []
            for idx, issue in enumerate(decomposed_issues, 1)
        }
        default_issue_id = decomposed_issues[0].issue_id if decomposed_issues else "issue_1"
        for block in context.evidence_blocks:
            owner = block.issue_id
            if owner == "statutory_bridge" or not owner:
                owner = default_issue_id
            if owner not in context_issue_map:
                context_issue_map[owner] = []
            meta = dict(context.chunk_metadata_registry.get(block.chunk_id, {}))
            meta["chunk_id"] = block.chunk_id
            context_issue_map[owner].append(meta)

        evidence_completeness = self.evidence_gate.evaluate(
            issues=decomposed_issues,
            issue_evidence_map=context_issue_map,
            selection_results=selection_results,
        )

        # Verified statutory schedules and arithmetic do not need a generative
        # model pass. This avoids both hallucinated numbers and Ollama latency.
        single_issue = len(decomposed_issues) <= 1
        deterministic_answer = (
            grounded_retirement_age_answer(resolved_q, context.available_chunk_ids)
            if single_issue else None
        )
        deterministic_ids = AGE_EVIDENCE_IDS if deterministic_answer else ()
        deterministic_issue = "Tuổi nghỉ hưu sớm"
        if single_issue and not deterministic_answer:
            deterministic_answer = grounded_support_answer(resolved_q, context.available_chunk_ids)
            deterministic_ids = SUPPORT_EVIDENCE_IDS if deterministic_answer else ()
            deterministic_issue = "Hỗ trợ đóng BHXH tự nguyện"
        if single_issue and not deterministic_answer:
            deterministic_answer = grounded_multisite_answer(resolved_q, context.available_chunk_ids)
            deterministic_ids = MULTISITE_EVIDENCE_IDS if deterministic_answer else ()
            deterministic_issue = "Thẩm quyền hồ sơ lao động nước ngoài làm việc tại nhiều tỉnh"
        if single_issue and not deterministic_answer:
            deterministic_answer = grounded_workplace_lockout_answer(resolved_q, context.available_chunk_ids)
            deterministic_ids = LOCKOUT_EVIDENCE_IDS if deterministic_answer else ()
            deterministic_issue = "Đóng cửa tạm thời nơi làm việc khi đình công"
        if deterministic_answer:
            registry = context.chunk_metadata_registry
            cited_ids = list(deterministic_ids)
            citations = context.evidence_mapper.format_citations_from_metadata(
                [registry[cid] for cid in cited_ids]
            )
            validated = ValidatedResponse(
                raw_answer=deterministic_answer,
                final_answer=format_answer_markdown(deterministic_answer) + "\n\n" + citations,
                legal_findings=[LegalFinding(
                    issue_id=decomposed_issues[0].issue_id if decomposed_issues else "issue_1",
                    issue=deterministic_issue,
                    finding=deterministic_answer,
                    supporting_chunk_ids=cited_ids,
                )],
                cited_chunk_ids=cited_ids,
                rejected_chunk_ids=[],
                formatted_citations=citations,
                is_fully_grounded=True,
            )
            validated.evidence_coverage = evidence_completeness.to_dict()
            validated.case_analysis = case_analysis.to_dict()
            return {
                "context": context,
                "raw_llm_output": "[deterministic statutory calculation]",
                "validated_resp": validated,
                "locked_chunk_ids": locked_chunk_ids,
                "llm_latency_ms": 0.0,
                "evidence_completeness": evidence_completeness,
            }

        # Construct Prompt
        conv_summary = self.memory.get_history_summary()
        user_prompt = build_user_prompt(
            query=norm_q,
            context_str=context.prompt_context,
            history_summary=conv_summary,
            needs_clarification_hint=route_decision.needs_clarification,
            clarification_reason_hint=route_decision.clarification_reason or "",
            decomposed_issues=decomposed_issues if len(decomposed_issues) > 1 else None,
            calculation_result=calculation_result,
            case_analysis=case_analysis,
            evidence_completeness=evidence_completeness,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        # Invoke Local Qwen LLM. With an on_token callback the model is streamed:
        # the JSON is accumulated and the partial "answer" value is surfaced as a
        # live draft. Validation below always runs on the COMPLETE output.
        t_llm_start = time.perf_counter()
        llm: Any = self.llm_manager.get_llm()
        if on_token is not None and hasattr(llm, "stream"):
            buffer_parts: List[str] = []
            last_draft = ""
            for chunk in llm.stream(messages):
                piece = getattr(chunk, "content", chunk)
                if not isinstance(piece, str):
                    piece = str(piece or "")
                if not piece:
                    continue
                buffer_parts.append(piece)
                draft = extract_partial_json_string("".join(buffer_parts), "answer")
                if draft and draft != last_draft:
                    last_draft = draft
                    _safe_emit(on_token, draft)
            raw_llm_output = "".join(buffer_parts)
        else:
            llm_response = llm.invoke(messages)
            if hasattr(llm_response, "content"):
                content_val = llm_response.content
                raw_llm_output = content_val if isinstance(content_val, str) else str(content_val)
            else:
                raw_llm_output = str(llm_response)
        t_llm_end = time.perf_counter()
        llm_latency_ms = (t_llm_end - t_llm_start) * 1000

        # Parse structured JSON output
        parsed_answer: LegalAnswer = self.validator.parse_llm_json(raw_llm_output)

        # Enforce clarification flag only if query was ambiguous AND no clarification facts exist in memory
        from rag.query_processor import is_scenario_or_legal_consultation
        is_scenario = is_scenario_or_legal_consultation(norm_q, raw_query=resolved_q)
        user_has_facts = self.memory.has_clarification_facts()
        if is_scenario or (user_has_facts and premise_result.is_sufficient) or route_decision.is_exact_reference() or (premise_result.is_sufficient and not route_decision.needs_clarification and not premise_result.needs_clarification):
            # Scenario/consultation, exact reference, or sufficient premise -> MUST ANSWER, DO NOT CLARIFY
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
            issue_evidence_map={
                issue_id: [str(item.get("chunk_id")) for item in chunks if item.get("chunk_id")]
                for issue_id, chunks in context_issue_map.items()
            },
            expected_issues=decomposed_issues,
            unsupported_issue_ids=evidence_completeness.unsupported_issue_ids,
            case_analysis=case_analysis,
        )
        validated_resp.evidence_coverage = evidence_completeness.to_dict()
        validated_resp.case_analysis = case_analysis.to_dict()

        return {
            "context": context,
            "raw_llm_output": raw_llm_output,
            "validated_resp": validated_resp,
            "locked_chunk_ids": locked_chunk_ids,
            "llm_latency_ms": llm_latency_ms,
            "evidence_completeness": evidence_completeness,
        }

    # -------------------------------------------------------------------------
    # Public orchestrator
    # -------------------------------------------------------------------------

    def run(
        self,
        question: str,
        update_memory: bool = True,
        on_stage: Optional[StageCallback] = None,
        on_token: Optional[TokenCallback] = None,
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
            on_stage: Optional UI callback (stage_key, label) fired as stages start.
            on_token: Optional UI callback receiving the live draft answer while
                the local model streams. The final validated answer may differ.

        Returns:
            ChainExecutionResult with validated legal answer and full telemetry.
        """
        t0 = time.perf_counter()

        # Stage 0: Normalize
        norm_q = normalize_query(question)
        if not norm_q:
            return self._handle_empty_query(question)

        # Stage 0b: Conversational fast-track. Checked on the raw turn BEFORE
        # memory resolution, which would otherwise append legal context to
        # "cảm ơn" and make it look like a legal question.
        smalltalk = detect_smalltalk(question, has_history=bool(self.memory.history))
        if smalltalk is not None:
            return self._handle_smalltalk(question, norm_q, smalltalk, t0)

        _safe_emit(on_stage, "analyze", "Đang phân tích câu hỏi và ngữ cảnh hội thoại…")
        colloquial_q = normalize_colloquial_vietnamese(norm_q)
        resolved_q, followup_standalone = self._resolve_followup(colloquial_q, on_stage)

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

        from rag.query_processor import is_scenario_or_legal_consultation
        is_scenario = is_scenario_or_legal_consultation(resolved_q, raw_query=question)
        if is_scenario:
            premise_result.needs_clarification = False
            premise_result.clarification_question = None
            premise_result.clarification_options = []
            premise_result.is_sufficient = True

        calc_result = BenefitCalculator.extract_and_calculate(resolved_q, effective_facts)
        if calc_result and calc_result.needs_clarification:
            if is_scenario:
                calc_result = None
            else:
                premise_result.needs_clarification = True
                premise_result.clarification_question = calc_result.explanation

        if premise_result.needs_clarification:
            return self._handle_premise_gate(
                question, norm_q, resolved_q, route_decision, premise_result, update_memory, t0,
            )

        # Stage 3: Retrieve & Select
        _safe_emit(
            on_stage, "retrieve",
            "Đang truy hồi điều luật (BM25 + Vector + Đồ thị tri thức Neo4j)…"
            if self.graph_enabled else "Đang truy hồi điều luật (BM25 + Vector)…",
        )
        ret_sel = self._retrieve_and_select(norm_q, resolved_q, route_decision, premise_result)
        graph_ids = [
            str(c.get("chunk_id")) for c in ret_sel["combined_candidate_chunks"]
            if c.get("retrieval_source") == "graph" and c.get("chunk_id")
        ]
        if graph_ids:
            ret_sel["retrieval_method"] = f"{ret_sel['retrieval_method']} + Neo4j Graph Expansion"
        if getattr(self.hybrid_retriever, "dense_ready", True) is False and "BGE-M3" in ret_sel["retrieval_method"]:
            ret_sel["retrieval_method"] = ret_sel["retrieval_method"].replace(
                "BM25 + BGE-M3", "BM25 only - dense unavailable"
            )

        # Give the retirement calculator the complete legal table and both
        # Article 5 exceptions. The small local model must not do age/month
        # subtraction or silently omit the ten-year exception.
        if len(ret_sel["decomposed_issues"]) <= 1 and retirement_age_request(resolved_q):
            age_chunks = []
            for chunk_id in AGE_EVIDENCE_IDS:
                chunk = self.context_builder._get_chunk_by_id(chunk_id)
                if chunk:
                    age_chunks.append(chunk)
            if len(age_chunks) == len(AGE_EVIDENCE_IDS):
                ret_sel["locked_chunks"] = age_chunks + [
                    chunk for chunk in ret_sel["locked_chunks"]
                    if chunk.get("chunk_id") not in set(AGE_EVIDENCE_IDS)
                ]
                ret_sel["locked_chunk_ids"] = list(AGE_EVIDENCE_IDS) + [
                    chunk_id for chunk_id in ret_sel["locked_chunk_ids"]
                    if chunk_id not in set(AGE_EVIDENCE_IDS)
                ]

        if len(ret_sel["decomposed_issues"]) <= 1 and is_support_question(resolved_q):
            support_chunks = [self.context_builder._get_chunk_by_id(cid) for cid in SUPPORT_EVIDENCE_IDS]
            if all(support_chunks):
                support_ids = set(SUPPORT_EVIDENCE_IDS)
                ret_sel["locked_chunks"] = support_chunks + [
                    chunk for chunk in ret_sel["locked_chunks"]
                    if chunk.get("chunk_id") not in support_ids
                ]
                ret_sel["locked_chunk_ids"] = list(SUPPORT_EVIDENCE_IDS) + [
                    cid for cid in ret_sel["locked_chunk_ids"] if cid not in support_ids
                ]

        if len(ret_sel["decomposed_issues"]) <= 1 and is_multisite_filing_question(resolved_q):
            multisite_chunks = [self.context_builder._get_chunk_by_id(cid) for cid in MULTISITE_EVIDENCE_IDS]
            if all(multisite_chunks):
                multisite_ids = set(MULTISITE_EVIDENCE_IDS)
                ret_sel["locked_chunks"] = multisite_chunks + [
                    chunk for chunk in ret_sel["locked_chunks"]
                    if chunk.get("chunk_id") not in multisite_ids
                ]
                ret_sel["locked_chunk_ids"] = list(MULTISITE_EVIDENCE_IDS) + [
                    cid for cid in ret_sel["locked_chunk_ids"] if cid not in multisite_ids
                ]

        # Stage 4: Generate & Validate
        _safe_emit(on_stage, "generate", "Đang soạn câu trả lời từ căn cứ đã khóa…")
        gen_val = self._generate_and_validate(
            followup_standalone or norm_q, resolved_q, route_decision, premise_result,
            ret_sel["locked_chunks"], ret_sel["locked_chunk_ids"],
            ret_sel["multi_issue_locked"], ret_sel["decomposed_issues"],
            ret_sel["case_analysis"], ret_sel["selection_results"],
            calculation_result=calc_result,
            on_token=on_token,
        )
        _safe_emit(on_stage, "validate", "Đã đối soát trích dẫn với căn cứ pháp lý.")



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
            case_analysis=ret_sel["case_analysis"],
            evidence_completeness=gen_val["evidence_completeness"],
            graph_expanded_chunk_ids=graph_ids,
            followup_rewrite=followup_standalone,
        )

    def invoke(
        self,
        input: Any,
        config: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChainExecutionResult:
        """Standard LangChain Runnable interface: accepts str or dict with 'query'/'question'."""
        if isinstance(input, str):
            question = input
        elif isinstance(input, dict):
            question = str(input.get("query") or input.get("question") or input.get("input") or "")
        else:
            question = str(input)
        return self.run(question, **kwargs)

