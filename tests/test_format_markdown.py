# -*- coding: utf-8 -*-
"""
Tests for format_answer_markdown utility in rag.output_validator.
Ensures responses are cleanly formatted into Markdown paragraphs, sections, and bullet highlights.
"""
from rag.output_validator import format_answer_markdown


def test_format_answer_markdown_continuous_text():
    raw_wall_of_text = (
        "Hành vi từ chối làm việc của anh A là đúng pháp luật. Dựa vào Điều 36 Bộ luật Lao động 2019, "
        "người lao động có quyền từ chối làm việc trong trường hợp nguy hiểm đến tính mạng, sức khỏe. "
        "Cụ thể, theo Điểm c Khoản 1 Điều 36 Bộ luật Lao động 2019, người lao động có quyền từ chối làm việc. "
        "Quyết định sa thải của công ty đối với anh A là không đúng căn cứ pháp luật. "
        "Nếu công ty vẫn ép buộc anh A phải làm việc ở khu vực nguy hiểm đó và xảy ra tai nạn, trách nhiệm pháp lý thuộc về công ty. "
        "Công ty đã vi phạm nghĩa vụ bảo vệ an toàn lao động của người lao động. "
        "Lời khuyên cho anh A là nên giữ lại bằng chứng về việc từ chối làm việc."
    )

    formatted = format_answer_markdown(raw_wall_of_text)

    # Must contain multiple paragraphs separated by \n\n
    paragraphs = [p for p in formatted.split("\n\n") if p.strip()]
    assert len(paragraphs) >= 4, f"Expected at least 4 paragraphs, got {len(paragraphs)}"

    # Specific sections must be broken into separate paragraphs
    assert any("Quyết định sa thải" in p for p in paragraphs)
    assert any("Nếu công ty" in p or "trách nhiệm pháp lý" in p for p in paragraphs)
    assert any("💡 **Lời khuyên" in p for p in paragraphs)


def test_format_answer_markdown_single_newlines():
    single_newline_text = (
        "Về vấn đề 1, công ty vi phạm mức lương thử việc.\n"
        "Về vấn đề 2, việc không đóng bảo hiểm là trái luật.\n"
        "Về vấn đề 3, kéo dài thời gian là sai phạm."
    )

    formatted = format_answer_markdown(single_newline_text)
    paragraphs = [p for p in formatted.split("\n\n") if p.strip()]
    assert len(paragraphs) == 3, f"Expected 3 paragraphs, got {len(paragraphs)}"


def test_format_answer_markdown_preserves_lists_and_headings():
    markdown_text = (
        "### 1. Vấn đề thử việc\n\n"
        "- Điều kiện 1: Tối đa 60 ngày\n"
        "- Điều kiện 2: Lương tối thiểu 85%\n\n"
        "### 2. Vấn đề nghỉ việc\n\n"
        "Người lao động phải báo trước ít nhất 30 ngày."
    )

    formatted = format_answer_markdown(markdown_text)
    assert "### 1. Vấn đề thử việc" in formatted
    assert "- Điều kiện 1: Tối đa 60 ngày" in formatted
    assert "- Điều kiện 2: Lương tối thiểu 85%" in formatted
    assert "### 2. Vấn đề nghỉ việc" in formatted
