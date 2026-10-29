"""Regressions found by the project audit, without network or production writes."""

from __future__ import annotations

import json
import pickle
import sqlite3
import sys
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from types import SimpleNamespace

import pytest

from config import settings
from rag import embeddings
from rag.bm25_retriever import BM25Retriever
from rag.embeddings import LocalBGEEmbeddings, format_retrieval_text, get_parent_clause_map
from rag.vectorstore import LegalVectorStore
from scripts.health_check import run_health_checks
from ui.utils.session import SessionManager


@pytest.mark.parametrize("nested", [False, True])
def test_evidence_scoring_handles_nullable_corpus_metadata(nested):
    from rag.evidence_selector import EvidenceSelector
    from rag.legal_issue_parser import LegalIssueParser

    metadata = {
        "chunk_id": "nullable",
        "doc_id": None,
        "article_title": None,
        "content": None,
        "article_number": "²",
        "clause_number": None,
    }
    chunk = {"metadata": metadata, "content": None} if nested else metadata
    scored = EvidenceSelector().score_candidate(LegalIssueParser().parse("Tiền lương"), chunk)
    assert scored.chunk_id == "nullable"
    assert scored.article_title == ""
    assert scored.content == ""
    assert scored.article_number is None


def write_corpus(path, content, chunk_id="D#d1-k1"):
    row = {
        "chunk_id": chunk_id,
        "doc_id": "D",
        "article_number": "1",
        "clause_number": "1",
        "content": content,
    }
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return row


def test_parent_clauses_follow_corpus_and_revision(tmp_path):
    first, second = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_corpus(first, "Corpus A")
    row = write_corpus(second, "Corpus B")
    assert get_parent_clause_map(first)[("D", "1", "1")] == "Corpus A"
    assert get_parent_clause_map(second)[("D", "1", "1")] == "Corpus B"
    row.update(point="a", content="Point content")
    assert "Corpus B" in format_retrieval_text(row, corpus_path=second)
    write_corpus(first, "Updated and longer clause")
    assert get_parent_clause_map(first)[("D", "1", "1")] == "Updated and longer clause"


def test_context_builders_keep_independent_corpus_snapshots(tmp_path):
    from rag.context_builder import ContextBuilder

    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    write_corpus(first, "First corpus")
    write_corpus(second, "Second corpus")
    a, b = ContextBuilder(corpus_path=str(first)), ContextBuilder(corpus_path=str(second))
    assert a._get_chunk_by_id("D#d1-k1")["content"] == "First corpus"
    assert b._get_chunk_by_id("D#d1-k1")["content"] == "Second corpus"
    assert a._get_chunk_by_id("D#d1-k1")["content"] == "First corpus"
    write_corpus(first, "Updated corpus with longer content")
    fresh = ContextBuilder(corpus_path=str(first))
    assert fresh._get_chunk_by_id("D#d1-k1")["content"] == "Updated corpus with longer content"
    assert a._get_chunk_by_id("D#d1-k1")["content"] == "First corpus"


def test_chain_uses_retriever_corpus_for_context_and_anchors(tmp_path):
    from rag.chain import VietLaborRAGChain

    corpus = tmp_path / "custom.jsonl"
    write_corpus(corpus, "custom data")
    retriever = SimpleNamespace(bm25_retriever=SimpleNamespace(corpus_path=corpus))
    chain = VietLaborRAGChain(hybrid_retriever=retriever, llm_manager=SimpleNamespace())
    assert chain.context_builder._get_chunk_by_id("D#d1-k1")["content"] == "custom data"
    assert chain.qa_anchor_index.corpus_path == corpus


@pytest.mark.parametrize("batch", [None, {}, "invalid", [1]])
def test_accounts_reject_malformed_row_responses(batch):
    from app.accounts import AccountError, Accounts
    from config.supabase import SupabaseConfig

    account = Accounts(SupabaseConfig(), transport=SimpleNamespace())
    account.rest = lambda *args, **kwargs: batch
    with pytest.raises(AccountError, match="không hợp lệ"):
        account.rows("profiles")


def test_admin_preload_honors_injected_transports():
    from app.admin_service import AdminService

    client = SimpleNamespace(
        require_admin=lambda: None,
        admin_permissions=lambda: {"manage_admins": False, "configured": True},
        rows=lambda table, **kwargs: [{"table": table}],
        rpc=lambda name: [] if name == "my_feedback" else {"users": 1},
    )
    data = AdminService(client).load("admin-dashboard", preload_all=True)
    assert data["profiles"] == [{"table": "profiles"}]
    assert data["legal_documents"] == [{"table": "legal_documents"}]
    assert "admin_invitations" not in data
    assert data["privacy_configured"] is True


@pytest.fixture
def fake_models(monkeypatch):
    created, encoded = [], []

    class Model:
        def __init__(self, name, **kwargs):
            assert kwargs["local_files_only"] is True
            created.append(name)
            self.name = name

        def encode(self, text, **kwargs):
            encoded.append((self.name, text))
            return SimpleNamespace(tolist=lambda: [1.0 if self.name == "model-a" else 2.0])

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=Model))
    monkeypatch.setattr(LocalBGEEmbeddings, "_models", {})
    monkeypatch.setattr(LocalBGEEmbeddings, "_model_locks", {})
    monkeypatch.setattr(LocalBGEEmbeddings, "_query_cache", OrderedDict())
    return created, encoded


def test_embedding_cache_is_scoped_to_model_and_returns_copies(fake_models):
    a = LocalBGEEmbeddings("model-a", device="cpu")
    b = LocalBGEEmbeddings("model-b", device="cpu")
    result = a.embed_query("same query")
    result[0] = 999
    assert b.embed_query("same query") == [2.0]
    assert a.embed_query("same query") == [1.0]
    assert fake_models[0] == ["model-a", "model-b"]
    assert len(fake_models[1]) == 2


def test_concurrent_embedding_load_and_query_are_shared_once(fake_models):
    def query(_):
        return LocalBGEEmbeddings("model-a", device="cpu").embed_query("one")

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(query, range(16))) == [[1.0]] * 16
    assert fake_models[0] == ["model-a"]
    assert len(fake_models[1]) == 1


def test_embedding_cache_is_bounded_lru(fake_models):
    model = LocalBGEEmbeddings("model-a", device="cpu")
    for index in range(512):
        model.embed_query(str(index))
    model.embed_query("0")
    model.embed_query("512")
    assert len(model._query_cache) == 512
    assert (*model._model_key, "0", True) in model._query_cache
    assert (*model._model_key, "1", True) not in model._query_cache


def test_failed_embedding_never_substitutes_a_different_model(fake_models, monkeypatch):
    calls = []

    def fail(name, **kwargs):
        calls.append(name)
        raise OSError("model missing")

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=fail))
    with pytest.raises(OSError, match="model missing"):
        LocalBGEEmbeddings("missing-model", device="cpu").embed_query("query")
    assert calls == ["missing-model"]


def test_default_embedding_model_does_not_depend_on_other_cached_models(monkeypatch):
    monkeypatch.delenv("EMBEDDING_MODEL_NAME", raising=False)
    assert embeddings._detect_default_embedding_model() == "BAAI/bge-m3"
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", " model-b ")
    assert embeddings._detect_default_embedding_model() == "model-b"


def test_relative_config_paths_are_independent_of_launch_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIETLABOR_TEST_PATH", "storage/custom")
    assert settings._project_path("VIETLABOR_TEST_PATH", tmp_path) == settings.PROJECT_ROOT / "storage/custom"
    monkeypatch.setenv("VIETLABOR_TEST_PATH", " ")
    assert settings._project_path("VIETLABOR_TEST_PATH", tmp_path) == tmp_path


def test_session_snapshots_do_not_mutate_private_cache(tmp_path):
    manager = SessionManager(tmp_path / "history.json")
    conversation = manager.create_conversation()
    manager.append_message(conversation["id"], "user", "original", structured_data={"citations": ["one"]})
    snapshot = manager.load_conversations()
    snapshot[0]["messages"][0]["structured_data"]["citations"].append("injected")
    assert manager.get_conversation(conversation["id"])["messages"][0]["structured_data"]["citations"] == ["one"]
    manager.save_conversations(snapshot)
    snapshot[0]["messages"].clear()
    assert len(manager.get_conversation(conversation["id"])["messages"]) == 1


def test_failed_history_write_is_reported_without_mutating_cache(tmp_path, monkeypatch):
    import ui.utils.session as session

    manager = SessionManager(tmp_path / "history.json")
    conversation = manager.create_conversation()
    before = manager.storage_path.read_bytes()

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(session.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        manager.append_message(conversation["id"], "user", "unsaved")
    assert manager.get_conversation(conversation["id"])["messages"] == []
    assert manager.storage_path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("pointer", [[], None, {"version": None}, {"version": 123}, {"version": "invalid"}])
def test_invalid_active_index_pointer_falls_back(tmp_path, monkeypatch, pointer):
    from app import admin_jobs

    path = tmp_path / "active.json"
    path.write_text(json.dumps(pointer), encoding="utf-8")
    monkeypatch.setattr(admin_jobs, "POINTER", path)
    assert admin_jobs.active_index() is None


def test_health_check_uses_configured_paths_and_isolates_storage_errors(tmp_path, monkeypatch):
    chroma, bm25, corpus = tmp_path / "chroma", tmp_path / "bm25", tmp_path / "corpus.jsonl"
    chroma.mkdir()
    bm25.mkdir()
    write_corpus(corpus, "clause")
    (chroma / "chroma.sqlite3").write_bytes(b"broken")
    (bm25 / "index_meta.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(settings, "CHROMA_INDEX_DIR", chroma)
    monkeypatch.setattr(settings, "BM25_INDEX_DIR", bm25)
    monkeypatch.setattr(settings, "PRODUCTION_CORPUS_PATH", corpus)
    result = run_health_checks()
    assert result["config_loaded"] is True
    assert result["corpus_chunks"] == 1
    assert "chroma_error" in result and "bm25_error" in result
    assert result["index_counts_match"] is False
    monkeypatch.setattr(settings, "CHROMA_INDEX_DIR", tmp_path / "absent")
    assert run_health_checks()["vector_db_exists"] is False


def test_health_check_counts_only_production_collection(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CHROMA_INDEX_DIR", tmp_path)
    with closing(sqlite3.connect(tmp_path / "chroma.sqlite3")) as con:
        con.executescript("""
            CREATE TABLE collections(id TEXT, name TEXT);
            CREATE TABLE segments(id TEXT, collection TEXT);
            CREATE TABLE embeddings(segment_id TEXT);
            INSERT INTO collections VALUES ('a', 'vietlabor_chunks_v3'), ('b', 'other');
            INSERT INTO segments VALUES ('sa', 'a'), ('sb', 'b');
            INSERT INTO embeddings VALUES ('sa'), ('sb'), ('sb');
        """)
    assert run_health_checks()["chroma_chunks"] == 1


def test_bm25_rebuild_invalidates_chunk_lookup_with_same_count(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, "alpha clause", chunk_id="old")
    retriever = BM25Retriever(tmp_path / "bm25", corpus, tokenizer_mode="whitespace")
    retriever.build_index()
    assert retriever.get_chunk("old") is not None
    write_corpus(corpus, "beta clause", chunk_id="new")
    retriever.build_index(force=True)
    assert retriever.get_chunk("old") is None
    assert retriever.get_chunk("new")["content"] == "beta clause"


@pytest.mark.parametrize("top_k", [0, -1])
def test_empty_retrieval_limit_does_not_load_indexes(tmp_path, top_k):
    assert BM25Retriever(tmp_path / "bm25", tmp_path / "missing").retrieve("query", top_k=top_k) == []
    assert LegalVectorStore(tmp_path / "chroma").query("query", top_k=top_k) == []


def test_vector_rebuild_ignores_unverified_legacy_backup(tmp_path, monkeypatch):
    from rag import vectorstore

    corpus = tmp_path / "corpus.jsonl"
    write_corpus(corpus, "new content", chunk_id="chunk")
    persist = tmp_path / "chroma"
    monkeypatch.setattr(vectorstore, "DEFAULT_PERSIST_DIR", persist)
    (tmp_path / "bge_m3_vectors_backup.pkl").write_bytes(pickle.dumps({"chunk": [9.0, 9.0, 9.0]}))
    encoded, stored = [], []

    def encode(texts, **kwargs):
        encoded.extend(texts)
        return [[1.0, 2.0, 3.0] for _ in texts]

    model = SimpleNamespace(model_name="test", dimension=3, device="cpu", embed_documents=encode)
    collection = SimpleNamespace(
        get=lambda **kwargs: {"ids": [], "documents": [], "metadatas": []},
        count=lambda: len(stored),
        upsert=lambda **kwargs: stored.extend(kwargs["embeddings"]),
    )
    store = LegalVectorStore(persist, corpus_path=corpus, embedding_model=model)
    store.client = SimpleNamespace(
        get_or_create_collection=lambda **kwargs: collection, delete_collection=lambda **kwargs: None
    )
    store.build_index(force=True)
    assert len(encoded) == 1 and "new content" in encoded[0]
    assert stored == [[1.0, 2.0, 3.0]]


def test_runtime_dependency_manifests_match():
    import tomllib

    from packaging.requirements import Requirement

    root = settings.PROJECT_ROOT
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = {
        Requirement(line).name: str(Requirement(line).specifier)
        for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    for dependency in project["project"]["dependencies"]:
        requirement = Requirement(dependency)
        assert manifest[requirement.name] == str(requirement.specifier)
