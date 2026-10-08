# -*- coding: utf-8 -*-
"""
VietLabor AI - Session & Conversation History Persistence (Phase 6)
Persists real chat history to storage/chat_history.json.
No hardcoded fake history.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import CHAT_HISTORY_PATH

logger = logging.getLogger(__name__)

HISTORY_STORAGE_PATH = CHAT_HISTORY_PATH
_HISTORY_LOCK = threading.RLock()


def generate_title_from_query(query: str) -> str:
    """Generates a clean, concise 2-5 word title from the user's initial question."""
    q = query.strip()
    q_lower = q.lower()

    if any(k in q_lower for k in ["nguyên tắc giao kết", "nguyên tắc nền tảng khi giao kết", "giao kết hđlđ dựa trên"]):
        return "Nguyên tắc giao kết HĐLĐ"

    if any(k in q_lower for k in ["sếp đấm", "sếp đánh", "sếp tát", "hành hung", "đánh đập", "ngược đãi"]):
        return "Bạo lực tại nơi làm việc"
    if any(k in q_lower for k in ["đi làm trước", "vào làm trước", "làm chính thức rồi", "mới ký hđlđ", "chưa ký hợp đồng", "chưa có hợp đồng", "hẹn ký sau", "ký hợp đồng sau"]):
        return "Đi làm trước khi ký HĐLĐ"

    if "thử việc" in q_lower:
        if any(k in q_lower for k in ["3 tháng", "ba tháng"]):
            return "Thử việc 3 tháng"
        if any(k in q_lower for k in ["2 tháng", "hai tháng"]):
            return "Thử việc 2 tháng"
        if any(k in q_lower for k in ["lương", "tiền lương"]):
            return "Lương thử việc"
        return "Thời gian thử việc"

    if "nghỉ việc" in q_lower or "thôi việc" in q_lower or "chấm dứt" in q_lower:
        if "2 năm" in q_lower:
            return "Nghỉ việc hợp đồng 2 năm"
        if "tổ lái" in q_lower or "phi công" in q_lower:
            return "Nghỉ việc tổ lái tàu bay"
        if "dưới 12 tháng" in q_lower:
            return "Nghỉ việc HĐ dưới 12 tháng"
        if "không xác định" in q_lower:
            return "Nghỉ việc HĐ vô thời hạn"
        return "Thời hạn báo trước khi nghỉ việc"

    if any(k in q_lower for k in ["thỏa thuận công việc", "thoả thuận công việc", "không phải hợp đồng lao động"]):
        return "Xác định quan hệ lao động"

    if any(k in q_lower for k in ["làm thêm giờ", "làm thêm ngày", "lương làm thêm", "tiền lương làm thêm", "tăng ca", "làm ngoài giờ"]):
        if "ngày lễ" in q_lower or "nghỉ lễ" in q_lower:
            return "Lương làm thêm ngày lễ"
        if "ban đêm" in q_lower:
            return "Lương làm việc ban đêm"
        if "trong một ngày" in q_lower or "1 ngày" in q_lower:
            return "Giới hạn làm thêm theo ngày"
        return "Tiền lương làm thêm"

    if "giữ bằng" in q_lower or "bằng gốc" in q_lower or "văn bằng" in q_lower:
        return "Công ty giữ bằng đại học"
    if "căn cước" in q_lower or "giấy tờ" in q_lower:
        return "Công ty giữ giấy tờ tùy thân"
    if "chậm trả lương" in q_lower or "nợ lương" in q_lower:
        return "Công ty chậm trả lương"
    if "kỷ luật" in q_lower:
        if "sa thải" in q_lower:
            return "Quy định kỷ luật sa thải"
        return "Hình thức kỷ luật lao động"
    if "phép năm" in q_lower or "nghỉ phép" in q_lower:
        return "Quy định ngày nghỉ phép năm"
    if "ly hôn" in q_lower:
        return "Thủ tục ly hôn"
    if any(k in q_lower for k in ["bị té", "té ngã", "tai nạn lao động", "tai nạn khi làm việc", "bồi thường tai nạn"]):
        return "Bồi thường tai nạn lao động"
    if any(k in q_lower for k in ["trừ phí", "trả thiếu lương", "bớt lương", "khấu trừ", "không trả đủ lương"]):
        return "Khấu trừ tiền lương trái phép"
    if "tai nạn giao thông" in q_lower or "nồng độ cồn" in q_lower:
        return "Xử phạt vi phạm giao thông"

    # Fallback: take first 5-6 words
    words = q.split()
    if len(words) <= 5:
        return q.rstrip("?.,!")
    return " ".join(words[:5]).rstrip("?.,!")


class SessionManager:
    """Manages chat session lifecycle and file-backed persistence."""

    def __init__(self, storage_path: Path = HISTORY_STORAGE_PATH):
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._cached_conversations: Optional[List[Dict[str, Any]]] = None
        self._cache_mtime: float = -1.0

    def load_conversations(self) -> List[Dict[str, Any]]:
        """Loads conversations from disk storage with thread-safe mtime caching."""
        with _HISTORY_LOCK:
            if not self.storage_path.exists():
                self._cached_conversations = []
                self._cache_mtime = -1.0
                return []
            try:
                current_mtime = self.storage_path.stat().st_mtime
                if self._cached_conversations is not None and self._cache_mtime == current_mtime:
                    return [dict(c) for c in self._cached_conversations]
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._cached_conversations = data
                        self._cache_mtime = current_mtime
                        return [dict(c) for c in data]
                    return []
            except Exception as e:
                logger.warning("Failed to load chat history: %s", e)
                return []

    def save_conversations(self, conversations: List[Dict[str, Any]]) -> None:
        """Persists conversations atomically to avoid partial JSON files."""
        with _HISTORY_LOCK:
            temp_path = self.storage_path.with_name(
                f".{self.storage_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                with open(temp_path, "x", encoding="utf-8") as f:
                    json.dump(conversations, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.storage_path)
                self._cached_conversations = [dict(c) for c in conversations]
                try:
                    self._cache_mtime = self.storage_path.stat().st_mtime
                except OSError:
                    self._cache_mtime = -1.0
            except Exception as e:
                logger.error("Failed to save chat history: %s", e)
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def create_conversation(self, title: str = "Cuộc trò chuyện mới") -> Dict[str, Any]:
        """Creates and stores a fresh conversation."""
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            now = datetime.datetime.now()
            conv_id = str(uuid.uuid4())[:8]

            new_conv = {
                "id": conv_id,
                "title": title,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "display_time": "Hôm nay " + now.strftime("%H:%M"),
                "messages": [],
            }
            convs.insert(0, new_conv)
            self.save_conversations(convs)
            return new_conv

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Finds a conversation by ID."""
        convs = self.load_conversations()
        for c in convs:
            if c["id"] == conv_id:
                return c
        return None

    def ensure_conversation(self, conv_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns a valid conversation, recovering from a stale UI ID.

        Streamlit session state can outlive a conversation deleted from another
        rerun or browser tab. Prefer the requested conversation, then the most
        recently updated one, and create a fresh conversation only when history
        is empty.
        """
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            if conv_id:
                for conversation in convs:
                    if conversation.get("id") == conv_id:
                        return conversation
            if convs:
                return convs[0]
            return self.create_conversation("Cuộc trò chuyện mới")

    def update_conversation_title(self, conv_id: str, new_title: str) -> None:
        """Updates conversation title."""
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            for c in convs:
                if c["id"] == conv_id:
                    c["title"] = new_title
                    c["updated_at"] = datetime.datetime.now().isoformat()
                    break
            self.save_conversations(convs)

    def delete_conversation(self, conv_id: str) -> None:
        """Deletes a conversation by ID."""
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            convs = [c for c in convs if c["id"] != conv_id]
            self.save_conversations(convs)

    def append_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        attachment: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends a user or assistant message to a conversation."""
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            now = datetime.datetime.now()
            timestamp_str = now.strftime("%H:%M")

            for c in convs:
                if c["id"] == conv_id:
                    if role == "user" and (c["title"] == "Cuộc trò chuyện mới" or not c["messages"]):
                        c["title"] = generate_title_from_query(content)

                    msg = {
                        "id": str(uuid.uuid4())[:8],
                        "role": role,
                        "content": content,
                        "timestamp": timestamp_str,
                        "created_at": now.isoformat(),
                        "structured_data": structured_data or {},
                    }
                    if attachment:
                        msg["attachment"] = attachment
                    c["messages"].append(msg)
                    c["updated_at"] = now.isoformat()
                    c["display_time"] = "Hôm nay " + timestamp_str
                    break
            else:
                raise KeyError(f"Conversation not found: {conv_id}")

            convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            self.save_conversations(convs)

    def pop_last_exchange(self, conv_id: str) -> Optional[str]:
        """Removes the trailing assistant answer and the user question before it.

        Used by "Tạo lại câu trả lời": the returned question is resubmitted, so it
        is removed here to avoid a duplicate user bubble. Returns None when the
        conversation does not end with a user -> assistant pair.
        """
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            for c in convs:
                if c["id"] != conv_id:
                    continue
                msgs = c.get("messages", [])
                if len(msgs) < 2 or msgs[-1].get("role") != "assistant" or msgs[-2].get("role") != "user":
                    return None
                question = str(msgs[-2].get("content", ""))
                del msgs[-2:]
                c["updated_at"] = datetime.datetime.now().isoformat()
                self.save_conversations(convs)
                return question
            return None

    def set_message_feedback(self, conv_id: str, msg_id: str, rating: str) -> bool:
        """Stores 'up' / 'down' feedback on an assistant message."""
        if rating not in {"up", "down"}:
            raise ValueError("rating must be 'up' or 'down'")
        with _HISTORY_LOCK:
            convs = self.load_conversations()
            for c in convs:
                if c["id"] != conv_id:
                    continue
                for m in c.get("messages", []):
                    if m.get("id") == msg_id and m.get("role") == "assistant":
                        m["feedback"] = rating
                        self.save_conversations(convs)
                        return True
            return False
