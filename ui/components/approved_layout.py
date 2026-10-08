"""Interactive Streamlit surface based on the approved VietLaborAI design.

Only static artwork comes from the approved preview. Forms, navigation,
document lists, conversations and citations are real accessible controls.
All external content is escaped before it enters the component DOM.
"""
from __future__ import annotations

import html
import json
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st
from markdown_it import MarkdownIt
from streamlit.components.v2 import component

from ui.components.citation_card import _safe_official_url
from ui.utils.formatting import format_provision_badge
from ui.utils.legal_templates import LEGAL_TEMPLATES

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'
FRONTEND = ROOT / 'frontend'
PROMPTS = [
    'Thời giờ làm việc tối đa là bao nhiêu?',
    'Nghỉ phép năm được bao nhiêu ngày?',
    'Quy định về sa thải người lao động?',
    'Hợp đồng lao động có những loại nào?',
]
NAVIGATION = [
    ('home', 'Trang chủ', 'home-filled'),
    ('chat', 'Trợ lý AI', 'message-circle'),
    ('documents', 'Tra cứu văn bản', 'file-description'),
    ('topics', 'Chủ đề pháp luật', 'books'),
    ('templates', 'Mẫu văn bản', 'file-text'),
    ('situations', 'Tình huống thực tế', 'scale'),
    ('faq', 'Câu hỏi thường gặp', 'help-circle'),
    ('news', 'Tin tức - Cập nhật', 'speakerphone'),
    ('about', 'Giới thiệu', 'info-circle'),
]
DOCUMENTS = [
    ('Bộ luật Lao động 2019 (VBHN 18/VBHN-VPQH)', 'Văn bản gốc quy định toàn diện quan hệ lao động, hợp đồng, tiền lương, thời giờ làm việc và kỷ luật', 'https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm'),
    ('Nghị định 145/2020/NĐ-CP', 'Quy định chi tiết và hướng dẫn thi hành Bộ luật Lao động về điều kiện lao động và quan hệ lao động', 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm'),
    ('Nghị định 12/2022/NĐ-CP', 'Quy định xử phạt vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội và đưa NLĐ đi nước ngoài', 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-12-2022-nd-cp-35116.htm'),
    ('Thông tư 10/2020/TT-BLĐTBXH', 'Hướng dẫn thi hành nội dung hợp đồng lao động, phụ cấp lương, tiền thưởng và hội đồng thương lượng', 'https://congbao.chinhphu.vn/van-ban/thong-tu-so-10-2020-tt-bldtbxh-32709.htm'),
    ('Nghị định 38/2022/NĐ-CP (Lương tối thiểu vùng)', 'Quy định mức lương tối thiểu vùng theo tháng và theo giờ áp dụng đối với người lao động', 'https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-38-2022-nd-cp-35805.htm'),
    ('Nghị định 337/2025/NĐ-CP (HĐLĐ điện tử)', 'Quy định chi tiết về giao kết, sửa đổi và thực hiện hợp đồng lao động điện tử theo chuẩn pháp lý', 'https://congbao.chinhphu.vn'),
    ('Luật Bảo hiểm xã hội (VBHN 19/VBHN-VPQH)', 'Quy định các chế độ ốm đau, thai sản, tai nạn lao động, bệnh nghề nghiệp, hưu trí và tử tuất', 'https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-19-vbhn-vpqh-468972.htm'),
    ('Luật An toàn, vệ sinh lao động (Số 84/2015/QH13)', 'Quy định các biện pháp bảo đảm an toàn, vệ sinh lao động và chế độ bồi thường tai nạn lao động', 'https://congbao.chinhphu.vn/van-ban/luat-an-toan-ve-sinh-lao-dong-2015-20412.htm'),
]


def esc(value) -> str:
    return html.escape(str(value or ''), quote=True)


@lru_cache(maxsize=32)
def icon(name: str) -> str:
    # Vendored Tabler icons; no runtime requests or third-party scripts.
    svg = (STATIC / 'icons' / f'{name}.svg').read_text(encoding='utf-8')
    return svg.replace('<svg ', '<svg aria-hidden="true" focusable="false" ')


def sprite(x: int, y: int, width: int, height: int, cls: str, label: str) -> str:
    """Display the approved artwork without resampling or regenerating it."""
    sx = 100 * x / (1643 - width)
    sy = 100 * y / (957 - height)
    sw = 100 * 1643 / width
    sh = 100 * 957 / height
    return (f'<span class="art-sprite {cls}" role="img" aria-label="{esc(label)}" '
            f'style="aspect-ratio:{width}/{height};--sx:{sx}%;--sy:{sy}%;--sw:{sw}%;--sh:{sh}%"></span>')


def nav_button(view: str, title: str, glyph: str, active: bool = False) -> str:
    return (f'<button class="nav-item{" active" if active else ""}" data-view="{view}" '
            f'{"aria-current=page" if active else ""}>{icon(glyph)}<span>{esc(title)}</span></button>')


def query_button(query: str, cls: str = 'question') -> str:
    return f'<button class="{cls}" data-query="{esc(query)}"><span>{esc(query)}</span>{icon("chevron-right")}</button>'


def render_citations(data: dict) -> str:
    if data.get('needs_clarification'):
        return ''
    cards, seen = [], set()
    for citation in data.get('citations', []) or []:
        cid = citation.get('chunk_id')
        if cid and cid in seen:
            continue
        seen.add(cid)
        label = format_provision_badge(citation.get('article', ''), citation.get('clause', ''), citation.get('point', ''))
        links = []
        for field, title in [('deep_link_url', 'Mở điều khoản'), ('source_url', 'Mở nguồn văn bản')]:
            url = _safe_official_url(citation.get(field))
            if url:
                links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{title}{icon("external-link")}</a>')
        cards.append(f'<details class="citation"><summary>{icon("file-description")}<span><strong>{esc(citation.get("document_title"))}</strong><small>{esc(label)}</small></span></summary><div><p>{esc(citation.get("article_title"))}</p><blockquote>{esc(citation.get("excerpt"))}</blockquote><div class="citation-links">{"".join(links)}</div></div></details>')
    return '<h3 class="citations-title">Căn cứ pháp lý</h3>' + ''.join(cards) if cards else ''


def render_messages(messages: list[dict], busy: bool) -> str:
    markdown = MarkdownIt('commonmark', {'html': False, 'breaks': True}).enable('table')
    rows = []
    last_assistant = next((m.get('id') for m in reversed(messages) if m.get('role') == 'assistant'), None)
    for msg in messages:
        content = str(msg.get('content') or '')
        if msg.get('role') == 'user':
            att_html = ''
            att = msg.get('attachment')
            if att and isinstance(att, dict):
                att_name = esc(att.get('name', 'Tài liệu đính kèm'))
                att_size = esc(att.get('size_formatted', ''))
                att_html = (
                    f'<div class="user-attached-file">'
                    f'<span class="attached-file-icon">{icon("file-text")}</span>'
                    f'<div class="attached-file-info">'
                    f'<strong class="attached-file-name">{att_name}</strong>'
                    f'<span class="attached-file-size">{att_size}</span>'
                    f'</div></div>'
                )
            rows.append(f'<div class="user-message"><div>{att_html}{esc(content)}</div></div>')
            continue
        data = msg.get('structured_data') or {}
        mid = esc(msg.get('id'))
        answer = markdown.render(content)
        followups = ''.join(query_button(str(q), 'followup') for q in data.get('suggested_followups', []) or [])
        coverage = data.get('evidence_coverage') or {}
        coverage_html = ''
        total = int(coverage.get('total_issue_count') or 0)
        if total > 1:
            complete = int(coverage.get('complete_issue_count') or 0)
            coverage_html = f'<p class="coverage">Kiểm tra căn cứ: {complete}/{total} vấn đề đủ căn cứ.'
            if data.get('unresolved_issue_ids'):
                coverage_html += ' Các vấn đề còn thiếu đã bị chặn kết luận.'
            coverage_html += '</p>'
        actions = f'<button data-copy="{mid}" title="Sao chép câu trả lời" aria-label="Sao chép câu trả lời">{icon("copy")}</button>'
        if not data.get('is_smalltalk'):
            if msg.get('id') == last_assistant and not busy:
                actions += f'<button data-event="regenerate" title="Tạo lại câu trả lời" aria-label="Tạo lại câu trả lời">{icon("refresh")}</button>'
            for rating, glyph, title in [('up', 'thumb-up', 'Câu trả lời hữu ích'), ('down', 'thumb-down', 'Câu trả lời chưa đúng hoặc chưa đủ')]:
                actions += f'<button data-feedback="{rating}" data-message="{mid}" aria-label="{title}" title="{title}" aria-pressed="{str(msg.get("feedback") == rating).lower()}">{icon(glyph)}</button>'
        if msg.get('feedback'):
            actions += '<small>Đã ghi nhận đánh giá. Cảm ơn bạn!</small>'
        rows.append(f'<article class="assistant-message"><div class="answer-brand">{sprite(727,120,168,135,"answer-logo","VietLaborAI")}<strong>VietLaborAI</strong></div><div class="answer-markdown">{answer}</div>{coverage_html}{render_citations(data)}<div class="followups">{followups}</div><div class="message-actions">{actions}</div></article>')
    if busy:
        rows.append('<div class="thinking" role="status"><div class="thinking-spinner"><span></span><span></span><span></span></div><span class="thinking-text" id="vl-thinking-text">Đang tra cứu và đối soát căn cứ pháp lý...</span></div>')
    return ''.join(rows)


def composer(busy: bool) -> str:
    disabled = ' disabled' if busy else ''
    return f'''<form class="composer" aria-label="Đặt câu hỏi cho trợ lý pháp luật">
        <label class="sr-only" for="vl-question">Câu hỏi về luật lao động</label>
        <div class="composer-attachment-bar" style="display:none;">
            <div class="attachment-preview">
                <span class="preview-icon">{icon("file-text")}</span>
                <div class="preview-details">
                    <span class="preview-name"></span>
                    <span class="preview-size"></span>
                </div>
                <button type="button" class="preview-remove" title="Hủy tệp đính kèm" aria-label="Hủy tệp đính kèm">{icon("x")}</button>
            </div>
        </div>
        <textarea id="vl-question" name="question" maxlength="2000" placeholder="Nhập câu hỏi hoặc tải lên hợp đồng/văn bản cần tra cứu..."{disabled}></textarea>
        <input type="file" class="vl-file-input" accept=".txt,.pdf,.docx,.doc" style="display:none"{disabled}>
        <div class="composer-bottom">
            <button type="button" class="attach" data-attach-btn{disabled}>{icon('paperclip')}<span>Đính kèm văn bản</span></button>
            <div class="send-group">
                <span class="counter" aria-live="polite">0/2000</span>
                <button class="send" type="submit"{disabled}>{icon('send')}<span>Gửi câu hỏi</span></button>
            </div>
        </div>
    </form>'''


def home_suggestions() -> str:
    topics = [
        ('Hợp đồng lao động', 'Hợp đồng lao động có những loại nào & thời hạn thử việc tối đa?', 'file-text'),
        ('Tiền lương & Tăng ca', 'Cách tính lương làm thêm giờ ban đêm và ngày nghỉ lễ Tết?', 'scale'),
        ('Kỷ luật & Sa thải', 'Quy định về sa thải người lao động và điều kiện bồi thường?', 'books'),
        ('Bảo hiểm & Nghỉ phép', 'Quy định về số ngày nghỉ phép năm và chế độ bảo hiểm xã hội?', 'file-description'),
    ]
    cards = ''.join(
        f'''<button class="home-topic-card" data-query="{esc(q)}">
          <div class="home-topic-meta">
            <span class="home-topic-icon">{icon(g)}</span>
            <strong class="home-topic-cat">{esc(cat)}</strong>
          </div>
          <p class="home-topic-text">{esc(q)}</p>
          <span class="home-topic-arrow">{icon("chevron-right")}</span>
        </button>'''
        for cat, q, g in topics
    )
    return f'''<div class="home-section">
      <div class="home-section-head">
        <h2>Gợi ý tra cứu phổ biến</h2>
        <span class="home-section-sub">Bấm chọn câu hỏi để trợ lý AI giải đáp ngay</span>
      </div>
      <div class="home-topics-grid">{cards}</div>
    </div>'''


def news_cards() -> str:
    first = sprite(298,744,227,131,'article-photo','Sách pháp luật và cán cân')
    second = sprite(780,744,222,131,'article-photo','Đọc và đối chiếu hồ sơ lao động')
    return f'''<div class="home-section">
      <div class="home-section-head">
        <h2>Điểm tin & Hướng dẫn pháp luật</h2>
        <button class="text-link" data-view="news">Xem tất cả {icon('chevron-right')}</button>
      </div>
      <div class="home-news-grid">
        <button class="home-article-card" data-query="Những điều cần biết về hợp đồng lao động">
          <div class="article-thumb">{first}</div>
          <div class="article-details">
            <span class="article-badge">Cẩm nang</span>
            <strong>Những điều cần biết về hợp đồng lao động</strong>
            <p>Nội dung bắt buộc, quyền và nghĩa vụ cốt lõi của người lao động.</p>
          </div>
          {icon('chevron-right')}
        </button>
        <button class="home-article-card" data-query="Quyền lợi khi chấm dứt hợp đồng lao động">
          <div class="article-thumb">{second}</div>
          <div class="article-details">
            <span class="article-badge">Quyền lợi</span>
            <strong>Quyền lợi khi chấm dứt hợp đồng lao động</strong>
            <p>Trợ cấp thôi việc, thời hạn giải quyết chế độ và chốt sổ BHXH.</p>
          </div>
          {icon('chevron-right')}
        </button>
      </div>
      <div class="home-trust-bar">
        <span>{icon('scale')} Đối soát căn cứ chuẩn xác: Bộ luật Lao động 2019 • Nghị định 145/2020/NĐ-CP • Luật Bảo hiểm xã hội</span>
      </div>
    </div>'''


def document_row(title: str, description: str, url: str = '') -> str:
    attrs = f'href="{esc(url)}" target="_blank" rel="noopener noreferrer"' if url else 'data-view="documents"'
    tag = 'a' if url else 'button'
    return f'<{tag} class="document-row" {attrs}><span class="document-icon">{icon("file-description")}</span><span><strong>{esc(title)}</strong><small>{esc(description)}</small></span></{tag}>'


def right_panel() -> str:
    docs = ''.join(document_row(*d) for d in DOCUMENTS[:4])
    topics = [
        ('Thời giờ làm việc tối đa là bao nhiêu?', 'Thời giờ làm việc & Nghỉ ngơi'),
        ('Thời gian thử việc tối đa là bao lâu?', 'Hợp đồng & Thử việc'),
        ('Làm thêm giờ được tính lương thế nào?', 'Tiền lương & Phụ cấp'),
        ('Quy định về sa thải người lao động?', 'Kỷ luật & Tranh chấp'),
    ]
    topic_items = ''.join(
        f'<button class="quick-topic-card" data-query="{esc(q)}">'
        f'<span><strong>{esc(label)}</strong><small>{esc(q)}</small></span>{icon("chevron-right")}'
        f'</button>'
        for q, label in topics
    )
    return f'''<aside class="right-panel" aria-label="Văn bản và chủ đề tra cứu">
        <section class="documents-panel">
            <div class="panel-heading"><h2>Văn bản pháp luật nổi bật</h2><button class="text-link" data-view="documents">Xem tất cả {icon('chevron-right')}</button></div>
            <div class="document-list">{docs}</div>
        </section>
        <section class="utilities-panel">
            <h2>Chủ đề tra cứu thường gặp</h2>
            <div class="quick-topics-list">{topic_items}</div>
        </section>
    </aside>'''


def secondary_content(view: str) -> str:
    title = next((t for v, t, _ in NAVIGATION if v == view), 'VietLaborAI')
    back = f'<button class="text-link" data-view="home">{icon("home-filled")} Trang chủ</button>'

    if view == 'documents':
        content = (
            '<p class="page-intro">Cơ sở dữ liệu văn bản pháp luật lao động Việt Nam hiện hành được tích hợp trực tiếp để trợ lý AI đối chiếu, tra cứu và trích dẫn căn cứ chính xác.</p>'
            '<label class="search-label" for="document-search">Tìm kiếm theo tên văn bản, số hiệu hoặc chủ đề</label>'
            '<input id="document-search" class="document-search" type="search" placeholder="Nhập tên văn bản (ví dụ: Bộ luật Lao động, Nghị định 145, Tiền lương, BHXH...)...">'
            '<div class="searchable-documents">'
            + ''.join(document_row(*d) for d in DOCUMENTS)
            + '</div><p class="no-results" hidden>Không tìm thấy văn bản phù hợp.</p>'
            f'<div class="doc-help-card">{icon("file-description")}<div><strong>Cần tra cứu điều khoản cụ thể?</strong><p>Bạn chỉ cần nhập tình huống hoặc câu hỏi vào ô chat, trợ lý AI sẽ tự động định vị chính xác điều khoản, khoản, điểm trong văn bản gốc.</p></div></div>'
        )

    elif view == 'topics':
        topic_sections = [
            ("Hợp đồng lao động & Thử việc", "file-text", "Điều 13 - 33 BLLĐ 2019 & Thông tư 10/2020", [
                "Có mấy loại hợp đồng lao động theo Bộ luật Lao động 2019?",
                "Thời gian thử việc tối đa đối với từng vị trí công việc là bao lâu?",
                "Mức lương trong thời gian thử việc tối thiểu bằng bao nhiêu % lương chính thức?",
                "Đi làm trước khi ký hợp đồng lao động có được pháp luật bảo vệ không?",
                "Công ty có được quyền giữ bản chính bằng đại học hoặc CCCD của nhân viên không?",
            ]),
            ("Tiền lương, Làm thêm giờ & Khấu trừ lương", "scale", "Điều 90 - 104 BLLĐ 2019 & Nghị định 145/2020", [
                "Cách tính tiền lương làm thêm giờ (tăng ca) vào ban đêm và ngày nghỉ lễ Tết?",
                "Công ty chậm trả lương bao lâu thì phải trả thêm tiền lãi cho nhân viên?",
                "Mức khấu trừ tiền lương tối đa mỗi tháng là bao nhiêu %?",
                "Doanh nghiệp có bắt buộc phải trả lương tháng 13 theo luật không?",
                "Quy định về thời điểm thanh toán lương và bảng kê chi tiết tiền lương?",
            ]),
            ("Thời giờ làm việc & Nghỉ phép năm", "books", "Điều 105 - 116 BLLĐ 2019", [
                "Thời giờ làm việc bình thường tối đa là bao nhiêu giờ trong một tuần?",
                "Số giờ làm thêm tối đa trong 1 ngày, 1 tháng và 1 năm là bao nhiêu?",
                "Người lao động làm việc 1 năm được hưởng bao nhiêu ngày nghỉ phép năm?",
                "Thôi việc mà chưa nghỉ hết số ngày phép năm có được thanh toán tiền không?",
                "Quy định về số ngày nghỉ việc riêng hưởng nguyên lương khi kết hôn hoặc tang lễ?",
            ]),
            ("Kỷ luật lao động & Kỷ luật sa thải", "books", "Điều 117 - 133 BLLĐ 2019", [
                "Có bao nhiêu hình thức xử lý kỷ luật lao động theo quy định pháp luật?",
                "Những trường hợp nào doanh nghiệp được quyền sa thải người lao động?",
                "Công ty có được phạt tiền hoặc trừ lương thay cho xử lý kỷ luật lao động không?",
                "Trình tự, thủ tục xử lý kỷ luật lao động bắt buộc phải qua những bước nào?",
                "Thời hiệu xử lý kỷ luật lao động tối đa là bao nhiêu tháng?",
            ]),
            ("Chấm dứt hợp đồng lao động & Trợ cấp thôi việc", "file-description", "Điều 34 - 48 BLLĐ 2019", [
                "Người lao động muốn nghỉ việc phải báo trước bao nhiêu ngày theo từng loại hợp đồng?",
                "Những trường hợp nào người lao động được nghỉ việc ngay không cần báo trước?",
                "Điều kiện và cách tính tiền trợ cấp thôi việc khi chấm dứt hợp đồng lao động?",
                "Thời hạn tối đa công ty phải thanh toán hết tiền lương và chốt sổ BHXH khi nhân viên nghỉ việc?",
                "Quyền lợi của người lao động khi bị công ty chấm dứt hợp đồng lao động trái pháp luật?",
            ]),
            ("Chế độ Bảo hiểm xã hội, Thai sản & Tai nạn lao động", "scale", "Luật BHXH & Luật An toàn, vệ sinh lao động", [
                "Điều kiện hưởng chế độ thai sản đối với lao động nữ và lao động nam khi vợ sinh con?",
                "Mức trợ cấp ốm đau và thời gian nghỉ ốm đau tối đa được BHXH chi trả?",
                "Bị tai nạn giao thông trên đường đi làm về có được xem là tai nạn lao động không?",
                "Người lao động cần làm gì khi công ty trốn đóng hoặc nợ tiền BHXH kéo dài?",
                "Trách nhiệm bồi thường của doanh nghiệp khi xảy ra tai nạn lao động tại nơi làm việc?",
            ]),
        ]
        content = '<p class="page-intro">Tổng hợp các chuyên đề pháp luật lao động cốt lõi. Bấm vào bất kỳ câu hỏi nào để trợ lý AI giải đáp chi tiết cùng căn cứ pháp lý.</p>'
        content += ''.join(
            f'''<div class="topic-category-card">
                <div class="category-header">
                    <span class="category-icon">{icon(glyph)}</span>
                    <div>
                        <h3>{esc(cat)}</h3>
                        <small>{esc(basis)}</small>
                    </div>
                </div>
                <div class="category-questions">
                    {''.join(query_button(q) for q in qs)}
                </div>
            </div>'''
            for cat, glyph, basis, qs in topic_sections
        )

    elif view == 'templates':
        content = (
            '<p class="page-intro">Kho biểu mẫu pháp lý lao động chuẩn hóa theo quy định mới nhất của Bộ luật Lao động 2019 '
            'và các văn bản hướng dẫn thi hành. Bạn có thể <strong>xem và sao chép trực tiếp toàn văn mẫu chuẩn</strong> '
            'để sử dụng ngay hoặc bấm <strong>Nhờ AI điền thông tin</strong> để được AI hướng dẫn chi tiết theo tình huống riêng của mình.</p>'
        )
        content += '<div class="templates-grid">' + ''.join(
            f'''<div class="template-card">
                <div class="template-head">
                    <div class="template-badges">
                        <span class="template-tag">{esc(t['tag'])}</span>
                        <span class="template-basis-tag">{esc(t['basis'])}</span>
                    </div>
                    <h4>{esc(t['title'])}</h4>
                </div>
                <p class="template-desc">{esc(t['summary'])}</p>
                <div class="template-actions">
                    <button class="template-btn template-btn-view" data-template="{esc(t['id'])}">{icon("file-text")} <span>Xem toàn văn & Sao chép</span></button>
                    <button class="template-btn template-btn-ai" data-query="{esc(t['query'])}">{icon("message-circle")} <span>Nhờ AI điền thông tin</span></button>
                </div>
            </div>'''
            for t in LEGAL_TEMPLATES
        ) + '</div>'

    elif view == 'situations':
        situations_list = [
            ("Bị công ty giữ bản chính bằng đại học hoặc CCCD", "Trái pháp luật", "Công ty yêu cầu nộp bằng gốc đại học để cam kết làm việc tối thiểu 2 năm.", "Điều 17 BLLĐ 2019 nghiêm cấm giữ giấy tờ tùy thân, văn bằng. Phạt tiền từ 20 - 25 triệu đồng theo Nghị định 12/2022/NĐ-CP.", "Công ty bắt giữ bằng đại học gốc có vi phạm pháp luật không và xử lý thế nào?"),
            ("Bị ép làm thêm giờ (tăng ca) quá số giờ quy định", "Thời giờ làm việc", "Quản lý bắt buộc nhân viên ở lại làm thêm 3-4 tiếng mỗi ngày, không có thỏa thuận đồng ý.", "Phải có sự đồng ý của NLĐ; không quá 40 giờ/tháng, 200 giờ/năm (trường hợp đặc biệt 300 giờ theo Điều 107 BLLĐ).", "Công ty có được ép buộc nhân viên tăng ca không và quyền từ chối làm thêm giờ?"),
            ("Bị sa thải đột ngột hoặc chấm dứt HĐLĐ qua tin nhắn/email", "Sa thải trái luật", "Công ty báo nhân viên nghỉ việc ngay trong ngày mà không có lý do chính đáng hoặc không tổ chức họp kỷ luật.", "Sa thải trái luật: Doanh nghiệp phải nhận lại làm việc, trả đủ lương những ngày không được làm việc và bồi thường ít nhất 2 tháng lương (Điều 41).", "Bị công ty đuổi việc đột ngột qua tin nhắn có phải sa thải trái luật không?"),
            ("Công ty nợ lương, chậm trả lương quá 30 ngày", "Tiền lương", "Đã quá ngày trả lương hơn 1 tháng nhưng công ty liên tục khất nợ không có lý do bất khả kháng.", "Chậm từ 15 ngày trở lên phải trả thêm tiền lãi; chậm quá 30 ngày NLĐ có quyền đơn phương chấm dứt HĐLĐ ngay không cần báo trước (Điều 35, 97).", "Công ty chậm trả lương quá 30 ngày người lao động có quyền nghỉ việc ngay không?"),
            ("Tai nạn giao thông trên đường từ nhà đến công ty", "Tai nạn lao động", "Người lao động va chạm giao thông khi đang di chuyển trên lộ trình từ nơi ở đến nơi làm việc.", "Được hưởng chế độ tai nạn lao động nếu xảy ra trên tuyến đường và thời gian hợp lý từ nơi ở đến nơi làm việc (Điều 45 Luật An toàn VSLĐ).", "Bị tai nạn giao thông trên đường đi làm có được thanh toán chế độ tai nạn lao động không?"),
            ("Lao động nữ mang thai bị công ty chấm dứt hợp đồng", "Bảo vệ lao động nữ", "Công ty viện lý do tái cơ cấu để chấm dứt hợp đồng lao động với nhân viên đang mang thai tháng thứ 5.", "Nghiêm cấm NSDLĐ sa thải hoặc đơn phương chấm dứt HĐLĐ đối với NLĐ vì lý do mang thai, nghỉ thai sản, nuôi con dưới 12 tháng (Điều 137 BLLĐ).", "Công ty có được đuổi việc hoặc không gia hạn hợp đồng với nhân viên đang mang thai không?"),
            ("Thử việc kéo dài 3 tháng và trả lương dưới 85%", "Thử việc sai luật", "Tuyển nhân viên kinh doanh trình độ đại học nhưng bắt thử việc 3 tháng với mức lương 70%.", "Trình độ CĐ/ĐH thử việc tối đa 60 ngày; lương thử việc ít nhất 85% lương chính thức. Vi phạm bị phạt tiền và phải bồi hoàn đủ 100% lương (Điều 25, 26).", "Công ty bắt thử việc 3 tháng và trả lương 70% có đúng luật lao động không?"),
            ("Công ty tự ý trừ tiền lương do nhân viên làm hỏng hàng", "Khấu trừ lương", "Thiết bị bị hỏng hóc trong giờ làm việc, công ty tự động trừ hết 50% lương tháng mà không lập biên bản.", "Chỉ được khấu trừ bồi thường khi có thỏa thuận hoặc biên bản; mức khấu trừ không được quá 30% tiền lương tháng của NLĐ (Điều 102 BLLĐ).", "Quy định về việc công ty trừ lương nhân viên khi làm hỏng thiết bị tài sản?"),
        ]
        content = '<p class="page-intro">Các tình huống tranh chấp và rủi ro pháp lý phổ biến nhất nơi làm việc. Bấm xem cách giải quyết, căn cứ pháp lý và chế tài xử lý theo luật hiện hành.</p>'
        content += '<div class="situations-grid">' + ''.join(
            f'''<div class="situation-card">
                <div class="situation-header">
                    <span class="situation-tag">{esc(tag)}</span>
                    <h4>{esc(title)}</h4>
                </div>
                <div class="situation-body">
                    <div class="situation-fact"><strong>Tình huống:</strong> {esc(fact)}</div>
                    <div class="situation-law"><strong>Căn cứ & Chế tài:</strong> {esc(law)}</div>
                </div>
                <button class="situation-btn" data-query="{esc(q)}">{icon("scale")} <span>Giải quyết tình huống này với AI</span></button>
            </div>'''
            for title, tag, fact, law, q in situations_list
        ) + '</div>'

    elif view == 'faq':
        faq_list = [
            ("Người lao động ký hợp đồng 2 năm muốn xin nghỉ việc phải báo trước bao nhiêu ngày?",
             "Theo Điều 35 Bộ luật Lao động 2019, đối với hợp đồng lao động xác định thời hạn từ 12 tháng đến 36 tháng, người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước cho người sử dụng lao động ít nhất 30 ngày. "
             "Đặc biệt, nếu bị chậm trả lương, bị ngược đãi, đánh đập hoặc người sử dụng lao động bố trí không đúng công việc đã thỏa thuận, bạn có quyền nghỉ việc ngay lập tức mà không cần báo trước.",
             "Thời hạn báo trước khi nghỉ việc hợp đồng lao động 2 năm?"),
            ("Thời gian thử việc tối đa là bao lâu và mức lương thử việc tối thiểu là bao nhiêu?",
             "Theo Điều 25 và Điều 26 BLLĐ 2019: Thời gian thử việc tối đa là 180 ngày (người quản lý doanh nghiệp), 60 ngày (công việc có chức danh nghề nghiệp cần trình độ từ cao đẳng trở lên), 30 ngày (trung cấp, công nhân kỹ thuật), và 06 ngày làm việc đối với các công việc giản đơn khác. "
             "Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng ít nhất phải bằng 85% mức lương của công việc đó.",
             "Quy định thời gian thử việc tối đa và mức lương thử việc theo luật lao động?"),
            ("Làm thêm giờ (tăng ca) vào ban đêm và ngày nghỉ lễ Tết được tính tiền lương như thế nào?",
             "Theo Điều 98 BLLĐ 2019: Làm thêm ngày thường hưởng ít nhất 150%; ngày nghỉ hàng tuần hưởng ít nhất 200%; ngày nghỉ lễ, tết, ngày nghỉ có hưởng lương hưởng ít nhất 300% (chưa kể tiền lương ngày lễ đối với người hưởng lương ngày). "
             "Nếu làm thêm vào ban đêm (từ 22h đến 06h sáng hôm sau), bạn còn được trả thêm ít nhất 30% tiền lương tính theo đơn giá tiền lương ban ngày và thêm 20% tiền lương của công việc làm vào ban ngày của ngày đó.",
             "Cách tính tiền lương làm thêm giờ ban đêm và ngày nghỉ lễ Tết?"),
            ("Điều kiện và cách tính tiền trợ cấp thôi việc khi chấm dứt hợp đồng lao động?",
             "Theo Điều 46 BLLĐ 2019: Người sử dụng lao động có trách nhiệm trả trợ cấp thôi việc cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên. Mỗi năm làm việc được trợ cấp một nửa tháng tiền lương. "
             "Thời gian tính trợ cấp thôi việc là tổng thời gian làm việc thực tế trừ đi thời gian đã tham gia bảo hiểm thất nghiệp (BHTN) và thời gian đã được chi trả trợ cấp thôi việc trước đó. Tiền lương tính trợ cấp là bình quân tiền lương 06 tháng liền kề trước khi nghỉ việc.",
             "Điều kiện và công thức tính trợ cấp thôi việc theo BLLĐ 2019?"),
            ("Người lao động làm việc 1 năm được bao nhiêu ngày phép năm? Thôi việc chưa nghỉ hết có được thanh toán tiền không?",
             "Theo Điều 113 BLLĐ 2019: Người lao động làm việc đủ 12 tháng trong điều kiện bình thường được nghỉ 12 ngày làm việc hưởng nguyên lương. Cứ đủ 05 năm làm việc cho một người sử dụng lao động thì số ngày nghỉ phép năm được tăng thêm tương ứng 01 ngày (Điều 114). "
             "Trường hợp do thôi việc, mất việc làm mà chưa nghỉ hết số ngày nghỉ hằng năm thì được người sử dụng lao động thanh toán tiền lương cho những ngày chưa nghỉ.",
             "Quy định về ngày nghỉ phép năm và thanh toán tiền phép năm chưa nghỉ hết?"),
            ("Người sử dụng lao động có được giữ bản chính CMND/CCCD hoặc bằng đại học của người lao động không?",
             "Theo Điều 17 BLLĐ 2019: Pháp luật nghiêm cấm hành vi giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ của người lao động khi giao kết, thực hiện hợp đồng lao động. "
             "Theo Nghị định 12/2022/NĐ-CP (Điều 9), người sử dụng lao động có hành vi giữ bản chính giấy tờ tùy thân, văn bằng của người lao động sẽ bị xử phạt vi phạm hành chính từ 20.000.000 đồng đến 25.000.000 đồng và buộc phải trả lại giấy tờ ngay lập tức.",
             "Doanh nghiệp giữ bằng đại học gốc của nhân viên bị phạt bao nhiêu?"),
        ]
        content = '<p class="page-intro">Tuyển tập những vướng mắc pháp lý thường gặp nhất được trích xuất trực tiếp từ các quy định của Bộ luật Lao động 2019 và các văn bản thi hành.</p>'
        content += '<div class="faq-list">' + ''.join(
            f'''<details class="faq-accordion" open>
                <summary class="faq-question">
                    <span class="faq-q-icon">{icon("help-circle")}</span>
                    <strong>{esc(q)}</strong>
                </summary>
                <div class="faq-content">
                    <p>{esc(a)}</p>
                    <button class="faq-ask-btn" data-query="{esc(ask_q)}">{icon("message-circle")} <span>Hỏi sâu hơn về quy định này</span></button>
                </div>
            </details>'''
            for q, a, ask_q in faq_list
        ) + '</div>'

    elif view == 'news':
        news_list = [
            ("Nghị định mới về mức lương tối thiểu vùng: Những điều chỉnh người lao động cần biết", "Chính sách mới", "2026",
             "Chính phủ ban hành quy định mới về mức lương tối thiểu theo tháng và theo giờ. Mức lương áp dụng cho 4 vùng kinh tế nhằm bảo đảm mức sống tối thiểu của người lao động trong bối cảnh giá cả thị trường biến động.",
             "Mức lương tối thiểu vùng mới nhất hiện nay là bao nhiêu và cách áp dụng?"),
            ("Quy định chi tiết về giao kết hợp đồng lao động điện tử và giá trị pháp lý chữ ký số", "Chuyển đổi số", "2026",
             "Hướng dẫn toàn diện về giá trị pháp lý của hợp đồng lao động điện tử theo quy định mới, các phương tiện xác thực số hợp lệ và nghĩa vụ bảo mật dữ liệu nhân sự của doanh nghiệp.",
             "Hợp đồng lao động điện tử có giá trị pháp lý tương đương hợp đồng giấy không?"),
            ("Tăng cường thanh tra xử phạt nghiêm các hành vi vi phạm về tiền lương và bảo hiểm xã hội", "Thanh tra - Xử phạt", "2026",
             "Bộ Lao động - Thương binh và Xã hội đẩy mạnh thanh tra chuyên ngành, tập trung vào các hành vi nợ lương kéo dài, trốn đóng BHXH, bắt buộc làm thêm giờ trái thỏa thuận theo Nghị định 12/2022/NĐ-CP.",
             "Các mức phạt hành chính đối với hành vi nợ lương và trốn đóng BHXH của công ty?"),
            ("Cẩm nang bảo vệ quyền lợi lao động nữ: Chế độ thai sản, nuôi con nhỏ và phòng chống quấy rối", "Bảo vệ quyền lợi", "2026",
             "Hệ thống quy định bảo vệ thai sản, quyền từ chối làm việc ban đêm hoặc làm thêm giờ khi mang thai từ tháng thứ 7, cùng các quy định bắt buộc về phòng chống quấy rối tình dục tại nơi làm việc.",
             "Quy định pháp luật bảo vệ lao động nữ mang thai và nuôi con nhỏ dưới 12 tháng?"),
        ]
        content = '<p class="page-intro">Cập nhật những thay đổi pháp lý, văn bản chỉ đạo và tin tức chính sách lao động - tiền lương - bảo hiểm xã hội mới nhất.</p>'
        content += '<div class="news-full-grid">' + ''.join(
            f'''<article class="news-card-rich">
                <div class="news-meta">
                    <span class="news-badge">{esc(tag)}</span>
                    <span class="news-date">{esc(date)}</span>
                </div>
                <h3>{esc(title)}</h3>
                <p>{esc(desc)}</p>
                <button class="news-read-btn" data-query="{esc(q)}">{icon("chevron-right")} <span>Tra cứu quy định liên quan</span></button>
            </article>'''
            for title, tag, date, desc, q in news_list
        ) + '</div>'

    else:
        content = '<p>VietLaborAI là trợ lý hỗ trợ tra cứu, đối chiếu và giải thích pháp luật lao động Việt Nam dựa trên văn bản trong cơ sở dữ liệu.</p><h2>Cách sử dụng</h2><p>Nhập câu hỏi hoặc chọn một gợi ý. Cung cấp thêm dữ kiện khi trợ lý cần làm rõ. Mở phần căn cứ pháp lý để đối chiếu điều khoản và văn bản gốc.</p><p class="resource-note">VietLabor AI hỗ trợ tra cứu thông tin pháp luật lao động từ các văn bản trong cơ sở dữ liệu. Nội dung cung cấp mang tính tham khảo và không thay thế ý kiến tư vấn chuyên môn cho tình huống pháp lý cụ thể.</p>'

    return f'<section class="resource-page">{back}<h1>{title}</h1>{content}</section>'


def layout_markup(view: str, messages: list[dict], conversations: list[dict], busy: bool, active_id: str) -> str:
    brand = (sprite(56,8,86,61,'header-symbol','Biểu tượng VietLaborAI')
             + '<span class="brand-copy"><strong>VietLabor<span>AI</span></strong><small>Trợ lý pháp luật lao động</small></span>')

    # 1. New Chat button at top of sidebar (ChatGPT style)
    new_chat_btn = f'''<button class="new-chat-btn" data-event="new_chat" title="Bắt đầu cuộc trò chuyện mới">
      {icon("plus")} <span>Cuộc trò chuyện mới</span>
    </button>'''

    # 2. Main views - Keep only 'Trang chủ'
    main_nav = nav_button('home', 'Trang chủ', 'home-filled', view == 'home')

    # 3. Sidebar Conversation History (ChatGPT style)
    if conversations:
        sidebar_conv_rows = ''.join(
            f'''<div class="sidebar-conv-row{' active' if c["id"] == active_id and view == "chat" else ""}">
              <button class="sidebar-conv-item" data-conversation="{esc(c["id"])}" title="{esc(c.get("title"))}">
                {icon("message-circle")}
                <span class="sidebar-conv-title">{esc(c.get("title"))}</span>
              </button>
              <button class="sidebar-conv-delete" data-delete="{esc(c["id"])}" title="Xóa cuộc trò chuyện" aria-label="Xóa cuộc trò chuyện {esc(c.get("title"))}">
                {icon("trash")}
              </button>
            </div>'''
            for c in conversations
        )
    else:
        sidebar_conv_rows = '<div class="sidebar-conv-empty">Chưa có lịch sử trò chuyện</div>'

    sidebar_history = f'''<div class="sidebar-history-section">
      <div class="sidebar-history-header">
        <span>Lịch sử trò chuyện</span>
        <span class="sidebar-history-count">{len(conversations)}</span>
      </div>
      <div class="sidebar-conv-list">{sidebar_conv_rows}</div>
    </div>'''

    # 4. Other navigation links (exclude about as it is already in header)
    other_nav = ''.join(nav_button(v, t, g, v == view) for v, t, g in NAVIGATION[2:-1])

    left_nav = f'''<nav class="left-navigation" aria-label="Điều hướng chính">
      {new_chat_btn}
      <div class="nav-group">{main_nav}</div>
      <div class="sidebar-divider"></div>
      {sidebar_history}
      <div class="sidebar-divider"></div>
      <div class="nav-group nav-group-secondary">{other_nav}</div>
    </nav>'''

    # Center Panel - render all views as view-panes for 0ms instant client-side switching
    home_pane = f'''<div class="view-pane" data-pane="home"><section class="welcome"><div class="hero-art"><div class="hero-backdrop" aria-hidden="true">{sprite(309,80,895,336,'hero-sprite','')}</div><div class="hero-content">{sprite(727,120,168,135,'hero-symbol','Biểu tượng VietLaborAI')}<h1 class="hero-wordmark">VietLabor<span>AI</span></h1><strong>Trợ lý tra cứu pháp luật lao động Việt Nam</strong><p>Tra cứu quy định, hiểu quyền lợi, giải đáp tình huống lao động.</p></div></div>{composer(busy)}{home_suggestions()}{news_cards()}</section></div>'''

    if not messages:
        feed = f'''<div class="chat-empty-state">
          <div class="empty-badge">{icon("message-circle")}</div>
          <h2>Tôi có thể giúp gì cho bạn hôm nay?</h2>
          <p>Trợ lý AI chuyên sâu về pháp luật lao động Việt Nam. Hãy nhập câu hỏi về quyền lợi, hợp đồng, tiền lương hoặc bảo hiểm bên dưới.</p>
          <div class="empty-suggestions">
            <div class="empty-suggestions-label">Gợi ý câu hỏi phổ biến:</div>
            <div class="empty-grid">{''.join(f'<button class="empty-card" data-query="{esc(q)}"><span>{esc(q)}</span>{icon("chevron-right")}</button>' for q in PROMPTS)}</div>
          </div>
        </div>'''
    else:
        feed = render_messages(messages, busy)

    chat_pane = f'''<div class="view-pane" data-pane="chat"><section class="chat-page">
      <div class="chat-heading">
        <div class="chat-heading-title">
          <h1>Trợ lý pháp luật lao động</h1>
          <span class="chat-badge-ai">AI Assistant</span>
        </div>
      </div>
      <div class="message-feed">{feed}</div>
      {composer(busy)}
    </section></div>'''

    sec_panes = ''.join(
        f'<div class="view-pane" data-pane="{v}">{secondary_content(v)}</div>'
        for v in ['documents', 'topics', 'templates', 'situations', 'faq', 'news', 'about']
    )

    center = f'{home_pane}{chat_pane}{sec_panes}'

    history = ''.join(f'<div class="history-row"><button class="history-item" data-conversation="{esc(c["id"])}" {"aria-current=true" if c["id"] == active_id else ""}>{icon("message-circle")}<span>{esc(c.get("title"))}<small>{esc(c.get("display_time"))}</small></span></button><button class="history-delete" data-delete="{esc(c["id"])}" title="Xóa cuộc trò chuyện" aria-label="Xóa cuộc trò chuyện {esc(c.get("title"))}">{icon("trash")}</button></div>' for c in conversations)
    css_block = f'<style>{get_surface_css()}</style>'
    return f'''{css_block}<div class="vl-app" data-view="{esc(view)}" data-busy="{str(busy).lower()}">
      <header class="site-header"><button class="header-brand" data-view="home" aria-label="VietLaborAI, về trang chủ">{brand}</button><nav aria-label="Thông tin"><button data-view="about">Giới thiệu</button><button data-dialog="guide">Hướng dẫn sử dụng</button><button data-dialog="feedback">Phản hồi</button><span class="header-divider"></span><button class="login" data-dialog="login">{icon('user')} Đăng nhập</button></nav><button class="mobile-menu" data-mobile-menu aria-label="Mở menu">{icon('menu')}</button></header>
      <div class="app-body">{left_nav}<main class="center-panel">{center}</main>{right_panel()}</div>
      <footer class="app-disclaimer"><span>VietLaborAI có thể cung cấp thông tin chưa tuyệt đối chính xác. Luôn đối chiếu với văn bản pháp luật gốc.</span><span class="disclaimer-links"><button data-dialog="policy">Chính sách sử dụng</button><i>•</i><button data-dialog="terms">Điều khoản</button><i>•</i><button data-dialog="contact">Liên hệ</button></span></footer>
      <dialog class="info-dialog"><div class="dialog-heading"><h2></h2><button class="dialog-close" aria-label="Đóng">{icon('x')}</button></div><div class="dialog-body"></div></dialog>
      <script type="application/json" id="vl-templates-data">{json.dumps(LEGAL_TEMPLATES)}</script>
      <template id="history-content">{history or '<p>Chưa có lịch sử trò chuyện.</p>'}</template><div class="toast" role="status" aria-live="polite"></div>
    </div>'''


def get_surface_css() -> str:
    css = (FRONTEND / 'approved.css').read_text(encoding='utf-8')
    return css.replace('__APPROVED_ART__', '/app/static/approved-homepage.png')


@lru_cache(maxsize=1)
def get_surface():
    css = get_surface_css()
    return component('vietlaborai_approved_surface_v11', html='<div class="vl-mount"></div>', css=css, js=(FRONTEND / 'approved.js').read_text(encoding='utf-8'), isolate_styles=True)


def render_approved_layout(*, view, messages, conversations, busy=False, active_id='', notice=''):
    payload = {
        'markup': layout_markup(view,messages,conversations,busy,active_id),
        'conversation_id': active_id,
        'notice': notice,
        'messages': [{'id': m.get('id'), 'content': str(m.get('content') or '')} for m in messages],
    }
    return get_surface()(data=payload, key='approved_surface', on_action_change=lambda: None)
