# -*- coding: utf-8 -*-
"""
VietLabor AI - Chat Service Adapter (Phase 6)
Thin integration adapter between VietLaborRAGChain and the Streamlit UI.
Does NOT modify any backend reasoning logic.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from config.metadata_registry import get_verified_metadata
from rag.chain import VietLaborRAGChain, ChainExecutionResult, StageCallback, TokenCallback
from rag.conversational import detect_smalltalk
from rag.evidence_mapper import CitationSanitizer
from rag.output_validator import format_answer_markdown

logger = logging.getLogger(__name__)

# Canonical Official Document URLs for Vietnam Labor Law
OFFICIAL_DOC_URLS = {
    "VBHN_18_2026": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm",
    "18/VBHN-VPQH": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm",
    "45/2019/QH14": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm",
    "ND_145_2020": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm",
    "145/2020/NĐ-CP": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm",
    "ND_12_2022": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx",
    "12/2022/NĐ-CP": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx",
    "ND_283_2026": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm",
    "283/2026/NĐ-CP": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm",
    "L_84_2015": "https://congbao.chinhphu.vn/van-ban/luat-so-84-2015-qh13-15356.htm",
    "84/2015/QH13": "https://congbao.chinhphu.vn/van-ban/luat-so-84-2015-qh13-15356.htm",
    "VBHN_58_2025": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
    "19/VBHN-VPQH": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
}

# Direct HTML Document URLs on Thư Viện Pháp Luật (supports direct #dieu_X anchor auto-scroll)
TVPL_DOC_URLS = {
    "VBHN_18_2026": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
    "18/VBHN-VPQH": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
    "45/2019/QH14": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx",
    "ND_145_2020": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-459400.aspx",
    "145/2020/NĐ-CP": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-459400.aspx",
    "ND_12_2022": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-lao-dong-bao-hiem-nguoi-lam-viec-nuoc-ngoai-479312.aspx",
    "12/2022/NĐ-CP": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-lao-dong-bao-hiem-nguoi-lam-viec-nuoc-ngoai-479312.aspx",
    "L_84_2015": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Luat-an-toan-ve-sinh-lao-dong-2015-281961.aspx",
    "84/2015/QH13": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Luat-an-toan-ve-sinh-lao-dong-2015-281961.aspx",
    "VBHN_58_2025": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
    "58/VBHN-VPQH": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
    "19/VBHN-VPQH": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
    "TT_10_2020": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-10-2020-TT-BLDTBXH-noi-dung-hop-dong-lao-dong-hoi-dong-thuong-luong-tap-the-458145.aspx",
    "10/2020/TT-BLĐTBXH": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Thong-tu-10-2020-TT-BLDTBXH-noi-dung-hop-dong-lao-dong-hoi-dong-thuong-luong-tap-the-458145.aspx",
    "ND_283_2026": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm",
    "283/2026/NĐ-CP": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm",
}

# Standard Friendly Titles
FRIENDLY_DOC_TITLES = {
    "VBHN_18_2026": "Bộ luật Lao động 2019",
    "18/VBHN-VPQH": "Bộ luật Lao động 2019",
    "45/2019/QH14": "Bộ luật Lao động 2019",
    "ND_145_2020": "Nghị định 145/2020/NĐ-CP",
    "145/2020/NĐ-CP": "Nghị định 145/2020/NĐ-CP",
    "ND_12_2022": "Nghị định 12/2022/NĐ-CP",
    "12/2022/NĐ-CP": "Nghị định 12/2022/NĐ-CP",
    "ND_283_2026": "Nghị định 283/2026/NĐ-CP",
    "283/2026/NĐ-CP": "Nghị định 283/2026/NĐ-CP",
    "L_84_2015": "Luật An toàn, vệ sinh lao động 2015",
    "84/2015/QH13": "Luật An toàn, vệ sinh lao động 2015",
    "VBHN_58_2025": "Luật Bảo hiểm xã hội",
    "58/VBHN-VPQH": "Luật Bảo hiểm xã hội",
}


def answer_smalltalk(question: str, has_history: bool = False) -> Optional[Dict[str, Any]]:
    """Instant UI response for greetings/thanks/identity, or None for real questions.

    Needs no retriever, embedding model or Ollama, so the first "Xin chào" of a
    session answers immediately instead of waiting for the RAG stack to load.
    """
    reply = detect_smalltalk(unicodedata.normalize("NFC", question or ""), has_history=has_history)
    if reply is None:
        return None
    return {
        "answer": reply.answer,
        "raw_answer": reply.answer,
        "final_answer": reply.answer,
        "findings": [],
        "citations": [],
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
        "out_of_scope": False,
        "is_smalltalk": True,
        "smalltalk_intent": reply.intent,
        "suggested_followups": list(reply.suggestions),
        "latency_ms": 0.0,
        "locked_chunk_ids": [],
        "graph_expanded_chunk_ids": [],
        "retrieval_method": "None (Conversational fast-track)",
        "evidence_coverage": {},
        "unresolved_issue_ids": [],
        "is_fully_grounded": True,
    }


class ChatService:
    """Thin adapter providing structured UI responses from the RAG backend."""

    def __init__(self, chain: Optional[VietLaborRAGChain] = None):
        self.chain = chain or VietLaborRAGChain()

    def reset_conversation(self) -> None:
        """Clears conversational working memory for a new session."""
        self.chain.memory.clear()

    def restore_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """Rebuilds this service's private short-term memory from one chat.

        The UI keeps a separate ChatService per Streamlit session.  Replaying
        messages here prevents facts from the previously selected conversation
        from leaking into the newly selected one.
        """
        self.chain.memory.clear()
        pending_user: Optional[str] = None
        for message in messages:
            role = str(message.get("role") or "")
            content = str(message.get("content") or "")
            if role == "user":
                if pending_user is not None:
                    self.chain.memory.add_turn(pending_user, "")
                pending_user = content
            elif role == "assistant" and pending_user is not None:
                if (message.get("structured_data") or {}).get("is_smalltalk"):
                    pending_user = None  # greetings/thanks carry no legal facts
                    continue
                self.chain.memory.add_turn(pending_user, content)
                pending_user = None
        if pending_user is not None:
            self.chain.memory.add_turn(pending_user, "")

    def ask(
        self,
        question: str,
        update_memory: bool = True,
        on_stage: Optional[StageCallback] = None,
        on_token: Optional[TokenCallback] = None,
    ) -> Dict[str, Any]:
        """Executes RAG inference and maps output to clean UI response schema.

        on_stage / on_token are optional real-time callbacks (see VietLaborRAGChain.run).
        """
        norm_q = unicodedata.normalize("NFC", question).strip()
        result: ChainExecutionResult = self.chain.run(
            norm_q, update_memory=update_memory, on_stage=on_stage, on_token=on_token,
        )
        if result.is_smalltalk:
            fast = answer_smalltalk(norm_q, has_history=bool(self.chain.memory.history))
            if fast is not None:
                fast["latency_ms"] = result.total_latency_ms
                return fast

        val_resp = result.validated_response
        registry = result.formatted_context.chunk_metadata_registry

        # Map candidate text excerpts
        chunk_text_map: Dict[str, str] = {}
        for chk in result.retrieved_chunks:
            cid = chk.get("id") or chk.get("chunk_id")
            txt = chk.get("content") or chk.get("text") or ""
            if cid and txt:
                chunk_text_map[cid] = txt

        # Build Enriched Citations List
        enriched_citations: List[Dict[str, Any]] = []
        for cid in val_resp.cited_chunk_ids:
            meta = registry.get(cid, {})
            doc_id = meta.get("doc_id", "")
            doc_no = meta.get("document_no", "")
            raw_title = meta.get("document_title", "")
            doc_title = FRIENDLY_DOC_TITLES.get(doc_id) or FRIENDLY_DOC_TITLES.get(doc_no) or raw_title or "Văn bản pháp luật"

            art_num = meta.get("article_number")
            cl_num = meta.get("clause_number")
            pt = meta.get("point")
            art_title = meta.get("article_title", "")

            # Excerpt from chunk text
            excerpt = chunk_text_map.get(cid) or meta.get("text") or meta.get("content") or ""
            if len(excerpt) > 400:
                excerpt = excerpt[:400].strip() + "..."

            verified_meta = get_verified_metadata(doc_id)
            source_url = (
                meta.get("official_source")
                or meta.get("source_url")
                or verified_meta.get("official_source")
                or OFFICIAL_DOC_URLS.get(doc_id)
                or OFFICIAL_DOC_URLS.get(doc_no)
                or ""
            )

            # Deep link directly to the specific article on TVPL (with #dieu_X anchor)
            tvpl_base = TVPL_DOC_URLS.get(doc_id) or TVPL_DOC_URLS.get(doc_no)
            deep_link_url = ""
            if tvpl_base:
                if art_num is not None and "thuvienphapluat.vn" in tvpl_base:
                    deep_link_url = f"{tvpl_base}#dieu_{art_num}"
                else:
                    deep_link_url = tvpl_base
            elif source_url:
                deep_link_url = source_url

            enriched_citations.append({
                "chunk_id": cid,
                "document_title": doc_title,
                "document_number": doc_no,
                "article": str(art_num) if art_num is not None else "",
                "article_number": str(art_num) if art_num is not None else "",
                "clause": str(cl_num) if cl_num is not None else "",
                "clause_number": str(cl_num) if cl_num is not None else "",
                "point": str(pt) if pt is not None else "",
                "article_title": art_title,
                "excerpt": excerpt,
                "source_url": source_url,
                "deep_link_url": deep_link_url,
            })

        # Build Per-Finding Citations for Compound Issues
        findings_data: List[Dict[str, Any]] = []
        if val_resp.legal_findings:
            for f in val_resp.legal_findings:
                f_cites = []
                f_cids = f.supporting_chunk_ids or []
                for cid in f_cids:
                    matching_c = next((c for c in enriched_citations if c["chunk_id"] == cid), None)
                    if matching_c:
                        f_cites.append(matching_c)
                findings_data.append({
                    "issue_id": f.issue_id or "",
                    "issue": f.issue or "",
                    "text": f.finding,
                    "citations": f_cites,
                    "grounding_status": f.grounding_status,
                    "grounding_reason": f.grounding_reason or "",
                })

        # Determine out_of_scope status
        is_out_of_scope = (
            result.route_decision.strategy == "out_of_scope"
            or val_resp.abstain_reason == "Out of scope"
            or (val_resp.abstain and "ngoài phạm vi" in val_resp.final_answer.lower())
        )

        # Dynamic Suggested Follow-up Chips
        suggested_followups = (
            val_resp.clarification_options
            if (val_resp.needs_clarification and val_resp.clarification_options)
            else self._generate_followups(
                question=norm_q,
                needs_clarification=val_resp.needs_clarification,
                is_out_of_scope=is_out_of_scope,
            )
        )

        # Extract Clean Core Answer (strip redundant raw citation footers if already structured)
        clean_answer = val_resp.final_answer
        parts = re.split(r"\n\s*(?:căn cứ pháp lý|căn cứ|can cu phap ly)\s*:", clean_answer, flags=re.IGNORECASE)
        if len(parts) > 1:
            clean_answer = parts[0].strip()

        # Defensive safety net: if clean_answer still looks like raw JSON, synthesize from findings
        if clean_answer.strip().startswith("{") and (
            '"findings"' in clean_answer or '"issue"' in clean_answer or '"conclusion"' in clean_answer
        ):
            if findings_data:
                synth_parts = []
                for idx, fd in enumerate(findings_data, 1):
                    iss = fd.get("issue", "").strip()
                    txt = fd.get("text", "").strip()
                    heading = f"### {iss}" if iss else f"### Vấn đề {idx}"
                    synth_parts.append(f"{heading}\n{txt}")
                clean_answer = "\n\n".join(synth_parts)
            else:
                try:
                    re_parsed = self.chain.validator.parse_llm_json(clean_answer)
                    if re_parsed.answer and not re_parsed.answer.strip().startswith("{"):
                        clean_answer = re_parsed.answer
                except Exception:
                    pass

        # Guarantee no raw tokens like [E1], (E1) ever reach the user
        def _replace_token_with_citation(match):
            tok_num = match.group(1) or match.group(2)
            try:
                idx = int(tok_num) - 1
                if 0 <= idx < len(enriched_citations):
                    c = enriched_citations[idx]
                    art_str = f"Điều {c['article']}" if c.get('article') else ""
                    cl_str = f"Khoản {c['clause']} " if c.get('clause') else ""
                    doc_str = c.get('document_title') or "Bộ luật Lao động 2019"
                    cite_label = f"{cl_str}{art_str} {doc_str}".strip()
                    start_pos = match.start()
                    prefix_text = clean_answer[:start_pos].rstrip()
                    if not prefix_text or prefix_text.endswith(('.', '!', '?', '\n', ':', '-')):
                        return f"Theo {cite_label},"
                    return cite_label
            except Exception:
                pass
            return ""

        clean_answer = re.sub(r"\[\s*E(\d+)\s*\]|\(\s*E(\d+)\s*\)", _replace_token_with_citation, clean_answer)
        clean_answer = format_answer_markdown(clean_answer)
        for fd in findings_data:
            fd["text"] = re.sub(r"\[\s*E(\d+)\s*\]|\(\s*E(\d+)\s*\)", _replace_token_with_citation, fd.get("text", ""))
        # Phase 5H.3: CitationSanitizer - Sanitize any remaining phantom citations on UI boundary
        allowed_arts = {str(c.get("article")).strip() for c in enriched_citations if c.get("article")}
        clean_answer, _ = CitationSanitizer.sanitize(clean_answer, allowed_arts)
        for fd in findings_data:
            if fd.get("text"):
                fd["text"], _ = CitationSanitizer.sanitize(fd["text"], allowed_arts)

        return {
            "answer": clean_answer,
            "raw_answer": val_resp.raw_answer,
            "final_answer": val_resp.final_answer,
            "findings": findings_data,
            "citations": enriched_citations,
            "needs_clarification": val_resp.needs_clarification,
            "clarification_question": val_resp.clarification_question,
            "clarification_options": val_resp.clarification_options,
            "out_of_scope": is_out_of_scope,
            "suggested_followups": suggested_followups,
            "latency_ms": result.total_latency_ms,
            "locked_chunk_ids": result.locked_chunk_ids,
            "case_analysis": val_resp.case_analysis,
            "evidence_coverage": val_resp.evidence_coverage,
            "unresolved_issue_ids": val_resp.unresolved_issue_ids,
            "is_fully_grounded": val_resp.is_fully_grounded,
            "is_smalltalk": False,
            "retrieval_method": result.retrieval_method,
            "graph_expanded_chunk_ids": result.graph_expanded_chunk_ids,
        }

    def _generate_followups(
        self,
        question: str,
        needs_clarification: bool,
        is_out_of_scope: bool,
    ) -> List[str]:
        """Generates dynamic quick-reply chips tailored to conversational state."""
        q_lower = question.lower()

        if needs_clarification:
            if any(k in q_lower for k in ["thử việc", "thu viec"]):
                return [
                    "Người quản lý doanh nghiệp",
                    "Cao đẳng trở lên",
                    "Trung cấp / kỹ thuật",
                    "Công việc khác",
                    "Tôi không rõ",
                ]
            if any(k in q_lower for k in ["nghỉ việc", "báo trước", "chấm dứt", "thôi việc"]):
                return [
                    "Hợp đồng không xác định thời hạn",
                    "Hợp đồng 12 - 36 tháng",
                    "Hợp đồng dưới 12 tháng",
                    "Tổ lái tàu bay",
                    "Tôi không rõ",
                ]
            if any(k in q_lower for k in ["làm thêm", "tăng ca", "thêm giờ"]):
                return [
                    "Giới hạn trong 01 ngày",
                    "Giới hạn trong 01 tháng",
                    "Giới hạn trong 01 năm",
                    "Tôi không rõ",
                ]
            if any(k in q_lower for k in ["phép năm", "nghỉ phép", "nghi phep"]):
                return [
                    "Điều kiện làm việc bình thường",
                    "Nghề nặng nhọc, độc hại",
                    "Nghề đặc biệt nặng nhọc, độc hại",
                    "Tôi không rõ",
                ]
            return [
                "Tôi không rõ",
                "Hợp đồng xác định thời hạn",
                "Hợp đồng không xác định thời hạn",
            ]

        if is_out_of_scope:
            return [
                "Thử việc tối đa bao nhiêu ngày?",
                "Thời hạn báo trước khi nghỉ việc",
                "Làm thêm ngày lễ được tính lương thế nào?",
                "Các hình thức xử lý kỷ luật lao động",
            ]

        # Contextual related questions for regular answers
        if any(k in q_lower for k in ["nguyên tắc giao kết", "nguyên tắc nền tảng khi giao kết", "giao kết hđlđ dựa trên"]):
            return [
                "Người sử dụng lao động phải cung cấp những thông tin gì?",
                "Người lao động phải cung cấp những thông tin gì?",
                "Hành vi nào bị cấm khi giao kết HĐLĐ?",
            ]
        if any(k in q_lower for k in ["đi làm trước", "vào làm trước", "làm chính thức rồi", "mới ký hđlđ", "chưa ký hợp đồng", "chưa có hợp đồng", "hẹn ký sau", "ký hợp đồng sau"]):
            return [
                "Không ký hợp đồng bằng văn bản bị xử phạt thế nào?",
                "Quyền lợi những ngày làm trước khi ký được tính ra sao?",
                "Hợp đồng dưới 01 tháng có cần lập thành văn bản không?",
            ]
        if any(k in q_lower for k in ["sếp đấm", "sếp đánh", "sếp tát", "hành hung", "đánh đập", "ngược đãi"]):
            return [
                "Tôi cần thu thập chứng cứ gì?",
                "Tôi có được nghỉ việc ngay không cần báo trước?",
                "Khi nào tôi nên trình báo Công an?",
            ]
        if any(k in q_lower for k in ["thỏa thuận công việc", "thoả thuận công việc", "không phải hợp đồng lao động", "giữ giấy tờ", "giấy tờ tùy thân"]):
            return [
                "Thủ tục yêu cầu hòa giải tranh chấp tiền công?",
                "Thời hiệu khởi kiện tranh chấp lao động là bao lâu?",
                "Mức phạt khi giữ giấy tờ tùy thân của người lao động?",
            ]
        if any(k in q_lower for k in ["thử việc"]):
            return [
                "Tiền lương trong thời gian thử việc?",
                "Kết thúc thử việc không báo thì sao?",
                "Có được thử việc 2 lần không?",
            ]
        if any(k in q_lower for k in ["nghỉ việc", "báo trước"]):
            return [
                "Trường hợp nào nghỉ việc không cần báo trước?",
                "Bao lâu sau khi nghỉ việc thì công ty phải thanh toán tiền?",
                "Chưa nghỉ hết phép năm có được thanh toán tiền không?",
            ]
        if any(k in q_lower for k in ["làm thêm giờ", "làm thêm ngày", "lương làm thêm", "tiền lương làm thêm", "tăng ca", "làm ngoài giờ"]):
            return [
                "Làm việc vào ban đêm được trả thêm bao nhiêu %?",
                "Làm thêm ngày lễ được trả bao nhiêu % lương?",
                "Công ty có được ép làm thêm giờ không?",
            ]

        return [
            "Thời gian thử việc tối đa?",
            "Thời hạn báo trước khi nghỉ việc?",
            "Quy định về ngày nghỉ phép năm?",
        ]
