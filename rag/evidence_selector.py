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
        return {
            "chunk_id": chunk.get("chunk_id", meta.get("chunk_id", "")),
            "doc_id": meta.get("doc_id", ""),
            "document_no": meta.get("document_no", meta.get("doc_id", "")),
            "document_title": meta.get("doc_title", meta.get("document_title", "")),
            "article_number": int(meta["article_number"]) if meta.get("article_number") is not None and str(meta["article_number"]).isdigit() else None,
            "article_title": meta.get("article_title", ""),
            "clause_number": int(meta["clause_number"]) if meta.get("clause_number") is not None and str(meta["clause_number"]).isdigit() else None,
            "point": str(meta.get("point") or "").strip().lower() or None,
            "content": chunk.get("content", meta.get("content", "")),
            "domain": meta.get("domain", "CORE_LABOR"),
            "status": meta.get("status", "CURRENT"),
        }

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

        # 3. Topic & Domain score (Phase 5G)
        s_top = 0.0
        c_domain = m.get("domain", "CORE_LABOR")
        c_status = m.get("status", "CURRENT")

        # Status-aware guard: suppressed repealed law from overriding current law
        if c_status == "REPEALED":
            s_top += SCORE_HARD_SUPPRESS  # -15.0

        if getattr(issue, "domain", "CORE_LABOR") == "RETIREMENT":
            if doc_id == "ND_135_2020" or c_domain == "RETIREMENT" or (doc_id == "VBHN_18_2026" and art_num == 169):
                s_top += SCORE_LOCK  # +5.0
            else:
                s_top -= SCORE_STRONG
        elif getattr(issue, "domain", "CORE_LABOR") == "UNEMPLOYMENT_INSURANCE":
            if doc_id in ["LVL_74_2025", "ND_374_2025"] or c_domain == "UNEMPLOYMENT_INSURANCE":
                s_top += SCORE_LOCK  # +5.0
            else:
                s_top -= SCORE_STRONG
        elif getattr(issue, "domain", "CORE_LABOR") == "FOREIGN_WORKER":
            if doc_id == "ND_219_2025" or c_domain == "FOREIGN_WORKER" or (doc_id == "VBHN_18_2026" and art_num in [151, 152, 153, 154, 155]):
                s_top += SCORE_LOCK  # +5.0
            else:
                s_top -= SCORE_STRONG
        elif getattr(issue, "domain", "CORE_LABOR") == "CORE_LABOR":
            # Protect CORE queries from collision with extended provisions
            if c_domain in ["RETIREMENT", "UNEMPLOYMENT_INSURANCE", "FOREIGN_WORKER"]:
                s_top -= SCORE_STRONG  # -3.0

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
            if doc_id == "VBHN_18_2026":
                s_int += 1.5
            elif doc_id == "ND_12_2022":
                s_int -= 1.0
        elif issue.intent == "SANCTION":
            if doc_id == "ND_12_2022":
                s_int += 2.0
            elif doc_id == "VBHN_18_2026":
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

        # General employee notice period (Điều 35 Khoản 1)
        if "flight_crew" not in issue.special_conditions and "special_occupation_notice" not in issue.qualifiers:
            if doc_id == "VBHN_18_2026" and art_num == 35:
                if "contract_definite_12_36_months" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "b" else 4.0
                    elif cl_num == 2:
                        s_qual -= 6.0
                elif "contract_indefinite" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "a" else 4.0
                    elif cl_num == 2:
                        s_qual -= 6.0
                elif "contract_under_12_months" in issue.qualifiers:
                    if cl_num == 1:
                        s_qual += 8.0 if pt == "c" else 4.0
                    elif cl_num == 2:
                        s_qual -= 6.0
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

        # 8. Statutory Specificity (point/clause vs generic article heading)
        s_spec = 0.0
        if pt is not None:
            s_spec += 0.5
        elif cl_num is not None:
            s_spec += 0.3
        elif "-heading" in cid or art_title and not cl_num:
            s_spec -= 0.5  # Deprioritize plain article headings if clauses/points are available

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

        is_ambiguous = (best_score < self.min_confidence) or (margin < self.min_margin and len(scored_list) > 1 and scored_list[0].article_number != scored_list[1].article_number)

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
