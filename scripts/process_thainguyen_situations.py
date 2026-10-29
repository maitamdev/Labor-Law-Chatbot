# -*- coding: utf-8 -*-
"""
VietLabor AI - Process & Ingest Thai Nguyen PBGDPL Legal Situations
Scrapes 12 official labor law situations from:
https://pbgdplthainguyen.gov.vn/de-cuong-tuyen-truyen/mot-so-tinh-huong-phap-luat-ve-linh-vuc-lao-dong-646.html
Converts them into ChatML training dataset, QA question anchors, and UI situations.
"""
import json
import re
import ssl
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
URL = "https://pbgdplthainguyen.gov.vn/de-cuong-tuyen-truyen/mot-so-tinh-huong-phap-luat-ve-linh-vuc-lao-dong-646.html"

SYSTEM_PROMPT = (
    "Bạn là VietLabor AI - Trợ lý pháp lý chuyên sâu về pháp luật lao động Việt Nam. "
    "Hãy giải đáp câu hỏi của người dùng một cách chính xác, mạch lạc và luôn viện dẫn "
    "cụ thể căn cứ pháp luật (Điều, Khoản, Điểm của Bộ luật Lao động, Luật BHXH, Luật ATVSLĐ "
    "hoặc các Nghị định, Thông tư hướng dẫn thi hành liên quan)."
)

SITUATION_METADATA = {
    1: {
        "title": "Người lao động từ chối làm việc khi nguy cơ sạt lở đe dọa tính mạng",
        "tag": "An toàn lao động",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "5"}, {"doc_id": "L_84_2015", "article_number": "16"}],
        "summary_law": "Điểm d Khoản 1 Điều 5 BLLĐ 2019 và Điều 16 Luật ATVSLĐ: NLĐ có quyền từ chối làm việc khi có nguy cơ rõ ràng đe dọa tính mạng. NSDLĐ khiển trách, cắt thưởng là trái luật."
    },
    2: {
        "title": "Trách nhiệm đào tạo, bồi dưỡng nâng cao tay nghề cho người lao động",
        "tag": "Đào tạo nghề",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "60"}, {"doc_id": "VBHN_18_2026", "article_number": "6"}],
        "summary_law": "Điều 6, Điều 60, Điều 61, Điều 62 BLLĐ 2019: NSDLĐ có nghĩa vụ lập kế hoạch, bố trí kinh phí đào tạo, bồi dưỡng kỹ năng nghề và thông báo kết quả cho cơ quan chuyên môn cấp tỉnh."
    },
    3: {
        "title": "Doanh nghiệp không đóng bảo hiểm và giữ sổ BHXH của người lao động",
        "tag": "Bảo hiểm xã hội",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "168"}, {"doc_id": "VBHN_18_2026", "article_number": "48"}],
        "summary_law": "Điều 168 BLLĐ 2019, Điều 21 Luật BHXH: NSDLĐ phải đóng BHXH bắt buộc và hoàn thành thủ tục xác nhận, trả lại sổ BHXH cho NLĐ khi thôi việc; vi phạm bị xử phạt theo NĐ 12/2022/NĐ-CP."
    },
    4: {
        "title": "Làm việc lâu năm nhưng chỉ thỏa thuận miệng, không ký hợp đồng văn bản",
        "tag": "Hợp đồng lao động",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "13"}, {"doc_id": "VBHN_18_2026", "article_number": "14"}],
        "summary_law": "Điều 13, Điều 14 BLLĐ 2019: Công việc từ 01 tháng trở lên bắt buộc phải giao kết bằng văn bản; thỏa thuận có trả lương và chịu sự quản lý là quan hệ lao động được pháp luật bảo vệ."
    },
    5: {
        "title": "Công ty nợ lương, chậm trả lương liên tục nhiều tháng",
        "tag": "Tiền lương",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "97"}, {"doc_id": "VBHN_18_2026", "article_number": "35"}],
        "summary_law": "Điều 97 BLLĐ 2019 quy định kỳ hạn trả lương. Chậm trả lương không đúng hạn cho phép NLĐ đơn phương chấm dứt HĐLĐ không cần báo trước (Điểm b Khoản 2 Điều 35) và khiếu nại theo NĐ 24/2018."
    },
    6: {
        "title": "Sử dụng lao động chưa đủ 15 tuổi làm thêm giờ và ban đêm",
        "tag": "Lao động chưa thành niên",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "143"}, {"doc_id": "VBHN_18_2026", "article_number": "145"}],
        "summary_law": "Điều 143, Điều 145, Điều 146 BLLĐ 2019: Người chưa đủ 15 tuổi chỉ làm tối đa 4 giờ/ngày, 20 giờ/tuần; tuyệt đối không được làm thêm giờ hoặc làm việc ban đêm; vi phạm bị phạt theo NĐ 12/2022."
    },
    7: {
        "title": "Khai man văn bằng và trách nhiệm bồi thường khi chấm dứt HĐLĐ",
        "tag": "Nghĩa vụ cung cấp thông tin",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "16"}, {"doc_id": "VBHN_18_2026", "article_number": "36"}],
        "summary_law": "Điều 16 BLLĐ 2019: NLĐ phải cung cấp thông tin trung thực về học vấn. Cung cấp bằng giả cho phép NSDLĐ đơn phương chấm dứt HĐLĐ (Điểm g Khoản 1 Điều 36) và NLĐ không được trợ cấp thôi việc."
    },
    8: {
        "title": "Chấm dứt HĐLĐ khi công ty không bố trí đúng công việc và địa điểm",
        "tag": "Đơn phương chấm dứt HĐLĐ",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "35"}, {"doc_id": "VBHN_18_2026", "article_number": "29"}],
        "summary_law": "Điểm a Khoản 2 Điều 35 BLLĐ 2019: Không được bố trí đúng công việc, địa điểm làm việc đã thỏa thuận thì NLĐ có quyền nghỉ việc ngay không cần báo trước, không bị coi là đơn phương trái luật."
    },
    9: {
        "title": "Lao động nữ đi làm sớm trước khi hết thời gian nghỉ thai sản",
        "tag": "Chế độ thai sản",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "139"}, {"doc_id": "VBHN_18_2026", "article_number": "140"}],
        "summary_law": "Khoản 4 Điều 139 BLLĐ 2019 và Điều 40 Luật BHXH 2014: Sau khi nghỉ ít nhất 4 tháng và có xác nhận y tế, NLĐ đi làm sớm vẫn được hưởng nguyên tiền lương và trọn vẹn trợ cấp thai sản."
    },
    10: {
        "title": "Sử dụng lao động 16 tuổi làm công việc nặng nhọc tại công trường",
        "tag": "Lao động chưa thành niên",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "147"}, {"doc_id": "VBHN_18_2026", "article_number": "144"}],
        "summary_law": "Điều 147 BLLĐ 2019 và Thông tư 09/2020/TT-BLĐTBXH: Nghiêm cấm bố trí người từ đủ 15 đến dưới 18 tuổi làm việc tại công trường xây dựng hoặc công việc nặng nhọc, nguy hiểm danh mục cấm."
    },
    11: {
        "title": "Sinh viên làm việc bán thời gian: Bản chất quan hệ lao động và quyền lợi",
        "tag": "Lao động bán thời gian",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "32"}, {"doc_id": "VBHN_18_2026", "article_number": "13"}],
        "summary_law": "Điều 13, Điều 32 BLLĐ 2019: Làm việc không trọn thời gian vẫn là HĐLĐ đầy đủ quyền lợi (lương, bảo hộ, an toàn), hưởng quyền bình đẳng như người làm việc trọn thời gian."
    },
    12: {
        "title": "Thời hiệu xử lý kỷ luật lao động và bồi thường thiệt hại tài sản",
        "tag": "Kỷ luật lao động",
        "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "123"}, {"doc_id": "VBHN_18_2026", "article_number": "129"}],
        "summary_law": "Điều 123 BLLĐ 2019: Thời hiệu xử lý kỷ luật thông thường là 06 tháng. Quá thời hiệu công ty không được ra quyết định kỷ luật; việc bồi thường thiệt hại xử lý theo Điều 129 và quy trình luật định."
    }
}


def clean_text(text: str) -> str:
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def scrape_situations():
    print(f"1. Dang tai noi dung tu {URL}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("div", id="news-bodyhtml")
    if not body:
        raise ValueError("Khong tim thay the div id='news-bodyhtml'")

    raw_text = body.get_text()
    pattern = re.compile(r'Tình huống số\s+(\d+)\s*:(.*?)(?=(?:Tình huống số\s+\d+\s*:|Tác giả bài viết|$))', re.DOTALL)
    matches = pattern.findall(raw_text)
    print(f"2. Da boc tach thanh cong {len(matches)} tinh huong phap ly.")

    parsed_situations = []
    for num_str, content in matches:
        num = int(num_str)
        content = clean_text(content)

        # Split Fact, Hoi, Tra loi
        hoi_split = re.split(r'\n\s*(?:Hỏi\s*:|Câu hỏi\s*:)', content, maxsplit=1)
        fact = clean_text(hoi_split[0]) if len(hoi_split) > 1 else ""
        rest = clean_text(hoi_split[1]) if len(hoi_split) > 1 else content

        tl_split = re.split(r'\n\s*(?:Trả lời\s*:|Đáp\s*:)', rest, maxsplit=1)
        hoi = clean_text(tl_split[0]) if len(tl_split) > 1 else ""
        tra_loi = clean_text(tl_split[1]) if len(tl_split) > 1 else rest

        meta = SITUATION_METADATA.get(num, {
            "title": f"Tình huống pháp luật lao động số {num}",
            "tag": "Pháp luật lao động",
            "law_anchors": [{"doc_id": "VBHN_18_2026", "article_number": "5"}],
            "summary_law": "Quy định theo Bộ luật Lao động 2019."
        })

        parsed_situations.append({
            "number": num,
            "title": meta["title"],
            "tag": meta["tag"],
            "law_anchors": meta["law_anchors"],
            "summary_law": meta["summary_law"],
            "fact": fact,
            "question": hoi,
            "raw_answer": tra_loi,
        })
    return parsed_situations


def create_chatml_record(s: dict) -> dict:
    fact = s["fact"]
    q = s["question"]
    raw_ans = s["raw_answer"]
    title = s["title"]
    tag = s["tag"]

    user_prompt = (
        f"**Tình huống thực tế:**\n{fact}\n\n"
        f"**Câu hỏi:** {q}"
    )

    # Format authoritative advisory response matching VietLabor AI standards
    assistant_reply = (
        f"Chào bạn, liên quan đến tình huống **{title}** ({tag}), VietLabor AI xin tư vấn căn cứ theo pháp luật lao động hiện hành như sau:\n\n"
        f"### 1. Kết luận và Căn cứ pháp lý trực tiếp\n"
        f"{s['summary_law']}\n\n"
        f"### 2. Phân tích chi tiết quy định pháp luật\n"
        f"{raw_ans}\n\n"
        f"### 3. Khuyến nghị thực hiện\n"
        f"- Người lao động và người sử dụng lao động cần đối chiếu đúng các quy định trên để bảo đảm quyền và lợi ích hợp pháp của mình.\n"
        f"- Trường hợp có tranh chấp phát sinh không thể thương lượng hòa giải, các bên có quyền gửi đơn khiếu nại đến Chánh Thanh tra Sở Lao động - Thương binh và Xã hội hoặc khởi kiện tại Tòa án nhân dân có thẩm quyền."
    )

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_reply}
        ]
    }


def main():
    situations = scrape_situations()
    if not situations:
        print("Khong co du lieu tinh huong.")
        return

    # 1. Save processed JSON
    processed_json_path = PROJECT_ROOT / "data" / "processed" / "thainguyen_legal_situations.json"
    with open(processed_json_path, "w", encoding="utf-8") as f:
        json.dump(situations, f, ensure_ascii=False, indent=2)
    print(f"3. Da luu danh sach 12 tinh huong vao: {processed_json_path}")

    # 2. Generate ChatML training file
    training_file = PROJECT_ROOT / "data" / "training" / "vietlabor_thainguyen_situations_chatml.jsonl"
    chatml_records = [create_chatml_record(s) for s in situations]

    with open(training_file, "w", encoding="utf-8") as f:
        for rec in chatml_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"4. Da tao file training ChatML ({len(chatml_records)} records): {training_file}")

    # 3. Append to main dataset if not already present
    main_training_file = PROJECT_ROOT / "data" / "training" / "vietlabor_sft_1000_chatml.jsonl"
    if main_training_file.exists():
        existing_lines = [line for line in main_training_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        existing_count = len(existing_lines)

        # Check if already appended
        is_already_appended = any("Lò Văn Dũng" in line for line in existing_lines)
        if not is_already_appended:
            with open(main_training_file, "a", encoding="utf-8") as f:
                for rec in chatml_records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"5. Da sap nhap 12 tinh huong vao tap du lieu chinh: {main_training_file} (Tong: {existing_count + len(chatml_records)} records).")
        else:
            print(f"5. Du lieu da duoc sap nhap truoc do trong {main_training_file}.")

    # 4. Integrate into qa_question_anchors.jsonl
    anchor_file = PROJECT_ROOT / "data" / "processed" / "qa_question_anchors.jsonl"
    if anchor_file.exists():
        existing_anchors = [json.loads(line) for line in anchor_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        # Cleanly re-populate Thai Nguyen anchors (sheet_row >= 9000)
        existing_anchors = [a for a in existing_anchors if a.get("sheet_row", 0) < 9000]
        anchors_added = 0
        existing_q_texts = {a["question"] for a in existing_anchors}

        row_id = 9001
        for s in situations:
            raw_q = s["question"]
            # Split into distinct sentences / sub-questions
            sub_qs = [part.strip() for part in re.split(r'[\?\n]+', raw_q) if len(part.strip()) >= 15]
            for sub_q in sub_qs:
                q_text = sub_q if sub_q.endswith("?") else sub_q + "?"
                if q_text not in existing_q_texts:
                    existing_anchors.append({
                        "sheet_row": row_id,
                        "question": q_text,
                        "law_anchors": s["law_anchors"],
                        "reviewed_chunk_ids": []
                    })
                    existing_q_texts.add(q_text)
                    anchors_added += 1
                    row_id += 1

        with open(anchor_file, "w", encoding="utf-8") as f:
            for a in existing_anchors:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        print(f"6. Da cap nhat {anchors_added} question anchors vao: {anchor_file}")

    print("=== HOAN TAT INTEGRATION TOAN BO 12 TINH HUONG THAI NGUYEN ===")


if __name__ == "__main__":
    main()
