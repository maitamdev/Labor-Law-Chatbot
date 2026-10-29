"""
Export Chat History Utility for VietLabor AI.
Formats multi-turn consultation sessions into Markdown or plain text.
"""
from typing import Dict, List


def export_chat_to_markdown(messages: List[Dict[str, str]], title: str = "Biên bản Tư vấn Pháp luật Lao động") -> str:
    """Format chat turn list into structured Markdown document."""
    lines = [f"# {title}", "", "---", ""]
    for idx, msg in enumerate(messages, 1):
        role = "Luật sư AI" if msg.get("role") == "assistant" else "Người dùng"
        content = msg.get("content", "").strip()
        lines.append(f"### Lượt {idx} - {role}:")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
