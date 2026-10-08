# -*- coding: utf-8 -*-
"""
VietLabor AI - Issue Decomposer
Detects multi-issue compound legal queries and splits them into distinct sub-issues
to enable independent per-issue retrieval and prevent context omission.
"""
from dataclasses import dataclass, field
import re
import unicodedata
from typing import List, Optional, Tuple

from rag.legal_issue_parser import detect_legal_events, determine_required_evidence_roles
from rag.query_expander import QueryExpander


@dataclass
class DecomposedIssue:
    issue_id: str          # E.g. "issue_1", "issue_2"
    raw_issue_text: str    # Segment from user query
    retrieval_query: str   # Expanded query for hybrid search
    domain: str = "CORE_LABOR"  # "CORE_LABOR" | "RETIREMENT" | "UNEMPLOYMENT_INSURANCE" | "FOREIGN_WORKER" | "OCCUPATIONAL_SAFETY" | "OCCUPATIONAL_ACCIDENT_DISEASE" | "SOCIAL_INSURANCE"
    legal_event: str = "UNKNOWN"
    legal_events: List[str] = field(default_factory=list)
    required_evidence_roles: List[str] = field(default_factory=list)


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

    LEGAL_TOPIC_KEYWORDS = [
        "trách nhiệm", "quyền", "nghĩa vụ", "bảo hiểm", "bhxh", "bhyt", "bhtn",
        "tai nạn", "tnlđ", "chế độ", "hưởng", "bồi thường", "trợ cấp", "chi phí",
        "lương", "thưởng", "kỷ luật", "khiển trách", "sa thải", "đuổi việc",
        "nghỉ việc", "nghỉ từ", "nghỉ ngay", "báo trước", "thôi việc", "chấm dứt", "hợp đồng", "hđlđ", "thử việc",
        "học nghề", "tập nghề", "làm thêm", "tăng ca", "nghỉ phép", "thai sản",
        "ốm đau", "hưu", "nghỉ hưu", "xử phạt", "phạt", "trái luật", "đúng luật",
        "hợp pháp", "khiếu nại", "tố cáo", "từ chối", "an toàn", "vệ sinh", "quy định",
        "pháp luật", "luật", "kiện", "tòa án", "tranh chấp", "giấy tờ", "giữ bản chính"
    ]

    def __init__(self, query_expander: Optional[QueryExpander] = None):
        self.expander = query_expander or QueryExpander()

    @staticmethod
    def _add_contextual_roles(events: List[str], roles: List[str], narrative: str) -> None:
        """Carry only a tightly-scoped cross-issue fact into termination evidence.

        A resignation question can depend on an earlier late-wage fact even when
        that fact is not repeated in the numbered sub-question.
        """
        text = (narrative or "").lower()
        late_wage = any(term in text for term in [
            "chậm trả lương", "chậm lương", "nợ lương", "không trả lương",
            "không trả đủ lương", "trả lương không đúng hạn",
        ])
        if "TERMINATION" in events and late_wage:
            if "EMPLOYEE_NO_NOTICE_EXCEPTION" not in roles:
                roles.append("EMPLOYEE_NO_NOTICE_EXCEPTION")
            if "EMPLOYEE_NOTICE_REQUIREMENT" in roles:
                roles.remove("EMPLOYEE_NOTICE_REQUIREMENT")
        if (
            "DE_FACTO_LABOR_CONTRACT" in events
            and any(term in text for term in ["khởi kiện", "kiện", "tòa án", "tranh chấp"])
            and "INDIVIDUAL_LABOUR_DISPUTE_PROCEDURE" not in roles
        ):
            roles.append("INDIVIDUAL_LABOUR_DISPUTE_PROCEDURE")

        misassigned_work = any(term in text for term in [
            "không được bố trí đúng", "không bố trí đúng", "bố trí công việc không đúng",
            "không đúng công việc", "làm công việc khác", "chuyển làm việc khác",
            "chuyển sang làm việc khác", "chuyển công việc khác", "làm bốc vác",
            "công nhân bốc vác", "không đúng thỏa thuận", "không đúng hợp đồng",
            "không theo đúng hợp đồng", "chuyển người lao động làm công việc khác",
            "bố trí công việc theo đúng hợp đồng", "không bố trí theo đúng hợp đồng",
            "kiến nghị bố trí công việc", "kiến nghị với giám đốc",
        ])
        if misassigned_work:
            if "MISASSIGNED_WORK_TERMINATION" not in events:
                events.append("MISASSIGNED_WORK_TERMINATION")
            if "EMPLOYEE_NO_NOTICE_FOR_MISASSIGNED_WORK" not in roles:
                roles.append("EMPLOYEE_NO_NOTICE_FOR_MISASSIGNED_WORK")
            if "WORK_REASSIGNMENT_LIMITS" not in roles:
                roles.append("WORK_REASSIGNMENT_LIMITS")
            if any(term in text for term in ["bồi thường", "nghỉ việc", "chấm dứt", "tự ý"]):
                if "EMPLOYEE_UNLAWFUL_TERMINATION_LIABILITY" not in roles:
                    roles.append("EMPLOYEE_UNLAWFUL_TERMINATION_LIABILITY")
            if "EMPLOYEE_NOTICE_REQUIREMENT" in roles:
                roles.remove("EMPLOYEE_NOTICE_REQUIREMENT")
            if "UNLAWFUL_TERMINATION_COMPENSATION" in roles:
                roles.remove("UNLAWFUL_TERMINATION_COMPENSATION")

    def decompose(self, query: str) -> List[DecomposedIssue]:
        """Decomposes a query into one or more focused legal issues."""
        if not query or not isinstance(query, str):
            return []

        norm_q = unicodedata.normalize("NFC", query).strip()
        sub_items: List[Tuple[str, Optional[str]]] = []

        # 0A. Explicit Issue Markers: "Vấn đề 1:", "Vấn đề 2:" or "Câu 1:", "Câu 2:"
        van_de_matches = list(re.finditer(r"(?:^|\n|\s+)(?:vấn đề|câu|yêu cầu)\s*(\d+)\s*:\s*", norm_q, re.IGNORECASE))
        if len(van_de_matches) >= 2:
            raw_qs = []
            for i, m in enumerate(van_de_matches):
                start_idx = m.end()
                end_idx = van_de_matches[i + 1].start() if i + 1 < len(van_de_matches) else len(norm_q)
                issue_text = norm_q[start_idx:end_idx].strip()
                if issue_text:
                    raw_qs.append(issue_text)

            if len(raw_qs) >= 2:
                results = []
                for idx, q_text in enumerate(raw_qs, start=1):
                    q_lower = q_text.lower()
                    expanded = self.expander.expand(q_text)
                    q_events = detect_legal_events(q_text)
                    q_roles = determine_required_evidence_roles(q_events, q_lower)
                    self._add_contextual_roles(q_events, q_roles, norm_q)
                    det_domain = self._detect_domain(q_text)

                    # Fine-grained adjustment for specific sub-question intents:
                    # 1. Mandatory insurance for contracts >= 1 month
                    if any(k in q_lower for k in ["đóng bảo hiểm", "tham gia bảo hiểm", "trách nhiệm trong việc đóng bảo hiểm", "trách nhiệm đóng bảo hiểm"]) and any(k in q_lower for k in ["01 tháng", "1 tháng", "từ 1 tháng", "từ 01 tháng"]):
                        det_domain = "CROSS_DOMAIN"
                        expanded = f"{q_text} trách nhiệm đóng bảo hiểm xã hội bắt buộc từ 01 tháng Điều 168 Khoản 1 Bộ luật Lao động 2019 Điều 2 Khoản 1 Điểm a và Điều 21 Luật Bảo hiểm xã hội 58/VBHN Điều 44 Nghị định 283/2026/NĐ-CP"
                        if "INSURANCE_CONTRIBUTION" not in q_events:
                            q_events.append("INSURANCE_CONTRIBUTION")
                        if "EMPLOYER_INSURANCE_OBLIGATION" not in q_roles:
                            q_roles.append("EMPLOYER_INSURANCE_OBLIGATION")

                    # 2. Uninsured occupational accident
                    elif any(k in q_lower for k in ["tai nạn", "tnlđ"]) and any(k in q_lower for k in ["chưa đóng bảo hiểm", "không đóng bảo hiểm", "chưa tham gia", "trốn đóng", "doanh nghiệp chưa đóng", "chưa đóng"]):
                        det_domain = "OCCUPATIONAL_SAFETY"
                        expanded = f"{q_text} trách nhiệm người sử dụng lao động khi người lao động bị tai nạn lao động mà doanh nghiệp chưa đóng bảo hiểm chi phí y tế tiền lương bồi thường trợ cấp Điều 38 Điều 39 Khoản 4 Luật An toàn vệ sinh lao động Điều 44 Nghị định 283/2026/NĐ-CP"
                        if "OCCUPATIONAL_ACCIDENT" not in q_events:
                            q_events.append("OCCUPATIONAL_ACCIDENT")
                        if "UNPAID_INSURANCE" not in q_events:
                            q_events.append("UNPAID_INSURANCE")
                        for r in ["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY", "EMPLOYER_ACCIDENT_COMPENSATION", "UNINSURED_ACCIDENT_SUBSTITUTION"]:
                            if r not in q_roles:
                                q_roles.append(r)

                    # 3. Statutory employee rights
                    elif any(k in q_lower for k in ["quyền của người lao động", "quyền người lao động", "có những quyền gì"]):
                        det_domain = "CORE_LABOR"
                        expanded = "quyền của người lao động theo quy định pháp luật lao động Điều 5 Bộ luật Lao động 2019 các quyền cơ bản"
                        if "STATUTORY_EMPLOYEE_RIGHTS" not in q_events:
                            q_events.append("STATUTORY_EMPLOYEE_RIGHTS")

                    # 4. Safety work refusal
                    elif any(k in q_lower for k in ["từ chối làm việc", "từ chối tiếp tục làm việc"]):
                        det_domain = "CROSS_DOMAIN"
                        expanded = f"{q_text} quyền từ chối làm việc khi có nguy cơ đe dọa trực tiếp đến tính mạng sức khỏe Điểm d Khoản 1 Điều 5 Bộ luật Lao động Điểm đ Khoản 1 Điều 6 Luật An toàn vệ sinh lao động"
                        if "SAFETY_WORK_REFUSAL" not in q_events:
                            q_events.append("SAFETY_WORK_REFUSAL")

                    results.append(
                        DecomposedIssue(
                            issue_id=f"issue_{idx}",
                            raw_issue_text=q_text,
                            retrieval_query=expanded,
                            domain=det_domain,
                            legal_event=q_events[0] if q_events else "UNKNOWN",
                            legal_events=q_events,
                            required_evidence_roles=q_roles,
                        )
                    )
                return results

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
                if p_clean.lower() in ["vì sao", "tại sao", "như thế nào", "ra sao", "đúng không", "sao"]:
                    if raw_qs:
                        raw_qs[-1] = f"{raw_qs[-1]} ({p_clean})"
                    continue
                # Split compound 'và' if joining distinct actions
                sub_splits = re.split(r"\s+và\s+(?=(?:kéo dài|không đóng|không trả|giữ bằng|sa thải|xử phạt))", p_clean, flags=re.IGNORECASE)
                for s in sub_splits:
                    s_clean = s.strip()
                    if len(s_clean) >= 5:
                        # Ignore conversational meta-talk or trailing chatter without any legal keywords
                        if not any(kw in s_clean.lower() for kw in self.LEGAL_TOPIC_KEYWORDS):
                            continue
                        raw_qs.append(s_clean)
                        
            if len(raw_qs) >= 2:
                results = []
                for idx, q_text in enumerate(raw_qs, start=1):
                    enriched = self._enrich_with_scenario(q_text, scenario)
                    expanded = self.expander.expand(enriched)
                    # Classify the legal event from the sub-question itself.
                    # Scenario enrichment is for retrieval facts only; using the
                    # whole narrative here contaminates one issue with another.
                    q_events = detect_legal_events(q_text)
                    q_roles = determine_required_evidence_roles(q_events, q_text.lower())
                    self._add_contextual_roles(q_events, q_roles, scenario)
                    det_domain = self._detect_domain(enriched)

                    # Fine-grained adjustment for specific sub-question intents
                    q_lower = q_text.lower()
                    if any(k in q_lower for k in ["đóng bảo hiểm", "tham gia bảo hiểm", "trách nhiệm trong việc đóng bảo hiểm", "trách nhiệm đóng bảo hiểm"]) and any(k in q_lower for k in ["01 tháng", "1 tháng", "từ 1 tháng", "từ 01 tháng"]):
                        det_domain = "CROSS_DOMAIN"
                        expanded = f"{enriched} trách nhiệm đóng bảo hiểm xã hội bắt buộc từ 01 tháng Điều 168 Khoản 1 Bộ luật Lao động 2019 Điều 2 Khoản 1 Điểm a và Điều 21 Luật Bảo hiểm xã hội 58/VBHN Điều 44 Nghị định 283/2026/NĐ-CP"
                        if "INSURANCE_CONTRIBUTION" not in q_events:
                            q_events.append("INSURANCE_CONTRIBUTION")
                        if "EMPLOYER_INSURANCE_OBLIGATION" not in q_roles:
                            q_roles.append("EMPLOYER_INSURANCE_OBLIGATION")
                    elif any(k in q_lower for k in ["tai nạn", "tnlđ"]) and any(k in q_lower for k in ["chưa đóng bảo hiểm", "không đóng bảo hiểm", "chưa tham gia", "trốn đóng", "doanh nghiệp chưa đóng", "chưa đóng"]):
                        det_domain = "OCCUPATIONAL_SAFETY"
                        expanded = f"{enriched} trách nhiệm người sử dụng lao động khi người lao động bị tai nạn lao động mà doanh nghiệp chưa đóng bảo hiểm chi phí y tế tiền lương bồi thường trợ cấp Điều 38 Điều 39 Khoản 4 Luật An toàn vệ sinh lao động Điều 44 Nghị định 283/2026/NĐ-CP"
                        if "OCCUPATIONAL_ACCIDENT" not in q_events:
                            q_events.append("OCCUPATIONAL_ACCIDENT")
                        if "UNPAID_INSURANCE" not in q_events:
                            q_events.append("UNPAID_INSURANCE")
                        for r in ["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY", "EMPLOYER_ACCIDENT_COMPENSATION", "UNINSURED_ACCIDENT_SUBSTITUTION"]:
                            if r not in q_roles:
                                q_roles.append(r)
                    elif any(k in q_lower for k in ["quyền của người lao động", "quyền người lao động", "có những quyền gì"]):
                        det_domain = "CORE_LABOR"
                        expanded = "quyền của người lao động theo quy định pháp luật lao động Điều 5 Bộ luật Lao động 2019 các quyền cơ bản"
                        if "STATUTORY_EMPLOYEE_RIGHTS" not in q_events:
                            q_events.append("STATUTORY_EMPLOYEE_RIGHTS")
                    elif any(k in q_lower for k in ["kỷ luật", "khiển trách"]) and any(k in q_lower for k in ["thưởng", "cắt thưởng", "xét thưởng", "phạt tiền", "lương"]):
                        det_domain = "CROSS_DOMAIN"
                        expanded = f"{q_text} kỷ luật lao động khiển trách không xét thưởng cắt tiền thưởng phạt tiền cắt lương Điều 124 Điều 127 Bộ luật Lao động Điểm đ Khoản 1 Điều 6 Luật An toàn vệ sinh lao động"
                        if "SAFETY_WORK_REFUSAL" not in q_events:
                            q_events.append("SAFETY_WORK_REFUSAL")
                    elif any(k in q_lower for k in ["từ chối làm việc", "từ chối tiếp tục làm việc"]):
                        det_domain = "CROSS_DOMAIN"
                        expanded = f"{enriched} quyền từ chối làm việc khi có nguy cơ đe dọa trực tiếp đến tính mạng sức khỏe Điểm d Khoản 1 Điều 5 Bộ luật Lao động Điểm đ Khoản 1 Điều 6 Luật An toàn vệ sinh lao động"
                        if "SAFETY_WORK_REFUSAL" not in q_events:
                            q_events.append("SAFETY_WORK_REFUSAL")
                    elif any(k in q_lower for k in ["kỳ hạn trả lương", "thời hạn trả lương", "trả lương định kỳ"]):
                        det_domain = "CORE_LABOR"
                        expanded = f"{enriched} quy định về kỳ hạn trả lương cho người lao động Điều 97 Bộ luật Lao động 2019 trả lương theo giờ ngày tuần tháng sản phẩm khoán bất khả kháng"
                        if "WAGE_PAYMENT_SCHEDULE" not in q_events:
                            q_events.append("WAGE_PAYMENT_SCHEDULE")
                    elif any(k in q_lower for k in ["chậm trả lương", "chậm lương"]) and any(k in q_lower for k in ["xử lý", "như thế nào", "giải quyết", "bồi thường", "chế tài"]):
                        det_domain = "CORE_LABOR"
                        expanded = f"{enriched} xử lý trường hợp người sử dụng lao động chậm trả lương Khoản 4 Điều 97 đền bù tiền lãi Điểm b Khoản 2 Điều 35 đơn phương chấm dứt hợp đồng lao động không cần báo trước Điều 23 Nghị định 283/2026/NĐ-CP"
                        if "DELAYED_WAGE_REMEDY" not in q_events:
                            q_events.append("DELAYED_WAGE_REMEDY")
                    elif any(k in q_lower for k in ["khiếu nại", "tạm ngừng làm việc", "ngừng làm việc"]) and any(k in q_lower for k in ["chậm trả lương", "chậm lương", "lương"]):
                        det_domain = "CORE_LABOR"
                        expanded = f"{enriched} quyền khiếu nại của người lao động khi công ty chậm trả lương Điều 94 Bộ luật Lao động 2019 khiếu nại lần đầu 180 ngày Điều 7 Nghị định 24/2018/NĐ-CP khiếu nại lần hai Điều 27 Chánh Thanh tra Sở khởi kiện Tòa án Điều 10 tự ý tạm ngừng làm việc bỏ việc sa thải Điều 125"
                        if "LABOUR_COMPLAINT" not in q_events:
                            q_events.append("LABOUR_COMPLAINT")
                    elif any(k in q_lower for k in ["thỏa thuận công việc", "tên gọi khác", "không phải hợp đồng lao động", "không phải là hợp đồng", "có phải hợp đồng lao động", "có được coi là hợp đồng"]):
                        det_domain = "CORE_LABOR"
                        expanded = f"{enriched} định nghĩa hợp đồng lao động thỏa thuận bằng tên gọi khác việc làm có trả công tiền lương sự quản lý điều hành giám sát được coi là hợp đồng lao động quyền khởi kiện Điều 13 Khoản 1 Bộ luật Lao động 2019"
                        if "DE_FACTO_LABOR_CONTRACT" not in q_events:
                            q_events.append("DE_FACTO_LABOR_CONTRACT")
                        if "EMPLOYMENT_RELATIONSHIP_DEFINITION" not in q_roles:
                            q_roles.append("EMPLOYMENT_RELATIONSHIP_DEFINITION")
                    elif any(k in q_lower for k in ["giấy tờ tùy thân", "bản chính", "giữ bằng", "giữ cccd", "giữ chứng minh", "đòi giữ"]):
                        det_domain = "CORE_LABOR"
                        expanded = f"{enriched} hành vi người sử dụng lao động không được làm khi giao kết thực hiện hợp đồng lao động giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ Điều 17 Khoản 1 Bộ luật Lao động 2019 Điều 15 Nghị định 283/2026/NĐ-CP"
                        if "EMPLOYER_PROHIBITED_ACTS" not in q_events:
                            q_events.append("EMPLOYER_PROHIBITED_ACTS")
                        if "PROHIBITED_ACTS_IDENTIFICATION" not in q_roles:
                            q_roles.append("PROHIBITED_ACTS_IDENTIFICATION")

                    if len(q_events) > 1 and "UNKNOWN" in q_events:
                        q_events.remove("UNKNOWN")
                    self._add_contextual_roles(q_events, q_roles, f"{scenario} {q_text}")
                    if "MISASSIGNED_WORK_TERMINATION" in q_events:
                        expanded = f"{enriched} quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước khi không được bố trí theo đúng công việc thỏa thuận Điều 35 Khoản 2 Điểm a chuyển người lao động làm công việc khác tạm thời quá 60 ngày Điều 29 Bộ luật Lao động 2019 nghĩa vụ bồi thường Điều 40"

                    results.append(
                        DecomposedIssue(
                            issue_id=f"issue_{idx}",
                            raw_issue_text=q_text,
                            retrieval_query=expanded,
                            domain=det_domain,
                            legal_event=q_events[0] if q_events else "UNKNOWN",
                            legal_events=q_events,
                            required_evidence_roles=q_roles,
                        )
                    )
                return results

        # 0B. Pattern: 3-domain compound query (sa thải trái luật + BHXH 1 lần + BHTN)
        q_lower = norm_q.lower()
        if any(k in q_lower for k in ["sa thải", "bị đuổi", "chấm dứt trái luật", "bồi thường"]) and \
           any(k in q_lower for k in ["bhxh một lần", "rút bhxh", "bhxh 1 lần"]) and \
           any(k in q_lower for k in ["bhtn", "thất nghiệp", "trợ cấp thất nghiệp"]):
            sub_items = [
                ("Công ty sa thải người lao động trái luật, nghĩa vụ bồi thường theo Điều 41 Bộ luật Lao động", "CORE_LABOR"),
                ("Điều kiện rút bảo hiểm xã hội một lần sau khi nghỉ việc theo Điều 70 Luật BHXH", "SOCIAL_INSURANCE"),
                ("Điều kiện hưởng trợ cấp thất nghiệp từ Quỹ BHTN theo Điều 81 Luật Việc làm", "UNEMPLOYMENT_INSURANCE"),
            ]

        # 0C. Pattern: Retirement age + Pension rate
        if not sub_items and any(k in q_lower for k in ["tuổi nghỉ hưu", "tuổi hưu", "135/2020"]) and any(k in q_lower for k in ["lương hưu", "tỷ lệ hưởng", "mức hưởng lương hưu"]):
            sub_items = [
                ("Tuổi nghỉ hưu của người lao động theo Điều 169 Bộ luật Lao động và Nghị định 135/2020", "RETIREMENT"),
                ("Điều kiện và tỷ lệ mức hưởng lương hưu hàng tháng theo Điều 64, 65, 66 Luật BHXH", "SOCIAL_INSURANCE"),
            ]

        # 0D. Pattern: Colloquial informal questions
        if not sub_items:
            # "tai nạn ở cty thì cty trả gì bhxh trả gì"
            if "tai nạn" in q_lower and any(k in q_lower for k in ["cty trả gì", "công ty trả gì", "công ty phải trả"]) and any(k in q_lower for k in ["bhxh trả gì", "quỹ trả gì", "bảo hiểm trả gì"]):
                sub_items = [
                    ("Trách nhiệm bồi thường chi phí y tế và tiền lương của công ty khi người lao động bị tai nạn theo Điều 38, 39 Luật ATVSLĐ", "OCCUPATIONAL_SAFETY"),
                    ("Điều kiện và mức hưởng trợ cấp tai nạn lao động từ Quỹ bảo hiểm tai nạn lao động BHXH theo Điều 45, 48 Luật ATVSLĐ và VBHN 06", "OCCUPATIONAL_ACCIDENT_DISEASE"),
                ]
            # "đang nghỉ thai sản cty đuổi việc thì được bồi thường gì và có được tiền thai sản ko" / "nghỉ sinh con xong đi làm lại bị sa thải"
            elif any(k in q_lower for k in ["mang thai", "thai sản", "sinh con", "nuôi con"]) and any(k in q_lower for k in ["đuổi việc", "cho nghỉ", "sa thải", "bị sa thải", "cho thôi việc"]) and any(k in q_lower for k in ["tiền thai sản", "chế độ thai sản", "trợ cấp thai sản", "hưởng thai sản", "bảo hiểm trả", "quỹ trả"]):
                sub_items = [
                    ("Công ty đơn phương chấm dứt hợp đồng sa thải lao động nữ trong thời gian mang thai nghỉ sinh con nuôi con, nghĩa vụ bảo đảm việc làm và bồi thường theo Điều 37, 41, 137 Bộ luật Lao động", "CORE_LABOR"),
                    ("Quyền lợi điều kiện hưởng chế độ thai sản và quyền khiếu nại bảo vệ quyền lợi của lao động nữ theo Luật Bảo hiểm xã hội", "SOCIAL_INSURANCE"),
                ]
            # "nghỉ hưu nhưng đóng mới 12 năm bhxh thì sao" / "đủ tuổi nghỉ hưu nhưng mới đóng bảo hiểm 10 năm"
            elif any(k in q_lower for k in ["nghỉ hưu", "tuổi hưu", "đủ tuổi"]) and any(k in q_lower for k in ["12 năm", "10 năm", "mới đóng", "chưa đủ 20 năm", "chưa đủ 15 năm", "chưa đủ năm"]) and any(k in q_lower for k in ["bhxh", "bảo hiểm"]):
                sub_items = [
                    ("Công ty giải quyết chấm dứt hợp đồng lao động khi người lao động đủ tuổi nghỉ hưu theo Điều 34, 169 Bộ luật Lao động", "CORE_LABOR"),
                    ("Người lao động đủ tuổi nghỉ hưu nhưng chưa đủ năm đóng BHXH, điều kiện rút BHXH một lần theo Điều 70 Luật BHXH hoặc đóng tự nguyện Điều 98", "SOCIAL_INSURANCE"),
                ]
            # Compound query: asking both about administrative sanction for unpaid insurance AND accident liability
            elif any(k in q_lower for k in ["chưa đóng", "không đóng", "ko đóng", "trốn đóng", "nợ bhxh", "nợ bảo hiểm", "chưa tham gia"]) and any(k in q_lower for k in ["bhxh", "bảo hiểm"]) and any(k in q_lower for k in ["tai nạn", "tnlđ", "máy kẹp", "máy ép", "ngã giàn giáo", "gãy chân", "gãy tay", "đứt tay", "bị thương", "chấn thương", "xe nâng", "máy khâu", "máy may", "đâm vào tay", "kẹp tay", "đâm vào"]) and any(k in q_lower for k in ["xử phạt thế nào", "tội trốn đóng", "bị phạt gì", "truy cứu"]):
                sub_items = [
                    ("Công ty chưa đóng bảo hiểm xã hội bắt buộc cho người lao động, nghĩa vụ tham gia và trách nhiệm của người sử dụng lao động theo Điều 168 Bộ luật Lao động và Điều 2 Luật Bảo hiểm xã hội", "CORE_LABOR"),
                    ("Người lao động bị tai nạn lao động khi công ty chưa đóng bảo hiểm xã hội, trách nhiệm của doanh nghiệp thanh toán chi phí y tế tiền lương và bồi thường thay thế cơ quan bảo hiểm theo Điều 38, 39 Luật An toàn vệ sinh lao động", "OCCUPATIONAL_SAFETY"),
                ]
            # "bị gãy chân trong ca làm việc thì có phải ốm đau ko" / "tai nạn lao động có phải là ốm đau không"
            elif any(k in q_lower for k in ["tai nạn lao động", "gãy chân", "gãy tay", "tnlđ", "tai nạn"]) and any(k in q_lower for k in ["có phải ốm đau", "ốm đau không", "ốm đau ko", "hay là ốm đau"]):
                sub_items = [
                    ("Chế độ và quyền lợi bồi thường của người lao động bị tai nạn lao động chấn thương trong giờ làm việc theo Luật An toàn vệ sinh lao động", "OCCUPATIONAL_SAFETY"),
                    ("Phân biệt chế độ ốm đau của Luật Bảo hiểm xã hội không áp dụng đối với tai nạn lao động theo Luật Bảo hiểm xã hội", "SOCIAL_INSURANCE"),
                ]

            # "deal lương ... chỉ trả ... làm phí ... vi phạm luật nào và hướng xử lý"
            elif any(k in q_lower for k in ["deal lương", "thỏa thuận lương", "chỉ trả", "trả thiếu", "bớt lương", "khấu trừ", "làm phí", "thu phí", "trừ phí", "giữ lương", "không trả đủ", "trả không đủ"]) and any(k in q_lower for k in ["vi phạm luật nào", "hướng xử lý", "làm sao để đòi", "giải quyết thế nào", "xử lý thế nào", "đòi lại tiền", "làm gì"]):
                sub_items = [
                    ("Hành vi công ty thỏa thuận lương nhưng chỉ trả một phần và tự ý trừ phí có vi phạm pháp luật không", "CORE_LABOR"),
                    ("Quyền lợi và hướng xử lý đòi lại tiền lương của người lao động khi bị công ty trả thiếu", "CORE_LABOR"),
                ]

        # Check for specific compound patterns
        # 1. Pattern: "công ty ... hay/hoặc ... bhxh/bảo hiểm" or "trợ cấp thôi việc ... hay trợ cấp thất nghiệp"
        if not sub_items:
            m_hay = re.search(r"^(.*?)(?:,\s*|\s+)(.+?)\s+(?:hay|hay là|hoặc)\s+(.+?)(\?)?$", norm_q, re.IGNORECASE)
            if m_hay and any(k in norm_q.lower() for k in ["công ty", "bhxh", "bhtn", "thôi việc", "thất nghiệp", "trả lương", "bảo hiểm", "bồi thường"]):
                scen = m_hay.group(1).strip()
                part1 = m_hay.group(2).strip()
                part2 = m_hay.group(3).strip()
                clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()
                p2_clean = re.sub(r"[?.!]+$", "", part2).strip().lower()
                is_p2_question_tag = p2_clean in [
                    "không", "ko", "chưa", "sao", "gì", "gì không", "gì ko", "gì khác", "gì khác không", "gì nữa không", "thế nào", "ra sao"
                ] or len(p2_clean) < 8 or not any(kw in p2_clean for kw in self.LEGAL_TOPIC_KEYWORDS)
                if not is_p2_question_tag and len(part1) >= 5 and len(part2) >= 5:
                    if "nghỉ sinh con" in norm_q.lower():
                        sub_items = [
                            ("Nghỉ sinh con thì người sử dụng lao động, công ty có phải trả lương không theo Điều 139 Bộ luật Lao động", "CORE_LABOR"),
                            ("Nghỉ sinh con thì cơ quan bảo hiểm xã hội chi trả trợ cấp thai sản theo Điều 34, 38, 39 Luật BHXH", "SOCIAL_INSURANCE"),
                        ]
                    elif "thôi việc" in norm_q.lower() and "thất nghiệp" in norm_q.lower():
                        sub_items = [
                            ("Nghỉ việc thì điều kiện và trách nhiệm chi trả trợ cấp thôi việc của công ty theo Điều 46 Bộ luật Lao động", "CORE_LABOR"),
                            ("Nghỉ việc thì điều kiện hưởng trợ cấp thất nghiệp từ Quỹ BHTN theo Điều 81 Luật Việc làm", "UNEMPLOYMENT_INSURANCE"),
                        ]
                    elif "trợ cấp thôi việc" in norm_q.lower():
                        sub_items = [
                            ("Trợ cấp thôi việc cho người lao động nghỉ việc do người sử dụng lao động chi trả theo Điều 46 Bộ luật Lao động", "CORE_LABOR"),
                            ("Cơ quan bảo hiểm xã hội có chi trả tiền trợ cấp thôi việc không theo quy định pháp luật BHXH", "CORE_LABOR"),
                        ]
                    else:
                        sub_items = [
                            (f"{clean_scen}, {part1}".strip(", "), None),
                            (f"{clean_scen}, {part2}".strip(", "), None),
                        ]

        # 2. Pattern: "công ty ... và bảo hiểm / BHXH ..."
        if not sub_items:
            m_comp_bh = re.search(r"^(.*?)(?:,\s*|\s+)(công ty|người sử dụng lao động|doanh nghiệp)\s+(.+?)\s+và\s+(bảo hiểm|bhxh|quỹ|cơ quan bhxh)\s+(.+?)(\?)?$", norm_q, re.IGNORECASE)
            if m_comp_bh:
                scen = m_comp_bh.group(1).strip()
                actor1 = m_comp_bh.group(2).strip()
                act1 = m_comp_bh.group(3).strip()
                actor2 = m_comp_bh.group(4).strip()
                act2 = m_comp_bh.group(5).strip()
                clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()

                if "tai nạn" in norm_q.lower():
                    sub_items = [
                        (f"{clean_scen}, trách nhiệm bồi thường chi phí y tế và tiền lương của công ty theo Điều 38, 39 Luật ATVSLĐ", "OCCUPATIONAL_SAFETY"),
                        (f"{clean_scen}, điều kiện và mức hưởng trợ cấp tai nạn lao động từ Quỹ BHXH theo Điều 45, 48 Luật ATVSLĐ và VBHN 06", "OCCUPATIONAL_ACCIDENT_DISEASE"),
                    ]
                elif "nghỉ hưu" in norm_q.lower() or "135/2020" in norm_q.lower():
                    sub_items = [
                        (f"{clean_scen}, công ty giải quyết chấm dứt hợp đồng lao động theo Điều 34, 169 Bộ luật Lao động và Nghị định 135/2020", "CORE_LABOR"),
                        (f"{clean_scen}, cơ quan BHXH giải quyết chế độ rút BHXH một lần hoặc đóng tự nguyện theo Điều 70, 98 Luật BHXH", "SOCIAL_INSURANCE"),
                    ]
                else:
                    sub_items = [
                        (f"{clean_scen}, {actor1} {act1}".strip(", "), None),
                        (f"{clean_scen}, {actor2} {act2}".strip(", "), None),
                    ]

        # 3. Pattern: "... từ công ty và từ BHXH" (ví dụ: qua đời do tai nạn nhận từ công ty và từ BHXH)
        if not sub_items:
            m_tu_cty_bh = re.search(r"^(.*?)\s+từ\s+(công ty|người sử dụng lao động|doanh nghiệp)\s+và\s+từ\s+(bhxh|bảo hiểm xã hội|quỹ|bảo hiểm)(.*)$", norm_q, re.IGNORECASE)
            if m_tu_cty_bh:
                pref = m_tu_cty_bh.group(1).strip()
                if "tai nạn lao động" in norm_q.lower() or "qua đời" in norm_q.lower() or "tử vong" in norm_q.lower():
                    sub_items = [
                        (f"{pref} khoản tiền bồi thường tử vong từ người sử dụng lao động công ty theo Khoản 5 Điều 38 Luật ATVSLĐ ít nhất 30 tháng tiền lương", "OCCUPATIONAL_SAFETY"),
                        (f"{pref} khoản tiền trợ cấp mai táng và trợ cấp tuất từ cơ quan BHXH theo Điều 66, 67 Luật BHXH và trợ cấp một lần khi chết do TNLĐ Điều 53 Luật ATVSLĐ", "SOCIAL_INSURANCE"),
                    ]
                else:
                    sub_items = [
                        (f"{pref} từ công ty".strip(), "CORE_LABOR"),
                        (f"{pref} từ BHXH".strip(), "SOCIAL_INSURANCE"),
                    ]

        # 4. Pattern: "được bồi thường hợp đồng thế nào và chế độ thai sản giải quyết ra sao" / "đơn phương chấm dứt... và chế độ BHXH..."
        if not sub_items:
            m_regimes = re.search(r"^(.*?)(?:,\s*|\s+)(được bồi thường\s+.*?|công ty có quyền đơn phương\s+.*?|công ty giải quyết chấm dứt\s+.*?)\s+và\s+(chế độ thai sản\s+.*?|chế độ bhxh\s+.*?|bhxh giải quyết\s+.*?)(\?)?$", norm_q, re.IGNORECASE)
            if m_regimes:
                scen = m_regimes.group(1).strip()
                clean_scen = re.sub(r"\s+thì$", "", scen, flags=re.IGNORECASE).strip()
                if "mang thai" in norm_q.lower() or "thai sản" in norm_q.lower():
                    sub_items = [
                        (f"{clean_scen}, nghĩa vụ bồi thường của công ty khi chấm dứt hợp đồng trái luật theo Điều 37, 41 Bộ luật Lao động", "CORE_LABOR"),
                        (f"{clean_scen}, điều kiện và mức hưởng chế độ thai sản từ cơ quan BHXH khi đã chấm dứt hợp đồng theo Khoản 4 Điều 31 Luật BHXH", "SOCIAL_INSURANCE"),
                    ]
                elif "ốm đau" in norm_q.lower():
                    sub_items = [
                        (f"{clean_scen}, người sử dụng lao động có quyền đơn phương chấm dứt hợp đồng lao động không theo Điểm b Khoản 1 Điều 36 Bộ luật Lao động", "CORE_LABOR"),
                        (f"{clean_scen}, chế độ trợ cấp ốm đau dài ngày của bảo hiểm xã hội theo Điều 26, 28 Luật BHXH", "SOCIAL_INSURANCE"),
                    ]
                else:
                    r1 = m_regimes.group(2).strip()
                    r2 = m_regimes.group(3).strip()
                    sub_items = [
                        (f"{clean_scen}, {r1}".strip(", "), None),
                        (f"{clean_scen}, {r2}".strip(", "), None),
                    ]

        # 5. Pattern: "tham gia / đóng (BHXH bắt buộc) và (BHTN)"
        if not sub_items:
            m_dong_dong = re.search(r"^(.*?)(?:tham gia|đóng)\s+(bhxh bắt buộc|bảo hiểm xã hội bắt buộc|bhxh)\s+và\s+(bhtn|bảo hiểm thất nghiệp)(.*)$", norm_q, re.IGNORECASE)
            if m_dong_dong:
                pref = m_dong_dong.group(1).strip()
                t1 = m_dong_dong.group(2).strip()
                t2 = m_dong_dong.group(3).strip()
                post = m_dong_dong.group(4).strip()
                if "nước ngoài" in norm_q.lower() or "người nước ngoài" in norm_q.lower():
                    sub_items = [
                        (f"{pref} người lao động nước ngoài có phải đóng tham gia BHXH bắt buộc không theo Điều 2 Luật BHXH và Nghị định 219 {post}".strip(), "SOCIAL_INSURANCE"),
                        (f"{pref} người lao động nước ngoài có phải đóng tham gia bảo hiểm thất nghiệp không theo Điều 59, 75 Luật Việc làm {post}".strip(), "UNEMPLOYMENT_INSURANCE"),
                    ]
                elif "thử việc" in norm_q.lower():
                    sub_items = [
                        (f"thời gian thử việc, hợp đồng thử việc riêng biệt không phải tham gia BHXH bắt buộc theo Điều 24 Bộ luật Lao động và Điều 2 Luật BHXH", "CORE_LABOR"),
                        (f"thời gian thử việc có phải đóng bảo hiểm thất nghiệp theo Điều 59, 75 Luật Việc làm không", "UNEMPLOYMENT_INSURANCE"),
                    ]
                else:
                    sub_items = [
                        (f"{pref} có phải đóng tham gia {t1} không theo quy định Luật BHXH {post}".strip(), "SOCIAL_INSURANCE"),
                        (f"{pref} có phải đóng tham gia {t2} không theo Điều 59, 75 Luật Việc làm {post}".strip(), "UNEMPLOYMENT_INSURANCE"),
                    ]

        # 6. Pattern: "vừa ... vừa ..."
        if not sub_items:
            m_vua = re.search(r"vừa\s+(.+?)\s+vừa\s+(.+)", norm_q, re.IGNORECASE)
            if m_vua:
                p1 = m_vua.group(1).strip()
                p2 = m_vua.group(2).strip()
                if any(k in norm_q.lower() for k in ["thất nghiệp", "bhtn"]) and any(k in norm_q.lower() for k in ["bhxh", "rút"]):
                    sub_items = [
                        ("Điều kiện và thời hạn nộp hồ sơ hưởng trợ cấp thất nghiệp theo Điều 81 Luật Việc làm", "UNEMPLOYMENT_INSURANCE"),
                        ("Điều kiện rút bảo hiểm xã hội một lần theo Điều 70 Luật BHXH", "SOCIAL_INSURANCE"),
                    ]
                else:
                    sub_items = [(p1, None), (p2, None)]

        # 7. Pattern: "nhận BHTN và BHXH một lần"
        if not sub_items:
            m_cross_ins = re.search(r"^(.*?)(?:hưởng|nhận|lấy)\s+(?:cả\s+)?(bhtn|trợ cấp thất nghiệp|bảo hiểm thất nghiệp)\s+và\s+(bhxh một lần|bảo hiểm xã hội một lần|bhxh 1 lần)(.*)$", norm_q, re.IGNORECASE)
            if m_cross_ins:
                pref = m_cross_ins.group(1).strip()
                post = m_cross_ins.group(4).strip()
                sub_items = [
                    (f"{pref} điều kiện và thủ tục hưởng trợ cấp thất nghiệp theo Điều 81 Luật Việc làm {post}".strip(), "UNEMPLOYMENT_INSURANCE"),
                    (f"{pref} điều kiện và thủ tục rút BHXH một lần theo Điều 70 Luật BHXH {post}".strip(), "SOCIAL_INSURANCE"),
                ]

        # 8. Pattern: "sa thải trái luật ... bồi thường của công ty và hưởng trợ cấp thất nghiệp"
        if not sub_items:
            m_sa_thai_bhtn = re.search(r"^(.*?)(tiền bồi thường\s+.*?)\s+và\s+(có được hưởng trợ cấp thất nghiệp\s+.*?)(\?)?$", norm_q, re.IGNORECASE)
            if m_sa_thai_bhtn:
                pref = m_sa_thai_bhtn.group(1).strip()
                t1 = m_sa_thai_bhtn.group(2).strip()
                t2 = m_sa_thai_bhtn.group(3).strip()
                sub_items = [
                    (f"{pref} {t1} theo Điều 41 Bộ luật Lao động", "CORE_LABOR"),
                    (f"{pref} {t2} theo Điều 81 Luật Việc làm", "UNEMPLOYMENT_INSURANCE"),
                ]

        # 9. Pattern: "nợ BHXH 6 tháng ... chốt sổ để hưởng trợ cấp thất nghiệp"
        if not sub_items:
            m_no_bhxh = re.search(r"^(.*?nợ tiền bảo hiểm xã hội.*?)\s+thì\s+(?:người lao động\s+)?có được chốt sổ để hưởng trợ cấp thất nghiệp không(\?)?$", norm_q, re.IGNORECASE)
            if m_no_bhxh:
                scen = m_no_bhxh.group(1).strip()
                sub_items = [
                    (f"{scen}, công ty và cơ quan bảo hiểm xã hội giải quyết chốt sổ bảo hiểm xã hội như thế nào theo Điều 2 Luật BHXH và Nghị định 158", "SOCIAL_INSURANCE"),
                    (f"{scen}, điều kiện nộp hồ sơ hưởng trợ cấp thất nghiệp khi bị nợ BHXH theo Điều 81 Luật Việc làm và Điều 9 Nghị định 374", "UNEMPLOYMENT_INSURANCE"),
                ]

        # 10. Fallback: Conjunction splitters
        if not sub_items:
            for splitter in self.COMPOUND_SPLITTERS:
                parts = splitter.split(norm_q)
                if len(parts) >= 2:
                    cleaned_parts = [p.strip() for p in parts if len(p.strip()) > 10]
                    if len(cleaned_parts) >= 2:
                        sub_items = [(p, None) for p in cleaned_parts]
                        break

        # 11. Fallback: simple "và"
        if not sub_items and " và " in norm_q.lower():
            parts = norm_q.split(" và ")
            if len(parts) == 2 and any(k in parts[1].lower() for k in ["có được", "không trả", "không đóng", "giữ bằng", "đóng tiền", "sa thải", "thất nghiệp", "bhxh", "tai nạn", "bồi thường", "bảo hiểm", "chế độ"]):
                p0_lower = parts[0].lower()
                p0_has_intent = any(k in p0_lower for k in [
                    "có được", "được không", "đúng không", "sai không", "vi phạm", "phạt", "bồi thường", "chế độ", "trách nhiệm", "khiếu nại", "nghỉ việc", "báo trước", "sa thải", "đuổi việc", "thôi việc", "thất nghiệp", "bhxh"
                ]) and not p0_lower.startswith(("tôi làm cho", "tôi làm việc", "tôi đang làm", "em làm cho", "mình làm cho"))
                if p0_has_intent and len(parts[0].strip()) > 10:
                    sub_items = [(parts[0].strip(), None), (parts[1].strip(), None)]

        # Fallback: single issue
        if not sub_items:
            sub_items = [(norm_q, None)]

        # Process each decomposed sub-query
        results: List[DecomposedIssue] = []

        # Only inherit subject if specific occupation (e.g. flight crew) and target has no actor
        subject_keywords = ["thành viên tổ lái"]
        inherited_subject = ""
        first_text_lower = sub_items[0][0].lower()
        for kw in subject_keywords:
            if kw in first_text_lower:
                inherited_subject = kw
                break

        for idx, (sub_text, explicit_dom) in enumerate(sub_items, start=1):
            clean_text = re.sub(r",?\s*(?:thì sao|thì vi phạm quy định nào|thì sai những gì|có đúng không|có được không)\??$", "", sub_text, flags=re.IGNORECASE).strip()
            if not clean_text:
                clean_text = sub_text

            if idx > 1 and inherited_subject and inherited_subject not in clean_text.lower():
                if not any(k in clean_text.lower() for k in ["bảo hiểm", "bhxh", "quỹ", "cơ quan bhxh", "công ty", "người sử dụng lao động"]):
                    clean_text = f"{inherited_subject} {clean_text}"

            clean_lower = clean_text.lower()
            if any(k in clean_lower for k in ["đóng bảo hiểm", "tham gia bảo hiểm", "trách nhiệm trong việc đóng bảo hiểm", "trách nhiệm đóng bảo hiểm"]) and any(k in clean_lower for k in ["01 tháng", "1 tháng", "từ 1 tháng", "từ 01 tháng"]):
                detected_dom = "CROSS_DOMAIN"
                expanded = f"{clean_text} trách nhiệm đóng bảo hiểm xã hội bắt buộc từ 01 tháng Điều 168 Khoản 1 Bộ luật Lao động 2019 Điều 2 Khoản 1 Điểm a và Điều 21 Luật Bảo hiểm xã hội 58/VBHN Điều 44 Nghị định 283/2026/NĐ-CP"
                sub_events = detect_legal_events(clean_text)
                if "INSURANCE_CONTRIBUTION" not in sub_events:
                    sub_events.append("INSURANCE_CONTRIBUTION")
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "EMPLOYER_INSURANCE_OBLIGATION" not in sub_roles:
                    sub_roles.append("EMPLOYER_INSURANCE_OBLIGATION")
            elif any(k in clean_lower for k in ["tai nạn", "tnlđ"]) and any(k in clean_lower for k in ["chưa đóng bảo hiểm", "không đóng bảo hiểm", "chưa tham gia", "trốn đóng", "doanh nghiệp chưa đóng", "chưa đóng"]):
                detected_dom = "OCCUPATIONAL_SAFETY"
                expanded = f"{clean_text} trách nhiệm người sử dụng lao động khi người lao động bị tai nạn lao động mà doanh nghiệp chưa đóng bảo hiểm chi phí y tế tiền lương bồi thường trợ cấp Điều 38 Điều 39 Khoản 4 Luật An toàn vệ sinh lao động Điều 44 Nghị định 283/2026/NĐ-CP"
                sub_events = detect_legal_events(clean_text)
                if "OCCUPATIONAL_ACCIDENT" not in sub_events:
                    sub_events.append("OCCUPATIONAL_ACCIDENT")
                if "UNPAID_INSURANCE" not in sub_events:
                    sub_events.append("UNPAID_INSURANCE")
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                for r in ["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY", "EMPLOYER_ACCIDENT_COMPENSATION", "UNINSURED_ACCIDENT_SUBSTITUTION"]:
                    if r not in sub_roles:
                        sub_roles.append(r)
            elif (any(k in clean_lower for k in ["tai nạn", "tnlđ", "bị ngã", "bị té", "té", "ngã giàn giáo", "máy kẹp", "chấn thương", "gãy chân", "gãy tay"])
                  and any(k in clean_lower for k in ["bồi thường", "chi phí", "trợ cấp", "tiền lương", "y tế", "cty trả", "công ty trả", "được gì", "gì không", "hay gì"])):
                detected_dom = "OCCUPATIONAL_SAFETY"
                expanded = f"{clean_text} trách nhiệm người sử dụng lao động khi người lao động bị tai nạn lao động thanh toán chi phí y tế trả đủ tiền lương bồi thường hoặc trợ cấp tai nạn lao động Điều 38 Điều 39 Luật An toàn vệ sinh lao động trợ cấp tai nạn từ Quỹ bảo hiểm xã hội Điều 45"
                sub_events = detect_legal_events(clean_text)
                if "OCCUPATIONAL_ACCIDENT" not in sub_events:
                    sub_events.append("OCCUPATIONAL_ACCIDENT")
                if "WORKPLACE_INJURY" not in sub_events:
                    sub_events.append("WORKPLACE_INJURY")
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                for r in ["EMPLOYER_MEDICAL_RESPONSIBILITY", "EMPLOYER_WAGE_RESPONSIBILITY", "EMPLOYER_ACCIDENT_COMPENSATION"]:
                    if r not in sub_roles:
                        sub_roles.append(r)
            elif "trợ cấp thôi việc" in clean_lower:
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} điều kiện hưởng trợ cấp thôi việc người lao động làm việc thường xuyên từ đủ 12 tháng trở lên Điều 46 Bộ luật Lao động 2019 Điều 8 Nghị định 145/2020/NĐ-CP"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "TERMINATION_SEVERANCE_ALLOWANCE" not in sub_roles:
                    sub_roles.append("TERMINATION_SEVERANCE_ALLOWANCE")
            elif any(k in clean_lower for k in ["bằng gốc", "nộp bằng", "bằng đại học gốc", "làm tin", "giữ bằng", "giấy tờ gốc"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} hành vi người sử dụng lao động không được làm khi giao kết thực hiện hợp đồng lao động giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ Điều 17 Khoản 1 Bộ luật Lao động 2019 Điều 15 Nghị định 283/2026/NĐ-CP"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "PROHIBITED_ACTS_IDENTIFICATION" not in sub_roles:
                    sub_roles.append("PROHIBITED_ACTS_IDENTIFICATION")
            elif any(k in clean_lower for k in ["nhiều hợp đồng", "nhiều công ty", "2 công ty", "hai công ty"]) or (("cty a" in clean_lower or "công ty a" in clean_lower) and ("cty b" in clean_lower or "công ty b" in clean_lower)):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} người lao động có thể giao kết nhiều hợp đồng lao động với nhiều người sử dụng lao động Điều 19 Khoản 1 Bộ luật Lao động 2019"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "MULTIPLE_CONTRACTS_PERMISSION" not in sub_roles:
                    sub_roles.append("MULTIPLE_CONTRACTS_PERMISSION")
            elif any(k in clean_lower for k in ["nợ lương", "chậm lương", "chậm trả lương"]) and any(k in clean_lower for k in ["nghỉ", "té", "nghỉ việc", "báo trước"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} người lao động có quyền đơn phương chấm dứt hợp đồng lao động không cần báo trước khi không được trả đủ lương hoặc trả lương không đúng thời hạn Điều 35 Khoản 2 Điểm b Bộ luật Lao động 2019"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
            elif any(k in clean_lower for k in ["deal lương", "thỏa thuận lương", "chỉ trả", "trả thiếu", "bớt lương", "khấu trừ", "làm phí", "thu phí", "trừ phí", "giữ lương", "không trả đủ", "trả không đủ"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} người sử dụng lao động phải trả lương đầy đủ đúng hạn không được can thiệp tự quyết chi tiêu lương khấu trừ tiền lương chỉ để bồi thường thiệt hại xử phạt hành vi trả không đủ tiền lương quyền đơn phương chấm dứt hợp đồng lao động Điều 90 Điều 94 Điều 102 Điều 35 Khoản 2 Điểm b Điều 188 Bộ luật Lao động 2019 Điều 17 Nghị định 12/2022/NĐ-CP Điều 23 Nghị định 283/2026/NĐ-CP"
                sub_events = detect_legal_events(clean_text)
                if "WAGE_AND_SALARY" not in sub_events:
                    sub_events.append("WAGE_AND_SALARY")
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                for r in ["WAGE_PAYMENT_RULE", "WAGE_DEDUCTION_LIMIT", "UNDERPAYMENT_SANCTION", "DISPUTE_RESOLUTION_PROCEDURE"]:
                    if r not in sub_roles:
                        sub_roles.append(r)
            elif any(k in clean_lower for k in ["mang thai", "thai sản", "nuôi con dưới 12 tháng"]) and any(k in clean_lower for k in ["sa thải", "đuổi việc", "chấm dứt", "cắt giảm"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} người sử dụng lao động không được sa thải hoặc đơn phương chấm dứt hợp đồng lao động đối với lao động nữ mang thai nuôi con dưới 12 tháng tuổi Điều 37 Khoản 3 Điều 137 Khoản 3 Bộ luật Lao động 2019"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "PREGNANCY_DISMISSAL_PROHIBITION" not in sub_roles:
                    sub_roles.append("PREGNANCY_DISMISSAL_PROHIBITION")
            elif any(k in clean_lower for k in ["sổ bảo hiểm", "trả sổ", "chốt sổ", "trả lại sổ"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận và trả lại sổ bảo hiểm xã hội thời hạn 14 ngày làm việc Điều 48 Khoản 1 Khoản 3 Bộ luật Lao động 2019"
                sub_events = detect_legal_events(clean_text)
                if "TERMINATION" not in sub_events:
                    sub_events.append("TERMINATION")
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "TERMINATION_SETTLEMENT_OBLIGATION" not in sub_roles:
                    sub_roles.append("TERMINATION_SETTLEMENT_OBLIGATION")
            elif any(k in clean_lower for k in ["thực tập", "thực tập sinh", "sinh viên thực tập"]):
                detected_dom = "CORE_LABOR"
                expanded = f"{clean_text} thực tập theo chương trình đào tạo của trường không phải quan hệ lao động hợp đồng đào tạo nghề học nghề tập nghề Điều 13 Khoản 1 Điều 61 Điều 62 Bộ luật Lao động 2019"
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
                if "EMPLOYMENT_RELATIONSHIP_DEFINITION" not in sub_roles:
                    sub_roles.append("EMPLOYMENT_RELATIONSHIP_DEFINITION")
                if "EMPLOYER_TRAINING_OBLIGATION" not in sub_roles:
                    sub_roles.append("EMPLOYER_TRAINING_OBLIGATION")
            else:
                expanded = self.expander.expand(clean_text)
                detected_dom = explicit_dom or self._detect_domain(clean_text)
                sub_events = detect_legal_events(clean_text)
                sub_roles = determine_required_evidence_roles(sub_events, clean_lower)
            self._add_contextual_roles(sub_events, sub_roles, norm_q)
            results.append(
                DecomposedIssue(
                    issue_id=f"issue_{idx}",
                    raw_issue_text=sub_text,
                    retrieval_query=expanded,
                    domain=detected_dom,
                    legal_event=sub_events[0] if sub_events else "UNKNOWN",
                    legal_events=sub_events,
                    required_evidence_roles=sub_roles,
                )
            )

        return results

    def _detect_domain(self, text: str) -> str:
        """Detects primary domain of a decomposed sub-query with fine-grained action precedence."""
        t = text.lower()

        # 1. Foreign worker
        if any(k in t for k in ["lao động nước ngoài", "người nước ngoài", "work permit", "giấy phép lao động", "gplđ", "219/2025"]):
            if not any(k in t for k in ["bhtn", "thất nghiệp", "bhxh", "bảo hiểm"]):
                return "FOREIGN_WORKER"

        # 2. Unemployment insurance
        if any(k in t for k in ["thất nghiệp", "bhtn", "quỹ bhtn", "việc làm", "chốt sổ để hưởng trợ cấp thất nghiệp", "hưởng thất nghiệp", "hưởng bhtn"]):
            if not any(k in t for k in ["chốt sổ bảo hiểm xã hội", "nợ bhxh", "nợ tiền bảo hiểm", "bhxh một lần"]):
                return "UNEMPLOYMENT_INSURANCE"

        # 3. Occupational safety (Employer duty, compensation & safety refusal)
        if any(k in t for k in ["bồi thường của công ty khi bị tai nạn", "công ty phải bồi thường khi tai nạn", "công ty có phải bồi thường trợ cấp", "tiền bồi thường nào từ công ty", "luật 84", "atvslđ", "bồi thường tai nạn", "trách nhiệm bồi thường chi phí y tế và tiền lương của công ty", "từ chối làm việc", "đe dọa tính mạng", "sạt lở", "nguy cơ tai nạn"]):
            if not any(k in t for k in ["quỹ tnlđ", "bảo hiểm giải quyết", "trợ cấp tnlđ"]):
                return "OCCUPATIONAL_SAFETY"

        # 4. Occupational accident disease (Fund benefits)
        if any(k in t for k in ["quỹ tnlđ", "trợ cấp tnlđ", "bảo hiểm giải quyết", "suy giảm khả năng lao động", "bệnh nghề nghiệp", "04/vbhn", "quỹ bảo hiểm tnlđ"]):
            return "OCCUPATIONAL_ACCIDENT_DISEASE"

        # 5. Core Labor (Contractual rights, employer obligations, termination, severance, discipline)
        if any(k in t for k in ["chấm dứt hợp đồng", "đơn phương", "sa thải", "bồi thường hợp đồng", "trợ cấp thôi việc", "thử việc", "trả lương", "nghĩa vụ bồi thường của công ty", "kỷ luật", "khiển trách", "cắt thưởng", "xét thưởng"]):
            if not any(k in t for k in ["chế độ thai sản", "chế độ ốm đau", "bhxh giải quyết", "cơ quan bhxh"]):
                return "CORE_LABOR"

        # 6. Retirement
        if any(k in t for k in ["tuổi nghỉ hưu", "135/2020", "nghị định 135"]) and not any(k in t for k in ["bhxh giải quyết", "rút một lần", "đóng tự nguyện"]):
            return "RETIREMENT"

        # 7. Social Insurance
        if any(k in t for k in ["bhxh", "bảo hiểm xã hội", "thai sản", "nghỉ sinh", "ốm đau", "rút một lần", "bhxh một lần", "hưu trí", "tử tuất", "mai táng", "58/vbhn", "chốt sổ bảo hiểm xã hội"]):
            return "SOCIAL_INSURANCE"

        return "CORE_LABOR"

    def _enrich_with_scenario(self, raw_q: str, scenario: str) -> str:
        """Finds sentences in scenario relevant to the sub-question and joins them."""
        if not scenario:
            return raw_q
        sentences = [p.strip() for p in re.split(r"(?<!\d)\.|\.(?!\d)|\n+|:", scenario) if p.strip()]
        matched: List[str] = []
        q_lower = raw_q.lower()
        for s in sentences:
            s_lower = s.lower()
            if any(k in q_lower for k in ["làm thêm", "tăng ca", "ngoài giờ"]):
                if any(k in s_lower for k in ["làm thêm", "tăng ca", "ngoài giờ", "giờ", "trừ thưởng"]):
                    matched.append(s)
            elif any(k in q_lower for k in ["báo trước", "nghỉ việc", "chấm dứt", "bồi thường"]):
                if any(k in s_lower for k in ["hợp đồng", "báo trước", "nghỉ việc", "chấm dứt", "bồi thường"]):
                    matched.append(s)
            elif any(k in q_lower for k in ["lương", "tiền lương", "thu nhập"]):
                if re.search(r"trả lương|chậm trả|nợ lương|kỳ hạn trả|mức lương", s_lower):
                    matched.append(s)
            elif any(k in q_lower for k in ["bhxh", "bảo hiểm"]):
                if re.search(r"bhxh|bảo hiểm", s_lower):
                    matched.append(s)
            elif any(k in q_lower for k in ["thông báo", "kết quả", "kéo dài", "ký hợp đồng"]):
                if re.search(r"thông báo|kết quả|kéo dài|đạt yêu cầu", s_lower):
                    matched.append(s)
            elif any(k in q_lower for k in ["từ chối", "kỷ luật", "khiển trách", "thưởng", "an toàn"]):
                if any(k in s_lower for k in ["sạt lở", "tính mạng", "sức khỏe", "từ chối", "kỷ luật", "khiển trách", "thưởng", "nguy cơ", "nguy hiểm"]):
                    matched.append(s)
            elif any(k in q_lower for k in ["thỏa thuận", "hợp đồng", "kiện", "trả tiền công"]):
                if any(k in s_lower for k in ["thỏa thuận", "hợp đồng", "công việc", "tiền công", "thanh toán"]):
                    matched.append(s)
            elif any(k in q_lower for k in ["giấy tờ", "tùy thân", "bản chính"]):
                if any(k in s_lower for k in ["giấy tờ", "tùy thân", "bản chính", "quản lý tiền", "trung thực"]):
                    matched.append(s)

        if any(k in q_lower for k in ["bhxh", "bảo hiểm"]):
            for s in sentences:
                if "thử việc riêng" in s.lower() and s not in matched:
                    matched.insert(0, s)

        if matched:
            return " ".join(matched) + ". " + raw_q
        return raw_q
