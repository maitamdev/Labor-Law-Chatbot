# -*- coding: utf-8 -*-
"""
VietLabor AI - Issue Decomposer
Detects multi-issue compound legal queries and splits them into distinct sub-issues
to enable independent per-issue retrieval and prevent context omission.
"""
from dataclasses import dataclass
import re
import unicodedata
from typing import List, Optional

from rag.query_expander import QueryExpander


@dataclass
class DecomposedIssue:
    issue_id: str          # E.g. "issue_1", "issue_2"
    raw_issue_text: str    # Segment from user query
    retrieval_query: str   # Expanded query for hybrid search


class IssueDecomposer:
    """Decomposes compound questions into distinct legal sub-queries."""

    # Conjunction splitters commonly used in Vietnamese legal questions
    COMPOUND_SPLITTERS = [
        re.compile(r"\s+và\s+(?:còn|đồng thời|lại)\s+", re.IGNORECASE),
        re.compile(r"\s+và\s+không\s+", re.IGNORECASE),
        re.compile(r"\s+và\s+có\s+được\s+", re.IGNORECASE),
        re.compile(r"\s*,\s*đồng thời\s+", re.IGNORECASE),
        re.compile(r"\s+vừa\s+(.+?)\s+vừa\s+", re.IGNORECASE),
    ]

    def __init__(self, query_expander: Optional[QueryExpander] = None):
        self.expander = query_expander or QueryExpander()

    def decompose(self, query: str) -> List[DecomposedIssue]:
        """Decomposes a query into one or more focused legal issues."""
        if not query or not isinstance(query, str):
            return []

        norm_q = unicodedata.normalize("NFC", query).strip()
        sub_texts: List[str] = []

        # 0. Check for Scenario + Questions marker: "câu hỏi:" or "hỏi:"
        m_marker = re.search(r"(?:câu hỏi|hỏi)\s*:\s*", norm_q, re.IGNORECASE)
        if m_marker:
            scenario = norm_q[:m_marker.start()].strip()
            q_part = norm_q[m_marker.end():].strip()
            
            raw_qs = []
            parts = re.split(r"(?:\?+|\n+|\b\d+[\.\)]\s*)", q_part)
            for p in parts:
                p_clean = p.strip().rstrip("?.,!")
                if len(p_clean) < 5:
                    continue
                # Split compound 'và' if joining distinct actions
                sub_splits = re.split(r"\s+và\s+(?=(?:kéo dài|không đóng|không trả|giữ bằng|sa thải|xử phạt))", p_clean, flags=re.IGNORECASE)
                for s in sub_splits:
                    s_clean = s.strip()
                    if len(s_clean) >= 5:
                        raw_qs.append(s_clean)
                        
            if len(raw_qs) >= 2:
                results = []
                for idx, q_text in enumerate(raw_qs, start=1):
                    enriched = self._enrich_with_scenario(q_text, scenario)
                    expanded = self.expander.expand(enriched)
                    results.append(
                        DecomposedIssue(
                            issue_id=f"issue_{idx}",
                            raw_issue_text=q_text,
                            retrieval_query=expanded,
                        )
                    )
                return results

        # Check for specific compound patterns
        # 1. "vừa ... vừa ..."
        m_vua = re.search(r"vừa\s+(.+?)\s+vừa\s+(.+)", norm_q, re.IGNORECASE)
        if m_vua:
            sub_texts = [m_vua.group(1).strip(), m_vua.group(2).strip()]
        else:
            # 2. Check other conjunction splitters
            for splitter in self.COMPOUND_SPLITTERS:
                parts = splitter.split(norm_q)
                if len(parts) >= 2:
                    # Filter and clean parts
                    cleaned_parts = [p.strip() for p in parts if len(p.strip()) > 10]
                    if len(cleaned_parts) >= 2:
                        sub_texts = cleaned_parts
                        break

            # 3. Specific compound query detection if delimiter is simple "và" with 2 verbs
            if not sub_texts and " và " in norm_q.lower():
                # E.g.: "Lao động nữ mang thai tháng thứ 7 có được yêu cầu làm thêm giờ ban đêm không và có được sa thải không?"
                parts = norm_q.split(" và ")
                if len(parts) == 2 and any(k in parts[1].lower() for k in ["có được", "không trả", "không đóng", "giữ bằng", "đóng tiền", "sa thải"]):
                    sub_texts = [parts[0].strip(), parts[1].strip()]

        # Fallback: single issue
        if not sub_texts:
            return [
                DecomposedIssue(
                    issue_id="issue_1",
                    raw_issue_text=norm_q,
                    retrieval_query=self.expander.expand(norm_q),
                )
            ]

        # Process each decomposed sub-query
        results: List[DecomposedIssue] = []

        # Check for prominent subject in first issue to inherit if second issue is elliptical
        subject_keywords = ["lao động nữ mang thai", "thành viên tổ lái", "người sử dụng lao động", "công ty"]
        inherited_subject = ""
        first_text_lower = sub_texts[0].lower()
        for kw in subject_keywords:
            if kw in first_text_lower:
                inherited_subject = kw
                break

        for idx, sub_text in enumerate(sub_texts, start=1):
            # Clean trailing question markers e.g. "thì sao?", "có đúng không?"
            clean_text = re.sub(r",?\s*(?:thì sao|thì vi phạm quy định nào|thì sai những gì|có đúng không|có được không)\??$", "", sub_text, flags=re.IGNORECASE).strip()
            if not clean_text:
                clean_text = sub_text

            # If subsequent issue is very short or missing subject, prepend inherited subject
            if idx > 1 and inherited_subject and inherited_subject not in clean_text.lower():
                clean_text = f"{inherited_subject} {clean_text}"

            expanded = self.expander.expand(clean_text)
            results.append(
                DecomposedIssue(
                    issue_id=f"issue_{idx}",
                    raw_issue_text=clean_text,
                    retrieval_query=expanded,
                )
            )

        return results

    def _enrich_with_scenario(self, raw_q: str, scenario: str) -> str:
        """Finds sentences in scenario relevant to the sub-question and joins them."""
        if not scenario:
            return raw_q
        # Split sentences without splitting currency numbers like 10.000.000
        sentences = [p.strip() for p in re.split(r"(?<!\d)\.|\.(?!\d)|\n+|:", scenario) if p.strip()]
        matched: List[str] = []
        q_lower = raw_q.lower()
        for s in sentences:
            s_lower = s.lower()
            if any(k in q_lower for k in ["lương", "tiền lương", "thu nhập"]):
                if re.search(r"\d+\s*(?:đồng|đ|triệu|tr|k)|\d+\s*%|lương|tiền lương", s_lower):
                    matched.append(s)
            elif any(k in q_lower for k in ["bhxh", "bảo hiểm"]):
                if re.search(r"bhxh|bảo hiểm", s_lower):
                    matched.append(s)
            elif any(k in q_lower for k in ["thông báo", "kết quả", "kéo dài", "ký hợp đồng"]):
                if re.search(r"thông báo|kết quả|kéo dài|đạt yêu cầu", s_lower):
                    matched.append(s)

        if any(k in q_lower for k in ["bhxh", "bảo hiểm"]):
            for s in sentences:
                if "thử việc riêng" in s.lower() and s not in matched:
                    matched.insert(0, s)

        if matched:
            return " ".join(matched) + ". " + raw_q
        return raw_q

