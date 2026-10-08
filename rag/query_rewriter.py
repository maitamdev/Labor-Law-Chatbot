# -*- coding: utf-8 -*-
"""
VietLabor AI - Relevance Grader & Adaptive Query Rewriter
Implements self-reflective evaluation inspired by ViLeXa & Corrective-RAG (CRAG):
1. RelevanceGrader: Assesses whether retrieved candidate chunks provide sufficient legal grounding.
2. AdaptiveQueryRewriter: Reformulates colloquial or under-specified queries into standard Vietnamese
   statutory terminology for iterative retrieval (max 1-2 retries).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Statutory expansion dictionary for common Vietnamese colloquial labor terms
COLLOQUIAL_LEGAL_MAP: Dict[str, str] = {
    "đuổi việc": "đơn phương chấm dứt hợp đồng lao động sa thải",
    "cho thôi việc": "chấm dứt hợp đồng lao động đơn phương",
    "sa thải ngang": "đơn phương chấm dứt hợp đồng lao động trái pháp luật Điều 36 Điều 41",
    "đuổi ngang": "đơn phương chấm dứt hợp đồng lao động trái pháp luật bồi thường",
    "quỵt lương": "chậm trả tiền lương vi phạm trả lương khiếu nại tiền lương",
    "quịt lương": "chậm trả tiền lương vi phạm trả lương",
    "nợ lương": "tiền lương trả chậm tiền lãi chậm trả lương",
    "giữ bằng": "hành vi người sử dụng lao động không được làm khi giao kết hợp đồng Điều 17",
    "giữ cccd": "giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ Điều 17",
    "giữ chứng chỉ": "giữ bản chính giấy tờ tùy thân văn bằng chứng chỉ Điều 17",
    "đặt cọc đi làm": "buộc người lao động thực hiện biện pháp bảo đảm bằng tiền Điều 17",
    "ép tăng ca": "thời giờ làm thêm làm thêm giờ sự đồng ý của người lao động Điều 107",
    "làm thêm không lương": "tiền lương làm thêm giờ làm việc vào ban đêm Điều 98",
    "bầu bì bị đuổi": "đơn phương chấm dứt hợp đồng lao động lao động nữ mang thai nuôi con dưới 12 tháng Điều 137",
    "nghỉ đẻ": "chế độ thai sản thời gian nghỉ thai sản lao động nữ",
    "tai nạn đi làm": "tai nạn lao động bồi thường tai nạn lao động Luật an toàn vệ sinh lao động",
    "bị té": "tai nạn lao động bị tai nạn ngã chấn thương trong giờ làm việc bồi thường chi phí y tế tiền lương trợ cấp Điều 38 Điều 39 Luật An toàn vệ sinh lao động",
    "té ngã": "tai nạn lao động bồi thường chi phí y tế tiền lương trợ cấp Điều 38 Điều 39 Luật An toàn vệ sinh lao động",
    "bị ngã": "tai nạn lao động bị ngã ngã giàn giáo chấn thương bồi thường chi phí y tế tiền lương Điều 38 Điều 39 Luật An toàn vệ sinh lao động",
    "đóng bảo hiểm thiếu": "trách nhiệm đóng bảo hiểm xã hội trốn đóng bảo hiểm bắt buộc",
    "không có bảo hiểm": "người lao động không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc chi trả cùng lúc tiền lương",
    "hết hạn hợp đồng": "chấm dứt hợp đồng lao động khi hết hạn hợp đồng Điều 34",
    "nghỉ việc không báo": "đơn phương chấm dứt hợp đồng lao động trái pháp luật nghĩa vụ báo trước Điều 35 Điều 40",
    "từ chối làm việc": "quyền từ chối làm việc đe dọa trực tiếp tính mạng sức khỏe Điều 5 Điều 6 Luật an toàn vệ sinh lao động",
    "sạt lở": "nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng sức khỏe Điều 6 Luật an toàn vệ sinh lao động",
    "nguy cơ đe dọa tính mạng": "nguy cơ rõ ràng đe dọa trực tiếp đến tính mạng sức khỏe quyền từ chối làm việc Điều 5 Điều 6",
    "cắt thưởng": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật Điều 127",
    "không xét thưởng": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật Điều 127",
    "bỏ vị trí làm việc": "rời bỏ nơi làm việc quyền từ chối làm việc không bị coi là vi phạm kỷ luật lao động Điều 6",
    # Trả sổ BHXH & giữ giấy tờ khi chấm dứt HĐLĐ (Điều 48 BLLĐ)
    "trả sổ bảo hiểm": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "trả sổ bhxh": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "không chịu trả sổ": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "không trả sổ": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "chưa trả sổ": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "giữ sổ bảo hiểm": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "giữ sổ bhxh": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    "chây ì không chịu trả sổ": "trách nhiệm của người sử dụng lao động khi chấm dứt hợp đồng lao động hoàn thành thủ tục xác nhận thời gian đóng bảo hiểm xã hội bảo hiểm thất nghiệp trả lại sổ bảo hiểm xã hội cùng giấy tờ khác Điều 48",
    # Phạt tiền trừ vào lương / trừ lương đi trễ thay xử lý kỷ luật (Điều 127 BLLĐ)
    "phạt tiền trừ vào lương": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền trừ lương": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền khi đi làm trễ": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "trừ lương khi đi làm trễ": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "trừ lương đi làm trễ": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "trừ lương đi trễ": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền đi trễ": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền đi làm muộn": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "trừ lương thay kỷ luật": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền thay kỷ luật": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    "phạt tiền thay cho xử lý kỷ luật": "hành vi bị nghiêm cấm khi xử lý kỷ luật lao động phạt tiền cắt lương thay việc xử lý kỷ luật lao động Điều 127",
    # Ép tăng ca / bắt tăng ca / làm thêm giờ không đồng ý (Điều 107 BLLĐ)
    "ép nhân viên tăng ca": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "bắt nhân viên tăng ca": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "bắt tăng ca": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "ép làm thêm": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "bắt làm thêm": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "ép làm thêm giờ": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "bắt làm thêm giờ": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    "không đồng ý tăng ca": "thời giờ làm thêm làm thêm giờ phải được sự đồng ý của người lao động Điều 107",
    # Hư hỏng dụng cụ thiết bị, rơi vỡ máy tính, khấu trừ bồi thường tối đa (Điều 130 BLLĐ)
    "làm rơi vỡ": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "làm rơi vỡ máy": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "làm vỡ máy": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "làm hỏng máy": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "hư hỏng máy": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "hư hỏng thiết bị": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "trừ lương bồi thường": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "bồi thường tối đa bao nhiêu tháng": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
    "bồi thường nhiều nhất bao nhiêu tháng": "xử lý bồi thường thiệt hại làm hư hỏng dụng cụ thiết bị tài sản bồi thường nhiều nhất là 03 tháng tiền lương khấu trừ vào tiền lương Điều 130",
}


@dataclass
class GradeResult:
    """Outcome of statutory relevance evaluation."""
    is_relevant: bool
    confidence_score: float
    reason: str
    suggested_focus: Optional[str] = None


class RelevanceGrader:
    """Grades retrieved legal candidate chunks to decide if query rewriting is warranted."""

    def __init__(
        self,
        min_candidate_count: int = 1,
        min_top_score_threshold: float = 0.005,
    ):
        self.min_candidate_count = min_candidate_count
        self.min_top_score_threshold = min_top_score_threshold

    def grade(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        primary_docs: Optional[Set[str]] = None,
        expected_intent: Optional[str] = None,
    ) -> GradeResult:
        """Evaluates relevance of retrieved candidate pool.
        
        Args:
            query: Current search query.
            candidates: Retrieved chunk dictionaries.
            primary_docs: Set of primary document IDs expected for this legal domain.
            expected_intent: Legal intent (e.g. SUBSTANTIVE_RULE, TERMINATION, etc.)
            
        Returns:
            GradeResult indicating if candidates are acceptable or query needs rewrite.
        """
        if not candidates or len(candidates) < self.min_candidate_count:
            return GradeResult(
                is_relevant=False,
                confidence_score=0.0,
                reason="Không tìm thấy đoạn luật nào khớp với truy vấn ban đầu.",
            )

        top_cand = candidates[0]
        top_score = top_cand.get("rerank_score", top_cand.get("score", 0.0))

        # Check if any candidate belongs to expected primary statutory documents
        has_primary = False
        if primary_docs:
            for c in candidates[:5]:
                doc_id = c.get("metadata", {}).get("doc_id", "")
                if doc_id in primary_docs:
                    has_primary = True
                    break

        # Check keyword presence in top chunk contents
        q_words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
        matched_words = 0
        top_content = (top_cand.get("content", "") + " " + top_cand.get("metadata", {}).get("article_title", "")).lower()
        for w in q_words:
            if w in top_content:
                matched_words += 1

        keyword_overlap_ratio = matched_words / max(len(q_words), 1)

        # High confidence if top candidate has high score and belongs to primary docs
        if primary_docs and not has_primary and keyword_overlap_ratio < 0.2:
            return GradeResult(
                is_relevant=False,
                confidence_score=float(top_score),
                reason="Tài liệu thu hồi chưa chứa văn bản nguồn chính cho lĩnh vực này.",
            )

        if top_score < self.min_top_score_threshold and keyword_overlap_ratio < 0.15:
            return GradeResult(
                is_relevant=False,
                confidence_score=float(top_score),
                reason=f"Độ tương đồng của kết quả hàng đầu quá thấp ({top_score:.4f}).",
            )

        return GradeResult(
            is_relevant=True,
            confidence_score=float(top_score),
            reason="Tài liệu thu hồi đạt tiêu chuẩn liên quan pháp lý.",
        )


class AdaptiveQueryRewriter:
    """Reformulates queries to improve statutory retrieval hit rate."""

    def __init__(self, llm_manager: Optional[Any] = None):
        self.llm_manager = llm_manager

    def rewrite_deterministic(self, query: str) -> str:
        """Fast dictionary-based canonical statutory substitution (0ms latency)."""
        expanded = query
        q_lower = query.lower()
        additions = []

        for colloquial, legal_terms in COLLOQUIAL_LEGAL_MAP.items():
            if colloquial in q_lower:
                additions.append(legal_terms)

        if additions:
            unique_terms = " ".join(dict.fromkeys(" ".join(additions).split()))
            return f"{query} {unique_terms}".strip()

        return query

    def rewrite_with_llm(
        self,
        query: str,
        domain: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        """Uses LLM to reformulate question into standard legal terminology if LLM is online."""
        if not self.llm_manager:
            return self.rewrite_deterministic(query)

        prompt_text = (
            f"Câu hỏi của người dùng: '{query}'\n"
            f"Lĩnh vực pháp lý: {domain or 'Luật Lao động Việt Nam'}\n"
            f"Vấn đề khi tìm kiếm: {reason or 'Chưa tìm thấy điều luật phù hợp'}\n\n"
            "Hãy viết lại câu hỏi trên thành 1 câu truy vấn ngắn gọn (dưới 30 từ), "
            "sử dụng đúng thuật ngữ quy phạm pháp luật trong Bộ luật Lao động, Nghị định hoặc Luật BHXH "
            "(ví dụ: 'đuổi việc' -> 'đơn phương chấm dứt hợp đồng lao động', 'nợ lương' -> 'chậm trả tiền lương'). "
            "Chỉ trả lời duy nhất câu truy vấn đã viết lại, không giải thích thêm."
        )

        try:
            # get_llm() forces the legal-answer JSON schema; a rewrite needs plain text.
            get_aux = getattr(self.llm_manager, "get_aux_llm", None)
            llm = get_aux(json_schema=None, num_predict=80) if callable(get_aux) else self.llm_manager.get_llm()
            messages = [
                SystemMessage(content="Bạn là chuyên gia tra cứu thuật ngữ Bộ luật Lao động Việt Nam. Nhiệm vụ của bạn là chuẩn hóa ngôn ngữ đời thường thành thuật ngữ pháp lý chính thức."),
                HumanMessage(content=prompt_text),
            ]
            response = llm.invoke(messages)
            content = response.content.strip()
            # Clean quotes or backticks if returned
            content = re.sub(r"^[\"']|[\"']$", "", content).strip()
            if content and len(content) > 5:
                logger.info(f"LLM rewritten query: '{query}' -> '{content}'")
                return content
        except Exception as e:
            logger.warning(f"LLM query rewrite failed: {e}. Falling back to deterministic rewrite.")

        return self.rewrite_deterministic(query)

    def rewrite(
        self,
        query: str,
        domain: Optional[str] = None,
        reason: Optional[str] = None,
        use_llm: bool = False,
    ) -> str:
        """Main rewrite entry point with automatic fallback."""
        if use_llm:
            return self.rewrite_with_llm(query, domain=domain, reason=reason)
        return self.rewrite_deterministic(query)
