from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.chat_service import ChatService
from config.settings import PRODUCTION_CORPUS_PATH
from rag.evidence_selector import EvidenceSelector
from ui.components.citation_card import _safe_official_url
from ui.utils.session import SessionManager


def test_runtime_paths_are_absolute() -> None:
    assert PRODUCTION_CORPUS_PATH.is_absolute()
    assert PRODUCTION_CORPUS_PATH.name == "legal_documents_v3.jsonl"


def test_nd24_migration_contains_only_verified_article_numbers() -> None:
    rows = [json.loads(line) for line in PRODUCTION_CORPUS_PATH.read_text(encoding="utf-8").splitlines()]
    nd24 = {row["chunk_id"]: row for row in rows if row.get("doc_id") == "ND_24_2018"}

    assert set(nd24) == {
        "ND_24_2018#d7",
        "ND_24_2018#d15",
        "ND_24_2018#d20",
        "ND_24_2018#d27",
    }
    assert nd24["ND_24_2018#d15"]["article_number"] == "15"
    assert nd24["ND_24_2018#d20"]["article_number"] == "20"
    assert nd24["ND_24_2018#d27"]["article_title"] == "Thụ lý giải quyết khiếu nại lần hai"
    assert "thì bạn" not in nd24["ND_24_2018#d27"]["content"].lower()


def test_official_source_url_allowlist() -> None:
    assert _safe_official_url("https://vanban.chinhphu.vn/example")
    assert _safe_official_url("https://vbpl.vn/TW/example")
    assert _safe_official_url("javascript:alert(1)") == ""
    assert _safe_official_url("http://vanban.chinhphu.vn/insecure") == ""
    assert _safe_official_url("https://vanban.chinhphu.vn.evil.example/phish") == ""


def test_verified_metadata_is_merged_for_legacy_chunks() -> None:
    meta = EvidenceSelector()._extract_meta(
        {
            "chunk_id": "ND_145_2020#d1",
            "content": "Nội dung thử nghiệm",
            "metadata": {"doc_id": "ND_145_2020", "article_number": "1"},
        }
    )
    assert meta["document_no"] == "145/2020/NĐ-CP"
    assert meta["effective_from"] == "2021-02-01"
    assert meta["status"] == "PARTIALLY_EFFECTIVE"
    assert meta["official_source"].startswith("https://")


def test_chat_service_restores_only_selected_conversation() -> None:
    service = ChatService()
    service.restore_conversation(
        [
            {"role": "user", "content": "Tôi ký hợp đồng 2 năm."},
            {"role": "assistant", "content": "Đã ghi nhận."},
        ]
    )
    assert service.chain.memory.accumulated_facts["contract_term"] == "2 năm"

    service.restore_conversation(
        [
            {"role": "user", "content": "Tôi có bằng đại học."},
            {"role": "assistant", "content": "Đã ghi nhận."},
        ]
    )
    assert "contract_term" not in service.chain.memory.accumulated_facts
    assert service.chain.memory.accumulated_facts["qualification"] == "cao đẳng trở lên"


def test_session_writes_are_atomic_under_threads(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path / "history.json")
    conv = manager.create_conversation()

    def append(index: int) -> None:
        manager.append_message(conv["id"], "user", f"Tin nhắn {index}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(append, range(12)))

    stored = manager.get_conversation(conv["id"])
    assert stored is not None
    assert len(stored["messages"]) == 12


def test_session_rejects_invalid_role(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path / "history.json")
    conv = manager.create_conversation()
    with pytest.raises(ValueError):
        manager.append_message(conv["id"], "system", "invalid")
