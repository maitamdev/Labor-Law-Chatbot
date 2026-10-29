from graph.synonym_mapper import expand_legal_terms


def test_expand_legal_terms():
    terms = expand_legal_terms("Công ty đuổi việc tôi không lý do và không trả tiền nghỉ việc")
    assert "sa thải" in terms
    assert "trợ cấp thôi việc" in terms

def test_expand_legal_terms_empty():
    terms = expand_legal_terms("Hôm nay trời đẹp")
    assert terms == []
