"""
Vietnamese Legal Terminology Synonym Mapper.
Expands colloquial workplace terms into formal statutory concepts.
"""
LEGAL_SYNONYM_DICTIONARY = {
    "đuổi việc": ["sa thải", "đơn phương chấm dứt hợp đồng lao động", "buộc thôi việc"],
    "cho nghỉ việc": ["chấm dứt hợp đồng lao động", "thôi việc"],
    "tiền nghỉ việc": ["trợ cấp thôi việc", "trợ cấp mất việc làm"],
    "lương làm thêm": ["tiền lương làm thêm giờ", "tiền làm việc vào ban đêm"],
    "hết hạn hợp đồng": ["hợp đồng lao động hết hạn", "chấm dứt hợp đồng lao động theo khoản 1 điều 34"],
    "hợp đồng dịch vụ": ["hợp đồng dịch vụ", "phân biệt hợp đồng dịch vụ và hợp đồng lao động"],
    "thử việc": ["thời gian thử việc", "hợp đồng thử việc", "tiền lương thử việc"],
    "bị tai nạn": ["tai nạn lao động", "bồi thường tai nạn lao động", "trợ cấp tai nạn lao động"],
}

def expand_legal_terms(text: str) -> list[str]:
    """Return canonical legal keywords corresponding to colloquial terms."""
    expanded = []
    text_lower = text.lower()
    for colloquial, formal_terms in LEGAL_SYNONYM_DICTIONARY.items():
        if colloquial in text_lower:
            expanded.extend(formal_terms)
    return list(dict.fromkeys(expanded))
