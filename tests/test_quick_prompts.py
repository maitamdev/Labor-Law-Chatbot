from ui.components.quick_prompts import DEFAULT_QUICK_PROMPTS, render_quick_prompts_html


def test_render_quick_prompts():
    html = render_quick_prompts_html()
    assert "quick-prompts-container" in html
    assert "Đơn phương chấm dứt HĐLĐ" in html
    assert len(DEFAULT_QUICK_PROMPTS) >= 4
