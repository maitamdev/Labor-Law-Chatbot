from __future__ import annotations

import unicodedata
import pytest
from pathlib import Path

from ingestion.cleaner import TextCleaner
from ingestion.loader import PDFLoader
from ingestion.parser import (
    ARTICLE_PATTERN,
    CHAPTER_PATTERN,
    CLAUSE_PATTERN,
    PART_PATTERN,
    POINT_PATTERN,
    SECTION_PATTERN,
    LegalParser,
)
from ingestion.schemas import LegalChunk, PageText


# ==============================================================================
# 1. UNICODE & CLEANER TESTS
# ==============================================================================

def test_unicode_nfc_normalization():
    cleaner = TextCleaner()
    # NFD decomposed Vietnamese text: 'e' + combining acute
    decomposed = "Hợp đồng lao động Việt Nam"
    normalized = cleaner.clean_text(decomposed)
    assert unicodedata.is_normalized("NFC", normalized)
    assert "Hợp đồng lao động Việt Nam" in normalized


def test_cleaner_preserves_legal_markers():
    cleaner = TextCleaner()
    raw = (
        "CHƯƠNG III\n"
        "HỢP ĐỒNG LAO ĐỘNG\n\n"
        "Điều 25. Thời gian thử việc\n"
        "1. Nội dung khoản 1 không bị xóa.\n"
        "a) Điểm a quy định chi tiết.\n"
        "b) Điểm b quy định tiếp theo.\n"
    )
    cleaned = cleaner.clean_text(raw)
    assert "CHƯƠNG III" in cleaned
    assert "Điều 25. Thời gian thử việc" in cleaned
    assert "1. Nội dung khoản 1 không bị xóa." in cleaned
    assert "a) Điểm a quy định chi tiết." in cleaned
    assert "b) Điểm b quy định tiếp theo." in cleaned


def test_cleaner_removes_standalone_page_numbers():
    cleaner = TextCleaner()
    raw = "Nội dung trang trước.\n2\nNội dung trang sau."
    cleaned = cleaner.clean_text(raw, page_number=2)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    assert "2" not in lines
    assert "Nội dung trang trước." in cleaned
    assert "Nội dung trang sau." in cleaned


def test_cleaner_unwraps_mid_sentence_lines():
    cleaner = TextCleaner()
    raw = (
        "1. Người lao động, người sử dụng lao động theo khoản\n"
        "3 Điều 2 của Bộ luật Lao động.\n"
        "2. Cơ quan, tổ chức khác theo quy định tại điểm\n"
        "a khoản 1 Điều 5.\n"
    )
    cleaned = cleaner.clean_text(raw)
    assert "theo khoản 3 Điều 2 của Bộ luật Lao động." in cleaned
    assert "theo quy định tại điểm a khoản 1 Điều 5." in cleaned


# ==============================================================================
# 2. REGEX PATTERN TESTS
# ==============================================================================

def test_regex_patterns():
    # Part
    m = PART_PATTERN.match("PHẦN THỨ NHẤT: NHỮNG QUY ĐỊNH CHUNG")
    assert m is not None
    assert "PHẦN THỨ NHẤT" in m.group(1)

    # Chapter
    m = CHAPTER_PATTERN.match("Chương II. HỢP ĐỒNG LAO ĐỘNG")
    assert m is not None
    assert m.group(2) == "II"

    # Section
    m = SECTION_PATTERN.match("Mục 1. GIAO KẾT HỢP ĐỒNG")
    assert m is not None
    assert m.group(2) == "1"

    # Article
    m = ARTICLE_PATTERN.match("Điều 25. Thời gian thử việc")
    assert m is not None
    assert m.group(1) == "25"
    assert m.group(2).strip() == "Thời gian thử việc"

    # Article with suffix
    m = ARTICLE_PATTERN.match("Điều 25a. Quy định chuyển tiếp")
    assert m is not None
    assert m.group(1) == "25a"

    # Clause
    m = CLAUSE_PATTERN.match("1. Thời gian thử việc do hai bên thỏa thuận.")
    assert m is not None
    assert m.group(1) == "1"

    # Point
    m = POINT_PATTERN.match("a) Không quá 180 ngày đối với công việc quản lý.")
    assert m is not None
    assert m.group(1) == "a"

    # Vietnamese 'đ' point
    m = POINT_PATTERN.match("đ) Các trường hợp khác theo quy định.")
    assert m is not None
    assert m.group(1) == "đ"


# ==============================================================================
# 3. SYNTHETIC FIXTURE PARSER TESTS
# ==============================================================================

@pytest.fixture
def synthetic_legal_pages() -> list[PageText]:
    """Synthetic legal text fixture strictly for testing parsing logic."""
    page_1_text = (
        "CHƯƠNG III\n"
        "HỢP ĐỒNG LAO ĐỘNG\n\n"
        "Điều 25. Thời gian thử việc\n"
        "1. Nội dung khoản thứ nhất quy định về thời gian.\n"
        "2. Nội dung khoản thứ hai quy định về điều kiện gồm:\n"
        "a) Điểm a mô tả chi tiết trường hợp một.\n"
    )
    page_2_text = (
        "b) Điểm b mô tả chi tiết trường hợp hai chạy qua trang mới.\n\n"
        "Điều 26. Tiền lương trong thời gian thử việc\n"
        "Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.\n"
    )
    return [
        PageText(doc_id="TEST_DOC", filename="test.pdf", page_number=1, text=page_1_text),
        PageText(doc_id="TEST_DOC", filename="test.pdf", page_number=2, text=page_2_text),
    ]


def test_parser_synthetic_fixture(synthetic_legal_pages):
    metadata = {
        "doc_id": "TEST_DOC",
        "doc_title": "Văn bản mẫu kiểm tra parser",
        "filename": "test.pdf",
        "document_no": "99/TEST",
    }
    parser = LegalParser(metadata)
    chunks = parser.parse_pages(synthetic_legal_pages)

    assert len(chunks) == 5

    # Chunk 1: Clause 1 of Article 25
    c1 = chunks[0]
    assert c1.chunk_id == "TEST_DOC#d25-k1"
    assert c1.article_number == "25"
    assert c1.clause_number == "1"
    assert c1.point is None
    assert "HỢP ĐỒNG LAO ĐỘNG" in (c1.chapter or "")
    assert c1.source_page_start == 1
    assert c1.source_page_end == 1
    assert "1. Nội dung khoản thứ nhất" in c1.content

    # Chunk 2: Clause 2 intro of Article 25
    c2 = chunks[1]
    assert c2.chunk_id == "TEST_DOC#d25-k2"
    assert c2.article_number == "25"
    assert c2.clause_number == "2"
    assert c2.point is None
    assert "2. Nội dung khoản thứ hai" in c2.content

    # Chunk 3: Point a of Clause 2 of Article 25
    c3 = chunks[2]
    assert c3.chunk_id == "TEST_DOC#d25-k2-a"
    assert c3.article_number == "25"
    assert c3.clause_number == "2"
    assert c3.point == "a"
    assert "a) Điểm a mô tả chi tiết" in c3.content

    # Chunk 4: Point b spanning from page 1 to 2
    c4 = chunks[3]
    assert c4.chunk_id == "TEST_DOC#d25-k2-b"
    assert c4.article_number == "25"
    assert c4.clause_number == "2"
    assert c4.point == "b"
    assert c4.source_page_start == 2
    assert c4.source_page_end == 2
    assert "b) Điểm b mô tả chi tiết" in c4.content

    # Chunk 5: Article 26 (no clauses)
    c5 = chunks[4]
    assert c5.chunk_id == "TEST_DOC#d26"
    assert c5.article_number == "26"
    assert c5.clause_number is None
    assert c5.point is None
    assert "Điều 26. Tiền lương" in c5.content


def test_deterministic_chunk_id(synthetic_legal_pages):
    parser1 = LegalParser({"doc_id": "TEST_DOC", "doc_title": "Test 1", "filename": "test.pdf"})
    parser2 = LegalParser({"doc_id": "TEST_DOC", "doc_title": "Test 1", "filename": "test.pdf"})

    chunks_run1 = parser1.parse_pages(synthetic_legal_pages)
    chunks_run2 = parser2.parse_pages(synthetic_legal_pages)

    ids1 = [c.chunk_id for c in chunks_run1]
    ids2 = [c.chunk_id for c in chunks_run2]

    assert ids1 == ids2
    assert ids1 == [
        "TEST_DOC#d25-k1",
        "TEST_DOC#d25-k2",
        "TEST_DOC#d25-k2-a",
        "TEST_DOC#d25-k2-b",
        "TEST_DOC#d26",
    ]


def test_article_without_clauses():
    """Article without any clauses should emit a single article chunk."""
    pages = [
        PageText(
            doc_id="DOC_A",
            filename="doc_a.pdf",
            page_number=1,
            text=(
                "Điều 7. Chức năng của tổ chức\n"
                "Tổ chức có chức năng nghiên cứu, đề xuất và tư vấn chính sách cho các cơ quan có thẩm quyền."
            ),
        )
    ]
    parser = LegalParser({"doc_id": "DOC_A", "doc_title": "Doc A", "filename": "doc_a.pdf"})
    chunks = parser.parse_pages(pages)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "DOC_A#d7"
    assert chunks[0].article_number == "7"
    assert chunks[0].clause_number is None
    assert chunks[0].point is None
    assert "Tổ chức có chức năng nghiên cứu" in chunks[0].content


# ==============================================================================
# 4. PDF LOADER TEST ON REAL FILE
# ==============================================================================

def test_pdf_loader_on_real_pdf():
    real_pdf = Path("data/raw/core/03_10_2020_TT_BLDTBXH.pdf")
    if not real_pdf.exists():
        pytest.skip("03_10_2020_TT_BLDTBXH.pdf not found")

    loader = PDFLoader(real_pdf, doc_id="TT_10_2020")
    pages = loader.load()

    assert len(pages) == 19
    assert pages[0].page_number == 1
    assert pages[18].page_number == 19
    assert "THÔNG TƯ" in pages[0].text
    assert len(pages[1].text.strip()) > 100


def test_provenance_and_metadata():
    from config.metadata_registry import get_verified_metadata

    meta = get_verified_metadata("TT_10_2020")
    assert meta["document_no"] == "10/2020/TT-BLĐTBXH"
    assert meta["issuer"] == "Bộ Lao động - Thương binh và Xã hội"
    assert meta["effective_from"] == "2021-01-01"
    assert meta["status"] == "Còn hiệu lực"

    pages = [
        PageText(
            doc_id="TT_10_2020",
            filename="03_10_2020_TT_BLDTBXH.pdf",
            page_number=1,
            text="Điều 1. Phạm vi\nNội dung điều 1.",
        )
    ]
    parser = LegalParser({
        **meta,
        "filename": "03_10_2020_TT_BLDTBXH.pdf",
        "extraction_method": "pdf_text",
        "text_source_url": "https://vbpl.vn",
        "extraction_timestamp": "2026-09-11T00:00:00Z",
    })
    chunks = parser.parse_pages(pages)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.document_no == "10/2020/TT-BLĐTBXH"
    assert c.extraction_method == "pdf_text"
    assert c.text_source_url == "https://vbpl.vn"
    assert c.extraction_timestamp == "2026-09-11T00:00:00Z"
    assert c.status == "Còn hiệu lực"
