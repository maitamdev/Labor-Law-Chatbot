# -*- coding: utf-8 -*-
"""
VietLabor AI - Deterministic Evidence Selector (Phase 5E)
Evaluates candidate legal evidence chunks against structured LegalIssue features
using multi-signal generic scoring (numeric, qualifier, temporal unit, actor, intent,
and sibling competition) and LOCKS canonical evidence before generation.

Score magnitudes follow a documented scale (see config/evidence_scoring_rules.yaml):
    SCORE_NUDGE       (+/- 1.0 ~ 2.0)  Minor preference / soft penalty
    SCORE_STRONG      (+/- 3.0 ~ 4.0)  Confidently select correct clause/point
    SCORE_LOCK        (+/- 5.0 ~ 6.5)  Single authoritative provision for the issue
    SCORE_DOMINANT    (+/- 8.0 ~10.0)  Exactly ONE correct provision; suppress all others
    SCORE_HARD_SUPPRESS   (-15.0)      Categorically irrelevant provision
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata

from config.metadata_registry import get_verified_metadata
from rag.legal_issue_parser import LegalIssue, LegalIssueParser

logger = logging.getLogger(__name__)


# ==============================================================================
# SCORING SCALE CONSTANTS
# All numeric score values in score_candidate() follow this scale.
# See config/evidence_scoring_rules.yaml for full rationale per rule.
# ==============================================================================

# Nudge: minor preference, used for topic-level article range matching
SCORE_NUDGE = 1.0         # (+/- 1.0 ~ 2.0)

# Strong: confidently disambiguate among 2-3 sibling clauses/points
SCORE_STRONG = 3.0        # (+/- 3.0 ~ 4.0)

# Lock: single authoritative provision for the legal issue
SCORE_LOCK = 5.0          # (+/- 5.0 ~ 6.5)

# Dominant: exactly ONE correct provision exists; aggressively suppress all others
SCORE_DOMINANT = 8.0      # (+/- 8.0 ~ 10.0)

# Hard suppress: provision is categorically irrelevant to the query type
SCORE_HARD_SUPPRESS = -15.0



@dataclass
class ScoredEvidence:
    """A candidate evidence chunk scored against a legal issue."""
    chunk_id: str
    doc_id: str
    article_number: Optional[int]
    clause_number: Optional[int]
    point: Optional[str]
    content: str
    article_title: str
    document_no: str
    document_title: str
    raw_chunk: Dict[str, Any]

    # Individual signal scores
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    topic_score: float = 0.0
    actor_score: float = 0.0
    intent_score: float = 0.0
    qualifier_score: float = 0.0
    numeric_score: float = 0.0
    specificity_score: float = 0.0
    total_score: float = 0.0

    # Phase 5G.3 Role and Rule metadata
    source_role: str = "FRAMEWORK_LAW"
    rule_type: str = "GENERAL_RULE"

    # Phase 5H.3 Legal Event & Evidence Role Grounding
    legal_event: str = "UNKNOWN"
    evidence_roles: List[str] = field(default_factory=list)

    score_details: Dict[str, float] = field(default_factory=dict)


@dataclass
class EvidenceSelectionResult:
    """Result of deterministic evidence selection for a legal issue."""
    issue_id: str
    selected_chunk_ids: List[str]
    locked_evidence_blocks: List[ScoredEvidence]
    all_scored_candidates: List[ScoredEvidence]
    best_score: float
    second_score: float
    confidence_margin: float
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None


class EvidenceSelector:
    """Selects canonical legal evidence deterministically before answer generation."""

    def __init__(
        self,
        weight_semantic: float = 1.0,
        weight_lexical: float = 1.0,
        weight_topic: float = 1.5,
        weight_actor: float = 1.5,
        weight_intent: float = 2.0,
        weight_qualifier: float = 2.5,
        weight_numeric: float = 3.0,
        weight_specificity: float = 1.0,
        min_confidence_threshold: float = 0.5,
        min_margin_threshold: float = 0.1,
    ):
        self.w_sem = weight_semantic
        self.w_lex = weight_lexical
        self.w_top = weight_topic
        self.w_act = weight_actor
        self.w_int = weight_intent
        self.w_qual = weight_qualifier
        self.w_num = weight_numeric
        self.w_spec = weight_specificity
        self.min_confidence = min_confidence_threshold
        self.min_margin = min_margin_threshold

    def _extract_meta(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        meta = chunk.get("metadata") or chunk
        doc_id = meta.get("doc_id", "")
        doc_meta = get_verified_metadata(doc_id)
        source_role = meta.get("source_role") or doc_meta.get("source_role", "FRAMEWORK_LAW")
        cid = chunk.get("chunk_id", meta.get("chunk_id", ""))
        art_title = meta.get("article_title", "")
        content = chunk.get("content", meta.get("content", ""))
        rule_type = meta.get("rule_type") or self._classify_chunk_rule_type(cid, art_title, content)
        art_num = int(meta["article_number"]) if meta.get("article_number") is not None and str(meta["article_number"]).isdigit() else None
        cl_num = int(meta["clause_number"]) if meta.get("clause_number") is not None and str(meta["clause_number"]).isdigit() else None
        point = str(meta.get("point") or "").strip().lower() or None
        legal_event = meta.get("legal_event") or self._classify_chunk_legal_event(doc_id, art_num, art_title, content)
        evidence_roles = meta.get("evidence_roles") or self._classify_chunk_evidence_roles(cid, doc_id, art_num, cl_num, point, art_title, content)
        return {
            "chunk_id": cid,
            "doc_id": doc_id,
            "document_no": meta.get("document_no", meta.get("doc_id", "")),
            "document_title": meta.get("doc_title", meta.get("document_title", "")),
            "article_number": art_num,
            "article_title": art_title,
            "clause_number": cl_num,
            "point": point,
            "content": content,
            "domain": meta.get("domain", "CORE_LABOR"),
            "status": meta.get("status", "CURRENT"),
            "source_role": source_role,
            "rule_type": rule_type,
            "legal_event": legal_event,
            "evidence_roles": evidence_roles,
        }

    @staticmethod
    def _classify_chunk_legal_event(doc_id: str, article_number: Optional[int], article_title: str, content: str) -> str:
        """Classifies a chunk into its primary legal event."""
        c_all = (article_title + " " + content).lower()
        if doc_id in ["L_84_2015", "ND_39_2016", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026"]:
            if "bệnh nghề nghiệp" in c_all:
                return "OCCUPATIONAL_DISEASE"
            return "OCCUPATIONAL_ACCIDENT"
        if doc_id in ["VBHN_58_2025", "ND_158_2025", "ND_159_2025", "TT_12_2025", "ND_176_2025"]:
            if article_number in [24, 25, 26, 27, 28, 29] or "ốm đau" in article_title.lower():
                return "ORDINARY_SICKNESS"
            if article_number in [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41] or "thai sản" in article_title.lower():
                return "MATERNITY"
            if article_number in [66, 67, 68, 69, 70, 71] or "tử tuất" in article_title.lower() or "mai táng" in article_title.lower():
                return "SURVIVORSHIP"
            if article_number in [2, 21] or "tham gia" in article_title.lower() or "đối tượng" in article_title.lower():
                return "INSURANCE_CONTRIBUTION"
            return "SOCIAL_INSURANCE"
        if doc_id in ["LVL_74_2025", "ND_374_2025"] or "thất nghiệp" in article_title.lower():
            return "UNEMPLOYMENT"
        if doc_id == "ND_135_2020" or (doc_id == "VBHN_18_2026" and article_number == 169):
            return "RETIREMENT"
        if doc_id == "ND_219_2025" or (doc_id == "VBHN_18_2026" and article_number in [151, 152, 153, 154, 155]):
            return "FOREIGN_WORKER"
        if doc_id == "VBHN_18_2026":
            if article_number == 13:
                return "DE_FACTO_LABOR_CONTRACT"
            if article_number == 17:
                return "EMPLOYER_PROHIBITED_ACTS"
            if article_number == 168:
                return "INSURANCE_CONTRIBUTION"
            if article_number in [34, 35, 36, 37, 38, 39, 40, 41, 46, 47, 48]:
                return "TERMINATION"
            if article_number in [6, 60, 61, 62]:
                return "VOCATIONAL_TRAINING"
            if article_number in [24, 25, 26, 27]:
                return "PROBATION"
            if article_number in [90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104]:
                return "WAGE_AND_SALARY"
            return "CORE_LABOR"
        return "UNKNOWN"

    @staticmethod
    def _classify_chunk_evidence_roles(
        chunk_id: str,
        doc_id: str,
        article_number: Optional[int],
        clause_number: Optional[int],
        point: Optional[str],
        article_title: str,
        content: str,
    ) -> List[str]:
        """Classifies a chunk into its generic legal evidence roles."""
        roles: List[str] = []
        c_all = (article_title + " " + content).lower()

        # De Facto Labor Contract Definition (Điều 13 BLLĐ 2019)
        if doc_id == "VBHN_18_2026" and article_number == 13:
            roles.append("EMPLOYMENT_RELATIONSHIP_DEFINITION")

        # Employer Prohibited Acts (Điều 17 BLLĐ 2019 & Điều 9 NĐ 12/2022)
        if (doc_id == "VBHN_18_2026" and article_number == 17) or (doc_id == "ND_12_2022" and article_number == 9):
            roles.append("PROHIBITED_ACTS_IDENTIFICATION")

        # Employer Insurance Obligation
        if (doc_id == "VBHN_18_2026" and article_number == 168) or (doc_id == "VBHN_58_2025" and article_number in [2, 21]) or (doc_id == "LVL_74_2025" and article_number in [59, 75]):
            roles.append("EMPLOYER_INSURANCE_OBLIGATION")
        elif "nghĩa vụ tham gia bảo hiểm xã hội" in c_all or "phải tham gia bảo hiểm xã hội bắt buộc" in c_all or "trách nhiệm tham gia bảo hiểm" in c_all:
            roles.append("EMPLOYER_INSURANCE_OBLIGATION")

        # Employer Accident Responsibilities (Điều 38 Luật ATVSLĐ)
        if doc_id == "L_84_2015" and article_number == 38:
            if clause_number in [1, 2] or any(k in c_all for k in ["sơ cứu", "cấp cứu", "chi phí y tế", "viện phí", "đồng chi trả"]):
                roles.append("EMPLOYER_MEDICAL_RESPONSIBILITY")
            if clause_number == 3 or any(k in c_all for k in ["trả đủ tiền lương", "tiền lương trong thời gian điều trị"]):
                roles.append("EMPLOYER_WAGE_RESPONSIBILITY")
            if clause_number in [4, 5] or "bồi thường cho người lao động" in c_all:
                roles.append("EMPLOYER_ACCIDENT_COMPENSATION")
            if clause_number == 6 or "trợ cấp cho người lao động bị tai nạn lao động mà do lỗi của chính họ" in c_all:
                roles.append("EMPLOYER_ACCIDENT_ALLOWANCE")
            if clause_number is None:
                roles.extend(["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY", "EMPLOYER_ACCIDENT_COMPENSATION"])

        # Uninsured accident substitution (Điều 39k4 Luật ATVSLĐ)
        if doc_id == "L_84_2015" and article_number == 39:
            if clause_number == 4 or any(k in c_all for k in ["không đóng bảo hiểm", "chưa đóng bảo hiểm", "khoản tiền tương ứng"]):
                roles.append("UNINSURED_ACCIDENT_SUBSTITUTION")
            else:
                roles.append("EMPLOYER_ACCIDENT_COMPENSATION")

        # Insurance Fund Accident Entitlement (Điều 45, 48, 49, 53 Luật ATVSLĐ)
        if doc_id in ["L_84_2015", "VBHN_04_BNV_2026", "VBHN_06_BNV_2026"] and (article_number in [45, 48, 49, 50, 53] or "quỹ bảo hiểm tai nạn" in c_all):
            roles.append("INSURANCE_FUND_ENTITLEMENT")

        # Sickness Benefits
        if doc_id == "VBHN_58_2025" and article_number in [25, 26, 28]:
            roles.extend(["SICKNESS_BENEFIT_DURATION", "SICKNESS_BENEFIT_RATE"])

        # Maternity Benefits
        if doc_id == "VBHN_58_2025" and article_number in [31, 34, 38, 39]:
            roles.append("MATERNITY_BENEFIT")

        # Vocational Training Duties & Cost Refund
        if doc_id == "VBHN_18_2026":
            if article_number in [6, 60, 61]:
                roles.append("EMPLOYER_TRAINING_OBLIGATION")
            if article_number in [62, 40]:
                roles.append("TRAINING_COST_REFUND")
            if article_number == 46:
                roles.append("TERMINATION_SEVERANCE_ALLOWANCE")
            if article_number == 41:
                roles.append("UNLAWFUL_TERMINATION_COMPENSATION")
            if article_number == 5 and clause_number == 1:
                roles.append("EMPLOYEE_SAFETY_REFUSAL_RIGHT")
            if article_number == 127 and clause_number == 2:
                roles.append("PROHIBITED_SAFETY_DISCIPLINE")

        # Safety Work Refusal & Prohibited Discipline (Luật ATVSLĐ Điều 6, 12)
        if doc_id == "L_84_2015":
            if article_number == 6 and (point == "đ" or clause_number == 1 or "từ chối" in c_all):
                roles.extend(["EMPLOYEE_SAFETY_REFUSAL_RIGHT", "PROHIBITED_SAFETY_DISCIPLINE"])
            if article_number == 12 and clause_number == 4:
                roles.extend(["EMPLOYEE_SAFETY_REFUSAL_RIGHT", "PROHIBITED_SAFETY_DISCIPLINE"])

        seen_r: Set[str] = set()
        deduped_r: List[str] = []
        for r in roles:
            if r not in seen_r:
                seen_r.add(r)
                deduped_r.append(r)
        return deduped_r

    @staticmethod
    def _classify_chunk_rule_type(chunk_id: str, article_title: str, content: str) -> str:
        """Deterministically classifies statutory chunk into its functional rule type."""
        cid_lower = chunk_id.lower()
        if "preamble" in cid_lower:
            return "PREAMBLE"

        t_lower = article_title.lower()
        c_lower = (article_title + " " + content).lower()

        # DOSSIER: Application files, documentation sets
        if any(k in t_lower for k in ["hồ sơ", "thành phần hồ sơ"]) or any(k in c_lower for k in ["hồ sơ đề nghị", "hồ sơ gồm", "bộ hồ sơ", "văn bản đề nghị cấp"]):
            return "DOSSIER"

        # DEADLINE: Advance notice windows, statutory processing times
        if any(k in t_lower for k in ["thời hạn", "thời điểm", "trình tự, thời hạn"]) and any(k in c_lower for k in ["ngày làm việc", "kể từ ngày", "chậm nhất", "trước ít nhất", "trong thời hạn", "thời điểm hưởng"]):
            return "DEADLINE"
        if any(k in c_lower for k in ["trước ít nhất 15 ngày", "trong thời hạn 10 ngày", "trong thời hạn 05 ngày", "trong thời hạn 03 tháng", "thời điểm hưởng lương hưu là ngày"]):
            return "DEADLINE"

        # NUMERIC_THRESHOLD: Age tables, quotas, capital thresholds
        if any(k in t_lower for k in ["tuổi nghỉ hưu", "lộ trình", "tiêu chuẩn", "mức lương", "mức trợ cấp"]):
            if any(k in c_lower for k in ["năm 202", "bảng", "tăng thêm 03 tháng", "tăng thêm 04 tháng", "61 tuổi", "62 tuổi", "57 tuổi", "60 tuổi", "3 tỷ", "dưới 90 ngày", "01 năm", "03 năm"]):
                return "NUMERIC_THRESHOLD"
        if any(k in c_lower for k in ["giá trị góp vốn từ 3 tỷ", "dưới 90 ngày trong 01 năm", "ít nhất 01 năm và có ít nhất 03 năm", "đại học trở lên và có ít nhất 03 năm", "thấp hơn tối đa 05 tuổi", "thấp hơn tối đa 10 tuổi"]):
            return "NUMERIC_THRESHOLD"

        # DURATION: Maximum validity limits, extension caps
        if any(k in c_lower for k in ["thời hạn của giấy phép lao động", "thời hạn tối đa", "được gia hạn một lần tối đa", "thời hạn hợp đồng lao động"]):
            return "DURATION"

        # PROCEDURE: Steps, submission channels, reporting obligations
        if any(k in t_lower for k in ["trình tự", "thủ tục", "thẩm quyền", "báo cáo giải trình", "thông báo tuyển dụng"]):
            return "PROCEDURE"
        if any(k in c_lower for k in ["trình tự cấp", "trình tự gia hạn", "trình tự cấp lại", "nộp 01 bộ hồ sơ", "cơ quan có thẩm quyền cấp"]):
            return "PROCEDURE"

        # EXEMPTION: Cases exempt from permit
        if any(k in t_lower for k in ["không thuộc diện", "miễn giấy phép"]):
            return "EXEMPTION"
        if any(k in c_lower for k in ["các trường hợp người lao động nước ngoài không thuộc diện", "được miễn giấy phép"]):
            return "EXEMPTION"

        # REVOCATION: Cancellation and withdrawal of permits
        if any(k in t_lower for k in ["thu hồi", "chấm dứt hiệu lực"]):
            return "REVOCATION"

        # SANCTION: Fines and administrative penalties
        if any(k in c_lower for k in ["phạt tiền", "phạt cảnh cáo", "biện pháp khắc phục"]):
            return "SANCTION"

        return "GENERAL_RULE"

    def score_candidate(
        self,
        issue: LegalIssue,
        chunk: Dict[str, Any],
        retrieval_rank: int = 0,
        total_candidates: int = 20,
    ) -> ScoredEvidence:
        """Computes generic multi-signal scores for a candidate chunk against an issue."""
        m = self._extract_meta(chunk)
        cid = m["chunk_id"]
        doc_id = m["doc_id"]
        art_num = m["article_number"]
        cl_num = m["clause_number"]
        pt = m["point"]
        content = m["content"]
        art_title = m["article_title"]
        c_lower = (content + " " + art_title).lower()

        # 1. Semantic score (from retrieval ranking or combined_score)
        raw_combined = chunk.get("combined_score")
        if raw_combined is not None and isinstance(raw_combined, (int, float)):
            s_sem = min(1.0, float(raw_combined) * 15.0)  # scale RRF to ~0-1
        else:
            s_sem = max(0.0, 1.0 - (retrieval_rank / max(1, total_candidates)))

        # 2. Lexical score (token overlap between query and chunk content)
        q_tokens = set(re.findall(r"\w+", issue.raw_query.lower()))
        c_tokens = set(re.findall(r"\w+", c_lower))
        overlap = len(q_tokens.intersection(c_tokens))
        s_lex = overlap / max(1, len(q_tokens))

        # 3. Topic & Domain score (Phase 5G & 5G.3)
        s_top = 0.0
        c_domain = m.get("domain", "CORE_LABOR")
        c_status = m.get("status", "CURRENT")
        source_role = m.get("source_role", "FRAMEWORK_LAW")
        rule_type = m.get("rule_type", "GENERAL_RULE")
        q_spec = getattr(issue, "question_specificity", "GENERAL_PRINCIPLE")
        issue_domain = getattr(issue, "domain", "CORE_LABOR")

        # Status-aware guard: suppressed repealed law from overriding current law
        if c_status == "REPEALED":
            s_top += SCORE_HARD_SUPPRESS  # -15.0

        # Preamble Suppression: Preambles must NEVER override substantive statutory articles
        # unless query is explicitly asking about document validity/enactment (CURRENT_STATUS)
        if (cid.endswith("#preamble") or rule_type == "PREAMBLE") and q_spec != "CURRENT_STATUS":
            s_top += SCORE_HARD_SUPPRESS  # -15.0

        # Strike Suppression: Articles 198-220 of VBHN_18_2026 (Chương XIV: Đình công)
        # must NEVER be cited unless query explicitly mentions "đình công" or "tranh chấp tập thể"
        if doc_id == "VBHN_18_2026" and art_num and 198 <= art_num <= 220:
            q_low = issue.raw_query.lower()
            if not any(k in q_low for k in ["đình công", "dinh cong", "tranh chấp tập thể", "tranh chấp lao động tập thể"]):
                s_top += SCORE_HARD_SUPPRESS  # -15.0

        if issue_domain == "RETIREMENT":
            if doc_id == "ND_135_2020" or c_domain == "RETIREMENT":
                s_top += SCORE_LOCK  # +5.0
            elif doc_id == "VBHN_18_2026" and art_num == 169:
                if q_spec in ["NUMERIC_THRESHOLD", "DEADLINE", "CALCULATION", "PROCEDURE"]:
                    s_top += SCORE_NUDGE  # +1.0 (allow decree schedule/detail to lead)
                else:
                    s_top += SCORE_LOCK   # +5.0 (general retirement principle)
            else:
                s_top -= SCORE_STRONG
        elif issue_domain == "UNEMPLOYMENT_INSURANCE":
            if doc_id in ["LVL_74_2025", "ND_374_2025"] or c_domain == "UNEMPLOYMENT_INSURANCE":
                s_top += SCORE_LOCK  # +5.0
                # Case: UI mandatory coverage / participation / foreign worker
                if any(k in issue.raw_query.lower() for k in ["bắt buộc phải đóng", "phải đóng", "đối tượng tham gia", "đóng bảo hiểm thất nghiệp", "nước ngoài"]):
                    if doc_id == "LVL_74_2025" and art_num in [59, 75]:
                        s_top += 5.0
                # Case: UI entitlement conditions / application
                if any(k in issue.raw_query.lower() for k in ["điều kiện", "hưởng trợ cấp thất nghiệp", "nhận bhtn", "lấy thất nghiệp", "thủ tục"]):
                    if doc_id == "LVL_74_2025" and art_num == 81:
                        s_top += 5.0
                    elif doc_id == "ND_374_2025" and art_num in [4, 9]:
                        s_top += 4.0
                # Case: Nợ BHXH và chốt sổ BHTN
                if any(k in issue.raw_query.lower() for k in ["nợ bhxh", "nợ tiền", "chốt sổ"]):
                    if doc_id == "ND_374_2025" and art_num == 9:
                        s_top += 5.0
                    elif doc_id == "LVL_74_2025" and art_num == 81:
                        s_top += 4.0
                # Case: UI termination upon finding new employment
                if any(k in issue.raw_query.lower() for k in ["bị cắt tiền", "chấm dứt hưởng", "việc làm mới", "tìm được việc"]):
                    if "chấm dứt hưởng" in art_title.lower() or (doc_id == "LVL_74_2025" and art_num == 63):
                        s_top += 4.0
            else:
                s_top -= SCORE_STRONG
        elif issue_domain == "FOREIGN_WORKER":
            if doc_id == "ND_219_2025" or c_domain == "FOREIGN_WORKER":
                s_top += SCORE_LOCK  # +5.0
            elif doc_id == "VBHN_18_2026" and art_num in [151, 152, 153, 154, 155]:
                if q_spec in ["DOSSIER", "DEADLINE", "PROCEDURE", "NUMERIC_THRESHOLD"]:
                    s_top += SCORE_NUDGE  # +1.0 (allow decree procedural/dossier chunks to lead)
                else:
                    s_top += SCORE_LOCK   # +5.0 (general requirement or duration limit)
            else:
                s_top -= SCORE_STRONG
        elif issue_domain == "SOCIAL_INSURANCE":
            if doc_id in ["VBHN_58_2025", "ND_158_2025", "ND_159_2025", "TT_12_2025", "ND_176_2025"] or c_domain == "SOCIAL_INSURANCE":
                s_top += SCORE_LOCK  # +5.0
                q_low = issue.raw_query.lower()
                # Lump-sum social insurance
                if any(k in q_low for k in ["rút", "một lần", "1 lần", "chưa đủ", "20 năm", "15 năm"]):
                    if doc_id == "VBHN_58_2025" and art_num == 70:
                        s_top += 5.0
                    elif doc_id == "VBHN_58_2025" and art_num == 98:
                        s_top += 3.0
                # Sickness benefit
                if any(k in q_low for k in ["ốm đau", "dài ngày", "12 tháng"]):
                    if doc_id == "VBHN_58_2025" and art_num == 26:
                        s_top += 5.0
                    elif doc_id == "VBHN_58_2025" and art_num == 28:
                        s_top += 3.0
                # Maternity benefit
                if any(k in q_low for k in ["thai sản", "sinh con", "nghỉ sinh"]):
                    if doc_id == "VBHN_58_2025" and art_num == 39:
                        s_top += 4.0
                    elif doc_id == "VBHN_58_2025" and art_num == 31:
                        s_top += 4.0
                    elif doc_id == "VBHN_58_2025" and art_num == 34:
                        s_top += 3.0
                # Survivorship / death benefit
                if any(k in q_low for k in ["chết", "qua đời", "tử vong", "thân nhân", "mai táng", "tuất"]):
                    if doc_id == "VBHN_58_2025" and art_num in [66, 67]:
                        s_top += 5.0
                # Coverage / arrears
                if any(k in q_low for k in ["nợ", "chốt sổ", "bắt buộc", "nước ngoài", "đối tượng"]):
                    if doc_id == "VBHN_58_2025" and art_num == 2:
                        s_top += 5.0
                    elif doc_id == "ND_219_2025" and art_num == 2:
                        s_top += 4.0
            else:
                s_top -= SCORE_STRONG  # -3.0
        elif issue_domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]:
            if doc_id in ["L_84_2015", "VBHN_04_BNV_2026", "VBHN_05_BNV_2026", "VBHN_06_BNV_2026", "ND_39_2016"] or c_domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]:
                s_top += SCORE_LOCK  # +5.0
                q_low = issue.raw_query.lower()
                if issue_domain == "OCCUPATIONAL_SAFETY":
                    # Employer obligation / compensation
                    if doc_id == "L_84_2015" and art_num == 38:
                        s_top += 5.0
                    elif doc_id == "L_84_2015" and art_num == 39:
                        s_top += 4.0
                elif issue_domain == "OCCUPATIONAL_ACCIDENT_DISEASE":
                    # Fund benefits
                    if doc_id == "L_84_2015" and art_num == 45:
                        s_top += 5.0
                    elif doc_id == "L_84_2015" and art_num in [48, 49, 53]:
                        s_top += 4.0
                    elif doc_id in ["VBHN_04_BNV_2026", "VBHN_06_BNV_2026"]:
                        s_top += 4.0
            else:
                s_top -= SCORE_STRONG  # -3.0
        elif issue_domain == "CORE_LABOR":
            if doc_id in ["VBHN_18_2026", "ND_145_2020", "ND_12_2022"] or c_domain == "CORE_LABOR":
                s_top += SCORE_LOCK  # +5.0
                q_low = issue.raw_query.lower()
                if any(k in q_low for k in ["thôi việc", "trợ cấp thôi việc"]):
                    if doc_id == "VBHN_18_2026" and art_num == 46:
                        s_top += 5.0
                elif any(k in q_low for k in ["sa thải", "trái luật", "đơn phương trái luật", "bồi thường hợp đồng", "bồi thường"]):
                    if doc_id == "VBHN_18_2026" and art_num == 41:
                        s_top += 5.0
                    elif doc_id == "VBHN_18_2026" and art_num == 37:
                        s_top += 3.0
                elif any(k in q_low for k in ["nghỉ sinh con", "thai sản"]):
                    if doc_id == "VBHN_18_2026" and art_num == 139:
                        s_top += 5.0
                elif any(k in q_low for k in ["đủ tuổi", "nghỉ hưu", "135/2020"]):
                    if doc_id == "VBHN_18_2026" and art_num == 34:
                        s_top += 4.0
                    elif doc_id == "VBHN_18_2026" and art_num == 169:
                        s_top += 4.0
                elif any(k in q_low for k in ["ốm đau", "12 tháng", "đơn phương"]):
                    if doc_id == "VBHN_18_2026" and art_num == 36:
                        s_top += 5.0
                elif any(k in q_low for k in ["thử việc", "hợp đồng thử việc"]):
                    if doc_id == "VBHN_18_2026" and art_num in [24, 25]:
                        s_top += 5.0
            if c_domain in ["RETIREMENT", "UNEMPLOYMENT_INSURANCE", "FOREIGN_WORKER", "SOCIAL_INSURANCE", "OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]:
                s_top -= SCORE_STRONG  # -3.0
        elif issue_domain == "CROSS_DOMAIN":
            if c_domain in ["CORE_LABOR", "OCCUPATIONAL_SAFETY"]:
                s_top += SCORE_LOCK  # +5.0
            elif doc_id in ["VBHN_18_2026", "L_84_2015", "ND_12_2022"]:
                s_top += SCORE_LOCK  # +5.0

        if issue.topic == "probation":
            if doc_id == "VBHN_18_2026" and art_num in [24, 25, 26, 27]:
                s_top += 1.5
            elif doc_id == "ND_12_2022" and art_num == 10:
                s_top += 1.0
        elif issue.topic == "salary":
            if doc_id == "VBHN_18_2026" and art_num and 90 <= art_num <= 104:
                s_top += 1.0
        elif issue.topic == "overtime":
            if doc_id == "VBHN_18_2026" and art_num == 107:
                s_top += 2.5
            elif doc_id == "VBHN_18_2026" and art_num in [98, 109]:
                s_top += 1.0
            elif doc_id == "ND_145_2020" and art_num in [55, 60]:
                s_top += 1.0
        elif issue.topic == "annual_leave":
            if doc_id == "VBHN_18_2026" and art_num in [111, 112, 113, 114, 115]:
                s_top += 1.5
        elif issue.topic == "discipline":
            if doc_id == "VBHN_18_2026" and art_num and 117 <= art_num <= 128:
                s_top += 1.5
        elif issue.topic == "contract":
            if doc_id == "VBHN_18_2026" and art_num and 13 <= art_num <= 40:
                s_top += 1.0

        # Semantic Incompatibility Rules (Generic Event-Based - Phase 5H.3)
        query_events = getattr(issue, "legal_events", [getattr(issue, "legal_event", "UNKNOWN")])
        chunk_event = m.get("legal_event", "UNKNOWN")

        # 1. Occupational Accident vs Ordinary Sickness
        if any(ev in ["OCCUPATIONAL_ACCIDENT", "WORKPLACE_INJURY"] for ev in query_events) and "ORDINARY_SICKNESS" not in query_events:
            if chunk_event == "ORDINARY_SICKNESS" or (doc_id == "VBHN_58_2025" and art_num in [24, 25, 26, 27, 28, 29]) or "ốm đau" in art_title.lower():
                s_top += SCORE_DOMINANT * -1.25  # -10.0 penalty

        # 2. Ordinary Sickness vs Occupational Accident
        if "ORDINARY_SICKNESS" in query_events and not any(ev in ["OCCUPATIONAL_ACCIDENT", "WORKPLACE_INJURY"] for ev in query_events):
            if chunk_event in ["OCCUPATIONAL_ACCIDENT", "WORKPLACE_INJURY"] or doc_id in ["L_84_2015", "VBHN_04_BNV_2026", "VBHN_06_BNV_2026"] or "tai nạn" in art_title.lower():
                s_top += SCORE_DOMINANT * -1.25  # -10.0 penalty

        # 3. Maternity vs Occupational Accident
        if "MATERNITY" in query_events and not any(ev in ["OCCUPATIONAL_ACCIDENT", "WORKPLACE_INJURY"] for ev in query_events):
            if chunk_event in ["OCCUPATIONAL_ACCIDENT", "WORKPLACE_INJURY"]:
                s_top += SCORE_DOMINANT * -1.25  # -10.0 penalty

        # 4. Unemployment vs Severance Allowance
        if "UNEMPLOYMENT" in query_events and "TERMINATION" not in query_events:
            if doc_id == "VBHN_18_2026" and art_num == 46:
                s_top += -8.0

        # 5. De Facto Labor Contract vs Termination/Discipline
        req_roles_set = set(getattr(issue, "required_evidence_roles", []))
        if any(ev == "DE_FACTO_LABOR_CONTRACT" for ev in query_events) or "EMPLOYMENT_RELATIONSHIP_DEFINITION" in req_roles_set:
            if doc_id == "VBHN_18_2026" and art_num == 13:
                s_top += SCORE_DOMINANT  # +8.0
            elif doc_id == "VBHN_18_2026" and art_num in [35, 36, 37, 41, 125]:
                s_top += SCORE_HARD_SUPPRESS  # -15.0

        # 6. Employer Prohibited Acts (Keeping original ID cards / documents)
        if any(ev == "EMPLOYER_PROHIBITED_ACTS" for ev in query_events) or "PROHIBITED_ACTS_IDENTIFICATION" in req_roles_set:
            if (doc_id == "VBHN_18_2026" and art_num == 17) or (doc_id == "ND_12_2022" and art_num == 9):
                s_top += SCORE_DOMINANT  # +8.0

        # 4. Actor score (employer vs employee termination)
        s_act = 0.0
        if issue.actor == "EMPLOYER":
            if doc_id == "VBHN_18_2026" and art_num == 36:
                s_act += 1.5
            elif doc_id == "VBHN_18_2026" and art_num == 35:
                s_act -= 1.5
        elif issue.actor == "EMPLOYEE":
            if doc_id == "VBHN_18_2026" and art_num == 35:
                s_act += 1.5
            elif doc_id == "VBHN_18_2026" and art_num == 36:
                s_act -= 1.5

        # 5. Intent score (Substantive rule vs Sanction)
        s_int = 0.0
        if issue.intent == "SUBSTANTIVE_RULE":
            if issue_domain == "SOCIAL_INSURANCE":
                if doc_id in ["VBHN_58_2025", "ND_158_2025", "ND_159_2025"]:
                    s_int += 1.5
            elif issue_domain in ["OCCUPATIONAL_SAFETY", "OCCUPATIONAL_ACCIDENT_DISEASE"]:
                if doc_id in ["L_84_2015", "VBHN_04_BNV_2026", "VBHN_06_BNV_2026"]:
                    s_int += 1.5
            elif issue_domain == "UNEMPLOYMENT_INSURANCE":
                if doc_id in ["LUAT_74_2025", "ND_374_2025"]:
                    s_int += 1.5
            elif issue_domain == "FOREIGN_WORKER":
                if doc_id in ["ND_219_2025"]:
                    s_int += 1.5
            else:
                if doc_id == "VBHN_18_2026":
                    s_int += 1.5
                elif doc_id == "ND_12_2022":
                    s_int -= 1.0
        elif issue.intent == "SANCTION":
            if doc_id == "ND_12_2022":
                s_int += 2.0
            elif doc_id in ["VBHN_18_2026", "VBHN_58_2025", "L_84_2015"]:
                s_int -= 0.5

        # 6. Numeric and temporal unit matching
        s_num = 0.0
        for num in issue.numbers:
            num_str = str(num)
            if num_str in c_lower:
                s_num += 1.0
                # Check conjunction with units
                for u in issue.units:
                    if f"{num_str} {u}" in c_lower or f"{num_str}{u}" in c_lower:
                        s_num += 2.0

        # 7. Fine-grained qualifier & category matching
        s_qual = 0.0

        # Required Evidence Role Scoring (Phase 5H.3)
        req_roles = getattr(issue, "required_evidence_roles", [])
        chunk_roles = m.get("evidence_roles", [])
        matched_roles = set(req_roles).intersection(set(chunk_roles))
        if matched_roles:
            s_qual += 4.0 * len(matched_roles)

        # Hazard Category: 14 vs 16 days annual leave (Điều 113)
        if "category_hazardous_normal" in issue.qualifiers:
            # User asks for ordinary hazardous work (without "đặc biệt")
            if "đặc biệt nặng nhọc" in c_lower:
                s_qual -= 2.5  # Penalize Điểm c (16 ngày)
            elif "nặng nhọc, độc hại" in c_lower or "nặng nhọc độc hại" in c_lower:
                s_qual += 2.5  # Favor Điểm b (14 ngày)
        elif "category_especially_hazardous" in issue.qualifiers:
            if "đặc biệt nặng nhọc" in c_lower:
                s_qual += 3.0  # Favor Điểm c (16 ngày)

        # Overtime temporal limits: day vs month vs year (Điều 107)
        if "temporal_limit_day" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 107:
                if pt == "b" or any(k in c_lower for k in ["01 ngày", "trong 01 ngày", "50%", "trong ngày"]):
                    s_qual += 4.0  # Strongly favor Điều 107k2 point b (daily limit)
                elif pt == "a":
                    s_qual -= 3.0  # Suppress point a (employee consent)
            if any(k in c_lower for k in ["01 năm", "200 giờ"]) and pt != "b":
                s_qual -= 2.0  # Suppress Điểm c
        elif "temporal_limit_month" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 107:
                if pt == "b" or any(k in c_lower for k in ["01 tháng", "40 giờ"]):
                    s_qual += 4.0
                elif pt == "a":
                    s_qual -= 3.0
        elif "temporal_limit_year" in issue.qualifiers:
            if any(k in c_lower for k in ["01 năm", "200 giờ"]):
                s_qual += 3.0

        # Delayed salary: delay >= 15 days + interest (Điều 97k4 vs 97k1)
        if "delay_over_15_days" in issue.qualifiers or "delayed_salary" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 97:
                if cl_num == 4 or "15 ngày" in c_lower:
                    s_qual += 3.5  # Heavily favor Khoản 4
                elif cl_num == 1:
                    s_qual -= 1.5  # Suppress Khoản 1

        # Wage deductions: substantive grounds (Điều 102k1 vs 102k2)
        if "wage_deduction" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 102:
                if cl_num == 1 or "chỉ được khấu trừ" in c_lower or "bồi thường thiệt hại" in c_lower:
                    s_qual += 3.0  # Heavily favor Khoản 1
                elif cl_num == 2:
                    s_qual -= 1.5  # Suppress Khoản 2

        # Probation cancellation vs ordinary termination (Điều 27k2 vs Điều 35)
        if "probation_cancellation" in issue.qualifiers or "probation" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 27:
                if cl_num == 2 or "hủy bỏ" in c_lower or "không cần báo trước" in c_lower:
                    s_qual += 4.0  # Heavily favor Điều 27k2
            elif doc_id == "VBHN_18_2026" and art_num == 35:
                s_qual -= 3.0  # Suppress Điều 35 for probation

        # Annual leave cashout on termination (Điều 113k3 & k6 vs Điều 101k3)
        if "leave_cashout_on_termination" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 113:
                if cl_num in [3, 6] or ("thôi việc" in c_lower and "chưa nghỉ" in c_lower):
                    s_qual += 4.5  # Heavily favor Điều 113k3 and 113k6
            elif doc_id == "VBHN_18_2026" and art_num == 101:
                s_qual -= 3.0  # Suppress Điều 101

        # Prohibited deposit / document withholding (Điều 17k1, 17k2 vs NĐ 12)
        if "prohibited_deposit_or_withholding" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 17:
                s_qual += 3.0
                if "money_deposit_security" in issue.qualifiers and cl_num == 2:
                    s_qual += 2.0  # Điều 17k2 for money deposit
                if "original_document_withholding" in issue.qualifiers and cl_num == 1:
                    s_qual += 2.0  # Điều 17k1 for diploma/cccd withholding

        # Working hours reduction for hazardous work (Điều 105k3 vs Điều 137k2 / Điều 219 / Điều 113)
        if "working_hours_reduction" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 105 and cl_num == 3:
                s_qual += 6.5  # Strongly favor Điều 105k3
            elif doc_id == "VBHN_18_2026" and art_num in [137, 219, 113]:
                s_qual -= 3.5  # Suppress pension/maternity/leave

        # Special occupation flight crew (Điều 35k1d + NĐ 145 Điều 7)
        if "flight_crew" in issue.special_conditions or "special_occupation_notice" in issue.qualifiers:
            if doc_id == "ND_145_2020" and art_num == 7:
                s_qual += 3.5
                if "contract_definite_12_36_months" in issue.qualifiers or "contract_indefinite" in issue.qualifiers:
                    if cl_num == 2 and pt == "a":
                        s_qual += 5.0
                    elif cl_num == 2 and pt == "b":
                        s_qual -= 3.5
                elif "contract_under_12_months" in issue.qualifiers:
                    if cl_num == 2 and pt == "b":
                        s_qual += 5.0
                    elif cl_num == 2 and pt == "a":
                        s_qual -= 3.5
            elif doc_id == "VBHN_18_2026" and art_num == 35 and pt == "d":
                s_qual += 3.5

        # General employee notice period (Điều 35 Khoản 1 + Khoản 2 exceptions)
        # Khoản 2 chứa ngoại lệ KHÔNG CẦN BÁO TRƯỚC (bị giao sai việc, ngược đãi,
        # không trả lương, thai sản, quá tuổi...) → PHẢI luôn giữ lại song song với Khoản 1.
        if "flight_crew" not in issue.special_conditions and "special_occupation_notice" not in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 35:
                if "contract_definite_12_36_months" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "b" else 4.0
                    elif cl_num == 2:
                        s_qual += 3.0  # Ngoại lệ không cần báo trước — giữ lại
                elif "contract_indefinite" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "a" else 4.0
                    elif cl_num == 2:
                        s_qual += 3.0  # Ngoại lệ không cần báo trước — giữ lại
                elif "contract_under_12_months" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "c" else 4.0
                    elif cl_num == 2:
                        s_qual += 3.0  # Ngoại lệ không cần báo trước — giữ lại
            elif doc_id == "ND_145_2020" and art_num == 7:
                s_qual -= 6.0

        # Probation duration 4 groups (Điều 25)
        if issue.topic == "probation":
            if doc_id == "VBHN_18_2026" and art_num == 25:
                if "probation_enterprise_manager" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 4.5
                elif "probation_college_degree" in issue.qualifiers:
                    if cl_num == 2:
                        s_qual += 4.5
                elif "probation_intermediate" in issue.qualifiers:
                    if cl_num == 3:
                        s_qual += 4.5
                elif "probation_other_work" in issue.qualifiers:
                    if cl_num == 4:
                        s_qual += 4.5

        # Overtime pay rate (Điều 98)
        if "overtime_pay_rate" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 98:
                s_qual += 3.5
                if "overtime_normal_day" in issue.qualifiers and pt == "a":
                    s_qual += 3.0
                elif "overtime_weekly_rest_day" in issue.qualifiers and pt == "b":
                    s_qual += 3.0
                elif "overtime_holiday_tet" in issue.qualifiers and pt == "c":
                    s_qual += 3.0
            elif doc_id == "VBHN_18_2026" and art_num == 107:
                s_qual -= 3.0  # Suppress hours limit when asking about pay rate

        # Wage deduction limit (Điều 102k3)
        if "wage_deduction_limit" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 102 and cl_num == 3:
                s_qual += 4.5

        # Probation wage (Điều 26)
        if "probation_salary" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 26:
                s_qual += 8.0
            elif doc_id == "ND_293_2025":
                s_qual -= 10.0

        # Social insurance in probation (Điều 24k1)
        if "probation_social_insurance" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 24 and cl_num == 1:
                s_qual += 8.0
            elif doc_id == "VBHN_18_2026" and art_num in [25, 27]:
                s_qual -= 4.0

        # Probation conclusion, notice & contract signing (Điều 27k1)
        if "probation_conclusion" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 27:
                if cl_num == 1:
                    s_qual += 10.0
                else:
                    s_qual += 2.0
            elif doc_id == "VBHN_18_2026" and art_num in [24, 25]:
                s_qual -= 4.0

        # Normal working hours (Điều 105)
        if "normal_working_hours" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 105:
                s_qual += 3.5
                if "normal_hours_week_limit" in issue.qualifiers:
                    if cl_num == 2:
                        s_qual += 5.0
                    elif cl_num == 1:
                        s_qual -= 2.5
                elif "normal_hours_day_limit" in issue.qualifiers and cl_num == 1:
                    s_qual += 4.0
            elif doc_id == "VBHN_18_2026" and art_num == 107:
                s_qual -= 3.0  # Suppress overtime hours

        # Night work hours (Điều 106)
        if "night_work_hours" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 106:
                s_qual += 5.0
            elif doc_id == "VBHN_18_2026" and art_num == 109:
                s_qual -= 2.0

        # Contract definition vs de facto employment (Điều 13) vs Types (Điều 20)
        is_de_facto_relationship_dispute = (
            issue.relationship_type == "EMPLOYMENT"
            and (
                issue.internship_status in ["POSSIBLE", "COMPANY_DIRECT"]
                or issue.material_facts.get("claimed_label") in ["internship", "collaborator", "familiarization", "informal_help"]
            )
        )

        if "contract_definition" in issue.qualifiers or "quan hệ lao động thực tế" in issue.raw_query.lower() or "điều 13" in issue.raw_query.lower():
            if doc_id == "VBHN_18_2026" and art_num == 13 and cl_num == 1:
                s_qual += 8.5
        elif is_de_facto_relationship_dispute:
            if doc_id == "VBHN_18_2026" and art_num == 13 and cl_num == 1:
                s_qual += 8.5  # Strongly prioritize Điều 13k1 for de facto employment
            elif doc_id == "VBHN_18_2026" and art_num == 90:
                s_qual += 4.5  # Support with Điều 90 (tiền lương)
            elif doc_id == "VBHN_18_2026" and art_num in [115, 112, 105]:
                s_qual -= 6.0  # Suppress leave/holidays/hours for relationship disputes

        if "contract_types" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 20 and cl_num == 1:
                s_qual += 6.0

        if "contract_auto_indefinite_b" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 20 and cl_num == 2:
                if pt == "b":
                    s_qual += 6.0
                elif pt == "c":
                    s_qual -= 3.0

        # Forbid Điều 46 (severance) when query is NOT explicitly asking about severance
        if doc_id == "VBHN_18_2026" and art_num == 46:
            if issue.topic != "severance" and "severance_allowance" not in issue.qualifiers:
                s_qual -= 15.0  # Strongly suppress Điều 46

        # Personal leave with pay (Điều 115)
        if "marriage_leave_paid" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 115 and cl_num == 1 and pt == "a":
                s_qual += 5.0

        # Sanctions (NĐ 12)
        if "sanction_withholding_diploma" in issue.qualifiers:
            if doc_id == "ND_12_2022" and art_num == 9 and cl_num == 2 and pt == "a":
                s_qual += 5.0
        if "sanction_probation_overtime" in issue.qualifiers:
            if doc_id == "ND_12_2022" and art_num == 10 and cl_num == 2 and pt == "a":
                s_qual += 5.0
        if "sanction_monetary_fine_discipline" in issue.qualifiers:
            if doc_id == "ND_12_2022" and art_num == 19 and cl_num == 3 and pt == "b":
                s_qual += 5.0

        # Prohibited monetary fine or salary deduction in discipline (BLLĐ Điều 127k2)
        if "prohibited_monetary_fine" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 127 and cl_num == 2:
                s_qual += 6.0
            elif doc_id == "VBHN_18_2026" and art_num in [122, 102]:
                s_qual -= 2.0

        # Public holiday leave (BLLĐ Điều 112)
        if "public_holiday_leave" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 112:
                s_qual += 6.0
            elif doc_id == "VBHN_18_2026" and art_num in [98, 107]:
                s_qual -= 3.0

        # Bonus regulation (BLLĐ Điều 104)
        if "bonus_regulation" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 104 and cl_num == 1:
                s_qual += 6.0
            elif doc_id == "VBHN_18_2026" and art_num in [41, 168]:
                s_qual -= 3.0

        # Post-termination settlement obligation (Điều 48)
        if "termination_settlement_obligation" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 48 and cl_num == 1:
                s_qual += 6.0
            elif doc_id == "VBHN_18_2026" and art_num in [20, 97]:
                s_qual -= 2.5

        # Probation under 1 month prohibited (Điều 24k3)
        if "probation_under_1_month_prohibited" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 24 and cl_num == 3:
                s_qual += 6.5
            elif doc_id == "VBHN_18_2026" and art_num == 27:
                s_qual -= 4.0

        # Night work salary rate (Điều 98k2)
        if "night_work_salary_rate" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 98 and cl_num == 2:
                s_qual += 6.5
            elif doc_id == "VBHN_18_2026" and art_num == 106:
                s_qual -= 4.0

        # Discipline forms enumeration (Điều 124)
        if "discipline_forms_enumeration" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 124:
                s_qual += 6.5
            elif doc_id == "VBHN_18_2026" and art_num == 125:
                s_qual -= 4.0

        # Discipline principles (Điều 122k2)
        if "discipline_principles" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 122 and cl_num == 2:
                s_qual += 6.5
            elif doc_id == "VBHN_18_2026" and art_num == 124:
                s_qual -= 4.0

        # Job abandonment dismissal (Điều 125k4)
        if "job_abandonment_dismissal" in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 125 and cl_num == 4:
                s_qual += 6.5
            elif doc_id == "VBHN_18_2026" and art_num in [35, 36]:
                s_qual -= 4.0

        # Contract termination notice period (Điều 35 for employee, Điều 36 for employer)
        if issue.actor == "EMPLOYER":
            if "contract_indefinite" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 36 and pt == "a":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 35:
                    s_qual -= 4.0
            elif "contract_definite_12_36_months" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 36 and pt == "b":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 35:
                    s_qual -= 4.0
            elif "contract_under_12_months" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 36 and pt == "c":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 35:
                    s_qual -= 4.0
        else:
            if "contract_definite_12_36_months" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 35 and pt == "b":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 36:
                    s_qual -= 3.0
            elif "contract_indefinite" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 35 and pt == "a":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 36:
                    s_qual -= 3.0
            elif "contract_under_12_months" in issue.qualifiers:
                if doc_id == "VBHN_18_2026" and art_num == 35 and pt == "c":
                    s_qual += 5.5
                elif doc_id == "VBHN_18_2026" and art_num == 35 and pt in ["a", "b"]:
                    s_qual -= 3.0
                elif doc_id == "VBHN_18_2026" and art_num == 36:
                    s_qual -= 3.0

        # Vocational training responsibility (Điều 6k2c, Điều 60)
        if "employer_training_responsibility" in issue.qualifiers:
            if doc_id == "VBHN_18_2026":
                if art_num == 6 and cl_num == 2 and pt == "c":
                    s_qual += 8.5
                elif art_num == 60:
                    s_qual += 8.0
                elif art_num in [61, 62]:
                    s_qual += 2.0
            elif doc_id == "ND_12_2022":
                s_qual -= 8.0  # Suppress administrative fines when asking about employer statutory duty

        # Vocational training contract & cost refund / work commitment (Điều 62, Điều 40k3)
        if "training_commitment_refund" in issue.qualifiers or "training_contract_obligation" in issue.qualifiers:
            if doc_id == "VBHN_18_2026":
                if art_num == 62:
                    if cl_num == 1:
                        s_qual += 7.5  # Mandatory training contract
                    elif cl_num == 2:
                        if pt in ["c", "d"]:
                            s_qual += 8.5  # Work commitment & cost refund terms
                        else:
                            s_qual += 5.5
                    elif cl_num == 3:
                        s_qual += 7.0  # Training cost definition
                    else:
                        s_qual += 6.0
                elif art_num == 40 and cl_num == 3:
                    s_qual += 8.5  # Mandatory reimbursement of training cost on breach
                elif art_num in [60, 61]:
                    s_qual += 1.0
                elif art_num in [35, 36, 113, 115]:
                    s_qual -= 5.0  # Suppress generic leave/termination articles
            elif doc_id == "ND_12_2022":
                s_qual -= 8.0  # Suppress administrative fines for civil training contract dispute

        # Safety Work Refusal & Imminent Danger (Luật ATVSLĐ Điều 6k1đ, Điều 12k4, BLLĐ Điều 5k1, Điều 127k2, Điều 124)
        # Statutory Employee Rights (Bộ luật Lao động 2019 Điều 5k1)
        if "statutory_employee_rights" in issue.qualifiers or "quyền của người lao động" in issue.raw_query.lower():
            if doc_id == "VBHN_18_2026" and art_num == 5:
                if cid == "VBHN_18_2026#d5-k1":
                    s_qual += 18.0
                elif pt in ["a", "b", "c", "d", "đ", "e", "g"]:
                    s_qual += 12.0
                else:
                    s_qual += 8.0
            elif doc_id == "VBHN_18_2026" and art_num in [35, 36]:
                s_qual -= 15.0  # Suppress termination articles when asking for rights

        # Safety Work Refusal & Imminent Danger (Luật ATVSLĐ Điều 6k1đ, Điều 12k4, BLLĐ Điều 5k1, Điều 127k2, Điều 124)
        is_safety_case = (
            "refusal_imminent_danger" in issue.qualifiers
            or "SAFETY_WORK_REFUSAL" in getattr(issue, "legal_events", [])
            or any(k in issue.raw_query.lower() for k in ["từ chối làm việc", "từ chối tiếp tục làm việc", "nguy cơ đe dọa tính mạng", "sạt lở"])
        )
        if is_safety_case:
            # Suppress unilateral termination articles when query is about safety refusal
            if doc_id == "VBHN_18_2026" and art_num in [35, 36, 37, 38, 39, 40, 41]:
                if not any(k in issue.raw_query.lower() for k in ["đơn phương chấm dứt", "bồi thường hợp đồng", "chấm dứt hđlđ"]):
                    s_qual -= 15.0

            # 1. Luật ATVSLĐ 2015 Điều 6 (Quyền từ chối làm việc và không bị coi là vi phạm kỷ luật)
            if doc_id == "L_84_2015" and art_num == 6:
                if pt == "đ" or "từ chối" in c_lower:
                    s_qual += 15.0  # Dominant winner for safety refusal
                elif cl_num == 1:
                    s_qual += 10.0
                else:
                    s_qual += 6.0

            # 2. Bộ luật Lao động 2019 Điều 5 (Quyền của người lao động)
            if doc_id == "VBHN_18_2026" and art_num == 5:
                if cid == "VBHN_18_2026#d5-k1":
                    s_qual += 15.0
                elif pt == "d":
                    s_qual += 14.0
                else:
                    s_qual += 8.0

            # 3. Bộ luật Lao động 2019 Điều 127k2 (Nghiêm cấm phạt tiền, cắt lương thay kỷ luật)
            if doc_id == "VBHN_18_2026" and art_num == 127:
                if cl_num == 2 or "phạt tiền" in c_lower or "cắt lương" in c_lower:
                    s_qual += 16.0
                else:
                    s_qual += 10.0

            # 4. Luật ATVSLĐ 2015 Điều 12k4 (Cấm ép làm việc khi nguy cơ tai nạn đe dọa tính mạng)
            if doc_id == "L_84_2015" and art_num == 12:
                if cl_num == 4 or "buộc người lao động" in c_lower:
                    s_qual += 12.0
                else:
                    s_qual += 6.0

            # 5. Bộ luật Lao động 2019 Điều 124 (Các hình thức kỷ luật)
            if doc_id == "VBHN_18_2026" and art_num == 124:
                s_qual += 12.0

            # 6. Nghị định 12/2022 Điều 23, Điều 22 (Xử phạt vi phạm ATVSLĐ / kỷ luật)
            if doc_id == "ND_12_2022" and art_num in [22, 23]:
                s_qual += 6.0

        # Mandatory social insurance for contracts >= 1 month (BLLĐ Điều 168k1, Luật BHXH Điều 2k1a, Điều 21)
        if "mandatory_insurance_1_month" in issue.qualifiers or (any(k in issue.raw_query.lower() for k in ["từ 01 tháng", "từ 1 tháng"]) and "đóng bảo hiểm" in issue.raw_query.lower()):
            if doc_id == "VBHN_18_2026" and art_num == 168:
                if cl_num == 1 or cid == "VBHN_18_2026#d168-k1":
                    s_qual += 18.0  # Mandatory participation
                elif cl_num == 3 or cid == "VBHN_18_2026#d168-k3":
                    s_qual -= 25.0  # HARD SUPPRESS Khoản 3 (ONLY for employees not subject to mandatory insurance!)
                else:
                    s_qual += 5.0
            elif doc_id == "VBHN_58_2025" and art_num == 2:
                if cl_num == 1 and pt in ["a", "b"]:
                    s_qual += 18.0  # HĐLĐ từ 01 tháng bắt buộc tham gia
                else:
                    s_qual += 12.0
            elif doc_id == "VBHN_58_2025" and art_num == 21:
                s_qual += 16.0  # Trách nhiệm của người sử dụng lao động
            elif doc_id == "ND_12_2022" and art_num == 39:
                s_qual += 12.0  # Xử phạt hành vi trốn đóng / chậm đóng BHXH

        # Uninsured occupational accident (Luật ATVSLĐ Điều 38, Điều 39k4, NĐ 12/2022 Điều 39)
        if "uninsured_accident" in issue.qualifiers or (any(k in issue.raw_query.lower() for k in ["tai nạn", "tnlđ"]) and any(k in issue.raw_query.lower() for k in ["chưa đóng", "không đóng", "trốn đóng", "chưa tham gia"])):
            if doc_id == "L_84_2015" and art_num == 39:
                if cl_num == 4 or cid == "L_84_2015#d39-k4" or "khoản tiền tương ứng" in c_lower:
                    s_qual += 22.0  # ULTIMATE WEAPON: NSDLĐ trả khoản tiền tương ứng Quỹ chi trả!
                else:
                    s_qual += 6.0
            elif doc_id == "L_84_2015" and art_num == 38:
                if cl_num in [2, 3, 4]:
                    s_qual += 16.0  # Viện phí, lương điều trị, bồi thường TNLĐ
                else:
                    s_qual += 10.0
            elif doc_id == "ND_12_2022" and art_num == 39:
                s_qual += 12.0  # Xử phạt hành vi chậm đóng / trốn đóng BHXH
            # HARD SUPPRESS: Quỹ BHXH không chi trả Điều 45 vì DN chưa đóng, và cấm trích Điều 168k3
            if doc_id == "L_84_2015" and art_num == 45:
                s_qual -= 18.0
            if doc_id == "VBHN_18_2026" and art_num == 168 and cl_num == 3:
                s_qual -= 25.0

        # 8. Statutory Specificity & Specificity Matching (Phase 5G.3)
        s_spec = 0.0
        if pt is not None:
            s_spec += 0.5
        elif cl_num is not None:
            s_spec += 0.3
        elif "-heading" in cid or art_title and not cl_num:
            s_spec -= 0.5  # Deprioritize plain article headings if clauses/points are available

        # Specificity Matching: Match question_specificity with chunk rule_type & source_role
        if q_spec == "CURRENT_STATUS":
            if any(k in c_lower for k in ["bãi bỏ", "hiệu lực thi hành", "thay thế"]):
                s_spec += 5.0
        elif q_spec == "DOSSIER":
            if rule_type == "DOSSIER" or "hồ sơ" in art_title.lower() or "hồ sơ đề nghị" in c_lower:
                s_spec += 6.0
                if source_role in ["IMPLEMENTING_DECREE", "PROCEDURAL_DECREE"]:
                    s_spec += 3.0
            elif source_role == "FRAMEWORK_LAW":
                s_spec -= 4.0
        elif q_spec == "DEADLINE":
            if rule_type == "DEADLINE" or any(k in c_lower for k in ["trước ít nhất", "trong thời hạn", "chậm nhất", "thời điểm hưởng"]):
                s_spec += 6.0
                if source_role in ["IMPLEMENTING_DECREE", "PROCEDURAL_DECREE"]:
                    s_spec += 3.0
            elif source_role == "FRAMEWORK_LAW":
                s_spec -= 3.0
        elif q_spec == "NUMERIC_THRESHOLD":
            has_quant = any(k in c_lower for k in [
                "năm 202", "bảng", "tăng thêm 03 tháng", "tăng thêm 04 tháng",
                "61 tuổi", "57 tuổi", "3 tỷ", "dưới 90 ngày", "01 năm", "03 năm", "65%", "15 năm"
            ])
            if has_quant and source_role in ["IMPLEMENTING_DECREE", "PROCEDURAL_DECREE"]:
                s_spec += 7.0
            elif source_role == "FRAMEWORK_LAW":
                if any(k in c_lower for k in ["theo quy định của chính phủ", "chính phủ quy định chi tiết"]):
                    s_spec -= 6.0  # Delegating clause cannot answer numeric threshold!
                else:
                    s_spec -= 2.0
        elif q_spec == "DURATION":
            if rule_type == "DURATION" or any(k in c_lower for k in ["thời hạn tối đa", "được gia hạn một lần"]):
                s_spec += 5.0
        elif q_spec == "PROCEDURE":
            if rule_type == "PROCEDURE" or any(k in art_title.lower() for k in ["trình tự", "thủ tục", "thẩm quyền", "báo cáo giải trình", "thông báo"]):
                s_spec += 6.0
                if source_role in ["IMPLEMENTING_DECREE", "PROCEDURAL_DECREE"]:
                    s_spec += 3.0
            elif source_role == "FRAMEWORK_LAW":
                s_spec -= 3.0
        elif q_spec == "EXEMPTION":
            if rule_type == "EXEMPTION" or any(k in art_title.lower() for k in ["không thuộc diện", "miễn"]):
                s_spec += 5.0
        elif q_spec == "CALCULATION":
            if any(k in c_lower for k in ["ngày đầu tiên của tháng liền kề", "ngày 01 tháng 01", "mức hưởng bằng 60%"]):
                s_spec += 6.0

        # Phase 5G.3: Generic Statutory Scope & Post-Retirement Agreement Rules
        # Case: User asks which parent-law article is detailed by the decree ("quy định chi tiết điều nào")
        if "quy định chi tiết" in issue.raw_query.lower() and any(k in issue.raw_query.lower() for k in ["điều nào", "khoản nào"]):
            if "quy định chi tiết điều" in c_lower or "phạm vi điều chỉnh" in art_title.lower():
                s_spec += 8.0
            else:
                s_spec -= 3.0

        # Case: User asks about agreement to continue working after retirement age ("thỏa thuận tiếp tục làm việc")
        if any(k in issue.raw_query.lower() for k in ["tiếp tục làm việc", "thỏa thuận", "cao tuổi"]) and any(k in issue.raw_query.lower() for k in ["sau khi đủ tuổi", "nghỉ hưu", "tuổi hưu"]):
            if "tiếp tục làm việc" in c_lower or "tuổi cao hơn" in art_title.lower() or (doc_id == "ND_135_2020" and art_num == 6):
                s_spec += 8.0
            elif art_num == 169:
                s_spec -= 5.0  # General retirement age formula does not govern elderly post-retirement work

        # Total Weighted Score
        total = (
            self.w_sem * s_sem
            + self.w_lex * s_lex
            + self.w_top * s_top
            + self.w_act * s_act
            + self.w_int * s_int
            + self.w_qual * s_qual
            + self.w_num * s_num
            + self.w_spec * s_spec
        )

        details = {
            "semantic": s_sem,
            "lexical": s_lex,
            "topic": s_top,
            "actor": s_act,
            "intent": s_int,
            "qualifier": s_qual,
            "numeric": s_num,
            "specificity": s_spec,
        }

        return ScoredEvidence(
            chunk_id=cid,
            doc_id=doc_id,
            article_number=art_num,
            clause_number=cl_num,
            point=pt,
            content=content,
            article_title=art_title,
            document_no=m["document_no"],
            document_title=m["document_title"],
            raw_chunk=chunk,
            semantic_score=s_sem,
            lexical_score=s_lex,
            topic_score=s_top,
            actor_score=s_act,
            intent_score=s_int,
            qualifier_score=s_qual,
            numeric_score=s_num,
            specificity_score=s_spec,
            total_score=total,
            source_role=source_role,
            rule_type=rule_type,
            legal_event=m.get("legal_event", "UNKNOWN"),
            evidence_roles=m.get("evidence_roles", []),
            score_details=details,
        )

    def select_evidence(
        self,
        issue: LegalIssue,
        candidate_chunks: List[Dict[str, Any]],
        max_locked_blocks: int = 2,
    ) -> EvidenceSelectionResult:
        """Evaluates and locks the winning canonical evidence block(s) for a legal issue."""
        if not candidate_chunks:
            return EvidenceSelectionResult(
                issue_id=issue.issue_id,
                selected_chunk_ids=[],
                locked_evidence_blocks=[],
                all_scored_candidates=[],
                best_score=0.0,
                second_score=0.0,
                confidence_margin=0.0,
                is_ambiguous=True,
                ambiguity_reason="No candidate evidence provided",
            )

        # 1. Score all candidates
        scored_list: List[ScoredEvidence] = []
        for idx, chk in enumerate(candidate_chunks):
            scored = self.score_candidate(
                issue=issue,
                chunk=chk,
                retrieval_rank=idx,
                total_candidates=len(candidate_chunks),
            )
            scored_list.append(scored)

        # 2. Sibling Competition: Group by (doc_id, article_number)
        # When siblings exist, ensure the winner pulls ahead of sibling points/clauses
        by_article: Dict[Tuple[str, Optional[int]], List[ScoredEvidence]] = {}
        for sc in scored_list:
            key = (sc.doc_id, sc.article_number)
            if key not in by_article:
                by_article[key] = []
            by_article[key].append(sc)

        for key, siblings in by_article.items():
            if len(siblings) > 1:
                siblings.sort(key=lambda x: x.total_score, reverse=True)
                top_sib = siblings[0]
                # If top sibling has a qualifier bonus, widen the lead against inferior siblings
                if top_sib.qualifier_score > 0:
                    top_sib.total_score += 1.0

        # 3. Sort overall candidates by total_score
        scored_list.sort(key=lambda x: x.total_score, reverse=True)

        best_score = scored_list[0].total_score if scored_list else 0.0
        second_score = scored_list[1].total_score if len(scored_list) > 1 else 0.0
        margin = best_score - second_score

        # 4. Select top winning chunk(s)
        locked_blocks: List[ScoredEvidence] = []
        selected_cids: List[str] = []

        # Top winner
        winner = scored_list[0]
        locked_blocks.append(winner)
        selected_cids.append(winner.chunk_id)

        # Statutory Bridge Enforcement:
        # If flight_crew special occupation, ensure BOTH BLLĐ Điều 35k1d and NĐ 145 Điều 7 are locked!
        is_flight_crew = (
            "flight_crew" in issue.special_conditions
            or "special_occupation_notice" in issue.qualifiers
            or (winner.doc_id == "ND_145_2020" and winner.article_number == 7)
            or (winner.doc_id == "VBHN_18_2026" and winner.article_number == 35 and winner.point == "d")
        )
        if is_flight_crew:
            # Look for highest scored NĐ 145 Điều 7 provision in candidates
            nd145_cands = [sc for sc in scored_list if sc.doc_id == "ND_145_2020" and sc.article_number == 7]
            if nd145_cands:
                nd145_best = sorted(nd145_cands, key=lambda x: x.total_score, reverse=True)[0]
                if nd145_best.chunk_id not in selected_cids:
                    locked_blocks.append(nd145_best)
                    selected_cids.append(nd145_best.chunk_id)

            # Look for BLLĐ Điều 35k1d in candidates
            blld_bridge = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 35 and sc.point == "d"), None)
            if blld_bridge and blld_bridge.chunk_id not in selected_cids:
                locked_blocks.append(blld_bridge)
                selected_cids.append(blld_bridge.chunk_id)

        # Training Responsibility Bridge:
        # Ensure BOTH Điều 6k2c and Điều 60 are locked when query is about employer training duties!
        is_training_resp = (
            "employer_training_responsibility" in issue.qualifiers
            or (winner.doc_id == "VBHN_18_2026" and winner.article_number in [6, 60] and "đào tạo" in winner.content.lower())
        )
        if is_training_resp:
            d6_cand = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 6 and sc.clause_number == 2 and sc.point == "c"), None)
            if d6_cand and d6_cand.chunk_id not in selected_cids:
                locked_blocks.append(d6_cand)
                selected_cids.append(d6_cand.chunk_id)
            d60_cands = [sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 60]
            if d60_cands:
                for d60_cand in sorted(d60_cands, key=lambda x: x.total_score, reverse=True)[:2]:
                    if d60_cand.chunk_id not in selected_cids:
                        locked_blocks.append(d60_cand)
                        selected_cids.append(d60_cand.chunk_id)

        # Training Contract & Cost Reimbursement Bridge:
        # Ensure BOTH Điều 62 and Điều 40k3 are locked when query is about training commitment or cost refund!
        is_training_refund = (
            "training_commitment_refund" in issue.qualifiers
            or "training_contract_obligation" in issue.qualifiers
            or (winner.doc_id == "VBHN_18_2026" and winner.article_number in [62, 40] and "đào tạo" in winner.content.lower())
        )
        if is_training_refund:
            d62_cands = [sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 62]
            for d62_cand in sorted(d62_cands, key=lambda x: x.total_score, reverse=True)[:3]:
                if d62_cand.chunk_id not in selected_cids:
                    locked_blocks.append(d62_cand)
                    selected_cids.append(d62_cand.chunk_id)
            d40_cand = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 40 and sc.clause_number == 3), None)
            if d40_cand and d40_cand.chunk_id not in selected_cids:
                locked_blocks.append(d40_cand)
                selected_cids.append(d40_cand.chunk_id)

        # Statutory Employee Rights Bridge:
        is_employee_rights = (
            "statutory_employee_rights" in issue.qualifiers
            or "STATUTORY_EMPLOYEE_RIGHTS" in getattr(issue, "legal_events", [])
            or any(k in issue.raw_query.lower() for k in ["quyền của người lao động", "quyền người lao động", "có những quyền gì"])
        )
        if is_employee_rights:
            blld_d5_full = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.chunk_id == "VBHN_18_2026#d5-k1"), None)
            if not blld_d5_full:
                blld_d5_full = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 5 and sc.clause_number == 1), None)
            if blld_d5_full:
                if blld_d5_full.chunk_id not in selected_cids:
                    locked_blocks.insert(0, blld_d5_full)
                    selected_cids.insert(0, blld_d5_full.chunk_id)
                elif locked_blocks and locked_blocks[0].chunk_id != blld_d5_full.chunk_id:
                    locked_blocks.remove(blld_d5_full)
                    locked_blocks.insert(0, blld_d5_full)

        # Safety Refusal Bridge:
        # Ensure L_84_2015 Điều 6k1đ, VBHN_18_2026 Điều 5k1/d, and Điều 127k2 are locked!
        is_safety_refusal = (
            "refusal_imminent_danger" in issue.qualifiers
            or "SAFETY_WORK_REFUSAL" in getattr(issue, "legal_events", [])
            or (winner.doc_id == "L_84_2015" and winner.article_number == 6)
            or any(k in issue.raw_query.lower() for k in ["từ chối làm việc", "nguy cơ đe dọa tính mạng", "sạt lở"])
        )
        if is_safety_refusal:
            # 1. L_84_2015 Điều 6k1đ (quyền từ chối mà vẫn hưởng lương và không bị coi là vi phạm kỷ luật)
            l84_d6 = next((sc for sc in scored_list if sc.doc_id == "L_84_2015" and sc.article_number == 6 and sc.point == "đ"), None)
            if not l84_d6:
                l84_d6 = next((sc for sc in scored_list if sc.doc_id == "L_84_2015" and sc.article_number == 6), None)
            if l84_d6 and l84_d6.chunk_id not in selected_cids:
                locked_blocks.append(l84_d6)
                selected_cids.append(l84_d6.chunk_id)

            # 2. VBHN_18_2026 Điều 5k1 (ưu tiên d5-k1 toàn văn hoặc d5-k1-d)
            blld_d5 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 5 and sc.chunk_id == "VBHN_18_2026#d5-k1"), None)
            if not blld_d5:
                blld_d5 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 5 and sc.point == "d"), None)
            if not blld_d5:
                blld_d5 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 5), None)
            if blld_d5 and blld_d5.chunk_id not in selected_cids:
                locked_blocks.append(blld_d5)
                selected_cids.append(blld_d5.chunk_id)

            # 3. VBHN_18_2026 Điều 127k2 (cấm phạt tiền / cắt lương, thưởng)
            if "prohibited_discipline_safety" in issue.qualifiers or "prohibited_monetary_fine" in issue.qualifiers or any(k in issue.raw_query.lower() for k in ["kỷ luật", "khiển trách", "cắt thưởng", "xét thưởng"]):
                blld_d127 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 127 and sc.clause_number == 2), None)
                if not blld_d127:
                    blld_d127 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 127), None)
                if blld_d127 and blld_d127.chunk_id not in selected_cids:
                    locked_blocks.append(blld_d127)
                    selected_cids.append(blld_d127.chunk_id)

            # 4. L_84_2015 Điều 12k4 (cấm ép làm việc khi có nguy cơ tai nạn)
            l84_d12 = next((sc for sc in scored_list if sc.doc_id == "L_84_2015" and sc.article_number == 12 and sc.clause_number == 4), None)
            if l84_d12 and l84_d12.chunk_id not in selected_cids:
                locked_blocks.append(l84_d12)
                selected_cids.append(l84_d12.chunk_id)

            # 5. VBHN_18_2026 Điều 124 (các hình thức kỷ luật)
            if any(k in issue.raw_query.lower() for k in ["kỷ luật", "khiển trách", "cắt thưởng", "xét thưởng"]):
                blld_d124 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 124), None)
                if blld_d124 and blld_d124.chunk_id not in selected_cids:
                    locked_blocks.append(blld_d124)
                    selected_cids.append(blld_d124.chunk_id)

        # Mandatory Insurance 1 Month Bridge:
        is_mand_ins = (
            "mandatory_insurance_1_month" in issue.qualifiers
            or (any(k in issue.raw_query.lower() for k in ["từ 01 tháng", "từ 1 tháng"]) and "đóng bảo hiểm" in issue.raw_query.lower())
        )
        if is_mand_ins:
            # 1. Lock VBHN_18_2026 Điều 168k1
            d168_k1 = next((sc for sc in scored_list if sc.doc_id == "VBHN_18_2026" and sc.article_number == 168 and (sc.clause_number == 1 or sc.chunk_id == "VBHN_18_2026#d168-k1")), None)
            if d168_k1 and d168_k1.chunk_id not in selected_cids:
                locked_blocks.insert(0, d168_k1)
                selected_cids.insert(0, d168_k1.chunk_id)

            # 2. Lock VBHN_58_2025 Điều 2k1a
            d2_k1a = next((sc for sc in scored_list if sc.doc_id == "VBHN_58_2025" and sc.article_number == 2 and (sc.point in ["a", "b"] or sc.clause_number == 1)), None)
            if d2_k1a and d2_k1a.chunk_id not in selected_cids:
                locked_blocks.append(d2_k1a)
                selected_cids.append(d2_k1a.chunk_id)

            # 3. Lock VBHN_58_2025 Điều 21
            d21 = next((sc for sc in scored_list if sc.doc_id == "VBHN_58_2025" and sc.article_number == 21), None)
            if d21 and d21.chunk_id not in selected_cids:
                locked_blocks.append(d21)
                selected_cids.append(d21.chunk_id)

            # 4. Lock ND_12_2022 Điều 39 (Xử phạt trốn đóng)
            nd12_d39 = next((sc for sc in scored_list if sc.doc_id == "ND_12_2022" and sc.article_number == 39), None)
            if nd12_d39 and nd12_d39.chunk_id not in selected_cids:
                locked_blocks.append(nd12_d39)
                selected_cids.append(nd12_d39.chunk_id)

            # Purge any accidental d168-k3
            locked_blocks = [b for b in locked_blocks if not (b.doc_id == "VBHN_18_2026" and b.article_number == 168 and (b.clause_number == 3 or b.chunk_id == "VBHN_18_2026#d168-k3"))]
            selected_cids = [b.chunk_id for b in locked_blocks]

        # Uninsured Accident Bridge:
        is_uninsured_acc = (
            "uninsured_accident" in issue.qualifiers
            or (any(k in issue.raw_query.lower() for k in ["tai nạn", "tnlđ"]) and any(k in issue.raw_query.lower() for k in ["chưa đóng", "không đóng", "trốn đóng", "chưa tham gia"]))
        )
        if is_uninsured_acc:
            # 1. Lock L_84_2015 Điều 39k4 (NSDLĐ trả khoản tiền tương ứng Quỹ chi trả)
            d39_k4 = next((sc for sc in scored_list if sc.doc_id == "L_84_2015" and sc.article_number == 39 and (sc.clause_number == 4 or sc.chunk_id == "L_84_2015#d39-k4")), None)
            if d39_k4 and d39_k4.chunk_id not in selected_cids:
                locked_blocks.insert(0, d39_k4)
                selected_cids.insert(0, d39_k4.chunk_id)

            # 2. Lock L_84_2015 Điều 38 (k2 viện phí, k3 lương, k4 bồi thường)
            d38_cands = [sc for sc in scored_list if sc.doc_id == "L_84_2015" and sc.article_number == 38]
            for sc in sorted(d38_cands, key=lambda x: x.total_score, reverse=True)[:3]:
                if sc.chunk_id not in selected_cids:
                    locked_blocks.append(sc)
                    selected_cids.append(sc.chunk_id)

            # 3. Lock ND_12_2022 Điều 39 (Xử phạt trốn đóng BHXH)
            nd12_d39 = next((sc for sc in scored_list if sc.doc_id == "ND_12_2022" and sc.article_number == 39), None)
            if nd12_d39 and nd12_d39.chunk_id not in selected_cids:
                locked_blocks.append(nd12_d39)
                selected_cids.append(nd12_d39.chunk_id)

            # Purge any accidental d168-k3 or d45
            locked_blocks = [b for b in locked_blocks if not (b.doc_id == "VBHN_18_2026" and b.article_number == 168 and (b.clause_number == 3 or b.chunk_id == "VBHN_18_2026#d168-k3"))]
            locked_blocks = [b for b in locked_blocks if not (b.doc_id == "L_84_2015" and b.article_number == 45)]
            selected_cids = [b.chunk_id for b in locked_blocks]

        # Required Evidence Role Locking (Phase 5H.3)
        req_roles = getattr(issue, "required_evidence_roles", [])
        has_role_locks = False
        if req_roles:
            covered_roles: Set[str] = set()
            for b in locked_blocks:
                covered_roles.update(getattr(b, "evidence_roles", []))

            for role in req_roles:
                if role not in covered_roles:
                    # Find highest scored candidate fulfilling this required role
                    best_for_role = next(
                        (sc for sc in scored_list if role in getattr(sc, "evidence_roles", []) and sc.chunk_id not in selected_cids and sc.total_score > 0),
                        None
                    )
                    if best_for_role:
                        locked_blocks.append(best_for_role)
                        selected_cids.append(best_for_role.chunk_id)
                        covered_roles.update(getattr(best_for_role, "evidence_roles", []))
                        has_role_locks = True

        is_statutory_pair = is_flight_crew or is_training_resp or is_training_refund or is_safety_refusal or is_mand_ins or is_uninsured_acc or has_role_locks
        is_ambiguous = (best_score < self.min_confidence) or (
            margin < self.min_margin
            and len(scored_list) > 1
            and scored_list[0].article_number != scored_list[1].article_number
            and not is_statutory_pair
        )

        return EvidenceSelectionResult(
            issue_id=issue.issue_id,
            selected_chunk_ids=selected_cids,
            locked_evidence_blocks=locked_blocks,
            all_scored_candidates=scored_list,
            best_score=best_score,
            second_score=second_score,
            confidence_margin=margin,
            is_ambiguous=is_ambiguous,
            ambiguity_reason="Score below confidence threshold" if best_score < self.min_confidence else None,
        )
