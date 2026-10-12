from rag.citation_normalizer import normalize_statute_name, extract_article_and_law

def test_normalize_statute_name():
    assert "Bộ luật Lao động 2019" in normalize_statute_name("theo bllđ 2019 quy định")
    assert "Nghị định 145/2020/NĐ-CP" in normalize_statute_name("nghị định 145/2020 hướng dẫn")
    assert "Nghị định 12/2022/NĐ-CP" in normalize_statute_name("xử phạt theo nghị định 12")

def test_extract_article_and_law():
    res = extract_article_and_law("Điểm a Khoản 2 Điều 36 Bộ luật Lao động 2019")
    assert res["article"] == 36
    assert res["clause"] == 2
    assert res["point"] == "a"
