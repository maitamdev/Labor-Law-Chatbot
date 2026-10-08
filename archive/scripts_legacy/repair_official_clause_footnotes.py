"""Idempotently repair official-text footnote extraction in known clause chunks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "processed" / "legal_documents_v3.jsonl"


def retrieval_text(record: dict) -> str:
    title = record.get("doc_title") or record.get("document_no")
    header = [f"Văn bản: {title}" if title else ""]
    if article := record.get("article_number"):
        article_title = record.get("article_title")
        header.append(f"Điều {article}: {article_title}" if article_title else f"Điều {article}")
    if clause := record.get("clause_number"):
        header.append(f"Khoản {clause}")
    prefix = " | ".join(part for part in header if part)
    return f"{prefix}\nNội dung: {record['content']}" if prefix else record["content"]


def _one_by_id(records: list[dict], chunk_id: str) -> dict | None:
    found = [record for record in records if record.get("chunk_id") == chunk_id]
    if len(found) > 1:
        raise RuntimeError(f"Duplicate corpus chunk id: {chunk_id}")
    return found[0] if found else None


def _set_content(record: dict, expected: str, recognized_bad_markers: tuple[str, ...]) -> bool:
    current = record.get("content", "")
    if current == expected:
        return False
    if not any(marker in current for marker in recognized_bad_markers):
        raise RuntimeError(f"Unexpected source text for {record.get('chunk_id')}; refusing to overwrite it.")
    record["content"] = expected
    record["retrieval_text"] = retrieval_text(record)
    return True


def repair_article_139(records: list[dict]) -> int:
    old_id = "VBHN_18_2026#d139"
    new_id = "VBHN_18_2026#d139-k1"
    old = _one_by_id(records, old_id)
    corrected = _one_by_id(records, new_id)
    if old is None and corrected is not None:
        if not corrected.get("content", "").startswith("1. ") or corrected.get("clause_number") != "1":
            raise RuntimeError("Article 139 clause 1 exists but does not match the normalized form.")
        return 0
    if old is None or corrected is not None:
        raise RuntimeError("Unexpected Article 139 chunk state; refusing to repair ambiguously.")

    current = old.get("content", "")
    prefix = "Điều 139. Nghỉ thai sản\n1.44 "
    if not current.startswith(prefix):
        raise RuntimeError("Article 139 source no longer matches the known footnote extraction issue.")
    old["chunk_id"] = new_id
    old["clause_number"] = "1"
    old["content"] = "1. " + current[len(prefix):]
    old["retrieval_text"] = retrieval_text(old)
    return 1


def repair_article_19(records: list[dict]) -> int:
    clause_1_id = "VBHN_90_2025#d19-k1"
    clause_2_id = "VBHN_90_2025#d19-k2"
    clause_4_id = "VBHN_90_2025#d19-k4"
    clause_1 = _one_by_id(records, clause_1_id)
    clause_2 = _one_by_id(records, clause_2_id)
    clause_4 = _one_by_id(records, clause_4_id)
    if clause_1 is None or clause_4 is None:
        raise RuntimeError("Expected current VBHN 90 Article 19 clause chunks were not found.")

    expected_1 = "1. Công đoàn có quyền, trách nhiệm phát triển đoàn viên công đoàn, thành lập công đoàn cơ sở, nghiệp đoàn cơ sở."
    expected_2 = (
        "2. Công đoàn cấp trên cơ sở có quyền, trách nhiệm cử cán bộ công đoàn đến doanh nghiệp, "
        "hợp tác xã, liên hiệp hợp tác xã, tổ chức, đơn vị để tuyên truyền, vận động, hướng dẫn "
        "người lao động gia nhập, thành lập công đoàn cơ sở."
    )
    expected_4 = "4. Công đoàn cơ sở, nghiệp đoàn cơ sở có trách nhiệm tuyên truyền, vận động, gặp gỡ người lao động để gia nhập Công đoàn."
    changed = 0
    if _set_content(clause_1, expected_1, ("2.9 Công đoàn cấp trên cơ sở", "3.10 (được bãi bỏ)")):
        changed += 1

    if clause_2 is None:
        clause_2 = dict(clause_1)
        clause_2["chunk_id"] = clause_2_id
        clause_2["clause_number"] = "2"
        clause_2["content"] = expected_2
        clause_2["retrieval_text"] = retrieval_text(clause_2)
        clause_1_index = records.index(clause_1)
        records.insert(clause_1_index + 1, clause_2)
        changed += 1
    elif _set_content(clause_2, expected_2, ("2.9 Công đoàn cấp trên cơ sở",)):
        changed += 1

    if _set_content(clause_4, expected_4, ("\n9 Khoản này được sửa đổi", "\n10 Khoản này được bãi bỏ")):
        changed += 1
    return changed


def main() -> None:
    records = [
        json.loads(line)
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = repair_article_139(records) + repair_article_19(records)

    fd, temp_name = tempfile.mkstemp(prefix=f".{CORPUS.name}.", suffix=".tmp", dir=CORPUS.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        Path(temp_name).replace(CORPUS)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise
    print(f"Repaired {changed} official-text clause chunk(s); reruns are idempotent.")


if __name__ == "__main__":
    main()
