"""Replace provisional legal excerpts with locally saved official Công báo texts.

The source files are deliberately explicit and checked before a corpus write.
Run without --apply to inspect article coverage first.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import fitz
try:
    from docx import Document
except ImportError:  # Inline excerpts and PDF sources do not require python-docx.
    Document = None

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.cleaner import TextCleaner
from ingestion.parser import LegalParser
from ingestion.schemas import PageText

RAW = ROOT / "data" / "raw" / "official_digital"
CORPUS = ROOT / "data" / "processed" / "legal_documents_v3.jsonl"


def format_retrieval_text(chunk: dict) -> str:
    """Build the embedding text without importing the model runtime."""
    header = []
    if title := chunk.get("doc_title") or chunk.get("document_no"):
        header.append(f"Văn bản: {title}")
    if chapter := chunk.get("chapter"):
        header.append(f"Chương: {chapter}")
    if article := chunk.get("article_number"):
        title = chunk.get("article_title")
        header.append(f"Điều {article}: {title}" if title else f"Điều {article}")
    if clause := chunk.get("clause_number"):
        header.append(f"Khoản {clause}")
    if point := chunk.get("point"):
        header.append(f"Điểm {point}")
    prefix = " | ".join(header)
    body = f"Nội dung: {(chunk.get('content') or '').strip()}"
    return f"{prefix}\n{body}" if prefix else body

SOURCES = (
    {
        "doc_id": "VBHN_99_2025", "filename": "99_VBHN_VPQH_part1.pdf",
        "filenames": ("99_VBHN_VPQH_part1.pdf", "99_VBHN_VPQH_part2.pdf", "99_VBHN_VPQH_part3.pdf"),
        "document_no": "99/VBHN-VPQH", "doc_title": "Văn bản hợp nhất 99/VBHN-VPQH - Bộ luật Tố tụng dân sự",
        "document_type": "Văn bản hợp nhất", "issuer": "Văn phòng Quốc hội", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "LABOR_DISPUTE",
        "corpus_scope": "SCOPED_EXCERPT",
        "official_source": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-99-vbhn-vpqh-46013.htm",
        "required_articles": {"91", "405", "410"}, "include_articles": {"91", "405", "410"},
    },
    {
        "doc_id": "LUAT_113_2025", "filename": "113_2025_QH15_congbao.pdf",
        "document_no": "113/2025/QH15", "doc_title": "Luật Dân số 113/2025/QH15",
        "document_type": "Luật", "issuer": "Quốc hội", "effective_from": "2026-07-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "MATERNITY",
        "official_source": "https://congbao.chinhphu.vn/van-ban/luat-so-113-2025-qh15-468675.htm",
        "required_articles": {"1", "29"},
    },
    {
        "doc_id": "ND_168_2026", "filename": "168_2026_ND_CP_congbao.pdf",
        "document_no": "168/2026/NĐ-CP", "doc_title": "Nghị định 168/2026/NĐ-CP hướng dẫn Luật Dân số",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-07-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "MATERNITY",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-168-2026-nd-cp-469560/65154.htm",
        "required_articles": {"1", "2"},
    },
    {
        "doc_id": "VBHN_90_2025", "filename": "90_VBHN_VPQH_congbao.pdf",
        "document_no": "90/VBHN-VPQH", "doc_title": "Văn bản hợp nhất 90/VBHN-VPQH - Luật Công đoàn",
        "document_type": "Văn bản hợp nhất", "issuer": "Văn phòng Quốc hội", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "COLLECTIVE_LABOR",
        "official_source": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-90-vbhn-vpqh-45984.htm",
        "required_articles": {"1", "25", "29", "34"},
    },
    {
        "doc_id": "ND_318_2025", "filename": "318_2025_ND_CP_congbao.pdf",
        "document_no": "318/2025/NĐ-CP", "doc_title": "Nghị định 318/2025/NĐ-CP về đăng ký lao động và thông tin thị trường lao động",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-01-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "EMPLOYMENT_SERVICE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-318-2025-nd-cp-46804.htm",
        "required_articles": {"1", "3", "5", "6", "7", "25"},
    },
    {
        "doc_id": "ND_352_2025", "filename": "352_2025_ND_CP_congbao.pdf",
        "document_no": "352/2025/NĐ-CP", "doc_title": "Nghị định 352/2025/NĐ-CP về dịch vụ việc làm",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-01-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "EMPLOYMENT_SERVICE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-352-2025-nd-cp-468351.htm",
        "required_articles": {"1", "14", "15", "20"},
    },
    {
        "doc_id": "TT_24_2022", "filename": "24_2022_TT_BLDTBXH_congbao.pdf",
        "document_no": "24/2022/TT-BLĐTBXH", "doc_title": "Thông tư 24/2022/TT-BLĐTBXH về bồi dưỡng bằng hiện vật",
        "document_type": "Thông tư", "issuer": "Bộ Lao động - Thương binh và Xã hội", "effective_from": "2023-03-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "OCCUPATIONAL_SAFETY",
        "official_source": "https://congbao.chinhphu.vn/van-ban/thong-tu-so-24-2022-tt-bldtbxh-38574.htm",
        "required_articles": {"1", "3", "4"},
    },
    {
        "doc_id": "TT_09_2020", "filename": "09_2020_TT_BLDTBXH_congbao.pdf",
        "document_no": "09/2020/TT-BLĐTBXH", "doc_title": "Thông tư 09/2020/TT-BLĐTBXH về lao động chưa thành niên",
        "document_type": "Thông tư", "issuer": "Bộ Lao động - Thương binh và Xã hội", "effective_from": "2021-03-15",
        "status": "CURRENT", "scope_tier": "extended", "domain": "CHILD_LABOR",
        "official_source": "https://congbao.chinhphu.vn/van-ban/thong-tu-so-09-2020-tt-bldtbxh-33378.htm",
        "required_articles": {"1", "5", "7"},
    },
    {
        "doc_id": "ND_219_2025", "filename": "219_2025_ND_CP_congbao.pdf",
        "document_no": "219/2025/NĐ-CP", "doc_title": "Nghị định 219/2025/NĐ-CP về người lao động nước ngoài làm việc tại Việt Nam",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2025-08-07",
        "status": "CURRENT", "scope_tier": "extended", "domain": "FOREIGN_WORKER",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-219-2025-nd-cp-45798.htm",
        "required_articles": {"1", "10", "21", "23", "25", "26", "28", "29", "34", "35", "36"},
    },
    {
        "doc_id": "ND_158_2025", "filename": "158_2025_ND_CP_congbao.pdf",
        "document_no": "158/2025/NĐ-CP", "doc_title": "Nghị định 158/2025/NĐ-CP về bảo hiểm xã hội bắt buộc",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended_wave2", "domain": "SOCIAL_INSURANCE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-158-2025-nd-cp-45240.htm",
        "required_articles": {"1", "7", "14", "26"},
    },
    {
        "doc_id": "ND_141_2026", "filename": "141_2026_ND_CP_congbao.pdf",
        "document_no": "141/2026/NĐ-CP", "doc_title": "Nghị định 141/2026/NĐ-CP sửa đổi chính sách thuế đối với hộ kinh doanh",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-01-01",
        "status": "CURRENT", "scope_tier": "extended_wave2", "domain": "SOCIAL_INSURANCE",
        "corpus_scope": "SCOPED_EXCERPT",
        "official_source": "https://vanban.chinhphu.vn/?classid=1&docid=217960&pageid=27160&typegroupid=4",
        "inline_pages": [
            {
                "page_number": 1,
                "text": "Điều 1. Sửa đổi, bổ sung một số điều của Nghị định số 68/2026/NĐ-CP ngày 05 tháng 3 năm 2026 của Chính phủ quy định về chính sách thuế và quản lý thuế đối với hộ kinh doanh, cá nhân kinh doanh\n1. Sửa đổi cụm từ ‘500 triệu đồng’ thành ‘01 tỷ đồng’ tại Điều 3, Điều 4, khoản 1 Điều 8, Điều 9, Điều 10, khoản 3 Điều 11, khoản 1 và khoản 2 Điều 12, khoản 4 Điều 17, khoản 3 Điều 18 Nghị định số 68/2026/NĐ-CP.",
            },
            {
                "page_number": 3,
                "text": "Điều 3. Hiệu lực thi hành\nNghị định này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026.",
            },
        ],
        "required_articles": {"1", "3"}, "include_articles": {"1", "3"},
    },
    {
        "doc_id": "ND_159_2025", "filename": "159_2025_ND_CP_congbao.docx",
        "document_no": "159/2025/NĐ-CP", "doc_title": "Nghị định 159/2025/NĐ-CP về bảo hiểm xã hội tự nguyện",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended_wave2", "domain": "SOCIAL_INSURANCE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-159-2025-nd-cp-45253.htm",
        "required_articles": {"1", "4", "5", "6", "7"},
    },
    {
        # Keep the historical internal ID so existing anchors remain valid; the
        # source and displayed document metadata point to the current official
        # consolidated text, 19/VBHN-VPQH (12 February 2026).
        "doc_id": "VBHN_58_2025", "filename": "19_2026_VBHN_VPQH_congbao.pdf",
        "document_no": "19/VBHN-VPQH", "doc_title": "Văn bản hợp nhất 19/VBHN-VPQH - Luật Bảo hiểm xã hội",
        "document_type": "Văn bản hợp nhất", "issuer": "Văn phòng Quốc hội", "signer": "Lê Quang Tùng",
        "issued_date": "2026-02-12", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended_wave2", "domain": "SOCIAL_INSURANCE",
        "corpus_scope": "FULL_TEXT",
        "official_source": "https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm",
        "required_articles": {"1", "31", "37", "53", "68", "102", "141"},
    },
    {
        "doc_id": "L_84_2015", "filename": "84_2015_QH13_congbao.pdf",
        "document_no": "84/2015/QH13", "doc_title": "Luật An toàn, vệ sinh lao động 84/2015/QH13",
        "document_type": "Luật", "issuer": "Quốc hội", "effective_from": "2016-07-01",
        "status": "PARTIALLY_EFFECTIVE", "scope_tier": "extended_wave2", "domain": "OCCUPATIONAL_SAFETY",
        "official_source": "https://congbao.chinhphu.vn/van-ban/luat-so-84-2015-qh13-15356.htm",
        "required_articles": {"1", "7", "19", "24", "39", "52", "93"},
    },
    {
        "doc_id": "LVL_74_2025", "filename": "74_2025_QH15_congbao.pdf",
        "document_no": "74/2025/QH15", "doc_title": "Luật Việc làm số 74/2025/QH15",
        "document_type": "Luật", "issuer": "Quốc hội", "effective_from": "2026-01-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "UNEMPLOYMENT_INSURANCE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/luat-so-74-2025-qh15-45562.htm",
        "required_articles": {"1", "15", "17", "27", "38", "39", "40", "41", "55"},
    },
    {
        "doc_id": "ND_374_2025", "filename": "374_2025_ND_CP.docx",
        "document_no": "374/2025/NĐ-CP", "doc_title": "Nghị định 374/2025/NĐ-CP về bảo hiểm thất nghiệp",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-01-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "UNEMPLOYMENT_INSURANCE",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-374-2025-nd-cp-468724.htm",
        "required_articles": {"1", "14"},
    },
    {
        "doc_id": "ND_283_2026", "filename": "283_2026_ND_CP_congbao.docx",
        "document_no": "283/2026/NĐ-CP", "doc_title": "Nghị định 283/2026/NĐ-CP về xử phạt lĩnh vực lao động, BHXH",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2026-09-10",
        "status": "CURRENT", "scope_tier": "core", "domain": "CORE_LABOR",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm",
        "required_articles": {"1", "7", "66", "67"},
    },
    {
        "doc_id": "LUAT_69_2020", "filename": "69_2020_QH14_congbao_real.pdf",
        "document_no": "69/2020/QH14", "doc_title": "Luật Người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng",
        "document_type": "Luật", "issuer": "Quốc hội", "effective_from": "2022-01-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "OVERSEAS_WORKER",
        "official_source": "https://congbao.chinhphu.vn/van-ban/luat-so-69-2020-qh14-32699.htm",
        "required_articles": {"1", "3", "5", "6", "10", "24"},
    },
    {
        "doc_id": "ND_44_2016", "filename": "44_2016_ND_CP_congbao_real.pdf",
        "document_no": "44/2016/NĐ-CP", "doc_title": "Nghị định 44/2016/NĐ-CP về huấn luyện an toàn, vệ sinh lao động",
        "document_type": "Nghị định", "issuer": "Chính phủ", "effective_from": "2016-07-01",
        "status": "PARTIALLY_EFFECTIVE", "scope_tier": "extended", "domain": "OCCUPATIONAL_SAFETY",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-44-2016-nd-cp-19916.htm",
        "required_articles": {"1", "17", "21"},
    },
    {
        "doc_id": "ND_129_2025", "filename": "129_2025_ND_CP.pdf",
        "document_no": "129/2025/NĐ-CP",
        "doc_title": "Nghị định 129/2025/NĐ-CP quy định về phân định thẩm quyền của chính quyền địa phương 02 cấp trong lĩnh vực quản lý nhà nước của Bộ Nội vụ",
        "document_type": "Nghị định", "issuer": "Chính phủ", "signer": "Nguyễn Hòa Bình",
        "issued_date": "2025-06-11", "effective_from": "2025-07-01",
        "status": "CURRENT", "scope_tier": "extended", "domain": "COLLECTIVE_LABOR",
        "corpus_scope": "SCOPED_EXCERPT",
        "official_source": "https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-129-2025-nd-cp-45076.htm",
        "text_source_url": "https://congbao.chinhphu.vn/tai-ve-van-ban-so-129-2025-nd-cp-45076-56755?format=pdf",
        "inline_pages": [
            {
                "page_number": 20,
                "text": "Điều 42. Khai báo tai nạn lao động, sự cố kỹ thuật gây mất an toàn, vệ sinh lao động\nCơ quan công an cấp xã có trách nhiệm:\n1. Nhận khai báo tai nạn lao động, sự cố kỹ thuật gây mất an toàn, vệ sinh lao động của người sử dụng lao động theo quy định tại điểm b khoản 1 Điều 34 Luật An toàn, vệ sinh lao động.\n2. Nhận thông báo của Ủy ban nhân dân cấp xã trong trường hợp xảy ra tai nạn lao động chết người, tai nạn lao động làm bị thương nặng từ hai người lao động trở lên theo quy định tại điểm d khoản 1 Điều 34 Luật An toàn, vệ sinh lao động.\n\nĐiều 45. Thời gian, nội dung khai báo tai nạn lao động\n1. Sở Nội vụ và cơ quan công an cấp xã có trách nhiệm nhận khai báo tai nạn lao động theo quy định tại điểm a khoản 1, điểm a khoản 2 và điểm b khoản 3 Điều 10 Nghị định số 39/2016/NĐ-CP ngày 15 tháng 5 năm 2016 của Chính phủ quy định chi tiết thi hành một số điều của Luật An toàn, vệ sinh lao động.\n2. Nội dung khai báo theo quy định tại điểm b khoản 1, điểm b khoản 2 Điều 10 Nghị định số 39/2016/NĐ-CP thực hiện theo Mẫu số 01 Phụ lục II ban hành kèm theo Nghị định này.\n3. Mẫu báo cáo nhanh theo quy định tại điểm b khoản 3 Điều 10 Nghị định số 39/2016/NĐ-CP thực hiện theo Mẫu số 06 Phụ lục II ban hành kèm theo Nghị định này."
            },
            {
                "page_number": 21,
                "text": "Điều 43. Điều tra vụ tai nạn lao động, sự cố kỹ thuật gây mất an toàn, vệ sinh lao động, sự cố kỹ thuật gây mất an toàn, vệ sinh lao động nghiêm trọng đối với người lao động làm việc không theo hợp đồng lao động\n1. Trường hợp tai nạn lao động làm bị thương nặng một người lao động làm việc không theo hợp đồng lao động theo quy định tại khoản 1 Điều 35 Luật An toàn, vệ sinh lao động thì Ủy ban nhân dân cấp xã nơi xảy ra tai nạn lao động phải lập biên bản ghi nhận sự việc để thống kê tai nạn lao động.\n2. Trường hợp người lao động tham gia bảo hiểm tai nạn lao động theo hình thức tự nguyện đối với người lao động làm việc không theo hợp đồng lao động theo quy định tại Điều 18 Nghị định số 143/2024/NĐ-CP ngày 01 tháng 11 năm 2024 của Chính phủ quy định về bảo hiểm tai nạn lao động theo hình thức tự nguyện đối với người lao động làm việc không theo hợp đồng lao động thì việc khai báo, điều tra thực hiện theo quy định tại Điều 49 Nghị định này."
            },
            {
                "page_number": 30,
                "text": "Điều 68. Quyết định đình công và thông báo thời điểm bắt đầu đình công\nÍt nhất là 05 ngày làm việc trước ngày bắt đầu đình công, tổ chức đại diện người lao động tổ chức và lãnh đạo đình công phải gửi văn bản về việc quyết định đình công cho người sử dụng lao động, Ủy ban nhân dân cấp xã và cơ quan chuyên môn thực hiện nhiệm vụ về lĩnh vực nội vụ thuộc Ủy ban nhân dân cấp tỉnh theo quy định tại khoản 3 Điều 202 Bộ luật Lao động."
            },
            {
                "page_number": 30,
                "text": "Điều 69. Thông báo quyết định đóng cửa tạm thời nơi làm việc\nÍt nhất 03 ngày làm việc trước ngày đóng cửa tạm thời nơi làm việc, người sử dụng lao động phải niêm yết công khai quyết định đóng cửa tạm thời nơi làm việc tại nơi làm việc và thông báo cho Ủy ban nhân dân cấp xã có nơi làm việc dự kiến đóng cửa theo quy định tại khoản 3 Điều 205 Bộ luật Lao động."
            }
        ],
        "required_articles": {"42", "43", "45", "68", "69"}, "include_articles": {"42", "43", "45", "68", "69"},
    },
)


def read_pages(spec: dict) -> list[PageText]:
    cleaner = TextCleaner()
    pages = []
    if spec.get("inline_pages"):
        pages.extend(PageText(
            doc_id=spec["doc_id"],
            filename=spec["filename"],
            page_number=int(page["page_number"]),
            text=page["text"],
        ) for page in spec["inline_pages"])
        return [cleaner.clean_page(page) for page in pages]
    if spec.get("inline_text"):
        pages.append(PageText(
            doc_id=spec["doc_id"],
            filename=spec["filename"],
            page_number=int(spec.get("source_page_number", 1)),
            text=spec["inline_text"],
        ))
        return [cleaner.clean_page(page) for page in pages]
    for filename in spec.get("filenames", (spec["filename"],)):
        source = RAW / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix == ".pdf":
            document = fitz.open(source)
            pages.extend(PageText(doc_id=spec["doc_id"], filename=source.name, page_number=len(pages) + 1,
                                  text=re.sub(
                                      r"(?im)^\s*(?:Ký bởi|Người ký):[^\n]*\n(?:\s*(?:Email|Cơ quan|Ngày ký|Thời gian ký):[^\n]*\n?){0,4}",
                                      "", document[i].get_text(),
                                  )) for i in range(len(document)))
        else:
            if Document is None:
                raise RuntimeError("python-docx is required to refresh a DOCX source")
            document = Document(source)
            paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            pages.append(PageText(doc_id=spec["doc_id"], filename=source.name, page_number=len(pages) + 1,
                                  text="\n".join(paragraphs)))
    return [cleaner.clean_page(page) for page in pages]


def build_chunks(spec: dict) -> list[dict]:
    metadata = {k: v for k, v in spec.items() if k not in {
        "required_articles", "include_articles", "filenames", "inline_text", "inline_pages", "source_page_number",
    }}
    metadata["extraction_method"] = "official_text"
    chunks = [item.model_dump() for item in LegalParser(metadata).parse_pages(read_pages(spec))]
    if include_articles := spec.get("include_articles"):
        chunks = [item for item in chunks if str(item.get("article_number")) in include_articles]
    if spec["doc_id"] == "ND_129_2025":
        for chunk in chunks:
            if str(chunk.get("article_number")) in {"42", "43", "45"}:
                chunk["domain"] = "OCCUPATIONAL_ACCIDENT_DISEASE"
    seen = set()
    for chunk in chunks:
        cid = chunk["chunk_id"]
        if cid in seen:
            raise RuntimeError(f"duplicate chunk id: {cid}")
        seen.add(cid)
        chunk["retrieval_text"] = format_retrieval_text(chunk)
    articles = {str(item["article_number"]) for item in chunks if item.get("article_number")}
    missing = spec["required_articles"] - articles
    if missing:
        raise RuntimeError(f"{spec['doc_id']}: required articles missing: {sorted(missing)}")
    if any(len(item["content"]) > 12000 for item in chunks):
        raise RuntimeError(f"{spec['doc_id']}: oversized chunk needs manual inspection")
    print(f"{spec['doc_id']}: {len(chunks)} chunks, {len(articles)} articles, range "
          f"{min(map(int, articles))}-{max(map(int, articles))}")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--doc-id", choices=[spec["doc_id"] for spec in SOURCES],
                        help="Process only this verified source (useful for scoped additions).")
    args = parser.parse_args()
    selected_sources = [spec for spec in SOURCES if args.doc_id is None or spec["doc_id"] == args.doc_id]
    replacements = {spec["doc_id"]: build_chunks(spec) for spec in selected_sources}
    if not args.apply:
        return
    old = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    removed = {doc_id: sum(item.get("doc_id") == doc_id for item in old) for doc_id in replacements}
    retained = [item for item in old if item.get("doc_id") not in replacements]
    for item in retained:
        if item.get("doc_id") == "ND_12_2022":
            item["effective_to"] = "2026-09-09"
            item["status"] = "REPEALED"
            item["replaced_by"] = "283/2026/NĐ-CP"
    new = retained + [item for spec in selected_sources for item in replacements[spec["doc_id"]]]
    ids = [item["chunk_id"] for item in new]
    if len(ids) != len(set(ids)):
        raise RuntimeError("corpus would contain duplicate chunk IDs")
    backup = CORPUS.with_name("legal_documents_v3.before_official_qa_refresh.jsonl")
    if not backup.exists():
        shutil.copy2(CORPUS, backup)
    temporary = CORPUS.with_suffix(".jsonl.tmp")
    temporary.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in new), encoding="utf-8")
    temporary.replace(CORPUS)
    print(f"Corpus refreshed: {len(old)} -> {len(new)}; old sources replaced: {removed}")


if __name__ == "__main__":
    main()
