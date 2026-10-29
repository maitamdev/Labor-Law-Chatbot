# -*- coding: utf-8 -*-
"""
National improvement loop: measure → compare to goals → write snapshot.

Usage:
    python scripts/run_improvement_cycle.py
    python scripts/run_improvement_cycle.py --skip-ablation
    python scripts/run_improvement_cycle.py --run-ablation
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOALS = PROJECT_ROOT / "data" / "evaluation" / "national_improvement_goals.json"
OUT_DIR = PROJECT_ROOT / "reports" / "improvement_cycle"
PYTHON = sys.executable

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _run(cmd: list[str], timeout: int = 3600) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out[-8000:]


def _corpus_chroma_counts() -> dict:
    import sqlite3

    corpus_path = PROJECT_ROOT / "data" / "processed" / "legal_documents_v3.jsonl"
    n = sum(1 for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip())
    sqlite_path = PROJECT_ROOT / "storage" / "chroma_v3" / "chroma.sqlite3"
    cc = 0
    if sqlite_path.is_file():
        try:
            with sqlite3.connect(str(sqlite_path)) as con:
                row = con.execute(
                    "SELECT COUNT(*) FROM embeddings WHERE segment_id IN ("
                    "SELECT id FROM segments WHERE collection = ("
                    "SELECT id FROM collections WHERE name = 'vietlabor_chunks_v3'"
                    "))"
                ).fetchone()
                cc = int(row[0]) if row else 0
        except Exception:
            try:
                with sqlite3.connect(str(sqlite_path)) as con:
                    row = con.execute("SELECT COUNT(*) FROM embeddings").fetchone()
                    cc = int(row[0]) if row else 0
            except Exception:
                cc = 0
    return {"corpus_chunks": n, "chroma_chunks": cc, "chroma_ratio": round(cc / n, 4) if n else 0}



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--run-ablation", action="store_true", help="Force ablation even if chroma incomplete")
    parser.add_argument("--pytest-args", default="-q --tb=no tests/test_retrieval.py tests/test_anchor_lock_policy.py")
    args = parser.parse_args()

    goals = json.loads(GOALS.read_text(encoding="utf-8")) if GOALS.is_file() else {}
    t0 = time.time()
    snapshot: dict = {
        "at": datetime.now(timezone.utc).isoformat(),
        "goals_version": goals.get("version"),
        "index": _corpus_chroma_counts(),
        "steps": {},
        "recommendations": [],
    }

    rc, out = _run([PYTHON, "-m", "pytest", *args.pytest_args.split()])
    snapshot["steps"]["pytest_fast"] = {"exit_code": rc, "tail": out[-2000:]}

    rc, out = _run([PYTHON, str(PROJECT_ROOT / "scripts" / "audit_corpus_coverage.py")], timeout=120)
    snapshot["steps"]["audit_corpus"] = {"exit_code": rc, "tail": out[-1500:]}

    chroma_ok = snapshot["index"]["chroma_ratio"] >= goals.get("metrics", {}).get("chroma_index_coverage", {}).get("floor", 0.99)
    if args.run_ablation or (not args.skip_ablation and chroma_ok):
        stamp = datetime.now().strftime("%Y-%m-%d")
        md = OUT_DIR / f"ablation_cycle_{stamp}.md"
        rc, out = _run(
            [
                PYTHON,
                str(PROJECT_ROOT / "scripts" / "evaluate_ablation.py"),
                "--configs",
                "bm25",
                "hybrid",
                "hybrid_norm",
                "--out",
                str(md),
            ],
            timeout=7200,
        )
        snapshot["steps"]["ablation"] = {"exit_code": rc, "report": str(md), "tail": out[-1500:]}
    else:
        snapshot["steps"]["ablation"] = {"skipped": True, "reason": "chroma incomplete; use run_chroma_index_background.ps1"}
        snapshot["recommendations"].append("Hoàn tất Chroma rồi chạy lại với --run-ablation.")

    if snapshot["index"]["chroma_ratio"] < 1.0:
        snapshot["recommendations"].append(
            f"Chroma {snapshot['index']['chroma_chunks']}/{snapshot['index']['corpus_chunks']} — tiếp tục scripts/run_chroma_index_background.ps1"
        )

    snapshot["elapsed_sec"] = round(time.time() - t0, 1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "latest_snapshot.json"
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"Wrote {out_path}")
    return 0 if snapshot["steps"].get("pytest_fast", {}).get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
