# -*- coding: utf-8 -*-
"""
VietLabor AI - Query Expander
Bridges colloquial user phrasing and formal legal statutory terminology
to eliminate RETRIEVAL_MISS without modifying user-facing legal conclusions.
"""
import re
import unicodedata
from typing import Dict, List, Tuple


class QueryExpander:
    """Expands natural language legal queries with statutory terminology for retrieval."""

    # Lexicon mapping colloquial expressions or specific factual scenarios to statutory phrases
    STATUTORY_EXPANSIONS: List[Tuple[List[str], str]] = [
        # Article 17 BLLĐ: Prohibited acts when concluding/performing labor contracts
        (["giữ bằng đại học", "giữ bằng tốt nghiệp", "giữ bằng gốc", "giữ văn bằng", "giữ chứng chỉ"],
         "giữ bản chính văn bằng chứng chỉ Điều 17 Bộ luật Lao động"),
        (["nộp tiền đặt cọc", "đóng tiền thế chấp", "đóng tiền cọc", "thế chấp tiền", "tiền thế chấp", "đặt cọc 5 triệu"],
         "biện pháp bảo đảm bằng tiền hoặc tài sản khác thực hiện hợp đồng lao động Điều 17 Bộ luật Lao động"),
        (["căn cước công dân gốc", "cccd gốc", "chứng minh nhân dân gốc", "giấy tờ tùy thân gốc", "nộp lại căn cước"],
         "giữ bản chính giấy tờ tùy thân Điều 17 Bộ luật Lao động"),

        # Article 105 & 109: Working hours and breaks
        (["ca liên tục", "làm việc theo ca liên tục", "ca 6 giờ"],
         "làm việc theo ca liên tục từ 06 giờ trở lên thời gian nghỉ giữa giờ được tính vào giờ làm việc Điều 109 Bộ luật Lao động"),
        (["đặc biệt nặng nhọc, độc hại", "đặc biệt nặng nhọc độc hại nguy hiểm"],
         "nghề công việc đặc biệt nặng nhọc độc hại nguy hiểm thời giờ làm việc rút ngắn Điều 105 Bộ luật Lao động"),

        # Article 107: Overtime limits
        (["giờ làm thêm trong một ngày", "giờ làm thêm của người lao động không được quá bao nhiêu giờ trong một ngày", "làm thêm trong ngày tối đa"],
         "số giờ làm thêm không quá 50% số giờ làm việc bình thường trong 01 ngày Điều 107 Bộ luật Lao động"),
        (["giờ làm thêm trong một tháng", "giờ làm thêm của người lao động không quá bao nhiêu giờ trong một tháng", "làm thêm trong tháng tối đa"],
         "tổng số giờ làm thêm không quá 40 giờ trong 01 tháng Điều 107 Bộ luật Lao động"),
        (["giờ làm thêm trong một năm", "giờ làm thêm của người lao động không quá bao nhiêu giờ trong một năm", "làm thêm trong năm tối đa"],
         "tổng số giờ làm thêm không quá 200 giờ trong 01 năm Điều 107 Bộ luật Lao động"),
        (["ép tôi làm thêm", "bắt tôi làm thêm", "ép làm thêm giờ"],
         "phải được sự đồng ý của người lao động khi làm thêm giờ Điều 107 Bộ luật Lao động"),

        # Article 98: Overtime and holiday pay
        (["làm ngày lễ được trả bao nhiêu", "tiền lương làm thêm ngày lễ", "lương làm thêm ngày lễ", "lương 300%", "tiền lương làm thêm giờ 300%", "không trả tiền lương làm thêm giờ 300%"],
         "tiền lương làm thêm giờ vào ngày nghỉ lễ tết ít nhất bằng 300% Điều 98 Bộ luật Lao động"),

        # Article 113: Annual leave
        (["nặng nhọc, độc hại, nguy hiểm được nghỉ bao nhiêu ngày phép", "công việc nặng nhọc độc hại được nghỉ bao nhiêu ngày"],
         "nghề công việc nặng nhọc độc hại nguy hiểm được nghỉ 14 ngày làm việc Điều 113 Bộ luật Lao động"),
        (["thôi việc mà chưa nghỉ hết số ngày phép", "chưa nghỉ hết phép", "chưa nghỉ hết số ngày phép hàng năm"],
         "thôi việc bị mất việc làm mà chưa nghỉ hằng năm hoặc chưa nghỉ hết số ngày nghỉ hằng năm thì được thanh toán tiền lương Điều 113 Bộ luật Lao động"),

        # Article 124: Disciplinary forms
        (["hình thức xử lý kỷ luật", "bao nhiêu hình thức kỷ luật", "hình thức kỷ luật lao động"],
         "hình thức xử lý kỷ luật lao động khiển trách kéo dài thời hạn nâng lương cách chức sa thải Điều 124"),

        # Article 122 & 137: Female employees
        (["mang thai tháng thứ 7", "mang thai từ tháng thứ 7", "nuôi con dưới 12 tháng tuổi"],
         "người lao động mang thai từ tháng thứ 07 không làm việc ban đêm làm thêm giờ Điều 137"),
        (["sa thải phụ nữ mang thai", "sa thải lao động mang thai", "kỷ luật người mang thai", "lao động nữ mang thai sa thải"],
         "không được xử lý kỷ luật lao động đối với người lao động nữ mang thai Điều 122"),

        # Article 36: Employer unilateral termination
        (["cho tôi nghỉ việc ngay lập tức", "cho nghỉ việc ngay lập tức", "người sử dụng lao động đơn phương", "công ty cho tôi nghỉ việc không báo trước"],
         "người sử dụng lao động đơn phương chấm dứt hợp đồng lao động thời hạn báo trước Điều 36"),

        # Article 48: Responsibilities upon contract termination
        (["không trả lương tháng cuối", "chậm trả lương tháng cuối", "thanh toán tiền lương khi chấm dứt", "trả lương tháng cuối", "lương tháng cuối"],
         "trách nhiệm của hai bên khi chấm dứt hợp đồng lao động thanh toán đầy đủ các khoản tiền trong thời hạn 14 ngày Điều 48"),

        # Article 10 NĐ 12/2022: Penalties for probation violations
        (["thử việc quá thời gian quy định bị phạt", "yêu cầu thử việc quá thời gian"],
         "xử phạt hành vi yêu cầu thử việc quá thời gian quy định Điều 10 Nghị định 12/2022"),
    ]

    def expand(self, query: str) -> str:
        """Enriches the query text with matching statutory keywords for retrieval only."""
        if not query:
            return ""

        norm_q = unicodedata.normalize("NFC", query).strip().lower()
        matched_expansions = []

        for trigger_phrases, expansion_text in self.STATUTORY_EXPANSIONS:
            for phrase in trigger_phrases:
                if phrase in norm_q:
                    if expansion_text not in matched_expansions:
                        matched_expansions.append(expansion_text)
                    break

        if matched_expansions:
            return f"{query} {' '.join(matched_expansions)}"
        return query
