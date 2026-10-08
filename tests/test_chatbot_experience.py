# -*- coding: utf-8 -*-
"""Chatbot-grade behaviour: small talk fast-track, streaming draft, live GraphRAG expansion."""
from __future__ import annotations

from typing import Any, Dict, List, cast

import pytest

from app.chat_service import answer_smalltalk
from rag.conversational import detect_smalltalk
from rag.hybrid_graph_retriever import HybridGraphRetriever
from rag.hybrid_retriever import HybridRetriever
from rag.query_router import QueryRouter
from rag.streaming import clean_draft_text, extract_partial_json_string


def test_broken_embedding_model_falls_back_to_bm25():
    class _BM25:
        def retrieve(self, q, top_k=5):
            return [{"chunk_id": "BL#d25-k1", "score": 3.2, "content": "thử việc", "metadata": {}}]

    class _CrashingDense:
        calls = 0

        def retrieve(self, q, top_k=5):
            _CrashingDense.calls += 1
            raise OSError("BAAI/bge-m3 does not appear to have a file named pytorch_model.bin")

    r = HybridRetriever(bm25_retriever=cast(Any, _BM25()), dense_retriever=cast(Any, _CrashingDense()))
    out = r.retrieve("thử việc bao lâu", top_k=3)
    assert [c["chunk_id"] for c in out] == ["BL#d25-k1"]
    assert r.dense_ready is False and ("pytorch_model.bin" in (r.dense_error or ""))
    r.retrieve("lần hai", top_k=3)
    assert _CrashingDense.calls == 1  # no repeated slow reload attempts


# --------------------------------------------------------------------------- small talk
@pytest.mark.parametrize("text,intent", [
    ("Xin chào", "greeting"),
    ("xin chao ban", "greeting"),
    ("Chào bạn nhé!", "greeting"),
    ("hi", "greeting"),
    ("Cảm ơn bạn nhiều", "thanks"),
    ("cam on", "thanks"),
    ("Bạn là ai?", "identity"),
    ("Chào bạn, bạn làm được gì?", "capabilities"),
    ("Tạm biệt", "goodbye"),
    ("ok", "ack"),
])
def test_smalltalk_detected(text, intent):
    reply = detect_smalltalk(text)
    assert reply is not None and reply.intent == intent
    assert reply.answer


@pytest.mark.parametrize("text", [
    "Xin chào, công ty nợ lương tôi 2 tháng thì sao?",
    "Chào bạn, thử việc tối đa bao lâu?",
    "Cảm ơn, vậy nghỉ việc báo trước mấy ngày?",
    "Điều 35 quy định gì?",
    "Tôi bị sa thải",
    "hợp đồng 2 năm",
    "",
])
def test_legal_questions_are_never_smalltalk(text):
    assert detect_smalltalk(text) is None


def test_router_marks_smalltalk_and_keeps_legal_routes():
    router = QueryRouter()
    assert router.route("Xin chào").strategy == "smalltalk"
    assert router.route("Thời gian thử việc tối đa là bao lâu?").strategy != "smalltalk"


def test_ui_fast_path_payload_has_no_citations_and_offers_chips():
    data = answer_smalltalk("Xin chào")
    assert data is not None
    assert data["is_smalltalk"] is True
    assert data["citations"] == [] and data["suggested_followups"]
    assert answer_smalltalk("Lương thử việc tối thiểu bao nhiêu?") is None


def test_thanks_reply_is_context_aware():
    assert "vừa rồi" in detect_smalltalk("cảm ơn", has_history=True).answer
    assert "vừa rồi" not in detect_smalltalk("cảm ơn", has_history=False).answer


# --------------------------------------------------------------------------- streaming
def test_partial_json_answer_extraction():
    assert extract_partial_json_string('{"find') is None
    assert extract_partial_json_string('{"answer": "Theo Điều 25') == "Theo Điều 25"
    assert extract_partial_json_string('{"answer": "Dòng 1\\nDòng 2\\') == "Dòng 1\nDòng 2"
    assert extract_partial_json_string('{"answer": "a \\"b\\" c", "findings": []}') == 'a "b" c'
    assert extract_partial_json_string('{"answer": "\\u0110i') == "Đi"


def test_draft_hides_evidence_tokens():
    assert clean_draft_text("Thử việc tối đa 60 ngày [E1] (E2).").strip() == "Thử việc tối đa 60 ngày ."


class _FakeChunk:
    def __init__(self, content: str):
        self.content = content


class _FakeStreamingLLM:
    def __init__(self, text: str):
        self.text = text

    def stream(self, _messages):
        for i in range(0, len(self.text), 7):
            yield _FakeChunk(self.text[i:i + 7])


def test_streamed_json_chunks_yield_growing_drafts():
    from rag import chain as chain_mod

    payload = '{"answer": "Thời gian thử việc tối đa là 60 ngày.", "findings": [], "needs_clarification": false, "out_of_scope": false}'
    drafts: List[str] = []

    fake = _FakeStreamingLLM(payload)
    parts: List[str] = []
    last = ""
    for ch in fake.stream(None):
        parts.append(ch.content)
        d = chain_mod.extract_partial_json_string("".join(parts), "answer")
        if d and d != last:
            last = d
            drafts.append(d)
    assert len(drafts) > 2
    assert drafts[-1] == "Thời gian thử việc tối đa là 60 ngày."


# --------------------------------------------------------------------------- GraphRAG
def _chunk(cid: str, doc: str, art: str, score: float) -> Dict[str, Any]:
    return {
        "chunk_id": cid, "score": score, "content": f"content {cid}", "retrieval_text": "",
        "metadata": {"doc_id": doc, "article_number": art},
    }


class _FakeBM25:
    def __init__(self, store: Dict[str, Dict[str, Any]]):
        self.store = store

    def get_chunk(self, cid: str, score: float = 0.0):
        c = self.store.get(cid)
        if c is None:
            return None
        out = dict(c)
        out["score"] = score
        return out


class _FakeGraph:
    def __init__(self, available: bool, related: List[Dict[str, Any]]):
        self.available = available
        self.related = related
        self.calls: List[Any] = []

    def is_available(self):
        return self.available

    def expand_related_chunks(self, seeds, limit=40):
        self.calls.append(seeds)
        return self.related


def _make_retriever(graph: _FakeGraph, base: List[Dict[str, Any]], store) -> HybridGraphRetriever:
    r = HybridGraphRetriever.__new__(HybridGraphRetriever)  # skip loading real indexes
    r.bm25_retriever = cast(Any, _FakeBM25(store))
    r.graph_retriever = cast(Any, graph)
    r.graph_weight = 1.2
    r.max_graph_chunks = 6
    r.max_chunks_per_related_article = 3
    r.last_graph_expansion = 0
    r.use_reranker = False
    r.reranker = None
    return r


def test_graph_offline_returns_plain_hybrid(monkeypatch):
    base = [_chunk("BL#d17", "VBHN_18_2026", "17", 0.03)]
    graph = _FakeGraph(available=False, related=[])
    r = _make_retriever(graph, base, {})
    monkeypatch.setattr("rag.hybrid_retriever.HybridRetriever.retrieve", lambda self, **kw: list(base))
    assert r.retrieve("giữ bằng gốc", top_k=5) == base
    assert graph.calls == []


def test_graph_online_adds_penalty_chunk_as_citable_evidence(monkeypatch):
    base = [
        _chunk("BL#d17-k1", "VBHN_18_2026", "17", 0.03),
        _chunk("BL#d35-k1", "VBHN_18_2026", "35", 0.02),
    ]
    store = {"ND12#d9-k2": _chunk("ND12#d9-k2", "ND_12_2022", "9", 0.0)}
    related = [
        {"seed_doc_id": "VBHN_18_2026", "seed_article": 17, "chunk_id": "ND12#d9-k2",
         "doc_id": "ND_12_2022", "article_number": 9, "relation": "PENALIZES", "b_is_source": True},
        {"seed_doc_id": "VBHN_18_2026", "seed_article": 17, "chunk_id": "MISSING#x",
         "doc_id": "X", "article_number": 1, "relation": "GUIDES", "b_is_source": True},
    ]
    graph = _FakeGraph(available=True, related=related)
    r = _make_retriever(graph, base, store)
    monkeypatch.setattr("rag.hybrid_retriever.HybridRetriever.retrieve", lambda self, **kw: [dict(c) for c in base])

    out = r.retrieve("công ty giữ bằng gốc bị phạt", top_k=5)
    ids = [c["chunk_id"] for c in out]
    assert "ND12#d9-k2" in ids                       # graph neighbour pulled in
    assert "MISSING#x" not in ids                    # never invent chunks outside the corpus
    added = next(c for c in out if c["chunk_id"] == "ND12#d9-k2")
    assert added["retrieval_source"] == "graph" and added["graph_relation"] == "PENALIZES"
    assert r.last_graph_expansion == 1
    assert graph.calls and {"doc_id": "VBHN_18_2026", "number": 17} in graph.calls[0]


def test_chain_uses_graph_retriever_by_default():
    import inspect
    from rag import chain as chain_mod
    src = inspect.getsource(chain_mod.VietLaborRAGChain.__init__)
    assert "HybridGraphRetriever(" in src


def test_internship_no_hardcoded_leak_and_proper_grounding():
    from rag.chain import VietLaborRAGChain
    chain = VietLaborRAGChain()
    chain.memory.clear()
    r1 = chain.run("tôi là sinh viên đi thực tập thì có cần kí hợp đồng lao động hong")
    assert r1.validated_response.needs_clarification is True

    r2 = chain.run("Thực tập theo trường (có giấy giới thiệu)")
    assert "chị trang" not in r2.answer.lower()
    assert "bốc vác" not in r2.answer.lower()
    assert "qc" not in r2.answer.lower()
    assert any(k in r2.answer.lower() for k in ["không cần", "không bắt buộc", "không phải", "chưa phải", "không thuộc", "không có nghĩa vụ", "chưa cần", "tùy thuộc", "điều 13", "điều 61"]), f"Unexpected answer: {r2.answer}"


def test_wage_underpayment_and_unauthorized_fee_deduction():
    from rag.chain import VietLaborRAGChain
    chain = VietLaborRAGChain()
    chain.memory.clear()
    q = "tôi là sinh viên mới ra trường và được nhận fesher tại 1 cty tư nhân . Deal lương lúc đầu là khoảng 8 triệu sau đó cty chỉ trả cho tôi tầm 5tr với lý do 3 triệu làm phí gì đó . Trong trường hợp này cty đang vi phạm luật nào và hướng xử lý là gì"
    res = chain.run(q)
    assert res is not None
    assert not res.validated_response.abstain
    cited = res.validated_response.cited_chunk_ids
    # Verify core wage provisions are grounded
    assert any("d94" in cid or "d102" in cid or "d188" in cid or "d23" in cid or "d17" in cid for cid in cited)
    # Ensure strike appendix is never cited
    assert not any("pl6" in cid.lower() or "danh-m-c" in cid.lower() for cid in cited)
    # Ensure answer explains violation and remedy clearly
    ans = res.answer.lower()
    assert any(k in ans for k in ["94", "102", "khấu trừ", "nguyên tắc trả lương"])


def test_workplace_accident_fall_compensation():
    from rag.chain import VietLaborRAGChain
    from rag.issue_decomposer import IssueDecomposer
    q = "tôi làm cho cty lao động và tôi bị té thì tôi có được bồi thường hay gì không"
    issues = IssueDecomposer().decompose(q)
    assert len(issues) == 1
    assert "tôi, gì không" not in issues[0].raw_issue_text

    chain = VietLaborRAGChain()
    chain.memory.clear()
    res = chain.run(q)
    assert res is not None
    assert not res.validated_response.abstain
    cited = res.validated_response.cited_chunk_ids
    assert any("d38" in cid or "d39" in cid or "d45" in cid for cid in cited)
    ans = res.answer.lower()
    assert any(k in ans for k in ["bồi thường", "tai nạn", "y tế", "tiền lương", "điều trị", "38"])
