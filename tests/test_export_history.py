from ui.utils.export_history import export_chat_to_markdown

def test_export_chat_to_markdown():
    msgs = [
        {"role": "user", "content": "Hỏi về thử việc"},
        {"role": "assistant", "content": "Theo Điều 24 BLLĐ 2019..."},
    ]
    md = export_chat_to_markdown(msgs)
    assert "# Biên bản Tư vấn Pháp luật Lao động" in md
    assert "Hỏi về thử việc" in md
    assert "Theo Điều 24 BLLĐ 2019" in md
