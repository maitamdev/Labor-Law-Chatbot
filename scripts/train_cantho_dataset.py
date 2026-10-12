# -*- coding: utf-8 -*-
"""
Script to generate ChatML training data and statutory question anchors
for all 106 legal situations from Can Tho PBGDPL:
https://pbgdpl.cantho.gov.vn/bo-cau-hoi-tinh-huong-va-giai-dap-phap-luat-ve-bo-luat-lao-dong-nam-2019
"""
import json
import logging
import os
import re
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cantho_trainer")

PROCESSED_JSON = r"d:\chatbot-law\data\processed\cantho_legal_situations.json"
CANTHO_CHATML = r"d:\chatbot-law\data\training\vietlabor_cantho_qa_chatml.jsonl"
MASTER_CHATML = r"d:\chatbot-law\data\training\vietlabor_sft_1000_chatml.jsonl"
QUESTION_ANCHORS = r"d:\chatbot-law\data\processed\qa_question_anchors.jsonl"

SYSTEM_PROMPT = (
    "Bạn là chuyên gia tư vấn pháp luật lao động Việt Nam, luôn cung cấp câu trả lời "
    "chính xác, viện dẫn căn cứ pháp lý rõ ràng (Bộ luật Lao động 2019, các Nghị định và Thông tư hướng dẫn), "
    "giải thích thấu đáo và đưa ra giải pháp bảo vệ quyền lợi hợp pháp của các bên."
)

DOC_MAPPING = {
    "Văn bản hợp nhất 18/VBHN-VPQH": "VBHN_18_2026",
    "Bộ luật Lao động 2019": "VBHN_18_2026",
    "BLLĐ": "VBHN_18_2026",
    "Nghị định 145/2020": "ND_145_2020",
    "Nghị định 12/2022": "ND_12_2022",
    "Luật Bảo hiểm xã hội": "VBHN_58_2025",
    "Luật BHXH": "VBHN_58_2025",
    "Luật An toàn, vệ sinh lao động": "L_84_2015",
    "Luật ATVSLĐ": "L_84_2015",
}


def build_chatml_and_anchors():
    with open(PROCESSED_JSON, "r", encoding="utf-8") as f:
        situations = json.load(f)

    logger.info("Loaded %d situations from %s", len(situations), PROCESSED_JSON)

    chatml_records = []
    new_anchors = []
    anchor_id_start = 9101

    for sit in situations:
        num = sit["number"]
        q_text = sit["question"].strip()
        ans_text = sit["answer"].strip()
        articles = sit.get("articles", [])

        # Clean answer to make it structured
        # Format citation block if not already formatted
        art_mention = ", ".join(articles) if articles else "Bộ luật Lao động 2019"
        
        chatml_ans = ans_text
        if "CĂN CỨ PHÁP LÝ:" not in chatml_ans and "Căn cứ pháp lý:" not in chatml_ans:
            chatml_ans += f"\n\n**Căn cứ pháp lý:**\n- {art_mention}, Bộ luật Lao động 2019."

        rec = {
            "id": f"cantho_sit_{num:03d}",
            "source": "pbgdpl.cantho.gov.vn",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": q_text},
                {"role": "assistant", "content": chatml_ans}
            ],
            "metadata": {
                "situation_number": num,
                "domain": "labor_law",
                "articles": articles,
                "source_url": sit.get("source_url")
            }
        }
        chatml_records.append(rec)

        # Question anchors extraction
        # Determine all cited articles
        law_anchors_list = []
        for a in articles:
            m = re.search(r"\d+[a-z]?", a, re.IGNORECASE)
            if m:
                art_val = m.group(0).lower()
                law_anchors_list.append({"doc_id": "VBHN_18_2026", "article_number": art_val})
        
        if not law_anchors_list:
            law_anchors_list = [{"doc_id": "VBHN_18_2026", "article_number": "5"}]

        primary_art = law_anchors_list[0]["article_number"]
        chunk_id = f"BL#d{primary_art}-k1"

        # 1. Add the full exact question as an anchor
        new_anchors.append({
            "sheet_row": anchor_id_start,
            "question": q_text,
            "law_anchors": law_anchors_list,
            "reviewed_chunk_ids": [chunk_id],
            "source_situation": f"cantho_sit_{num:03d}"
        })
        anchor_id_start += 1

        # 2. Add atomic sub-questions if available
        sub_questions = [p.strip() for p in re.split(r"[\?\n]+", q_text) if len(p.strip()) >= 20]
        for sq in sub_questions:
            sq_clean = sq + ("?" if not sq.endswith("?") else "")
            if sq_clean != q_text:
                new_anchors.append({
                    "sheet_row": anchor_id_start,
                    "question": sq_clean,
                    "law_anchors": law_anchors_list,
                    "reviewed_chunk_ids": [chunk_id],
                    "source_situation": f"cantho_sit_{num:03d}"
                })
                anchor_id_start += 1

    # 1. Save Can Tho ChatML file
    os.makedirs(os.path.dirname(CANTHO_CHATML), exist_ok=True)
    with open(CANTHO_CHATML, "w", encoding="utf-8") as f:
        for r in chatml_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info("Saved %d ChatML records to %s", len(chatml_records), CANTHO_CHATML)

    # 2. Merge into master SFT dataset (avoiding duplicates)
    existing_ids = set()
    existing_lines = []
    if os.path.exists(MASTER_CHATML):
        with open(MASTER_CHATML, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        obj = json.loads(line_str)
                        existing_ids.add(obj.get("id"))
                        existing_lines.append(line_str)
                    except Exception:
                        existing_lines.append(line_str)

    added_count = 0
    for r in chatml_records:
        if r["id"] not in existing_ids:
            existing_lines.append(json.dumps(r, ensure_ascii=False))
            existing_ids.add(r["id"])
            added_count += 1

    with open(MASTER_CHATML, "w", encoding="utf-8") as f:
        for l in existing_lines:
            f.write(l + "\n")
    logger.info("Master SFT dataset updated: added %d records, total now %d records.", added_count, len(existing_lines))

    # 3. Append to question anchors
    existing_anchors = []
    existing_q_anchors = set()
    if os.path.exists(QUESTION_ANCHORS):
        with open(QUESTION_ANCHORS, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        obj = json.loads(line_str)
                        existing_anchors.append(obj)
                        existing_q_anchors.add(obj.get("question", "").lower().strip())
                    except Exception:
                        pass

    anchors_added = 0
    for anc in new_anchors:
        q_norm = anc["question"].lower().strip()
        if q_norm not in existing_q_anchors:
            existing_anchors.append(anc)
            existing_q_anchors.add(q_norm)
            anchors_added += 1

    with open(QUESTION_ANCHORS, "w", encoding="utf-8") as f:
        for anc in existing_anchors:
            f.write(json.dumps(anc, ensure_ascii=False) + "\n")
    logger.info("Question anchors updated: added %d new anchors, total now %d anchors.", anchors_added, len(existing_anchors))

    print(f"\nTraining pipeline completed successfully:")
    print(f"- Can Tho ChatML: {len(chatml_records)} records -> {CANTHO_CHATML}")
    print(f"- Master SFT ChatML: {len(existing_lines)} total records -> {MASTER_CHATML}")
    print(f"- Question Anchors: {len(existing_anchors)} total anchors -> {QUESTION_ANCHORS}")


if __name__ == "__main__":
    build_chatml_and_anchors()
