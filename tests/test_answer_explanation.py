"""Keep complete legal explanations and their supporting provisions available."""

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.chat_service import ChatService
from rag.answer_quality import needs_overview_expansion, overview_evidence_is_complete
from rag.chain import VietLaborRAGChain
from rag.context_builder import ContextBuilder
from rag.output_validator import ValidatedResponse
from rag.statutory_constraints import StatutoryConstraintEngine


def test_dismissal_context_contains_cases_procedure_and_protected_periods():
    question = 'Quy định về sa thải người lao động?'
    plan = StatutoryConstraintEngine().plan(question)
    builder = ContextBuilder(max_context_chars=5500, max_chunks=8)
    context = builder.build_context([], query=question, expand_siblings=False,
                                    priority_chunk_ids=plan.priority_chunk_ids)
    blocks = {block.chunk_id: block.content for block in context.evidence_blocks}
    for clause in range(1, 5):
        assert f'VBHN_18_2026#d125-k{clause}' in blocks
    procedure = blocks['VBHN_18_2026#d122-k1']
    assert 'chứng minh' in procedure
    assert 'bào chữa' in procedure
    assert 'biên bản' in procedure
    protections = blocks['VBHN_18_2026#d122-k4']
    for phrase in ['ốm đau', 'tạm giữ', 'điều tra', 'mang thai', 'dưới 12 tháng']:
        assert phrase in protections
    assert len(context.prompt_context) <= 5500


def test_a_point_does_not_inherit_other_points_from_its_clause():
    builder = ContextBuilder()
    point = builder._get_chunk_by_id('VBHN_18_2026#d122-k4-b')
    assert point is not None
    context = builder.build_context([point], expand_siblings=False, enforce_statutory_bridge=False)
    content = context.evidence_blocks[0].content
    assert 'Không được xử lý kỷ luật' in content
    assert 'tạm giữ' in content
    assert 'mang thai' not in content


def test_overview_expansion_respects_brief_requests_and_limited_evidence():
    summary = 'Sa thải chỉ được áp dụng theo Điều 125 và đúng thủ tục.'
    assert needs_overview_expansion('Quy định về sa thải?', summary, 8)
    assert not needs_overview_expansion('Tóm tắt ngắn gọn quy định về sa thải?', summary, 8)
    assert not needs_overview_expansion('Thử việc tối đa bao nhiêu ngày?', summary, 8)
    assert not needs_overview_expansion('Quy định về sa thải?', summary, 1)


def test_citing_a_single_point_does_not_cover_its_whole_clause():
    builder = ContextBuilder()
    plan = StatutoryConstraintEngine().plan('Quy định về sa thải người lao động?')
    context = builder.build_context([], expand_siblings=False, enforce_statutory_bridge=False,
                                    priority_chunk_ids=plan.priority_chunk_ids)
    blocks = [block for block in context.evidence_blocks if block.article_number == 122 and block.clause_number == 1]
    point = next(block for block in blocks if block.point)
    clause = next(block for block in blocks if not block.point)
    assert not overview_evidence_is_complete(blocks, [point.evidence_id])
    assert overview_evidence_is_complete(blocks, [clause.evidence_id])


@pytest.mark.parametrize('retry_kind', ['complete', 'partial', 'unsupported', 'still_short', 'sparse'])
def test_thin_overview_gets_one_grounded_retry(retry_kind):
    question = 'Quy định về sa thải người lao động?'
    builder = ContextBuilder(max_context_chars=5500, max_chunks=8)
    plan = StatutoryConstraintEngine().plan(question)
    context = builder.build_context([], query=question, expand_siblings=False,
                                    priority_chunk_ids=plan.priority_chunk_ids)
    summary = 'Sa thải chỉ được áp dụng theo Điều 125 và đúng thủ tục tại Điều 122.'
    if retry_kind == 'sparse':
        summary = 'Sa thải chỉ được áp dụng trong các trường hợp luật định và phải tuân thủ thủ tục xử lý kỷ luật.'
    explanation = '### Các trường hợp và điều kiện áp dụng\n\n' + '\n\n'.join(
        block.content for block in context.evidence_blocks
        if block.chunk_id != 'VBHN_18_2026#d122-k1-a'
    )
    explanation = explanation.replace('theo quy định tại Điều 126 của Bộ luật này', 'theo quy định về xóa kỷ luật')
    evidence_ids = [block.evidence_id for block in context.evidence_blocks]
    calls = []

    def invoke(messages):
        calls.append(messages)
        answer = summary if len(calls) == 1 or retry_kind in {'still_short', 'sparse'} else explanation
        ids = ['E999'] if len(calls) > 1 and retry_kind == 'unsupported' else evidence_ids
        if retry_kind == 'sparse':
            ids = evidence_ids[:1]
        if len(calls) > 1 and retry_kind == 'partial':
            ids = evidence_ids[:2]
        return SimpleNamespace(content=json.dumps({
            'answer': answer, 'needs_clarification': False, 'out_of_scope': False,
            'findings': [{'issue_id': 'issue_1', 'issue': question,
                          'conclusion': answer, 'evidence_ids': ids}],
        }, ensure_ascii=False))

    manager = SimpleNamespace(get_llm=lambda: SimpleNamespace(invoke=invoke))
    retriever = SimpleNamespace(bm25_retriever=SimpleNamespace(corpus_path=builder.corpus_path))
    chain = VietLaborRAGChain(hybrid_retriever=cast(Any, retriever), llm_manager=cast(Any, manager))
    issues = chain.decomposer.decompose(question)
    case = chain.case_analyzer.analyze(question, issues)
    premise = chain.premise_gate.evaluate(chain.issue_parser.parse(question))
    result = chain._generate_and_validate(
        question, question, chain.router.route(question), premise, [], [], {}, issues, case, {},
    )
    answer = chain._answer_body(result['validated_resp'].final_answer)
    assert len(calls) == 2
    if retry_kind == 'complete':
        assert 'Các trường hợp và điều kiện áp dụng' in answer
        assert 'biên bản' in answer
        assert 'mang thai' in answer
    else:
        assert 'Nguyên tắc, trình tự, thủ tục xử lý kỷ luật lao động' in answer
        assert 'Áp dụng hình thức xử lý kỷ luật sa thải' in answer
        assert all(term in answer for term in ('05 ngày', '30 ngày', '20 ngày', '365 ngày'))
        assert '\n\nTheo Khoản' not in answer
        assert 'mang thai' in answer
        assert result['validated_resp'].is_fully_grounded
        assert not result['validated_resp'].phantom_citations


@pytest.mark.parametrize('with_footer', [False, True])
def test_ui_preserves_analysis_after_citation_heading_and_full_source(with_footer):
    explanation = (
        'Cần đối chiếu điều kiện áp dụng.\n\nCĂN CỨ PHÁP LÝ:\n'
        'Điều 125 quy định các trường hợp sa thải.\n\n'
        'PHÂN TÍCH:\nCần kiểm tra hành vi, chứng cứ và thủ tục trong trường hợp cụ thể.'
    )
    footer = 'CĂN CỨ PHÁP LÝ:\n[1] Bộ luật Lao động, Điều 125.' if with_footer else ''
    notice = 'Lưu ý: giữ lại thông báo sau phần căn cứ.'
    full_source = 'Nội dung khoản được dùng để trả lời. ' * 20 + 'Điểm cuối cần kiểm tra.'
    cid = 'TEST#d125-k1'
    response = ValidatedResponse(raw_answer=explanation,
                                 final_answer=explanation + '\n\n' + footer + '\n\n' + notice,
                                 formatted_citations=footer, cited_chunk_ids=[cid], rejected_chunk_ids=[])
    result = SimpleNamespace(
        is_smalltalk=False, validated_response=response,
        formatted_context=SimpleNamespace(chunk_metadata_registry={
            cid: {'document_title': 'Bộ luật Lao động', 'article_number': 125,
                  'clause_number': 1, 'content': full_source},
        }),
        retrieved_chunks=[{'chunk_id': cid, 'content': 'Câu dẫn chưa đầy đủ:'}],
        route_decision=SimpleNamespace(strategy='hybrid'), total_latency_ms=1,
        locked_chunk_ids=[cid], retrieval_method='test', graph_expanded_chunk_ids=[],
    )
    chain = SimpleNamespace(memory=SimpleNamespace(history=[]), run=lambda *args, **kwargs: result)
    payload = ChatService(chain=cast(Any, chain)).ask('Quy định về sa thải?', update_memory=False)
    assert 'Cần kiểm tra hành vi, chứng cứ và thủ tục' in payload['answer']
    assert notice in payload['answer']
    if footer:
        assert footer not in payload['answer']
    assert payload['citations'][0]['excerpt'] == full_source
