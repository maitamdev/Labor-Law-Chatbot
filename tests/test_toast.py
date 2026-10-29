from ui.components.toast import create_toast_payload, render_toast_html


def test_toast_payload():
    p = create_toast_payload("Sao chép thành công", "success")
    assert p["type"] == "success"
    assert "Sao chép thành công" in p["message"]
    html = render_toast_html(p)
    assert "toast-success" in html
