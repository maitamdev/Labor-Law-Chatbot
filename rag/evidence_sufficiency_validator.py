# -*- coding: utf-8 -*-
"""
VietLabor AI - Evidence Sufficiency Validator (Phase 5G.3)
Validates whether locked legal evidence chunks actually contain sufficient factual
and statutory details (numbers, deadlines, dossiers, schedules) to legally substantiate
the user's inquiry, or merely establish a general parent-law principle.

Outputs:
    SUPPORTED_AND_SUFFICIENT: Evidence contains both legal basis and required specific detail.
    SUPPORTED_BUT_INCOMPLETE: Evidence is relevant parent-law principle but lacks requested detail.
    UNSUPPORTED: Evidence is missing, irrelevant, or contrary to the claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class LegalClaimSupport:
    """Evaluation of a single material legal claim against its cited evidence."""
    claim: str
    evidence: List[str]
    support_status: str  # "SUPPORTED_AND_SUFFICIENT" | "SUPPORTED_BUT_INCOMPLETE" | "UNSUPPORTED"
    reason: str


@dataclass
class ValidationResult:
    """Overall evidence sufficiency validation result."""
    question: str
    question_specificity: str
    overall_status: str  # "SUPPORTED_AND_SUFFICIENT" | "SUPPORTED_BUT_INCOMPLETE" | "UNSUPPORTED"
    claims: List[LegalClaimSupport]
    cited_chunk_ids: List[str]
    is_legally_sufficient: bool
    missing_details: List[str] = field(default_factory=list)


class EvidenceSufficiencyValidator:
    """Validates whether locked evidence satisfies substantive sufficiency criteria."""

    def validate(
        self,
        question: str,
        question_specificity: str,
        locked_chunks: Sequence[Any],
        answer_text: Optional[str] = None,
        expected_facts: Optional[List[str]] = None,
        required_roles: Optional[List[str]] = None,
    ) -> ValidationResult:
        q_lower = question.lower()
        spec = question_specificity or "GENERAL_PRINCIPLE"

        # Combine text of all locked evidence chunks
        chunk_texts: List[str] = []
        cited_cids: List[str] = []
        has_preamble = False

        for chk in locked_chunks:
            meta = chk.get("metadata", {}) if isinstance(chk, dict) else getattr(chk, "raw_chunk", {})
            cid = chk.get("chunk_id", meta.get("chunk_id", "")) if isinstance(chk, dict) else getattr(chk, "chunk_id", "")
            content = chk.get("content", meta.get("content", "")) if isinstance(chk, dict) else getattr(chk, "content", "")
            art_title = meta.get("article_title", "") if isinstance(chk, dict) else getattr(chk, "article_title", "")

            cited_cids.append(cid)
            chunk_texts.append(f"{art_title}\n{content}")
            if "preamble" in cid.lower():
                has_preamble = True

        combined_evidence = "\n".join(chunk_texts).lower()

        claims: List[LegalClaimSupport] = []
        missing: List[str] = []

        # If no evidence locked, unsupported
        if not locked_chunks or not cited_cids:
            return ValidationResult(
                question=question,
                question_specificity=spec,
                overall_status="UNSUPPORTED",
                claims=[LegalClaimSupport(claim="No evidence locked", evidence=[], support_status="UNSUPPORTED", reason="No legal evidence cited")],
                cited_chunk_ids=[],
                is_legally_sufficient=False,
                missing_details=["All legal evidence missing"],
            )

        # 0. Event Mismatch Check (Phase 5H.3)
        # If question is about occupational accident/workplace injury, but evidence only discusses ordinary sickness
        has_accident = any(k in q_lower for k in ["tai nạn lao động", "tnlđ", "tai nạn khi đang làm", "bị máy kẹp", "ngã giàn giáo", "gãy chân khi đang làm", "gãy tay khi đang làm"])
        only_sickness = bool(chunk_texts) and all(
            any(k in txt.lower() for k in ["ốm đau", "chế độ ốm đau", "thời gian hưởng chế độ ốm đau"])
            and not any(k in txt.lower() for k in ["tai nạn lao động", "tnlđ", "bồi thường", "an toàn, vệ sinh lao động", "tai nạn"])
            for txt in chunk_texts
        )
        if has_accident and only_sickness and not any(k in q_lower for k in ["nghỉ ốm", "chế độ ốm đau", "có phải ốm đau"]):
            claims.append(LegalClaimSupport(
                claim="Legal Event Alignment",
                evidence=cited_cids,
                support_status="EVENT_MISMATCH",
                reason="Query asks about occupational accident, but retrieved evidence only governs ordinary sickness."
            ))
            return ValidationResult(
                question=question,
                question_specificity=spec,
                overall_status="EVENT_MISMATCH",
                claims=claims,
                cited_chunk_ids=cited_cids,
                is_legally_sufficient=False,
                missing_details=["Occupational accident provisions (Luật An toàn, vệ sinh lao động) required; sickness provisions cannot apply."],
            )

        # 0B. Relevance sanity check: If key domain/subject of the question is completely absent from evidence, mark UNSUPPORTED
        synonym_map = {
            "bhxh": ["bhxh", "bảo hiểm xã hội", "bảo hiểm"],
            "bảo hiểm xã hội": ["bảo hiểm xã hội", "bhxh", "bảo hiểm"],
            "bhtn": ["bhtn", "bảo hiểm thất nghiệp", "thất nghiệp"],
            "thất nghiệp": ["thất nghiệp", "bhtn", "bảo hiểm thất nghiệp"],
            "tnlđ": ["tnlđ", "tai nạn lao động", "tai nạn", "thương tật", "bồi thường"],
            "tai nạn": ["tai nạn", "tai nạn lao động", "thương tật", "chấn thương", "bồi thường"],
            "tai nạn lao động": ["tai nạn lao động", "tai nạn", "thương tật", "bồi thường", "an toàn, vệ sinh lao động"],
            "bệnh nghề nghiệp": ["bệnh nghề nghiệp", "suy giảm khả năng lao động", "bệnh tật"],
            "tuổi hưu": ["tuổi hưu", "tuổi nghỉ hưu", "nghỉ hưu", "hưu trí"],
            "nghỉ hưu": ["nghỉ hưu", "hưu trí", "tuổi nghỉ hưu", "lương hưu"],
            "hưu trí xã hội": ["hưu trí xã hội", "trợ cấp hưu trí", "hưu trí"],
            "sa thải": ["sa thải", "kỷ luật lao động", "xử lý kỷ luật"],
            "kỷ luật": ["kỷ luật", "kỷ luật lao động", "sa thải", "khiển trách"],
            "thử việc": ["thử việc", "hợp đồng thử việc"],
            "hết hạn": ["hết hạn", "chấm dứt hợp đồng", "thời hạn hợp đồng"],
            "thai sản": ["thai sản", "sinh con", "nghỉ thai sản"],
            "ốm đau": ["ốm đau", "điều trị", "bệnh tật", "nghỉ việc"],
        }
        core_query_terms = [t for t in [
            "thử việc", "hết hạn", "sa thải", "kỷ luật", "nghỉ hưu", "tuổi hưu",
            "thất nghiệp", "bhtn", "giấy phép", "lao động nước ngoài", "nghỉ lễ",
            "thai sản", "lương", "bảo hiểm xã hội", "bhxh", "ốm đau", "tai nạn",
            "tai nạn lao động", "bệnh nghề nghiệp", "tnlđ", "an toàn", "vệ sinh lao động",
            "bồi thường", "hưu trí xã hội", "rút một lần", "mai táng"
        ] if t in q_lower]
        if core_query_terms:
            has_relevant_term = any(
                any(syn in combined_evidence for syn in synonym_map.get(t, [t]))
                for t in core_query_terms
            )
            if not has_relevant_term:
                claims.append(LegalClaimSupport(
                    claim="Relevant statutory topic",
                    evidence=cited_cids,
                    support_status="UNSUPPORTED",
                    reason=f"Evidence does not discuss the queried topic ({', '.join(core_query_terms)})."
                ))
                return ValidationResult(
                    question=question,
                    question_specificity=spec,
                    overall_status="UNSUPPORTED",
                    claims=claims,
                    cited_chunk_ids=cited_cids,
                    is_legally_sufficient=False,
                    missing_details=[f"Relevant statutory provisions regarding {core_query_terms[0]}"],
                )

        # 1. Preamble check: Preamble cannot substantiate substantive or procedural queries
        if has_preamble and len(cited_cids) == 1 and spec != "CURRENT_STATUS":
            claims.append(LegalClaimSupport(
                claim=f"Preamble citation for {spec} query",
                evidence=cited_cids,
                support_status="SUPPORTED_BUT_INCOMPLETE",
                reason="Document preamble only recites authority to issue, lacking substantive/procedural rules."
            ))
            return ValidationResult(
                question=question,
                question_specificity=spec,
                overall_status="SUPPORTED_BUT_INCOMPLETE",
                claims=claims,
                cited_chunk_ids=cited_cids,
                is_legally_sufficient=False,
                missing_details=["Substantive statutory or decree article required; preamble is insufficient"],
            )

        # 2. Specificity-driven sufficiency checks
        if spec == "NUMERIC_THRESHOLD":
            # Check year 2026 retirement age
            if "năm 2026" in q_lower and any(k in q_lower for k in ["tuổi", "hưu"]):
                has_nam = ("61 tuổi 6 tháng" in combined_evidence or "61 tuổi, 06 tháng" in combined_evidence or ("61" in combined_evidence and "6 tháng" in combined_evidence))
                has_nu = ("57 tuổi" in combined_evidence or "57" in combined_evidence)
                asking_female_only = "nữ" in q_lower and "nam" not in q_lower
                asking_male_only = "nam" in q_lower and "nữ" not in q_lower

                if asking_female_only:
                    is_ok = has_nu
                elif asking_male_only:
                    is_ok = has_nam
                else:
                    is_ok = has_nam and has_nu

                if is_ok:
                    claims.append(LegalClaimSupport(claim="2026 retirement age milestone", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains exact 2026 age schedule"))
                else:
                    claims.append(LegalClaimSupport(claim="2026 retirement age milestone", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Evidence cites general formula (+3m/+4m) but lacks specific 2026 schedule"))
                    missing.append("Year 2026 specific retirement age milestone (Nam: 61 tuổi 6 tháng, Nữ: 57 tuổi)")

            # Check monthly increase rate (+3m male, +4m female)
            elif any(k in q_lower for k in ["mỗi năm tăng", "tăng thêm bao nhiêu tháng"]):
                if "3 tháng" in combined_evidence or "03 tháng" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Retirement monthly progression", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains monthly increase rate"))
                else:
                    claims.append(LegalClaimSupport(claim="Retirement monthly progression", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks specific monthly increase figures"))
                    missing.append("Monthly progression rate (+3 months male, +4 months female)")

            # Check LLC capital threshold (3 billion VND)
            elif any(k in q_lower for k in ["vốn góp tối thiểu", "số vốn góp"]):
                if "3 tỷ" in combined_evidence or "3.000.000.000" in combined_evidence or "ba tỷ" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="LLC foreign capital exemption threshold", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains 3 billion VND threshold"))
                else:
                    claims.append(LegalClaimSupport(claim="LLC foreign capital exemption threshold", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Cites parent law delegating to Government; lacks 3-billion-VND figure"))
                    missing.append("3 billion VND capital contribution threshold")

            # Check under 90 days exemption
            elif any(k in q_lower for k in ["dưới bao nhiêu ngày", "không quá mấy lần"]):
                if "90 ngày" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Short-term expert exemption limit", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains under 90 days rule"))
                else:
                    claims.append(LegalClaimSupport(claim="Short-term expert exemption limit", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks under 90 days per calendar year condition"))
                    missing.append("Under 90 days per calendar year exemption condition")

            # Check technical worker training & experience
            elif any(k in q_lower for k in ["lao động kỹ thuật", "đào tạo và kinh nghiệm"]):
                if ("1 năm" in combined_evidence or "01 năm" in combined_evidence) and ("3 năm" in combined_evidence or "03 năm" in combined_evidence):
                    claims.append(LegalClaimSupport(claim="Technical worker qualification threshold", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains 1-year training and 3-year experience criteria"))
                else:
                    claims.append(LegalClaimSupport(claim="Technical worker qualification threshold", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks quantitative 1-year training + 3-year experience threshold"))
                    missing.append("At least 1-year training + at least 3-year experience criteria")

            # General numeric check
            else:
                claims.append(LegalClaimSupport(claim="General numeric threshold", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Evidence provides quantitative basis"))

        elif spec == "DEADLINE":
            # Check foreign recruitment filing deadline (15 working days)
            if any(k in q_lower for k in ["bắt đầu làm việc", "gửi hồ sơ đề nghị cấp", "trước bao nhiêu ngày"]):
                if "15 ngày" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Work permit application filing deadline", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains 15-working-day advance filing deadline"))
                else:
                    claims.append(LegalClaimSupport(claim="Work permit application filing deadline", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks 15-working-day filing deadline"))
                    missing.append("Advance filing deadline of at least 15 working days")

            # Check UI application deadline (3 months)
            elif any(k in q_lower for k in ["hạn chót", "nộp hồ sơ lấy tiền thất nghiệp", "nộp trễ"]):
                if "3 tháng" in combined_evidence or "03 tháng" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Unemployment benefit filing deadline", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains 3-month filing window from termination"))
                else:
                    claims.append(LegalClaimSupport(claim="Unemployment benefit filing deadline", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks 3-month statutory application deadline"))
                    missing.append("3-month filing window from contract termination date")

            # Check pension commencement date
            elif "thời điểm hưởng lương hưu" in q_lower:
                if any(k in combined_evidence for k in ["tháng liền kề", "ngày đầu tiên"]):
                    claims.append(LegalClaimSupport(claim="Pension commencement date", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains first day of following month rule"))
                else:
                    claims.append(LegalClaimSupport(claim="Pension commencement date", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks first day of following month rule"))
                    missing.append("Commencement date rule (first day of the month following qualifying birth month)")
            else:
                claims.append(LegalClaimSupport(claim="General statutory deadline", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Evidence provides deadline basis"))

        elif spec == "DURATION":
            # Check work permit duration (2 years / gia hạn 1 lần)
            if any(k in q_lower for k in ["giấy phép lao động", "thời hạn tối đa của giấy phép"]):
                if any(k in combined_evidence for k in ["02 năm", "2 năm", "thời hạn của giấy phép lao động tối đa là 02 năm"]):
                    claims.append(LegalClaimSupport(claim="Work permit maximum validity", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains 2-year maximum validity limit"))
                else:
                    claims.append(LegalClaimSupport(claim="Work permit maximum validity", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks 2-year validity limit"))
                    missing.append("Work permit validity duration of up to 2 years")
            # Check probation duration (180 days, 60 days, 30 days)
            elif "thử việc" in q_lower:
                if any(k in combined_evidence for k in ["180 ngày", "60 ngày", "30 ngày", "06 ngày làm việc", "thời gian thử việc"]):
                    claims.append(LegalClaimSupport(claim="Probation maximum duration", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains probation duration thresholds"))
                else:
                    claims.append(LegalClaimSupport(claim="Probation maximum duration", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks probation duration figures"))
                    missing.append("Statutory probation duration limits")
            else:
                claims.append(LegalClaimSupport(claim="General statutory duration", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Evidence provides duration details"))

        elif spec == "DOSSIER":
            if any(k in combined_evidence for k in ["hồ sơ", "văn bản", "giấy chứng nhận", "bản sao"]):
                claims.append(LegalClaimSupport(claim="Dossier requirements", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains dossier component provisions"))
            else:
                claims.append(LegalClaimSupport(claim="Dossier requirements", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks specific dossier document components"))
                missing.append("Specific document list for application dossier")

        elif spec == "PROCEDURE":
            # Executive director criteria
            if "giám đốc điều hành" in q_lower:
                if "giám đốc điều hành" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Executive director standards", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains executive director definition"))
                else:
                    claims.append(LegalClaimSupport(claim="Executive director standards", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks executive director qualification standards"))
                    missing.append("Executive director qualification definition under decree")
            else:
                claims.append(LegalClaimSupport(claim="General statutory procedure", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains procedural sequence"))

        elif spec == "CALCULATION":
            # Missing birth month fallback
            if "chỉ ghi năm sinh" in q_lower or "không có ngày tháng sinh" in q_lower:
                if "ngày 01 tháng 01" in combined_evidence or "01/01" in combined_evidence:
                    claims.append(LegalClaimSupport(claim="Default birth date calculation", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains January 1st default rule"))
                else:
                    claims.append(LegalClaimSupport(claim="Default birth date calculation", evidence=cited_cids, support_status="SUPPORTED_BUT_INCOMPLETE", reason="Lacks January 1st fallback birth date rule"))
                    missing.append("January 1st fallback rule when only birth year is documented")
            else:
                claims.append(LegalClaimSupport(claim="General calculation rule", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Contains calculation basis"))

        else:
            # Default general principle
            claims.append(LegalClaimSupport(claim="Substantive legal principle", evidence=cited_cids, support_status="SUPPORTED_AND_SUFFICIENT", reason="Evidence directly substantiates the query"))

        # Required Roles Evaluation (Phase 5H.3)
        if required_roles:
            all_chunk_roles: Set[str] = set()
            for chk in locked_chunks:
                meta = chk.get("metadata", {}) if isinstance(chk, dict) else getattr(chk, "raw_chunk", {})
                roles = meta.get("evidence_roles") or getattr(chk, "evidence_roles", [])
                all_chunk_roles.update(roles)

            for req_role in required_roles:
                role_satisfied = req_role in all_chunk_roles
                if not role_satisfied:
                    if req_role == "EMPLOYER_INSURANCE_OBLIGATION" and any(k in combined_evidence for k in ["bắt buộc", "tham gia bảo hiểm", "đóng bảo hiểm"]):
                        role_satisfied = True
                    elif req_role == "EMPLOYER_MEDICAL_RESPONSIBILITY" and any(k in combined_evidence for k in ["sơ cứu", "cấp cứu", "chi phí y tế", "viện phí"]):
                        role_satisfied = True
                    elif req_role == "EMPLOYER_WAGE_RESPONSIBILITY" and any(k in combined_evidence for k in ["tiền lương trong thời gian", "trả đủ tiền lương"]):
                        role_satisfied = True
                    elif req_role == "EMPLOYER_ACCIDENT_COMPENSATION" and any(k in combined_evidence for k in ["bồi thường", "suy giảm khả năng lao động", "thương tật"]):
                        role_satisfied = True
                    elif req_role == "UNINSURED_ACCIDENT_SUBSTITUTION" and any(k in combined_evidence for k in ["chưa đóng bảo hiểm", "không đóng bảo hiểm", "tương ứng với chế độ"]):
                        role_satisfied = True

                if role_satisfied:
                    claims.append(LegalClaimSupport(
                        claim=f"Required Evidence Role: {req_role}",
                        evidence=cited_cids,
                        support_status="SUPPORTED_AND_SUFFICIENT",
                        reason=f"Evidence satisfies legal role {req_role}.",
                    ))
                else:
                    claims.append(LegalClaimSupport(
                        claim=f"Required Evidence Role: {req_role}",
                        evidence=cited_cids,
                        support_status="SUPPORTED_BUT_INCOMPLETE",
                        reason=f"Evidence lacks required legal role {req_role}.",
                    ))
                    missing.append(f"Statutory provision satisfying role {req_role}")

        # Determine overall status
        statuses = [c.support_status for c in claims]
        if any(s == "EVENT_MISMATCH" for s in statuses):
            overall = "EVENT_MISMATCH"
            is_sufficient = False
        elif all(s == "SUPPORTED_AND_SUFFICIENT" for s in statuses):
            overall = "SUPPORTED_AND_SUFFICIENT"
            is_sufficient = True
        elif any(s == "SUPPORTED_BUT_INCOMPLETE" for s in statuses):
            overall = "SUPPORTED_BUT_INCOMPLETE"
            is_sufficient = False
        else:
            overall = "UNSUPPORTED"
            is_sufficient = False

        return ValidationResult(
            question=question,
            question_specificity=spec,
            overall_status=overall,
            claims=claims,
            cited_chunk_ids=cited_cids,
            is_legally_sufficient=is_sufficient,
            missing_details=missing,
        )
