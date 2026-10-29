# -*- coding: utf-8 -*-
"""
Script to parse, evaluate and train 106 legal situations from Can Tho PBGDPL:
https://pbgdpl.cantho.gov.vn/bo-cau-hoi-tinh-huong-va-giai-dap-phap-luat-ve-bo-luat-lao-dong-nam-2019
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cantho_processor")

HTML_PATH = r"C:\Users\Asus\.gemini\antigravity-ide\brain\b210a86a-ad54-4940-895d-baf83c462509\.system_generated\steps\1005\content.md"
OUTPUT_JSON = r"d:\chatbot-law\data\processed\cantho_legal_situations.json"
OUTPUT_CHATML = r"d:\chatbot-law\data\training\vietlabor_cantho_qa_chatml.jsonl"
MASTER_CHATML = r"d:\chatbot-law\data\training\vietlabor_sft_1000_chatml.jsonl"
QUESTION_ANCHORS = r"d:\chatbot-law\data\processed\qa_question_anchors.jsonl"


def extract_articles(text: str) -> List[str]:
    """Finds referenced articles like Điều 5, Điều 13, Điều 112."""
    matches = re.findall(r"Điều\s+(\d+[a-z]?)", text, re.IGNORECASE)
    seen = set()
    res = []
    for m in matches:
        art = f"Điều {m}"
        if art not in seen:
            seen.add(art)
            res.append(art)
    return res


def parse_cantho_situations(html_path: str = HTML_PATH) -> List[Dict[str, Any]]:
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    content_div = soup.find("div", class_="entry-content")
    if not content_div:
        raise ValueError("Could not find div.entry-content in HTML")

    paragraphs = [p.get_text().strip() for p in content_div.find_all("p") if p.get_text().strip()]

    q_pattern = re.compile(r"^(Câu\s*hỏi|Câu)\s*(\d+)[:.]\s*(.*)", re.DOTALL | re.IGNORECASE)

    situations: List[Dict[str, Any]] = []
    current_q: Optional[Dict[str, Any]] = None
    current_a_lines: List[str] = []

    for p in paragraphs:
        m = q_pattern.match(p)
        if m:
            if current_q:
                current_q["answer"] = "\n\n".join(current_a_lines).strip()
                current_q["articles"] = extract_articles(current_q["answer"])
                situations.append(current_q)
            q_num = int(m.group(2))
            q_text = m.group(3).strip()
            current_q = {
                "number": q_num,
                "title": f"Tình huống {q_num}: {q_text[:70]}...",
                "question": q_text,
                "answer": "",
                "source": "Cổng thông tin PBGDPL TP. Cần Thơ",
                "source_url": "https://pbgdpl.cantho.gov.vn/bo-cau-hoi-tinh-huong-va-giai-dap-phap-luat-ve-bo-luat-lao-dong-nam-2019",
            }
            current_a_lines = []
        else:
            if current_q is not None:
                cleaned = re.sub(r"^\s*Trả lời\s*[:.]\s*", "", p, flags=re.IGNORECASE).strip()
                if cleaned:
                    current_a_lines.append(cleaned)

    if current_q:
        current_q["answer"] = "\n\n".join(current_a_lines).strip()
        current_q["articles"] = extract_articles(current_q["answer"])
        situations.append(current_q)

    logger.info("Successfully parsed %d situations from Can Tho document.", len(situations))
    return situations


if __name__ == "__main__":
    situations = parse_cantho_situations()
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(situations, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(situations)} situations to {OUTPUT_JSON}")
    for s in situations[:3]:
        print(f"[{s['number']}] {s['question'][:80]}")
        print(f"Articles: {s['articles']}")
        print(f"Answer: {s['answer'][:100]}...\n")
