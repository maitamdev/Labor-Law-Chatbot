"""Read-only diagnostics for the configured VietLabor corpus and indexes."""

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_health_checks() -> dict:
    results: dict[str, Any] = {"vector_db_exists": False, "bm25_index_exists": False}
    try:
        from config.settings import BM25_INDEX_DIR, CHROMA_INDEX_DIR, PRODUCTION_CORPUS_PATH
        from config.settings import PROJECT_ROOT as CFG_ROOT
    except Exception as exc:
        results.update(config_loaded=False, config_error=str(exc))
        return results

    results["config_loaded"] = CFG_ROOT.exists()
    results["vector_db_exists"] = CHROMA_INDEX_DIR.is_dir()
    results["bm25_index_exists"] = BM25_INDEX_DIR.is_dir()
    results["corpus_exists"] = PRODUCTION_CORPUS_PATH.is_file()
    results.update(corpus_chunks=0, chroma_chunks=0, bm25_chunks=0)
    try:
        if results["corpus_exists"]:
            with PRODUCTION_CORPUS_PATH.open(encoding="utf-8") as handle:
                results["corpus_chunks"] = sum(1 for line in handle if line.strip())
    except (OSError, UnicodeError) as exc:
        results["corpus_error"] = str(exc)

    sqlite_path = CHROMA_INDEX_DIR / "chroma.sqlite3"
    if sqlite_path.is_file():
        try:
            # A sqlite transaction context alone does not close the connection.
            with closing(sqlite3.connect(sqlite_path.resolve().as_uri() + "?mode=ro", uri=True)) as con:
                row = con.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE segment_id IN ("
                    "SELECT id FROM segments WHERE collection = ("
                    "SELECT id FROM collections WHERE name = ?))",
                    ("vietlabor_chunks_v3",),
                ).fetchone()
                results["chroma_chunks"] = int(row[0]) if row else 0
        except sqlite3.Error as exc:
            results["chroma_error"] = str(exc)

    bm25_meta_path = BM25_INDEX_DIR / "index_meta.json"
    if bm25_meta_path.is_file():
        try:
            meta = json.loads(bm25_meta_path.read_text(encoding="utf-8"))
            results["bm25_chunks"] = int(meta.get("total_chunks", 0))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            results["bm25_error"] = str(exc)

    results["index_counts_match"] = (
        results["corpus_chunks"] > 0
        and results["corpus_chunks"] == results["chroma_chunks"] == results["bm25_chunks"]
        and not any(key.endswith("_error") for key in results)
    )
    return results


if __name__ == "__main__":
    print("Health check results:", json.dumps(run_health_checks(), ensure_ascii=False, indent=2))
