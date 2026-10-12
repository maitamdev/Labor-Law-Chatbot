"""Knowledge-graph view renders exactly the statutory bridges used by the graph builder."""
import re
import xml.etree.ElementTree as ET

from graph.schema import DEFAULT_STATUTORY_BRIDGES
from ui.components.approved_layout import graph_explorer, layout_markup


def _svg(markup: str) -> str:
    return re.search(r'<svg class="kg-svg".*?</svg>', markup, re.S).group(0)


def test_graph_view_draws_one_edge_per_bridge_and_is_valid_svg():
    markup = graph_explorer()
    svg = _svg(markup)
    ET.fromstring(svg)  # well-formed (escaped descriptions, closed tags)
    assert svg.count('class="kg-edge') == len(DEFAULT_STATUTORY_BRIDGES)
    assert svg.count('kg-edge kg-penal') == sum(
        1 for b in DEFAULT_STATUTORY_BRIDGES if b['rel_type'].value == 'PENALIZES'
    )
    # 7 distinct decree articles + 8 distinct BLLĐ articles in the current bridge set.
    sources = {(b['source_doc_id'], b['source_article']) for b in DEFAULT_STATUTORY_BRIDGES}
    targets = {(b['target_doc_id'], b['target_article']) for b in DEFAULT_STATUTORY_BRIDGES}
    assert svg.count('kg-node kg-src') == len(sources)
    assert svg.count('kg-node kg-tgt') == len(targets)
    assert 'NĐ 283/2026 · Điều 25' in svg and 'BLLĐ 2019 · Điều 127' in svg


def test_graph_rows_send_questions_and_escape_descriptions():
    bridges = [{
        'source_doc_id': 'ND_145_2020', 'source_article': 8, 'rel_type': 'GUIDES',
        'target_doc_id': 'VBHN_18_2026', 'target_article': 46,
        'description': '<script>alert(1)</script>',
    }]
    markup = graph_explorer(bridges)
    assert '<script>' not in markup
    assert '&lt;script&gt;' in markup
    assert 'data-query="Điều 8 NĐ 145/2020 hướng dẫn Điều 46 Bộ luật Lao động 2019 như thế nào?"' in markup


def test_graph_view_is_reachable_from_navigation():
    markup = layout_markup('graph', [], [], False, '')
    assert 'data-view="graph"' in markup
    assert 'data-pane="graph"' in markup
    assert 'Đồ thị tri thức' in markup
