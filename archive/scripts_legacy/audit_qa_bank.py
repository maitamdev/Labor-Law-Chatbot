"""Deterministic row-by-row checks of the curated question bank.

This catches missing statutory coverage and suspicious facts. It is not a
substitute for a lawyer's semantic review of each answer.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "data" / "evaluation" / "labor_qa_sheet_snapshot.jsonl"
DEFAULT_LAW = ROOT / "data" / "processed" / "legal_documents_v3.jsonl"

DOC_IDS = {
    "45/2019/QH14": "VBHN_18_2026",
    "18/VBHN-VPQH": "VBHN_18_2026",
    "41/2024/QH15": "VBHN_58_2025",
    "19/VBHN-VPQH": "VBHN_58_2025",
    "58/VBHN-VPQH": "VBHN_58_2025",
    "50/2024/QH15": "VBHN_90_2025",
    "90/VBHN-VPQH": "VBHN_90_2025",
    "92/2015/QH13": "VBHN_99_2025",
    "85/2025/QH15": "VBHN_99_2025",
    "99/VBHN-VPQH": "VBHN_99_2025",
    "113/2025/QH15": "LUAT_113_2025",
    "84/2015/QH13": "L_84_2015",
    "74/2025/QH15": "LVL_74_2025",
    "69/2020/QH14": "LUAT_69_2020",
    "44/2016/NĐ-CP": "ND_44_2016",
    "145/2020/NĐ-CP": "ND_145_2020",
    "12/2022/NĐ-CP": "ND_12_2022",
    "283/2026/NĐ-CP": "ND_283_2026",
    "168/2026/NĐ-CP": "ND_168_2026",
    "318/2025/NĐ-CP": "ND_318_2025",
    "352/2025/NĐ-CP": "ND_352_2025",
    "135/2020/NĐ-CP": "ND_135_2020",
    "158/2025/NĐ-CP": "ND_158_2025",
    "141/2026/NĐ-CP": "ND_141_2026",
    "159/2025/NĐ-CP": "ND_159_2025",
    "219/2025/NĐ-CP": "ND_219_2025",
    "293/2025/NĐ-CP": "ND_293_2025",
    "129/2025/NĐ-CP": "ND_129_2025",
    "337/2025/NĐ-CP": "ND_337_2025",
    "374/2025/NĐ-CP": "ND_374_2025",
    "39/2016/NĐ-CP": "ND_39_2016",
    "10/2020/TT-BLĐTBXH": "TT_10_2020",
    "12/2025/TT-BNV": "TT_12_2025",
    "24/2022/TT-BLĐTBXH": "TT_24_2022",
    "09/2020/TT-BLĐTBXH": "TT_09_2020",
}

DOC_NO_RE = re.compile(
    r"\b\d{1,3}/(?:20\d{2}/(?:NĐ-CP|QH\d+|TT-[A-ZĐ-]+)|VBHN-[A-ZĐ-]+)\b",
    re.I,
)
ARTICLE_RE = re.compile(r"\bĐiều\s+(\d+[a-z]?)\b", re.I)
CLAUSE_RE = re.compile(
    r"\b(?:các\s+)?khoản\s+(\d+(?:\s*(?:,|và|–|-)\s*\d+)*)\s+Điều\s+(\d+[a-z]?)\b",
    re.I,
)
QUANTITY_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|ngày(?:\s+làm\s+việc)?|tháng|năm|giờ|tuần|triệu\s+đồng)\b",
    re.I,
)

SOURCE_ALIASES = (
    ("bộ luật lao động", "VBHN_18_2026"),
    ("luật bảo hiểm xã hội", "VBHN_58_2025"),
    ("luật bhxh", "VBHN_58_2025"),
    ("luật an toàn, vệ sinh lao động", "L_84_2015"),
    ("bộ luật tố tụng dân sự", "VBHN_99_2025"),
    ("luật công đoàn", "VBHN_90_2025"),
)


def extract_citation_pairs(source: str) -> set[tuple[str, str]]:
    """Bind preceding Điều references to the document named in each clause.

    This is a conservative structural check; a matching pair alone does not
    establish that an answer correctly applies that legal provision.
    """
    citation_lines = [line for line in source.splitlines() if not line.strip().startswith("http")]
    parts = [part.strip() for line in citation_lines for part in line.split(";") if part.strip()]
    pending: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for part in parts:
        article_mentions = [(match.start(), match.group(1)) for match in ARTICLE_RE.finditer(part)]
        doc_mentions = [(match.start(), DOC_IDS[match.group()]) for match in DOC_NO_RE.finditer(part)
                        if match.group() in DOC_IDS]
        for phrase, doc_id in SOURCE_ALIASES:
            doc_mentions.extend((match.start(), doc_id) for match in re.finditer(re.escape(phrase), part, re.I))
        doc_mentions.sort()
        if not doc_mentions:
            pending.update(article for _, article in article_mentions)
            continue
        # A preceding clause without a document belongs to the first document
        # named in this clause; this is common in short semicolon lists.
        pairs.update((doc_mentions[0][1], article) for article in pending)
        pending.clear()
        for position, article in article_mentions:
            following = next((doc_id for doc_position, doc_id in doc_mentions if doc_position > position), None)
            doc_id = following or doc_mentions[-1][1]
            pairs.add((doc_id, article))
    return pairs


def expand_clause_numbers(value: str) -> set[str]:
    numbers: set[str] = set()
    for token in re.findall(r"\d+\s*(?:[-–]\s*\d+)?", value):
        if "-" in token or "–" in token:
            start, end = (int(part.strip()) for part in re.split(r"[-–]", token))
            if end - start <= 30:
                numbers.update(str(number) for number in range(start, end + 1))
        else:
            numbers.add(str(int(token)))
    return numbers


def extract_clause_citations(source: str) -> set[tuple[str, str, str]]:
    """Extract explicit clause-level references and bind them to named acts."""
    parts = [part.strip() for line in source.splitlines() if not line.strip().startswith("http")
             for part in line.split(";") if part.strip()]
    refs: set[tuple[str, str, str]] = set()
    pending: list[tuple[str, set[str]]] = []
    for part in parts:
        doc_mentions = [(match.start(), DOC_IDS[match.group()]) for match in DOC_NO_RE.finditer(part)
                        if match.group() in DOC_IDS]
        for phrase, doc_id in SOURCE_ALIASES:
            doc_mentions.extend((match.start(), doc_id) for match in re.finditer(re.escape(phrase), part, re.I))
        doc_mentions.sort()
        for match in CLAUSE_RE.finditer(part):
            clauses = expand_clause_numbers(match.group(1))
            article = match.group(2)
            following = next((doc_id for position, doc_id in doc_mentions if position > match.end()), None)
            if following:
                refs.update((following, article, clause) for clause in clauses)
            elif doc_mentions:
                refs.update((doc_mentions[-1][1], article, clause) for clause in clauses)
            else:
                pending.append((article, clauses))
        if doc_mentions and pending:
            doc_id = doc_mentions[0][1]
            refs.update((doc_id, article, clause) for article, clauses in pending for clause in clauses)
            pending.clear()
    return refs


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"\s+", " ", value).strip()


def quantity_key(value: str) -> str:
    return re.sub(r"\b0+(?=\d)", "", norm(value))


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def audit(bank: list[dict], law: list[dict]) -> list[dict]:
    by_doc_article: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_doc_article_clauses: set[tuple[str, str, str]] = set()
    by_doc: set[str] = set()
    for chunk in law:
        doc_id = str(chunk.get("doc_id", ""))
        by_doc.add(doc_id)
        article = str(chunk.get("article_number", ""))
        if article:
            by_doc_article[(doc_id, article)].append(str(chunk.get("content", "")))
            clause = str(chunk.get("clause_number", ""))
            if clause:
                by_doc_article_clauses.add((doc_id, article, clause))

    question_counts = Counter(norm(row["question"]) for row in bank)
    findings: list[dict] = []
    for row in bank:
        source = row["source"]
        codes = sorted(set(DOC_NO_RE.findall(source)))
        mapped = [DOC_IDS[code] for code in codes if code in DOC_IDS]
        # Sheet references often use the statute title instead of its number.
        for phrase, doc_id in SOURCE_ALIASES:
            if phrase in source.lower() and doc_id not in mapped:
                mapped.append(doc_id)
        missing_docs = [code for code in codes if code not in DOC_IDS or DOC_IDS[code] not in by_doc]
        articles = sorted(set(ARTICLE_RE.findall(source)), key=lambda x: int(re.match(r"\d+", x).group()))
        citation_pairs = extract_citation_pairs(source)
        missing_articles = [f"{doc_id}:Điều {article}" for doc_id, article in sorted(citation_pairs)
                            if (doc_id, article) not in by_doc_article]
        clause_pairs = extract_clause_citations(source)
        missing_clauses = [f"{doc_id}:Điều {article}:khoản {clause}"
                           for doc_id, article, clause in sorted(clause_pairs)
                           if (doc_id, article, clause) not in by_doc_article_clauses]
        legal_text = " ".join(
            text for doc_id, article in citation_pairs
            for text in by_doc_article.get((doc_id, article), [])
        )
        common_text = quantity_key(row["question"] + " " + legal_text)
        ungrounded_quantities = sorted(set(
            match.group() for match in QUANTITY_RE.finditer(row["answer"])
            if quantity_key(match.group()) not in common_text
        ))
        flags: list[str] = []
        if missing_docs:
            flags.append("document_absent_from_runtime_corpus")
        if missing_articles:
            flags.append("cited_article_absent_from_runtime_corpus")
        if missing_clauses:
            flags.append("cited_clause_absent_from_runtime_corpus")
        if not codes:
            flags.append("document_number_not_explicit")
        if not articles:
            flags.append("article_not_explicit")
        if len(row["answer"].strip()) < 90:
            flags.append("answer_very_short")
        if ungrounded_quantities:
            flags.append("quantity_requires_manual_check")
        if question_counts[norm(row["question"])] > 1:
            flags.append("duplicate_question")
        findings.append({
            "sheet_row": row["sheet_row"],
            "flags": flags,
            "missing_documents": missing_docs,
            "missing_articles": missing_articles,
            "missing_clauses": missing_clauses,
            "quantities_to_check": ungrounded_quantities,
        })
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--law", type=Path, default=DEFAULT_LAW)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    bank, law = load_jsonl(args.bank), load_jsonl(args.law)
    findings = audit(bank, law)
    counts = Counter(flag for finding in findings for flag in finding["flags"])
    print(f"Question bank: {len(bank)} records; law corpus: {len(law)} chunks")
    print("Flags:", json.dumps(counts, ensure_ascii=False, sort_keys=True))
    for flag in ("document_absent_from_runtime_corpus", "cited_article_absent_from_runtime_corpus", "duplicate_question"):
        rows = [str(x["sheet_row"]) for x in findings if flag in x["flags"]]
        print(f"{flag}: {', '.join(rows[:80])}{' ...' if len(rows) > 80 else ''}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps({"question_count": len(bank), "flags": dict(counts), "findings": findings}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
