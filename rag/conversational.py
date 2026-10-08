# -*- coding: utf-8 -*-
"""
VietLabor AI - Conversational fast-track (small talk).

Detects pure social messages (greeting, thanks, goodbye, identity, capability
questions, short acknowledgements) so they are answered instantly WITHOUT
touching BM25 / ChromaDB / Neo4j / Ollama.

Design rule: be conservative. A message is small talk only if, after removing
the social phrase and filler words, NOTHING substantive remains. "Xin chào,
công ty nợ lương tôi" is therefore a legal question, not small talk.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = ["SmalltalkReply", "detect_smalltalk", "fold_vietnamese"]


@dataclass
class SmalltalkReply:
    intent: str  # greeting | thanks | goodbye | identity | capabilities | ack
    answer: str
    suggestions: List[str] = field(default_factory=list)


def fold_vietnamese(text: str) -> str:
    """Lowercase, strip diacritics (đ -> d), drop punctuation, collapse spaces."""
    t = unicodedata.normalize("NFD", (text or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("đ", "d")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Intent phrases (diacritic-free). Order inside each list: longest first.
_INTENT_PHRASES = {
    "corpus_scope": [
        "he thong co bao nhieu luat", "co bao nhieu luat vay", "co bao nhieu luat",
        "co may luat", "bao nhieu luat", "co nhung luat nao", "co nhung luat gi",
        "gom nhung luat nao", "gom nhung luat gi", "ban co bao nhieu luat", "bot co bao nhieu luat",
        "he thong gom nhung luat nao", "he thong co nhung luat nao", "cac luat trong he thong",
        "cac van ban trong he thong", "danh sach cac luat", "danh sach luat", "danh sach van ban",
        "tra cuu duoc nhung luat nao", "tra cuu duoc nhung van ban nao", "co nhung van ban nao",
        "co bao nhieu van ban", "gom nhung van ban nao", "co cac luat nao", "co cac van ban nao",
        "co nhung bo luat nao", "co may bo luat", "bao nhieu bo luat", "co cac bo luat nao",
        "trong he thong co gi", "co bao nhieu van ban luat",
    ],
    "identity": [
        "ban la ai", "ban ten la gi", "ban ten gi", "ten ban la gi", "ai tao ra ban",
        "ai phat trien ban", "ban la gi", "ban la bot gi", "gioi thieu ve ban", "gioi thieu ban than",
        "who are you",
    ],
    "capabilities": [
        "ban co the lam duoc gi", "ban co the lam gi", "ban lam duoc gi", "ban giup duoc gi",
        "ban giup gi duoc", "ban ho tro duoc gi", "ban ho tro gi", "ban biet lam gi",
        "huong dan su dung", "cach su dung", "su dung the nao", "toi nen hoi gi", "hoi duoc gi",
        "what can you do", "help",
    ],
    "thanks": [
        "cam on rat nhieu", "cam on nhieu", "cam on ban", "cam on", "cam ta",
        "thank you", "thanks", "thank", "tks", "thx", "ty",
    ],
    "goodbye": ["tam biet", "hen gap lai", "goodbye", "bye bye", "bye", "pai"],
    "greeting": [
        "xin chao", "chao buoi sang", "chao buoi chieu", "chao buoi toi", "chao",
        "hello", "helo", "hi", "hey", "alo", "a lo",
    ],
    "ack": ["duoc roi", "hieu roi", "ro roi", "oke", "okay", "ok", "vang", "uh", "um"],
}

_PRIORITY = ["corpus_scope", "identity", "capabilities", "thanks", "goodbye", "greeting", "ack"]

# Words that carry no legal substance in a social message.
_FILLERS = {
    "ban", "bot", "ad", "admin", "vietlabor", "ai", "tro", "ly", "oi", "nhe", "nha", "nhe",
    "a", "ah", "da", "vay", "the", "nhe", "nhieu", "rat", "lam", "qua", "minh", "toi", "em",
    "anh", "chi", "moi", "nguoi", "voi", "nhe", "nhi", "ha", "hen", "nhe", "roi", "nhe",
    "cho", "hoi", "co", "the", "khong", "ko", "k", "gi", "va", "nhe", "ne", "nghe",
}

# Any of these means the user is actually asking about labor law.
_LEGAL_SIGNALS = [
    "luong", "hop dong", "hdld", "thu viec", "nghi viec", "thoi viec", "sa thai", "bhxh",
    "bao hiem", "cong ty", "doanh nghiep", "lao dong", "lam them", "tang ca", "ky luat",
    "phep", "thai san", "tro cap", "nghi dinh", "luat", "xu phat", "bi phat", "phat tien",
    "boi thuong", "cham dut", "bao truoc", "nghi huu", "that nghiep", "tai nan",
]
_ARTICLE_REF = re.compile(r"\b(dieu|khoan|diem)\s+\d")

_DEFAULT_SUGGESTIONS = [
    "Thời gian thử việc tối đa là bao lâu?",
    "Nghỉ việc phải báo trước bao nhiêu ngày?",
    "Công ty chậm trả lương thì tôi có quyền gì?",
]

_CAPABILITY_TEXT = (
    "Tôi có thể giúp bạn:\n"
    "- **Tra cứu quy định**: thử việc, hợp đồng, tiền lương, làm thêm giờ, nghỉ phép, kỷ luật, BHXH…\n"
    "- **Phân tích tình huống**: kể lại sự việc, tôi sẽ tách từng vấn đề pháp lý và đối chiếu điều luật.\n"
    "- **Trích dẫn có căn cứ**: mỗi kết luận đều kèm Điều/Khoản cụ thể và liên kết văn bản gốc.\n"
    "- **Hỏi tiếp nối**: bạn có thể hỏi thêm, tôi ghi nhớ bối cảnh của cuộc trò chuyện."
)


def _build_reply(intent: str, has_history: bool) -> SmalltalkReply:
    if intent == "corpus_scope":
        answer = (
            "Cơ sở dữ liệu của **VietLabor AI** hiện bao gồm hệ thống các văn bản pháp luật lao động cốt lõi của Việt Nam:\n\n"
            "1. **Bộ luật Lao động 2019** (Văn bản hợp nhất số 18/VBHN-VPQH): Quy định toàn diện về quan hệ lao động, hợp đồng lao động, tiền lương, thời giờ làm việc - nghỉ ngơi, kỷ luật lao động và giải quyết tranh chấp lao động.\n"
            "2. **Luật An toàn, vệ sinh lao động 2015** (Luật số 84/2015/QH13): Quy định về an toàn lao động, tai nạn lao động, bệnh nghề nghiệp và trách nhiệm bồi thường, trợ cấp của người sử dụng lao động.\n"
            "3. **Luật Bảo hiểm xã hội** (Văn bản hợp nhất số 19/VBHN-VPQH & 58/VBHN-VPQH): Quy định về các chế độ bảo hiểm xã hội bắt buộc (ốm đau, thai sản, tai nạn lao động, hưu trí, tử tuất).\n"
            "4. **Nghị định 145/2020/NĐ-CP**: Hướng dẫn chi tiết thi hành Bộ luật Lao động về điều kiện lao động và quan hệ lao động.\n"
            "5. **Nghị định 12/2022/NĐ-CP & Nghị định 283/2026/NĐ-CP**: Quy định về xử phạt vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội.\n"
            "6. **Thông tư 10/2020/TT-BLĐTBXH**: Quy định chi tiết nội dung hợp đồng lao động và quy chế thương lượng tập thể.\n\n"
            "Bạn có thể đặt bất kỳ câu hỏi nào về các chế độ, quyền lợi hoặc tình huống pháp lý cụ thể liên quan đến các văn bản trên!"
        )
        suggestions = [
            "Thời gian thử việc tối đa là bao lâu?",
            "Quy định về ngày nghỉ phép năm?",
            "Công ty tự ý trừ lương thì xử lý thế nào?",
        ]
        return SmalltalkReply(intent=intent, answer=answer, suggestions=suggestions)
    elif intent == "identity":
        answer = (
            "Tôi là **VietLabor AI** — trợ lý tra cứu pháp luật lao động Việt Nam, chạy hoàn toàn "
            "cục bộ trên máy của bạn. Câu trả lời của tôi được đối chiếu với Bộ luật Lao động 2019 "
            "và các nghị định, thông tư hướng dẫn.\n\n" + _CAPABILITY_TEXT
        )
    elif intent == "capabilities":
        answer = _CAPABILITY_TEXT + "\n\nBạn đang gặp vấn đề gì? Hãy mô tả càng cụ thể càng tốt (loại hợp đồng, thời gian làm việc, công ty đã làm gì)."
    elif intent == "thanks":
        answer = (
            "Rất vui được hỗ trợ bạn! Nếu còn điểm nào về vấn đề vừa rồi chưa rõ, bạn cứ hỏi tiếp nhé."
            if has_history
            else "Rất vui được hỗ trợ bạn! Bạn cần tra cứu vấn đề lao động nào không?"
        )
    elif intent == "goodbye":
        answer = (
            "Tạm biệt bạn! Lưu ý: nội dung tôi cung cấp mang tính tham khảo; với tranh chấp cụ thể, "
            "bạn nên tham vấn thêm luật sư hoặc cơ quan quản lý lao động. Chúc bạn mọi điều thuận lợi!"
        )
    elif intent == "ack":
        answer = (
            "Vâng. Bạn có muốn hỏi tiếp về vấn đề vừa rồi hoặc một tình huống khác không?"
            if has_history
            else "Vâng. Bạn muốn tra cứu vấn đề lao động nào?"
        )
    else:  # greeting
        answer = (
            "Chào bạn, rất vui được gặp lại! Bạn muốn hỏi tiếp điều gì?"
            if has_history
            else (
                "Xin chào! Tôi là **VietLabor AI**, trợ lý tra cứu pháp luật lao động Việt Nam.\n\n"
                "Bạn có thể hỏi một quy định cụ thể hoặc kể lại tình huống của mình — "
                "tôi sẽ phân tích và trích dẫn điều luật tương ứng."
            )
        )
    suggestions = [] if intent == "goodbye" else list(_DEFAULT_SUGGESTIONS)
    return SmalltalkReply(intent=intent, answer=answer, suggestions=suggestions)


def detect_smalltalk(text: str, has_history: bool = False) -> Optional[SmalltalkReply]:
    """Returns a ready-made reply if `text` is pure small talk, else None."""
    folded = fold_vietnamese(text)
    if not folded or len(folded) > 80:
        return None
    padded = f" {folded} "

    # 1. First check corpus_scope questions before general _LEGAL_SIGNALS filter (as they contain "luat")
    for phrase in _INTENT_PHRASES.get("corpus_scope", []):
        pattern = f" {phrase} "
        if pattern in padded:
            rem = padded.replace(pattern, " ")
            substantive_dispute_signals = [
                "luong", "thu viec", "sa thai", "ky luat", "tang ca", "lam them",
                "bi phat", "phat tien", "boi thuong", "thai san", "tai nan", "nghi viec",
            ]
            if not any(sig in rem for sig in substantive_dispute_signals) and not _ARTICLE_REF.search(rem):
                return _build_reply("corpus_scope", has_history)

    if any(sig in padded for sig in _LEGAL_SIGNALS) or _ARTICLE_REF.search(folded):
        return None

    found: List[str] = []
    remaining = padded
    for intent in _PRIORITY:
        for phrase in _INTENT_PHRASES[intent]:
            pattern = f" {phrase} "
            if pattern in remaining:
                remaining = remaining.replace(pattern, " ")
                if intent not in found:
                    found.append(intent)
    if not found:
        return None

    leftover = [tok for tok in remaining.split() if tok not in _FILLERS]
    if leftover:
        return None

    primary = next(i for i in _PRIORITY if i in found)
    return _build_reply(primary, has_history)
