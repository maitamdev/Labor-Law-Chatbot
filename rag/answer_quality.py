"""Presentation requirements for broad legal questions, without adding legal facts."""

import re
from collections import OrderedDict
from typing import Sequence

from rag.conversational import fold_vietnamese
from rag.evidence_mapper import EvidenceBlock


def is_overview_question(query: str) -> bool:
    text = fold_vietnamese(query)
    if re.search(r"\b(?:tom tat|ngan gon|ngan nhat|mot cau|1 cau|vai dong)\b", text):
        return False
    return bool(re.search(
        r"\b(?:quy dinh (?:phap luat )?ve|cac truong hop|cac dieu kien|tong quan|"
        r"dieu kien va thu tuc|thu tuc va dieu kien)\b", text,
    ))


def needs_overview_expansion(query: str, answer: str, evidence_count: int, *, evidence_complete: bool = True) -> bool:
    """A one-line signpost to several provisions is not a usable overview."""
    if evidence_count < 3 or not is_overview_question(query):
        return False
    listed_items = re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+\S", answer)
    return len(answer.split()) < 100 or len(listed_items) < 2 or not evidence_complete


def overview_evidence_is_complete(blocks: Sequence[EvidenceBlock], evidence_ids: Sequence[str]) -> bool:
    """Require coverage of distinct supplied provisions, not a long citation list."""
    parents = {(b.document_no, b.article_number, b.clause_number) for b in blocks if not b.point}
    mentioned = {token.strip('[]').upper() for token in evidence_ids}
    required, covered = set(), set()
    for block in blocks:
        clause = (block.document_no, block.article_number, block.clause_number)
        if block.point and clause in parents:
            # Citing a whole clause covers its points, but citing one point
            # cannot stand in for the other points of that supplied clause.
            continue
        key = clause + (block.point,)
        required.add(key)
        if block.evidence_id.upper() in mentioned:
            covered.add(key)
    return required.issubset(covered)


def grounded_overview(blocks: Sequence[EvidenceBlock]) -> str:
    """Last-resort readable outline of supplied provisions, with no invented rules.

    The caller limits blocks to the single issue's verified sources. Full
    clauses cover their already-included points; do not repeat both versions.
    """
    full_clauses: dict[tuple[str, int | None, int | None], str] = {
        (b.document_no, b.article_number, b.clause_number): b.content
        for b in blocks if not b.point and b.clause_number is not None
    }
    articles: dict[tuple, list[EvidenceBlock]] = OrderedDict()
    for block in blocks:
        parent = full_clauses.get((block.document_no, block.article_number, block.clause_number), "")
        if block.point and all(line.strip() in parent for line in block.content.splitlines() if line.strip()):
            continue
        articles.setdefault((block.document_no, block.article_number, block.article_title), []).append(block)

    sections = []
    for (_, _, title), provisions in articles.items():
        parts = [f"### {title or 'Quy định áp dụng'}"]
        for block in provisions:
            # Display quoted cross-references without promoting them to an
            # independent citation; only the actual evidence label is linked.
            content = re.sub(r"theo quy định tại Điều \d+ của Bộ luật này", "theo quy định liên quan", block.content)
            lines = re.split(r"\n(?=[a-zđ]\)\s)", content)
            lead = re.sub(r"^\s*\d+[.)]\s*", "", lines[0]).strip()
            if len(lines) > 1:
                parts.append(f"**{lead}**")
                parts.extend("- " + re.sub(r"^[a-zđ]\)\s*", "", line).replace("\n", " ") for line in lines[1:])
            else:
                parts.append("- " + lead.replace("\n", " "))
            parts[-1] += f" ([{block.evidence_id}])."
        sections.append("\n\n".join(parts))
    return "\n\n".join(sections)


OVERVIEW_EXPLANATION_INSTRUCTION = (
    "[GIẢI THÍCH ĐẦY ĐỦ CHO CÂU HỎI TỔNG QUAN]\n"
    "Trường answer phải là bài giải thích 200–350 từ, không phải câu tóm tắt của findings. "
    "Mở đầu bằng kết luận ngắn, sau đó dùng các mục Markdown: "
    "(1) Các trường hợp/điều kiện áp dụng: diễn giải từng nhóm trong căn cứ thành gạch đầu dòng; "
    "(2) Nguyên tắc và thủ tục: nêu cụ thể những bước, yêu cầu đã có trong căn cứ; "
    "(3) Các giới hạn/ngoại lệ cần lưu ý, chỉ khi căn cứ có nội dung đó. "
    "Không được thay phần liệt kê bằng câu 'thuộc các trường hợp tại Điều...' hoặc 'tuân thủ trình tự luật định'. "
    "Không thêm thời hạn, mức phạt hay tình tiết ngoài các khối căn cứ. "
    "Mỗi nhận định gắn mã [E...] sau câu; không tự ghi số Điều/Khoản/Điểm hoặc viện dẫn chéo. "
    "Mỗi nhận định cần có evidence_ids tương ứng trong finding. Giữ nguyên schema JSON."
)
