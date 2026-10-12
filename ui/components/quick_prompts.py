"""
Quick Prompt suggestions for common Vietnamese labor law questions.
"""
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class QuickPrompt:
    id: str
    label: str
    query: str
    category: str

DEFAULT_QUICK_PROMPTS: List[QuickPrompt] = [
    QuickPrompt(
        "qp_1",
        "Đơn phương chấm dứt HĐLĐ",
        "Tôi muốn nghỉ việc thì cần báo trước bao nhiêu ngày theo BLLĐ 2019?",
        "Hợp đồng lao động",
    ),
    QuickPrompt(
        "qp_2",
        "Trợ cấp thôi việc",
        "Điều kiện và cách tính tiền trợ cấp thôi việc theo Nghị định 145/2020?",
        "Chế độ đãi ngộ",
    ),
    QuickPrompt(
        "qp_3",
        "Lương làm thêm giờ",
        "Tiền lương làm thêm vào ban đêm và ngày nghỉ lễ được tính như thế nào?",
        "Tiền lương",
    ),
    QuickPrompt(
        "qp_4",
        "Sa thải trái luật",
        "Người sử dụng lao động sa thải người lao động trái luật phải bồi thường những gì?",
        "Kỷ luật lao động",
    ),
]

def render_quick_prompts_html(prompts: List[QuickPrompt] = None) -> str:
    """Generate HTML chips for UI."""
    if prompts is None:
        prompts = DEFAULT_QUICK_PROMPTS
    chips = []
    for p in prompts:
        chip = f'''<button class="quick-prompt-chip" data-query="{p.query}">
            <span class="chip-category">[{p.category}]</span> {p.label}
        </button>'''
        chips.append(chip)
    return f'<div class="quick-prompts-container">{"".join(chips)}</div>'
