# -*- coding: utf-8 -*-
"""
VietLabor AI - Legal Graph Retriever
Performs multi-hop graph traversal and subgraph extraction in Neo4j,
returning structured relational legal contexts (Framework Laws, Guiding Decrees, Sanctions).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from graph.connector import Neo4jConnector, get_neo4j_connector
from graph.cypher_templates import CypherTemplates

logger = logging.getLogger(__name__)


class LegalGraphRetriever:
    """Retrieves interconnected legal subgraphs from Neo4j."""

    def __init__(self, connector: Optional[Neo4jConnector] = None):
        self.connector = connector or get_neo4j_connector()

    def is_available(self) -> bool:
        """Returns True if the Neo4j backend is responsive."""
        return self.connector.is_connected()

    def get_statutory_bridges(self, doc_id: str, article_number: int) -> List[Dict[str, Any]]:
        """Retrieves guiding decrees/circulars for a given framework law article."""
        if not self.is_available():
            return []
        return self.connector.run_query(
            CypherTemplates.GET_STATUTORY_BRIDGE,
            {"doc_id": doc_id, "article_number": article_number},
        )

    def get_penalties(self, doc_id: str, article_number: int) -> List[Dict[str, Any]]:
        """Retrieves sanction/penalty regulations (NĐ 12/2022) linked to a violated article."""
        if not self.is_available():
            return []
        return self.connector.run_query(
            CypherTemplates.GET_PENALTIES_FOR_ARTICLE,
            {"doc_id": doc_id, "article_number": article_number},
        )

    def retrieve_multi_hop_chain(self, doc_id: str, article_number: int) -> Optional[Dict[str, Any]]:
        """Executes full multi-hop traversal: Framework Article -> Guiding Decrees + Penalties."""
        if not self.is_available():
            return None
        records = self.connector.run_query(
            CypherTemplates.MULTI_HOP_LEGAL_CHAIN,
            {"doc_id": doc_id, "article_number": article_number},
        )
        return records[0] if records else None

    def expand_related_chunks(self, seeds: List[Dict[str, Any]], limit: int = 40) -> List[Dict[str, Any]]:
        """Returns chunk_ids of articles linked to the seed articles via GUIDES/PENALIZES.

        Args:
            seeds: [{"doc_id": str, "number": int}, ...] taken from lexical/dense hits.
            limit: Maximum number of related chunk records returned.
        """
        if not seeds or not self.is_available():
            return []
        return self.connector.run_query(
            CypherTemplates.RELATED_ARTICLE_CHUNKS,
            {"seeds": seeds, "limit": int(limit)},
        )

    def format_graph_context(self, chain_data: Dict[str, Any]) -> str:
        """Formats graph traversal results into a clean, markdown-formatted prompt context."""
        if not chain_data:
            return ""

        lines = [
            f"**Căn cứ Đồ thị Tri thức Pháp luật (Knowledge Graph Subgraph):**",
            f"- **Điều luật gốc**: {chain_data.get('framework_doc_id')} Điều {chain_data.get('framework_article_number')}: {chain_data.get('framework_title')}",
        ]

        guidings = [g for g in chain_data.get("guiding_articles", []) if g.get("doc_id")]
        if guidings:
            lines.append("  - **Văn bản hướng dẫn thi hành (Statutory Bridge)**:")
            for g in guidings:
                lines.append(f"    + {g.get('doc_id')} Điều {g.get('article')}: {g.get('content')[:150]}...")

        penalties = [p for p in chain_data.get("penalty_articles", []) if p.get("doc_id")]
        if penalties:
            lines.append("  - **Chế tài xử phạt liên quan (Sanctions)**:")
            for p in penalties:
                lines.append(f"    + {p.get('doc_id')} Điều {p.get('article')}: {p.get('content')[:150]}...")

        return "\n".join(lines)
