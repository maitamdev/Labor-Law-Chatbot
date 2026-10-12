"""
System Diagnostic and Environment Health Check Script for VietLabor AI.
"""
import sys
from pathlib import Path

def run_health_checks() -> dict:
    results = {}
    
    # 1. Storage check
    chroma_dir = Path("storage/chroma_v3")
    bm25_dir = Path("storage/bm25_v3")
    results["vector_db_exists"] = chroma_dir.exists()
    results["bm25_index_exists"] = bm25_dir.exists()
    
    # 2. Config check
    try:
        from config.settings import settings
        results["config_loaded"] = True
    except Exception as e:
        results["config_loaded"] = False
        results["config_error"] = str(e)
        
    return results

if __name__ == "__main__":
    res = run_health_checks()
    print("Health check results:", res)
