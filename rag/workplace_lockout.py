"""Narrow, statute-backed handling of temporary workplace closure during a strike.

This is distinct from closing a business or terminating an employment contract.
Only a matched legal concept and the complete current evidence set can trigger the
deterministic answer.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection


LOCKOUT_EVIDENCE_IDS = (
    "VBHN_18_2026#d203-k3-b",
    "VBHN_18_2026#d205",
    "VBHN_18_2026#d205-k1",
    "VBHN_18_2026#d205-k2",
    "ND_129_2025#d69",
    "VBHN_18_2026#d206-k1",
    "VBHN_18_2026#d206-k2",
)


def workplace_lockout_request(query: str) -> bool:
    """Match the legal lockout concept, not generic business closure."""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", query).lower())
    if "đóng cửa" not in text:
        return False
    return any(term in text for term in (
        "nơi làm việc", "chỗ làm", "đình công", "đóng cửa tạm thời nơi",
    ))


def standalone_lockout_rule_request(query: str) -> bool:
    """Do not answer sanction, wage, or termination disputes with this rule alone."""
    if not workplace_lockout_request(query):
        return False
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", query).lower())
    return not any(term in text for term in (
        "phạt", "chế tài", "bồi thường", "tiền lương", "trả lương", "trợ cấp",
        "chấm dứt hợp đồng", "chấm dứt hđlđ", "đơn phương", "sa thải",
    ))


def grounded_workplace_lockout_answer(query: str, available_chunk_ids: Collection[str]) -> str | None:
    if not standalone_lockout_rule_request(query):
        return None
    if not set(LOCKOUT_EVIDENCE_IDS).issubset(set(available_chunk_ids)):
        return None
    return (
        "Có. Người sử dụng lao động có quyền **đóng cửa tạm thời nơi làm việc**, nhưng không được tùy ý dùng quyền này như một cách chấm dứt hợp đồng lao động. "
        "Theo điểm b khoản 3 Điều 203 Bộ luật Lao động, trong thời gian đình công họ chỉ được đóng cửa tạm thời khi không đủ điều kiện duy trì hoạt động bình thường hoặc để bảo vệ tài sản.\n\n"
        "**Thủ tục:** Ít nhất 03 ngày làm việc trước ngày đóng cửa, phải niêm yết công khai quyết định tại nơi làm việc và thông báo cho tổ chức đại diện người lao động đang tổ chức, lãnh đạo đình công, Ủy ban nhân dân cấp tỉnh nơi dự kiến đóng cửa và Ủy ban nhân dân cấp xã nơi đó. Đầu mối cấp xã áp dụng theo Điều 69 Nghị định 129/2025/NĐ-CP, thay cho cách ghi cấp huyện ở khoản 3 Điều 205 Bộ luật Lao động.\n\n"
        "**Giới hạn:** Không được đóng cửa sớm hơn 12 giờ trước thời điểm bắt đầu đình công ghi trong quyết định đình công; cũng không được đóng cửa sau khi người lao động đã ngừng đình công (Điều 206). "
        "Quy định này về đóng cửa tạm thời trong đình công, không phải căn cứ đơn phương chấm dứt HĐLĐ tại Điều 36."
    )
