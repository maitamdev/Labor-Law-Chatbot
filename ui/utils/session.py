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
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HISTORY_STORAGE_PATH = Path("storage/chat_history.json")


def generate_title_from_query(query: str) -> str:
    """Generates a clean, concise 2-5 word title from the user's initial question."""
    q = query.strip()
    q_lower = q.lower()

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

    if "làm thêm" in q_lower or "tăng ca" in q_lower:
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

    def load_conversations(self) -> List[Dict[str, Any]]:
        """Loads conversations from disk storage."""
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.warning(f"Failed to load chat history: {e}")
            return []

    def save_conversations(self, conversations: List[Dict[str, Any]]) -> None:
        """Persists conversations to disk storage."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")

    def create_conversation(self, title: str = "Cuộc trò chuyện mới") -> Dict[str, Any]:
        """Creates and stores a fresh conversation."""
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

    def update_conversation_title(self, conv_id: str, new_title: str) -> None:
        """Updates conversation title."""
        convs = self.load_conversations()
        for c in convs:
            if c["id"] == conv_id:
                c["title"] = new_title
                c["updated_at"] = datetime.datetime.now().isoformat()
                break
        self.save_conversations(convs)

    def delete_conversation(self, conv_id: str) -> None:
        """Deletes a conversation by ID."""
        convs = self.load_conversations()
        convs = [c for c in convs if c["id"] != conv_id]
        self.save_conversations(convs)

    def append_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends a user or assistant message to a conversation."""
        convs = self.load_conversations()
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%H:%M")

        for c in convs:
            if c["id"] == conv_id:
                # If this is the first user message and title is default, update title
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
                c["messages"].append(msg)
                c["updated_at"] = now.isoformat()
                c["display_time"] = "Hôm nay " + timestamp_str
                break

        # Move recently updated conversation to top
        convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        self.save_conversations(convs)
