from scripts.health_check import run_health_checks

def test_health_check():
    res = run_health_checks()
    assert "vector_db_exists" in res
    assert "config_loaded" in res
    assert res["config_loaded"] is True
