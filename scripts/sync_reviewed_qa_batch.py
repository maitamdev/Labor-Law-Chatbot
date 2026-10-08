"""Sync the 2026-09-24 verified Sheet corrections into the chatbot RAG data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/evaluation/labor_qa_sheet_snapshot.jsonl"
CORRECTED = ROOT / "data/evaluation/labor_qa_corrected.jsonl"
ANCHORS = ROOT / "data/processed/qa_question_anchors.jsonl"
CORPUS = ROOT / "data/processed/legal_documents_v3.jsonl"

NQ_SOURCE = "https://vanban.chinhphu.vn/?classid=509&docid=218181&pageid=27160"
LAW84_SOURCE = "https://congbao.chinhphu.vn/van-ban/luat-so-84-2015-qh13-15356.htm"
ND44_SOURCE = "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-44-2016-nd-cp-19916.htm"
ND140_SOURCE = "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-140-2018-nd-cp-27432.htm"
ND44_CONSOLIDATED_SOURCE = (
    "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-2279-vbhn-bldtbxh-39619/45466.htm"
)

INSPECTION_ANSWER = (
    "Có. Tổ chức muốn hoạt động kiểm định kỹ thuật an toàn lao động phải được cấp "
    "Giấy chứng nhận đủ điều kiện hoạt động kiểm định. Theo Điều 4 Nghị định "
    "44/2016/NĐ-CP, được sửa đổi bởi khoản 1 Điều 1 Nghị định 140/2018/NĐ-CP, "
    "tổ chức phải: (1) bảo đảm thiết bị, dụng cụ kiểm định cho từng đối tượng theo "
    "quy trình kiểm định và quy chuẩn kỹ thuật quốc gia; (2) có ít nhất 02 kiểm định "
    "viên làm việc theo hợp đồng từ 12 tháng trở lên thuộc tổ chức để kiểm định mỗi "
    "đối tượng trong phạm vi đề nghị; và (3) có người phụ trách kỹ thuật hoạt động "
    "kiểm định đã làm kiểm định viên tối thiểu 02 năm."
)
INSPECTION_SOURCE = (
    "Khoản 1 Điều 32 — Luật An toàn, vệ sinh lao động số 84/2015/QH13; Điều 4 — "
    "Nghị định 44/2016/NĐ-CP, được sửa đổi bởi khoản 1 Điều 1 Nghị định 140/2018/NĐ-CP."
    f"\n{LAW84_SOURCE}\n{ND44_SOURCE}\n{ND140_SOURCE}"
)

UPDATES: dict[int, dict[str, str]] = {
    566: {
        "question": (
            "Trong thời gian từ ngày 01/07/2026 đến hết ngày 28/02/2027, doanh nghiệp "
            "muốn hoạt động dịch vụ việc làm có phải thực hiện thủ tục xin cấp giấy phép không?"
        ),
        "answer": (
            "Trong giai đoạn 01/07/2026–28/02/2027, theo Phụ lục I.4 lĩnh vực việc làm "
            "của Nghị quyết 66.18/2026/NQ-CP, không thực hiện thủ tục cấp giấy phép hoạt "
            "động dịch vụ việc làm. Vì vậy, không áp dụng quy trình cấp giấy phép thông "
            "thường trong giai đoạn này; đây là cơ chế tạm thời, không phải bãi bỏ vĩnh "
            "viễn. Doanh nghiệp vẫn phải tuân thủ các nghĩa vụ về hoạt động và quản lý "
            "dịch vụ việc làm không bị Nghị quyết cắt giảm."
        ),
        "source": (
            "Phụ lục I.4, lĩnh vực việc làm — Nghị quyết số 66.18/2026/NQ-CP "
            "(áp dụng từ 01/07/2026 đến hết 28/02/2027)\n" + NQ_SOURCE
        ),
    },
    567: {
        "question": (
            "Giấy phép hoạt động dịch vụ việc làm được cấp trước ngày 01/07/2026 và còn "
            "thời hạn có tiếp tục được sử dụng không? Trong giai đoạn 01/07/2026–28/02/2027 "
            "có thực hiện thủ tục gia hạn không?"
        ),
        "answer": (
            "Giấy phép đã được cấp trước ngày Nghị quyết 66.18/2026/NQ-CP có hiệu lực mà "
            "chưa hết hạn tiếp tục được sử dụng đến hết thời hạn ghi trên giấy phép. Trong "
            "giai đoạn 01/07/2026–28/02/2027 không thực hiện thủ tục gia hạn giấy phép hoạt "
            "động dịch vụ việc làm. Đây là cơ chế tạm thời; cần đối chiếu văn bản mới nếu "
            "được ban hành và có hiệu lực sớm hơn."
        ),
        "source": (
            "Phụ lục I.4, lĩnh vực việc làm; quy định chuyển tiếp — Nghị quyết số "
            "66.18/2026/NQ-CP\n" + NQ_SOURCE
        ),
    },
    792: {
        "source": (
            "Điều 32 Luật An toàn, vệ sinh lao động số 84/2015/QH13; Điều 4–8 Nghị định "
            "44/2016/NĐ-CP, trong đó Điều 4 được sửa đổi bởi khoản 1 Điều 1 Nghị định "
            f"140/2018/NĐ-CP.\n{LAW84_SOURCE}\n{ND44_SOURCE}\n{ND140_SOURCE}"
        ),
    },
    898: {"answer": INSPECTION_ANSWER, "source": INSPECTION_SOURCE},
    903: {"answer": INSPECTION_ANSWER, "source": INSPECTION_SOURCE},
}

NQ_CHUNK_ID = "NQ_66_18_2026#pl-i4-vieclam"
NQ_CONTENT = (
    "Phụ lục I.4 — D. Lĩnh vực việc làm. Không thực hiện quy định tại khoản 5 Điều 28 "
    "Luật Việc làm số 74/2025/QH15 liên quan đến mẫu giấy phép, hồ sơ, trình tự, thủ tục "
    "cấp, cấp lại, gia hạn, thu hồi giấy phép hoạt động dịch vụ việc làm. Trong thời gian "
    "áp dụng, không thực hiện các thủ tục cấp mới, cấp lại, gia hạn, thu hồi giấy phép "
    "hoạt động dịch vụ việc làm. Quy định chuyển tiếp: văn bản, giấy tờ đã được cơ quan, "
    "người có thẩm quyền ban hành, cấp trước ngày Nghị quyết có hiệu lực mà chưa hết hiệu "
    "lực hoặc chưa hết thời hạn sử dụng tiếp tục được áp dụng, sử dụng theo pháp luật đến "
    "hết thời hạn. Nội dung này áp dụng từ 01/07/2026 đến hết 28/02/2027; cơ chế có tính "
    "tạm thời và không tự bãi bỏ các nghĩa vụ hoạt động, quản lý khác không thuộc nội dung "
    "được cắt giảm."
)

ND44_TEXT = {
    "ND_44_2016#d4-k1": (
        "1. Tổ chức được cấp Giấy chứng nhận đủ điều kiện hoạt động kiểm định kỹ thuật an "
        "toàn lao động phải đáp ứng đủ các điều kiện sau đây:"
    ),
    "ND_44_2016#d4-k1-a": (
        "a) Bảo đảm thiết bị, dụng cụ phục vụ kiểm định cho từng đối tượng thuộc phạm vi "
        "kiểm định, theo yêu cầu tại quy trình kiểm định, quy chuẩn kỹ thuật quốc gia về "
        "an toàn, vệ sinh lao động."
    ),
    "ND_44_2016#d4-k1-b": (
        "b) Có ít nhất 02 kiểm định viên làm việc theo hợp đồng từ 12 tháng trở lên thuộc "
        "tổ chức để thực hiện kiểm định đối với mỗi đối tượng thuộc phạm vi đề nghị cấp "
        "Giấy chứng nhận đủ điều kiện hoạt động kiểm định."
    ),
    "ND_44_2016#d4-k1-c": (
        "c) Người phụ trách kỹ thuật hoạt động kiểm định của tổ chức phải có thời gian làm "
        "kiểm định viên tối thiểu 02 năm."
    ),
    "ND_44_2016#d4-k2": (
        "2. Các thiết bị, nhân lực nêu tại các điểm a, b và c khoản 1 Điều này chỉ được "
        "sử dụng để làm điều kiện đề nghị cấp Giấy chứng nhận đủ điều kiện hoạt động kiểm "
        "định kỹ thuật an toàn lao động đối với một tổ chức."
    ),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def update_qa_file(path: Path) -> None:
    rows = read_jsonl(path)
    if len(rows) != 1000 or len({row.get("sheet_row") for row in rows}) != 1000:
        raise RuntimeError(f"Expected 1000 unique physical Sheet rows in {path}")
    found: set[int] = set()
    for row in rows:
        sheet_row = int(row["sheet_row"])
        if sheet_row in UPDATES:
            row.update(UPDATES[sheet_row])
            found.add(sheet_row)
    if found != set(UPDATES):
        raise RuntimeError(f"Missing QA rows in {path}: {sorted(set(UPDATES) - found)}")
    write_jsonl(path, rows)


def make_nq_chunk() -> dict[str, Any]:
    title = "Cắt giảm thủ tục hành chính về dịch vụ việc làm"
    retrieval_text = (
        "Văn bản: Nghị quyết số 66.18/2026/NQ-CP | Phụ lục I.4: D. Lĩnh vực việc làm\n"
        f"Nội dung: {NQ_CONTENT}"
    )
    return {
        "chunk_id": NQ_CHUNK_ID,
        "doc_id": "NQ_66_18_2026",
        "doc_title": "Nghị quyết 66.18/2026/NQ-CP về cắt giảm thủ tục hành chính và điều kiện kinh doanh",
        "document_no": "66.18/2026/NQ-CP",
        "document_type": "Nghị quyết",
        "issuer": "Chính phủ",
        "part": "Phụ lục I.4",
        "chapter": None,
        "section": "D. Lĩnh vực việc làm",
        "article_number": "Phụ lục I.4",
        "article_title": title,
        "clause_number": None,
        "point": None,
        "content": NQ_CONTENT,
        "table_data": None,
        "source_file": "66_18_2026_NQ_CP_employment_excerpt.txt",
        "source_page_start": None,
        "source_page_end": None,
        "extraction_method": "reviewed_official_excerpt",
        "text_source_url": NQ_SOURCE,
        "effective_from": "2026-07-01",
        "effective_to": "2027-02-28",
        "status": "CURRENT",
        "official_source": NQ_SOURCE,
        "scope_tier": "extended",
        "domain": "EMPLOYMENT_SERVICE",
        "retrieval_text": retrieval_text,
    }


def update_nd44_chunks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obsolete = {"ND_44_2016#d4-k1-d", "ND_44_2016#d4-k1-đ"}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        chunk_id = row.get("chunk_id")
        if chunk_id in obsolete:
            continue
        if chunk_id not in ND44_TEXT:
            out.append(row)
            continue
        row["content"] = ND44_TEXT[chunk_id]
        row["doc_title"] = (
            "Nghị định 44/2016/NĐ-CP - Điều kiện kiểm định theo sửa đổi tại Nghị định 140/2018/NĐ-CP"
        )
        row["official_source"] = ND44_CONSOLIDATED_SOURCE
        row["text_source_url"] = ND44_CONSOLIDATED_SOURCE
        row["source_file"] = "11_44_2016_Article4_amended_by_140_2018.txt"
        row["source_page_start"] = None
        row["source_page_end"] = None
        row["extraction_method"] = "official_consolidated_excerpt"
        row["amended_by"] = "140/2018/NĐ-CP, khoản 1 Điều 1"
        row["amendment_source"] = ND140_SOURCE
        if chunk_id == "ND_44_2016#d4-k1":
            row["clause_number"] = "1"
            row["point"] = None
        elif chunk_id.endswith("-a"):
            row["clause_number"], row["point"] = "1", "a"
        elif chunk_id.endswith("-b"):
            row["clause_number"], row["point"] = "1", "b"
        elif chunk_id.endswith("-c"):
            row["clause_number"], row["point"] = "1", "c"
        elif chunk_id == "ND_44_2016#d4-k2":
            row["clause_number"], row["point"] = "2", None
        pieces = [f"Văn bản: {row['doc_title']}"]
        if row.get("chapter"):
            pieces.append(f"Chương: {row['chapter']}")
        pieces.append(f"Điều 4: {row.get('article_title') or 'Điều kiện cấp Giấy chứng nhận đủ điều kiện hoạt động kiểm định kỹ thuật an toàn lao động'}")
        if row.get("clause_number"):
            pieces.append(f"Khoản {row['clause_number']}")
        if row.get("point"):
            pieces.append(f"Điểm {row['point']}")
        row["retrieval_text"] = " | ".join(pieces) + f"\nNội dung: {row['content']}"
        out.append(row)
        seen.add(str(chunk_id))
    missing = set(ND44_TEXT) - seen
    if missing:
        raise RuntimeError(f"Missing ND 44 article 4 chunks: {sorted(missing)}")
    return out


def update_corpus() -> None:
    rows = read_jsonl(CORPUS)
    rows = update_nd44_chunks(rows)
    existing = [row for row in rows if row.get("chunk_id") == NQ_CHUNK_ID]
    if len(existing) > 1:
        raise RuntimeError(f"Duplicate new resolution chunk {NQ_CHUNK_ID}")
    chunk = make_nq_chunk()
    if existing:
        index = rows.index(existing[0])
        rows[index] = chunk
    else:
        rows.append(chunk)
    write_jsonl(CORPUS, rows)


def update_anchors() -> None:
    rows = read_jsonl(ANCHORS)
    by_row = {int(row["sheet_row"]): row for row in rows}
    if len(rows) != 1000 or len(by_row) != 1000:
        raise RuntimeError("Question anchors must contain exactly 1000 unique Sheet rows")
    for sheet_row in UPDATES:
        anchor = by_row[sheet_row]
        snapshot = next(row for row in read_jsonl(SNAPSHOT) if int(row["sheet_row"]) == sheet_row)
        anchor["question"] = snapshot["question"]
        if sheet_row in (566, 567):
            anchor["law_anchors"] = [{"doc_id": "NQ_66_18_2026", "article_number": "Phụ lục I.4"}]
            anchor["reviewed_chunk_ids"] = [NQ_CHUNK_ID]
        elif sheet_row == 792:
            anchor["reviewed_chunk_ids"] = [
                "L_84_2015#d32-k1",
                "ND_44_2016#d4-k1",
                "ND_44_2016#d4-k1-a",
                "ND_44_2016#d4-k1-b",
                "ND_44_2016#d4-k1-c",
            ]
        elif sheet_row in (898, 903):
            anchor["reviewed_chunk_ids"] = [
                "L_84_2015#d32-k1",
                "ND_44_2016#d4-k1",
                "ND_44_2016#d4-k1-a",
                "ND_44_2016#d4-k1-b",
                "ND_44_2016#d4-k1-c",
            ]
    write_jsonl(ANCHORS, rows)


def main() -> None:
    update_qa_file(SNAPSHOT)
    update_qa_file(CORRECTED)
    update_corpus()
    update_anchors()
    print("Synced verified Sheet rows 566, 567, 792, 898, and 903 into the local RAG dataset.")


if __name__ == "__main__":
    main()
