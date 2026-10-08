# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 3E Comprehensive Regression Test Suite
Validates that all defect patterns discovered in Phase 3D are resolved:
1. VBHN 18: Articles 76-79, 105, 107 exist in proper sequence without gaps.
2. TT 08: Articles 11, 18, 20 exist.
3. ND 145: No false Article 1e, no false articles > 115 (122, 123, 125, 137, 162, 169, 187).
4. ND 12: No false Article 110.
5. ND 293:
   - Region III is exactly 4,140,000 / 20,000 (No 'IHI').
   - Point d) and Point đ) are distinct and preserved.
   - Table data metadata is structured.
6. Zero local_ocr extraction method in production corpus.
7. Zero empty chunks, zero duplicate chunk IDs.
8. Numeric accuracy: '03 ngày' preserved accurately (no '05/03' contamination).
"""
import json
import pytest
from pathlib import Path

CORPUS_PATH = Path("data/processed/legal_documents.jsonl")

@pytest.fixture(scope="module")
def corpus():
    assert CORPUS_PATH.exists(), "Corpus file does not exist"
    chunks = []
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line.strip()))
    return chunks

def test_core_document_coverage(corpus):
    expected_docs = {
        "VBHN_18_2026": 220,
        "ND_145_2020": 115,
        "TT_10_2020": 12,
        "ND_293_2025": 5,
        "ND_12_2022": 64,
        "ND_337_2025": 30,
        "TT_08_2026": 24,
    }
    found_docs = {}
    for c in corpus:
        doc_id = c["doc_id"]
        art = c.get("article_number")
        if doc_id not in found_docs:
            found_docs[doc_id] = set()
        if art:
            found_docs[doc_id].add(int(art))

    assert len(found_docs) == 7, f"Expected 7 documents, got {len(found_docs)}"
    for doc_id, expected_max in expected_docs.items():
        assert doc_id in found_docs, f"Missing document {doc_id}"
        expected_range = set(range(1, expected_max + 1))
        actual_range = found_docs[doc_id]
        missing = expected_range - actual_range
        extra = actual_range - expected_range
        assert not missing, f"{doc_id} is missing articles: {sorted(list(missing))}"
        assert not extra, f"{doc_id} has false/extra articles: {sorted(list(extra))}"

def test_vbhn_18_critical_articles(corpus):
    vbhn_articles = {
        c.get("article_number"): c for c in corpus if c["doc_id"] == "VBHN_18_2026"
    }
    # Check Articles 76-79 (previously missing due to scan defect)
    for art in ["75", "76", "77", "78", "79", "80"]:
        assert art in vbhn_articles, f"VBHN 18 missing Article {art}"
    
    # Check Article 76 title and clauses
    c76 = [c for c in corpus if c["doc_id"] == "VBHN_18_2026" and c.get("article_number") == "76"]
    assert len(c76) == 7, f"Expected 7 clauses for Article 76, got {len(c76)}"
    assert all(c.get("article_title") == "Lấy ý kiến và ký kết thỏa ước lao động tập thể" for c in c76)
    
    # Check Articles 105 and 107
    assert "105" in vbhn_articles, "VBHN 18 missing Article 105"
    assert "107" in vbhn_articles, "VBHN 18 missing Article 107"
    c105 = [c for c in corpus if c["doc_id"] == "VBHN_18_2026" and c.get("article_number") == "105"]
    c107 = [c for c in corpus if c["doc_id"] == "VBHN_18_2026" and c.get("article_number") == "107"]
    assert all(c.get("article_title") == "Thời giờ làm việc bình thường" for c in c105)
    assert all(c.get("article_title") == "Làm thêm giờ" for c in c107)

def test_tt_08_critical_articles(corpus):
    tt08_articles = {
        c.get("article_number"): c for c in corpus if c["doc_id"] == "TT_08_2026"
    }
    assert "11" in tt08_articles, "TT 08 missing Article 11"
    assert "18" in tt08_articles, "TT 08 missing Article 18"
    assert "20" in tt08_articles, "TT 08 missing Article 20"

def test_nd_145_no_false_articles(corpus):
    nd145_articles = {
        c.get("article_number") for c in corpus if c["doc_id"] == "ND_145_2020" and c.get("article_number")
    }
    # No false 1e
    assert "1e" not in nd145_articles, "ND 145 contains false Article 1e"
    # No false articles exceeding 115
    for false_art in ["122", "123", "125", "137", "162", "169", "187"]:
        assert false_art not in nd145_articles, f"ND 145 contains false Article {false_art}"

def test_nd_12_no_false_articles(corpus):
    nd12_articles = {
        c.get("article_number") for c in corpus if c["doc_id"] == "ND_12_2022" and c.get("article_number")
    }
    assert "110" not in nd12_articles, "ND 12 contains false Article 110"
    for art in nd12_articles:
        assert int(art) <= 64, f"ND 12 contains article {art} exceeding 64"

def test_nd_293_table_and_points(corpus):
    nd293_chunks = [c for c in corpus if c["doc_id"] == "ND_293_2025"]
    
    # 1. Check Table in Article 3 Clause 1
    table_chunk = next(
        (c for c in nd293_chunks if c.get("article_number") == "3" and c.get("clause_number") == "1"),
        None
    )
    assert table_chunk is not None, "ND 293 missing Article 3 Clause 1 table chunk"
    assert table_chunk.get("table_data") is not None, "ND 293 table_data is None"
    
    expected_table = [
        {"region": "I", "monthly_minimum_wage": 5310000, "hourly_minimum_wage": 25500},
        {"region": "II", "monthly_minimum_wage": 4730000, "hourly_minimum_wage": 22700},
        {"region": "III", "monthly_minimum_wage": 4140000, "hourly_minimum_wage": 20000},
        {"region": "IV", "monthly_minimum_wage": 3700000, "hourly_minimum_wage": 17800},
    ]
    assert table_chunk["table_data"] == expected_table, f"Table data mismatch: {table_chunk['table_data']}"
    
    # Check no 'IHI' artifact
    assert "IHI" not in table_chunk["content"], "Found 'IHI' artifact in ND 293 table"
    assert "Vùng III" in table_chunk["content"], "Missing 'Vùng III' in ND 293 table"
    
    # 2. Check points d) and đ) in Article 3 Clause 3
    point_d = next(
        (c for c in nd293_chunks if c.get("article_number") == "3" and c.get("point") == "d"),
        None
    )
    point_dd = next(
        (c for c in nd293_chunks if c.get("article_number") == "3" and c.get("point") == "đ"),
        None
    )
    assert point_d is not None, "ND 293 missing Point d"
    assert point_dd is not None, "ND 293 missing Point đ"
    assert point_d["chunk_id"] != point_dd["chunk_id"], "Point d and đ share same chunk_id"
    assert "thay đổi tên hoặc chia" in point_d["content"], "Point d content mismatch"
    assert "thành lập mới" in point_dd["content"], "Point đ content mismatch"

def test_zero_ocr_in_production(corpus):
    for c in corpus:
        method = c.get("extraction_method")
        assert method in ("official_gazette_pdf_text", "pdf_text"), (
            f"Chunk {c['chunk_id']} has invalid extraction_method: '{method}'. "
            "Zero local_ocr is allowed in production corpus."
        )
        assert c.get("ocr_engine") is None, f"Chunk {c['chunk_id']} has unexpected ocr_engine"

def test_no_empty_or_duplicate_chunks(corpus):
    seen_ids = set()
    for c in corpus:
        cid = c["chunk_id"]
        assert cid not in seen_ids, f"Duplicate chunk_id: {cid}"
        seen_ids.add(cid)
        assert c["content"].strip(), f"Empty chunk: {cid}"

def test_notice_period_numerics(corpus):
    # Test Điều 35 Clause 1 Point c in VBHN 18 is '03 ngày'
    d35_c = next(
        (c for c in corpus if c["doc_id"] == "VBHN_18_2026" and c.get("article_number") == "35" and c.get("point") == "c"),
        None
    )
    assert d35_c is not None, "Missing VBHN 18 Article 35 Point c"
    assert "03 ngày làm việc" in d35_c["content"], f"Content mismatch in d35_c: {d35_c['content']}"
    assert "05/03" not in d35_c["content"], f"Contaminated '05/03' found in d35_c: {d35_c['content']}"

    # Test Điều 36 Clause 1 Point e is '05 ngày làm việc liên tục'
    d36_e = next(
        (c for c in corpus if c["doc_id"] == "VBHN_18_2026" and c.get("article_number") == "36" and c.get("point") == "e"),
        None
    )
    assert d36_e is not None, "Missing VBHN 18 Article 36 Point e"
    assert "05 ngày làm việc liên tục" in d36_e["content"], f"Content mismatch in d36_e: {d36_e['content']}"
