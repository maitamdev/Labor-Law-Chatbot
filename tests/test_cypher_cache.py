from graph.cypher_cache import CypherQueryCache


def test_cypher_cache_lru():
    c = CypherQueryCache(capacity=2)
    c.put("q1", [1, 2])
    c.put("q2", [3, 4])
    assert c.get("q1") == [1, 2]
    c.put("q3", [5, 6])
    assert c.get("q2") is None  # evicted
    assert c.get("q1") == [1, 2]
    assert c.get("q3") == [5, 6]
