# -*- coding: utf-8 -*-
"""
VietLabor AI - Legal Knowledge Graph Ontology & Schema
Defines academic-grade node labels, edge relationships, properties,
and data models for Vietnamese Labor Law Knowledge Graph in Neo4j.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LegalNodeLabel(str, Enum):
    """Core Node labels in the Legal Knowledge Graph."""
    DOCUMENT = "LegalDocument"        # e.g., VBHN_18_2026, ND_145_2020, ND_12_2022
    CHAPTER = "Chapter"                # e.g., Chương III: HỢP ĐỒNG LAO ĐỘNG
    ARTICLE = "Article"                # e.g., Điều 35, Điều 125
    CLAUSE = "Clause"                  # e.g., Khoản 1, Khoản 2
    POINT = "Point"                    # e.g., Điểm a, Điểm b
    PENALTY = "Penalty"                # e.g., Phạt tiền từ 5.000.000đ đến 10.000.000đ
    ACTOR = "Actor"                    # e.g., Người lao động, Người sử dụng lao động
    CONCEPT = "LegalConcept"          # e.g., Thử việc, Đơn phương chấm dứt HĐLĐ


class LegalRelationType(str, Enum):
    """Core Relationship types in the Legal Knowledge Graph."""
    # Structural hierarchy (Parent -> Child)
    HAS_CHAPTER = "HAS_CHAPTER"
    HAS_ARTICLE = "HAS_ARTICLE"
    HAS_CLAUSE = "HAS_CLAUSE"
    HAS_POINT = "HAS_POINT"

    # Statutory Bridge & Normative Hierarchy
    GUIDES = "GUIDES"                  # Decree/Circular GUIDES framework Article (e.g. NĐ 145/2020 GUIDES Điều 35 BLLĐ)
    AMENDS = "AMENDS"                  # Law A AMENDS Law B
    REPLACES = "REPLACES"              # Decree A REPLACES Decree B
    REFERENCES = "REFERENCES"          # Article X REFERENCES Article Y (e.g. Điều 36 viện dẫn Điều 35)

    # Sanctions & Compliance
    PENALIZES = "PENALIZES"            # Sanction node PENALIZES violation of Article (from NĐ 12/2022)
    APPLIES_TO = "APPLIES_TO"          # Article/Penalty APPLIES_TO Actor
    REGULATES = "REGULATES"            # Article REGULATES LegalConcept


@dataclass
class LegalEntity:
    """Represents a node entity in the Knowledge Graph."""
    label: LegalNodeLabel
    entity_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LegalRelation:
    """Represents a directed edge relationship in the Knowledge Graph."""
    source_id: str
    source_label: LegalNodeLabel
    rel_type: LegalRelationType
    target_id: str
    target_label: LegalNodeLabel
    properties: Dict[str, Any] = field(default_factory=dict)


# Common Statutory Bridge Mappings (Decree -> Framework Law Article)
# Used for deterministic graph construction and query expansion
DEFAULT_STATUTORY_BRIDGES: List[Dict[str, Any]] = [
    {
        "source_doc_id": "ND_145_2020",
        "source_article": 7,
        "rel_type": LegalRelationType.GUIDES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 35,
        "target_clause": "1",
        "target_point": "d",
        "description": "NĐ 145/2020 Điều 7 quy định ngành, nghề đặc thù hướng dẫn Điều 35 K1 Điểm d BLLĐ 2019",
    },
    {
        "source_doc_id": "ND_145_2020",
        "source_article": 8,
        "rel_type": LegalRelationType.GUIDES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 46,
        "description": "NĐ 145/2020 Điều 8 hướng dẫn tính trợ cấp thôi việc quy định tại Điều 46 BLLĐ 2019",
    },
    {
        "source_doc_id": "ND_145_2020",
        "source_article": 55,
        "rel_type": LegalRelationType.GUIDES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 98,
        "description": "NĐ 145/2020 Điều 55 hướng dẫn tính tiền lương làm thêm giờ quy định tại Điều 98 BLLĐ 2019",
    },
    {
        "source_doc_id": "ND_135_2020",
        "source_article": 3,
        "rel_type": LegalRelationType.GUIDES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 169,
        "description": "NĐ 135/2020 hướng dẫn lộ trình tuổi nghỉ hưu theo Điều 169 BLLĐ 2019",
    },
    # Sanctions: NĐ 12/2022 is REPEALED in the corpus (effective_to 2026-09-09,
    # replaced_by 283/2026/NĐ-CP), so penalty bridges point to the current decree.
    # Article pairs verified against data/processed/legal_documents_v3.jsonl
    # (see tests/test_graph_bridges.py).
    {
        "source_doc_id": "ND_283_2026",
        "source_article": 23,
        "rel_type": LegalRelationType.PENALIZES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 97,
        "description": "NĐ 283/2026 Điều 23 xử phạt vi phạm về tiền lương (kỳ hạn trả lương - Điều 97 BLLĐ 2019)",
    },
    {
        "source_doc_id": "ND_283_2026",
        "source_article": 24,
        "rel_type": LegalRelationType.PENALIZES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 107,
        "description": "NĐ 283/2026 Điều 24 xử phạt vi phạm về thời giờ làm việc, làm thêm giờ (Điều 107 BLLĐ 2019)",
    },
    {
        "source_doc_id": "ND_283_2026",
        "source_article": 25,
        "rel_type": LegalRelationType.PENALIZES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 125,
        "description": "NĐ 283/2026 Điều 25 xử phạt vi phạm về kỷ luật lao động, sa thải (Điều 125 BLLĐ 2019)",
    },
    {
        "source_doc_id": "ND_283_2026",
        "source_article": 25,
        "rel_type": LegalRelationType.PENALIZES,
        "target_doc_id": "VBHN_18_2026",
        "target_article": 127,
        "description": "NĐ 283/2026 Điều 25 xử phạt hành vi bị nghiêm cấm khi xử lý kỷ luật lao động (Điều 127 BLLĐ 2019)",
    },
]
