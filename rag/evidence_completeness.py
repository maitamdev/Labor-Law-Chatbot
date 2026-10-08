# -*- coding: utf-8 -*-
"""Per-issue evidence-completeness gate for labour-law RAG answers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class IssueEvidenceCoverage:
    issue_id: str
    issue_text: str
    status: str
    can_conclude: bool
    evidence_count: int
    chunk_ids: List[str] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)
    covered_roles: List[str] = field(default_factory=list)
    missing_roles: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


@dataclass
class EvidenceCompletenessResult:
    all_issues_grounded: bool
    complete_issue_count: int
    total_issue_count: int
    coverage_ratio: float
    unsupported_issue_ids: List[str] = field(default_factory=list)
    partial_issue_ids: List[str] = field(default_factory=list)
    issues: List[IssueEvidenceCoverage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt_block(self) -> str:
        lines = [
            "[CỔNG KIỂM TRA ĐỘ PHỦ CĂN CỨ - KẾT QUẢ DO BACKEND QUYẾT ĐỊNH]",
            f"- Độ phủ: {self.complete_issue_count}/{self.total_issue_count} vấn đề có căn cứ để kết luận.",
        ]
        for item in self.issues:
            line = f"- {item.issue_id}: {item.status}; chỉ được dùng căn cứ thuộc đúng nhóm của vấn đề này."
            if item.missing_roles:
                line += " Còn thiếu nhóm căn cứ: " + ", ".join(item.missing_roles) + "."
            if not item.can_conclude:
                line += " CẤM đưa ra kết luận khẳng định; phải ghi rõ chưa đủ căn cứ."
            lines.append(line)
        return "\n".join(lines)


class EvidenceCompletenessGate:
    """Checks that every decomposed issue owns usable, non-crossed evidence."""

    _SANCTION_TERMS = ("xử phạt", "mức phạt", "phạt bao nhiêu", "chế tài", "phạt tiền")

    @staticmethod
    def _chunk_meta(chunk: Dict[str, Any]) -> Dict[str, Any]:
        return chunk.get("metadata") or chunk

    def evaluate(
        self,
        issues: List[Any],
        issue_evidence_map: Dict[str, List[Dict[str, Any]]],
        selection_results: Optional[Dict[str, Any]] = None,
    ) -> EvidenceCompletenessResult:
        selection_results = selection_results or {}
        assessments: List[IssueEvidenceCoverage] = []

        normalized_issues = issues or []
        if not normalized_issues:
            normalized_issues = [type("SingleIssue", (), {"issue_id": "issue_1", "raw_issue_text": "Vấn đề pháp lý"})()]

        for index, issue in enumerate(normalized_issues, 1):
            issue_id = str(getattr(issue, "issue_id", None) or f"issue_{index}")
            issue_text = str(getattr(issue, "raw_issue_text", None) or "Vấn đề pháp lý")
            chunks = list(issue_evidence_map.get(issue_id, []))
            chunk_ids = [str(c.get("chunk_id") or self._chunk_meta(c).get("chunk_id") or "") for c in chunks]
            chunk_ids = [cid for cid in chunk_ids if cid]

            required_roles = list(dict.fromkeys(getattr(issue, "required_evidence_roles", None) or []))
            covered: Set[str] = set()
            rule_types: List[str] = []
            statuses: List[str] = []

            sel = selection_results.get(issue_id)
            if sel is not None:
                for scored in getattr(sel, "locked_evidence_blocks", []) or []:
                    if getattr(scored, "chunk_id", "") in chunk_ids:
                        covered.update(getattr(scored, "evidence_roles", []) or [])
                        rule_types.append(str(getattr(scored, "rule_type", "GENERAL_RULE")))

            for chunk in chunks:
                meta = self._chunk_meta(chunk)
                raw_roles = meta.get("evidence_roles") or []
                if isinstance(raw_roles, str):
                    raw_roles = [r.strip() for r in raw_roles.split(",") if r.strip()]
                if not raw_roles:
                    # Canonical bridge chunks inserted by ContextBuilder are
                    # not always present in the scored selection. Reuse the
                    # central classifier so their legal role is still audited.
                    from rag.evidence_selector import EvidenceSelector

                    article_raw = meta.get("article_number")
                    article = int(article_raw) if str(article_raw or "").isdigit() else None
                    clause_raw = meta.get("clause_number")
                    clause = int(clause_raw) if str(clause_raw or "").isdigit() else None
                    raw_roles = EvidenceSelector._classify_chunk_evidence_roles(
                        chunk_id=str(meta.get("chunk_id") or chunk.get("chunk_id") or ""),
                        doc_id=str(meta.get("doc_id") or ""),
                        article_number=article,
                        clause_number=clause,
                        point=str(meta.get("point") or "").lower() or None,
                        article_title=str(meta.get("article_title") or ""),
                        content=str(meta.get("content") or ""),
                    )
                covered.update(raw_roles)
                rule_types.append(str(meta.get("rule_type") or "GENERAL_RULE").upper())
                statuses.append(str(meta.get("status") or "CURRENT").upper())

            reasons: List[str] = []
            missing_roles = [role for role in required_roles if role not in covered]
            current_count = sum(1 for status in statuses if status not in {"REPEALED", "EXPIRED"})
            asks_sanction = any(term in issue_text.lower() for term in self._SANCTION_TERMS)
            has_substantive = any(rt not in {"SANCTION", "PREAMBLE"} for rt in rule_types)

            can_conclude = True
            status = "PASS"
            if not chunks or not chunk_ids:
                can_conclude = False
                status = "FAIL"
                reasons.append("Không có căn cứ nào được khóa cho vấn đề.")
            elif statuses and current_count == 0:
                can_conclude = False
                status = "FAIL"
                reasons.append("Các căn cứ tìm được đều đã hết hiệu lực hoặc bị bãi bỏ.")
            elif not asks_sanction and rule_types and not has_substantive:
                can_conclude = False
                status = "FAIL"
                reasons.append("Chỉ có căn cứ xử phạt, thiếu quy phạm nội dung để xác định quyền/nghĩa vụ.")
            elif missing_roles:
                if has_substantive and current_count > 0:
                    status = "PARTIAL"
                    can_conclude = True
                    reasons.append(f"Đã có quy phạm nội dung cơ bản nhưng còn thiếu vai trò: {', '.join(missing_roles)}.")
                else:
                    status = "INCOMPLETE"
                    can_conclude = False
                    reasons.append("Chưa phủ đủ mọi vai trò căn cứ bắt buộc; không được đưa ra kết luận khẳng định.")

            if sel is not None and getattr(sel, "is_ambiguous", False):
                if status == "PASS":
                    status = "PARTIAL"
                reasons.append(getattr(sel, "ambiguity_reason", None) or "Kết quả chọn căn cứ còn có độ mơ hồ.")

            assessments.append(
                IssueEvidenceCoverage(
                    issue_id=issue_id,
                    issue_text=issue_text,
                    status=status,
                    can_conclude=can_conclude,
                    evidence_count=len(chunk_ids),
                    chunk_ids=chunk_ids,
                    required_roles=required_roles,
                    covered_roles=sorted(covered),
                    missing_roles=missing_roles,
                    reasons=reasons,
                )
            )

        complete_count = sum(1 for item in assessments if item.can_conclude)
        total = len(assessments)
        unsupported = [item.issue_id for item in assessments if not item.can_conclude]
        partial = [item.issue_id for item in assessments if item.status in {"PARTIAL", "INCOMPLETE"}]
        return EvidenceCompletenessResult(
            all_issues_grounded=not unsupported,
            complete_issue_count=complete_count,
            total_issue_count=total,
            coverage_ratio=(complete_count / total) if total else 1.0,
            unsupported_issue_ids=unsupported,
            partial_issue_ids=partial,
            issues=assessments,
        )
