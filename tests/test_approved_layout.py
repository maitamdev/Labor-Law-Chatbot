"""Ensure the new UI does not execute message markup or weaken source links."""
from ui.components.approved_layout import layout_markup, render_citations, render_messages


def test_message_markup_and_history_titles_cannot_inject_html():
    messages = [
        {'id': 'user', 'role': 'user', 'content': '<img src=x onerror=alert(1)>'},
        {'id': 'assistant', 'role': 'assistant', 'content': '<script>alert(1)</script>\n\n[bad](javascript:alert(1))', 'structured_data': {}},
    ]
    rendered = render_messages(messages, False)
    assert '<script>' not in rendered
    assert '<img src=x' not in rendered
    assert 'href="javascript:' not in rendered
    assert '&lt;script&gt;' in rendered
    history = [{'id': 'test', 'title': '"><img src=x onerror=alert(1)>'}]
    markup = layout_markup('home', [], history, False, 'test')
    assert '<img src=x' not in markup
    assert '&lt;img src=x' in markup


def test_citations_keep_official_url_restrictions_and_deduplication():
    citations = [
        {'chunk_id': 'test', 'document_title': 'Source', 'article': '1', 'excerpt': '<script>unsafe</script>', 'source_url': 'javascript:alert(1)', 'deep_link_url': 'https://attacker.test/document'},
        {'chunk_id': 'test', 'document_title': 'Duplicate'},
        {'chunk_id': 'valid', 'document_title': 'Official', 'source_url': 'https://congbao.chinhphu.vn/document'},
    ]
    rendered = render_citations({'citations': citations})
    assert 'attacker.test' not in rendered
    assert 'javascript:' not in rendered
    assert 'Duplicate' not in rendered
    assert '<script>' not in rendered
    assert 'https://congbao.chinhphu.vn/document' in rendered
    assert 'rel="noopener noreferrer"' in rendered
    assert render_citations({'citations': citations, 'needs_clarification': True}) == ''


def test_citations_group_same_document_without_losing_provisions():
    citations = [
        {'chunk_id': f'LABOR#d125-k{i}', 'document_title': 'Bộ luật Lao động',
         'document_number': '45/2019/QH14', 'article': '125', 'clause': str(i),
         'excerpt': f'Nội dung khoản {i}.', 'source_url': 'https://congbao.chinhphu.vn/source'}
        for i in range(1, 5)
    ]
    citations.append({'chunk_id': 'DECREE#d70', 'document_title': 'Nghị định hướng dẫn',
                      'document_number': '145/2020/NĐ-CP', 'article': '70'})
    rendered = render_citations({'citations': citations + [citations[0]]})
    assert rendered.count('class="citation-group"') == 2
    assert rendered.count('class="citation"') == 5
    assert rendered.count('Bộ luật Lao động') == 1
    assert '4 trích dẫn' in rendered
    assert '<details class="citation-group" open' not in rendered
    for i in range(1, 5):
        assert f'Điều 125 · Khoản {i}' in rendered
        assert f'Nội dung khoản {i}.' in rendered


def test_busy_chat_disables_submissions_and_preserves_grounding_notice():
    message = {'id': 'a', 'role': 'assistant', 'content': 'Answer', 'structured_data': {'evidence_coverage': {'total_issue_count': 2, 'complete_issue_count': 1}, 'unresolved_issue_ids': ['missing'], 'suggested_followups': ['Clarify?']}}
    markup = layout_markup('chat', [message], [], True, 'test')
    assert 'data-busy="true"' in markup
    assert 'maxlength="2000"' in markup
    assert 'type="submit" disabled' in markup
    assert 'Các vấn đề còn thiếu đã bị chặn kết luận.' in markup
    assert 'data-event="regenerate"' not in markup
    assert 'data-query="Clarify?"' in markup


def test_responsive_breakpoints_remain_valid_after_desktop_scaling(monkeypatch):
    from typing import Any, cast

    from ui.components import approved_layout
    approved_layout.get_surface.cache_clear()
    monkeypatch.setattr(approved_layout, 'component', lambda name, **kwargs: kwargs)
    definition = cast(dict[str, Any], approved_layout.get_surface())
    css = definition['css']
    assert '@media (max-width:1100px)' in css
    assert '@media (max-width:760px)' in css
    assert '--u:1px' in css
    assert '@media (max-width:calc(' not in css
    assert '/app/static/approved-homepage.png' in css
    approved_layout.get_surface.cache_clear()


def test_templates_view_renders_all_eight_full_templates():
    import html
    import json

    from ui.utils.legal_templates import LEGAL_TEMPLATES

    assert len(LEGAL_TEMPLATES) == 8
    markup = layout_markup('templates', [], [], False, '')

    # All 8 templates rendered as cards with both view and AI actions
    for t in LEGAL_TEMPLATES:
        assert f'data-template="{t["id"]}"' in markup
        assert f'data-query="{html.escape(t["query"])}"' in markup
        assert html.escape(t['title']) in markup
        assert len(t['content']) > 500

    # JSON dataset embedded for instant client-side modal viewing and copying
    assert '<script type="application/json" id="vl-templates-data">' in markup
    start = markup.index('<script type="application/json" id="vl-templates-data">') + len('<script type="application/json" id="vl-templates-data">')
    end = markup.index('</script>', start)
    embedded = json.loads(markup[start:end])
    assert len(embedded) == 8
    assert embedded[0]['id'] == 'hop_dong_lao_dong'


def test_answers_offer_pdf_export_but_smalltalk_does_not():
    messages = [
        {'id': 'q', 'role': 'user', 'content': 'Thử việc tối đa bao lâu?'},
        {'id': 'a1', 'role': 'assistant', 'content': 'Tối đa 60 ngày.', 'structured_data': {}},
        {'id': 'a2', 'role': 'assistant', 'content': 'Xin chào!', 'structured_data': {'is_smalltalk': True}},
    ]
    rendered = render_messages(messages, False)
    assert 'data-export="a1"' in rendered
    assert 'data-export="a2"' not in rendered


def test_header_opens_real_email_login_and_upload_excludes_legacy_doc():
    markup = layout_markup('home', [], [], False, '')
    assert 'data-dialog="login"' not in markup
    assert 'data-auth-open="login"' in markup
    assert 'name="username" type="email"' in markup
    assert 'accept=".txt,.pdf,.docx"' in markup


def test_progressive_typing_attribute_on_new_assistant_message():
    messages = [
        {'id': 'q', 'role': 'user', 'content': 'Thử việc tối đa bao lâu?'},
        {'id': 'a1', 'role': 'assistant', 'content': 'Tối đa 60 ngày.', 'structured_data': {}},
    ]
    # Without typing_id: no typing class or attribute
    static_rendered = render_messages(messages, False, typing_id='')
    assert 'data-typing="true"' not in static_rendered
    assert 'is-typing' not in static_rendered

    # With typing_id: activates typewriter streaming reveal
    typing_rendered = render_messages(messages, False, typing_id='a1')
    assert 'data-typing="true"' in typing_rendered
    assert 'is-typing' in typing_rendered
    assert 'data-msg-id="a1"' in typing_rendered

