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

from rag.chain import VietLaborRAGChain, ChainExecutionResult
from rag.output_validator import format_answer_markdown

logger = logging.getLogger(__name__)

# Canonical Official Document URLs for Vietnam Labor Law
OFFICIAL_DOC_URLS = {
    "VBHN_18_2026": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx",
    "18/VBHN-VPQH": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx",
    "45/2019/QH14": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx",
    "ND_145_2020": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-460987.aspx",
    "145/2020/NĐ-CP": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-460987.aspx",
    "ND_12_2022": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx",
    "12/2022/NĐ-CP": "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-12-2022-ND-CP-xu-phat-vi-pham-hanh-chinh-linh-vuc-lao-dong-bao-hiem-xa-hoi-500735.aspx",
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
}


class ChatService:
    """Thin adapter providing structured UI responses from the RAG backend."""

    def __init__(self, chain: Optional[VietLaborRAGChain] = None):
        self.chain = chain or VietLaborRAGChain()

    def reset_conversation(self) -> None:
        """Clears conversational working memory for a new session."""
        self.chain.memory.clear()

    def ask(self, question: str, update_memory: bool = True) -> Dict[str, Any]:
        """Executes RAG inference and maps output to clean UI response schema."""
        norm_q = unicodedata.normalize("NFC", question).strip()
        result: ChainExecutionResult = self.chain.run(norm_q, update_memory=update_memory)

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

            source_url = meta.get("source_url") or OFFICIAL_DOC_URLS.get(doc_id) or OFFICIAL_DOC_URLS.get(doc_no) or ""

            enriched_citations.append({
                "chunk_id": cid,
                "document_title": doc_title,
                "document_number": doc_no,
                "article": str(art_num) if art_num is not None else "",
                "clause": str(cl_num) if cl_num is not None else "",
                "point": str(pt) if pt is not None else "",
                "article_title": art_title,
                "excerpt": excerpt,
                "source_url": source_url,
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
                    "issue": f.issue or "",
                    "text": f.finding,
                    "citations": f_cites,
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
                    return f"{cl_str}{art_str} {doc_str}".strip()
            except Exception:
                pass
            return ""

        clean_answer = re.sub(r"\[\s*E(\d+)\s*\]|\(\s*E(\d+)\s*\)", _replace_token_with_citation, clean_answer)
        clean_answer = format_answer_markdown(clean_answer)
        for fd in findings_data:
            fd["text"] = re.sub(r"\[\s*E(\d+)\s*\]|\(\s*E(\d+)\s*\)", _replace_token_with_citation, fd.get("text", ""))
            fd["text"] = format_answer_markdown(fd.get("text", ""))

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
        if any(k in q_lower for k in ["làm thêm", "tăng ca"]):
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
