# -*- coding: utf-8 -*-
"""Deterministic case-file analysis for long, multi-issue labour-law scenarios.

The LLM is deliberately not used for this stage.  The analyzer turns a narrative
into auditable facts and issue-level premise warnings before retrieval, so later
stages can distinguish facts supplied by the user from assumptions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
from typing import Any, Dict, Iterable, List


@dataclass
class CaseFact:
    fact_type: str
    value: str
    source_text: str


@dataclass
class IssueCaseProfile:
    issue_id: str
    issue_text: str
    domain: str
    legal_events: List[str] = field(default_factory=list)
    required_evidence_roles: List[str] = field(default_factory=list)
    relevant_fact_types: List[str] = field(default_factory=list)
    missing_material_facts: List[str] = field(default_factory=list)


@dataclass
class CaseAnalysisResult:
    is_complex: bool
    complexity_score: int
    character_count: int
    sentence_count: int
    issue_count: int
    facts: List[CaseFact] = field(default_factory=list)
    issue_profiles: List[IssueCaseProfile] = field(default_factory=list)
    analysis_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt_block(self) -> str:
        lines = [
            "[HỒ SƠ TÌNH HUỐNG DO HỆ THỐNG TRÍCH XUẤT - KHÔNG ĐƯỢC TỰ BỔ SUNG DỮ KIỆN]",
            f"- Độ phức tạp: {self.complexity_score}/10; số vấn đề: {self.issue_count}.",
        ]
        if self.facts:
            lines.append("- Dữ kiện đã có:")
            for fact in self.facts[:24]:
                lines.append(f"  + {fact.fact_type}: {fact.value}")
            intervals = [fact.value for fact in self.facts if fact.fact_type == "DATE_INTERVAL"]
            if intervals:
                lines.append("- KẾT QUẢ TÍNH NGÀY BẮT BUỘC (cấm tự tính khác): " + "; ".join(intervals))
        else:
            lines.append("- Dữ kiện đã có: chưa nhận diện được dữ kiện định lượng hoặc tài liệu cụ thể.")

        for profile in self.issue_profiles:
            lines.append(f"- {profile.issue_id}: {profile.issue_text}")
            if profile.missing_material_facts:
                lines.append(
                    "  + Dữ kiện có thể còn thiếu: "
                    + "; ".join(profile.missing_material_facts)
                    + ". Chỉ phân tích có điều kiện, không được tự giả định."
                )
        return "\n".join(lines)


class CaseAnalyzer:
    """Extracts a compact, deterministic case file from Vietnamese narratives."""

    _FACT_PATTERNS = {
        "DATE": re.compile(r"\b(?:ngày\s+)?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", re.I),
        "MONEY": re.compile(r"\b\d+(?:[\.,]\d+)?\s*(?:triệu|tr|nghìn|ngàn|đồng|vnđ)\b", re.I),
        "PERCENT": re.compile(r"\b\d+(?:[\.,]\d+)?\s*%", re.I),
        "DURATION": re.compile(
            r"\b\d+(?:[\.,]\d+)?\s*(?:ngày|tháng|năm|tuần|giờ|tiếng)(?:\s+làm\s+việc)?\b",
            re.I,
        ),
        "CONTRACT": re.compile(
            r"\b(?:hợp đồng|hđlđ)\s+(?:lao động\s+)?(?:không\s+xác\s+định\s+thời\s+hạn|"
            r"xác\s+định\s+thời\s+hạn|thời\s+vụ|thử\s+việc|dịch\s+vụ|cộng\s+tác\s+viên)\b",
            re.I,
        ),
        "DOCUMENT": re.compile(
            r"\b(?:quyết định|biên bản|nội quy|thỏa thuận|hợp đồng|email|tin nhắn|bảng lương|"
            r"bảng chấm công|giấy chứng nhận|hồ sơ bệnh án)\b",
            re.I,
        ),
    }

    _MATERIAL_FACT_RULES = {
        "TERMINATION": [
            ("loại hợp đồng và thời hạn còn lại", ("không xác định thời hạn", "xác định thời hạn", "hợp đồng", "hđlđ")),
            ("chủ thể chấm dứt hợp đồng", ("người lao động nghỉ", "công ty cho nghỉ", "sa thải", "đuổi việc", "đơn phương")),
            ("thời gian hoặc việc thực hiện báo trước", ("báo trước", "không báo", "ngày", "tháng")),
        ],
        "PROBATION": [
            ("công việc/chức danh thử việc", ("chức danh", "vị trí", "quản lý", "kỹ thuật", "nhân viên")),
            ("thời gian thử việc", ("thử việc", "ngày", "tháng")),
        ],
        "WAGE_AND_SALARY": [
            ("mức lương hoặc cách tính lương", ("lương", "đồng", "triệu", "vnđ")),
            ("kỳ hạn hoặc số ngày chậm trả", ("kỳ trả", "đến hạn", "chậm", "ngày", "tháng")),
            ("lý do chậm trả và việc người sử dụng lao động đã áp dụng biện pháp khắc phục", ("bất khả kháng", "thiên tai", "hỏa hoạn", "dịch bệnh", "đã tìm mọi biện pháp")),
        ],
        "OCCUPATIONAL_ACCIDENT": [
            ("hoàn cảnh tai nạn có liên quan đến công việc", ("tại nơi làm việc", "trong giờ", "nhiệm vụ", "trên đường")),
            ("kết quả giám định suy giảm khả năng lao động", ("suy giảm", "%", "giám định")),
            ("tình trạng tham gia bảo hiểm", ("đóng bảo hiểm", "chưa đóng", "bhxh", "bảo hiểm")),
        ],
        "OVERTIME": [
            ("số giờ làm thêm và khoảng thời gian tính", ("giờ", "tiếng", "ngày", "tháng", "năm")),
            ("sự đồng ý của người lao động", ("đồng ý", "ép", "bắt buộc", "tự nguyện")),
        ],
        "DISCIPLINE_AND_BONUS": [
            (
                "quy chế thưởng, hợp đồng lao động hoặc thỏa ước lao động tập thể quy định điều kiện hưởng thưởng",
                ("quy chế thưởng", "hợp đồng quy định thưởng", "thỏa ước lao động", "điều kiện thưởng"),
            ),
        ],
        "DE_FACTO_LABOR_CONTRACT": [
            ("việc làm và khoản tiền công", ("công việc", "trả công", "tiền công", "lương")),
            ("sự quản lý, điều hành hoặc giám sát", ("quản lý", "điều hành", "giám sát", "chấm công", "ca làm")),
        ],
        "WORKPLACE_VIOLENCE": [
            ("người thực hiện hành vi và quan hệ với người sử dụng lao động", ("sếp", "quản lý", "chủ", "giám đốc", "trưởng")),
            ("mức độ thương tích và tài liệu y tế", ("thương tích", "chảy máu", "đi khám", "bệnh viện", "giám định", "%")),
            ("chứng cứ về hành vi", ("camera", "nhân chứng", "ảnh", "video", "tin nhắn", "biên bản")),
        ],
        "CONTRACT_SIGNING_TIMING": [
            ("ngày thực tế bắt đầu làm việc và ngày giao kết hợp đồng", ("bắt đầu", "vào làm", "đi làm", "mới ký", "ký sau", "cuối tuần")),
            ("thời hạn dự kiến của hợp đồng", ("dưới 01 tháng", "dưới 1 tháng", "tháng", "năm", "không xác định thời hạn")),
        ],
    }

    @staticmethod
    def _dedupe(items: Iterable[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for item in items:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(item.strip())
        return result

    def extract_facts(self, narrative: str) -> List[CaseFact]:
        facts: List[CaseFact] = []
        seen = set()
        for fact_type, pattern in self._FACT_PATTERNS.items():
            for match in pattern.finditer(narrative):
                value = match.group(0).strip()
                key = (fact_type, value.lower())
                if key in seen:
                    continue
                seen.add(key)
                start = max(0, match.start() - 45)
                end = min(len(narrative), match.end() + 45)
                source = re.sub(r"\s+", " ", narrative[start:end]).strip()
                facts.append(CaseFact(fact_type=fact_type, value=value, source_text=source))

        # Deterministically calculate intervals between dates appearing in the
        # same sentence. This prevents the language model from turning, e.g.,
        # 20/09 -> 01/10 into an invented 30-day notice period.
        for sentence in [s for s in re.split(r"[.!?\n]+", narrative) if s.strip()]:
            date_matches = list(re.finditer(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", sentence))
            for left, right in zip(date_matches, date_matches[1:]):
                try:
                    start = datetime.strptime(left.group(0).replace("-", "/"), "%d/%m/%Y").date()
                    end = datetime.strptime(right.group(0).replace("-", "/"), "%d/%m/%Y").date()
                except ValueError:
                    continue
                days = (end - start).days
                if days < 0:
                    continue
                value = f"Từ {start.strftime('%d/%m/%Y')} đến {end.strftime('%d/%m/%Y')}: {days} ngày theo lịch"
                key = ("DATE_INTERVAL", value.lower())
                if key not in seen:
                    seen.add(key)
                    facts.append(CaseFact("DATE_INTERVAL", value, sentence.strip()))
        return facts

    def analyze(self, narrative: str, issues: List[Any]) -> CaseAnalysisResult:
        text = narrative or ""
        lower = text.lower()
        facts = self.extract_facts(text)
        sentence_count = len([p for p in re.split(r"[.!?\n]+", text) if p.strip()])
        issue_count = max(1, len(issues))

        score = min(
            10,
            (2 if len(text) >= 500 else 1 if len(text) >= 220 else 0)
            + min(4, max(0, issue_count - 1) * 2)
            + min(2, len(facts) // 4)
            + (1 if sentence_count >= 6 else 0),
        )

        profiles: List[IssueCaseProfile] = []
        for index, issue in enumerate(issues or [], 1):
            issue_id = str(getattr(issue, "issue_id", None) or f"issue_{index}")
            issue_text = str(getattr(issue, "raw_issue_text", None) or text)
            events = list(getattr(issue, "legal_events", None) or [])
            primary_event = str(getattr(issue, "legal_event", "UNKNOWN") or "UNKNOWN")
            if primary_event != "UNKNOWN" and primary_event not in events:
                events.insert(0, primary_event)

            missing: List[str] = []
            relevant_types: List[str] = []
            issue_lower = issue_text.lower()
            combined_lower = f"{lower} {issue_lower}"
            for event in events:
                rules = self._MATERIAL_FACT_RULES.get(event, [])
                for label, signals in rules:
                    if not any(signal in combined_lower for signal in signals):
                        missing.append(label)
                if rules:
                    relevant_types.extend(["DATE", "DURATION", "MONEY", "PERCENT", "CONTRACT", "DOCUMENT"])

            profiles.append(
                IssueCaseProfile(
                    issue_id=issue_id,
                    issue_text=issue_text,
                    domain=str(getattr(issue, "domain", "CORE_LABOR")),
                    legal_events=events,
                    required_evidence_roles=list(getattr(issue, "required_evidence_roles", None) or []),
                    relevant_fact_types=self._dedupe(relevant_types),
                    missing_material_facts=self._dedupe(missing),
                )
            )

        warnings: List[str] = []
        if issue_count > 1:
            warnings.append("Phải kết luận và gắn căn cứ độc lập cho từng vấn đề.")
        if any(profile.missing_material_facts for profile in profiles):
            warnings.append("Một số kết luận phải trình bày có điều kiện vì còn thiếu dữ kiện vật chất.")

        return CaseAnalysisResult(
            is_complex=score >= 4 or issue_count > 1,
            complexity_score=score,
            character_count=len(text),
            sentence_count=sentence_count,
            issue_count=issue_count,
            facts=facts,
            issue_profiles=profiles,
            analysis_warnings=warnings,
        )
