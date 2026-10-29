from graph.query_sanitizer import sanitize_cypher_param, validate_readonly_cypher


def test_validate_readonly_cypher():
    assert validate_readonly_cypher("MATCH (n:Article) RETURN n LIMIT 10") is True
    assert validate_readonly_cypher("MATCH (n) DELETE n") is False
    assert validate_readonly_cypher("CREATE (n:LegalConcept {name: 'test'})") is False
    assert validate_readonly_cypher("MATCH (a) SET a.name = 'x'") is False

def test_sanitize_cypher_param():
    clean = sanitize_cypher_param("BLLD 2019'; DROP ALL;")
    assert "'" not in clean
    assert ";" not in clean
