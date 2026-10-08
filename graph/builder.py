# -*- coding: utf-8 -*-
"""
VietLabor AI - Knowledge Graph Builder
Builds and populates the Neo4j Legal Knowledge Graph directly from processed
corpus data (READ-ONLY) and predefined statutory bridges without altering source files.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import PRODUCTION_CORPUS_PATH
from graph.connector import Neo4jConnector, get_neo4j_connector
from graph.cypher_templates import CypherTemplates
from graph.schema import DEFAULT_STATUTORY_BRIDGES

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Constructs the Vietnamese Legal Knowledge Graph in Neo4j."""

    def __init__(self, connector: Optional[Neo4jConnector] = None, corpus_path: Optional[Path] = None):
        self.connector = connector or get_neo4j_connector()
        self.corpus_path = corpus_path or PRODUCTION_CORPUS_PATH

    def initialize_schema(self) -> bool:
        """Creates unique constraints and indexes in Neo4j."""
        if not self.connector.is_connected():
            logger.warning("Neo4j not connected. Cannot initialize schema.")
            return False

        logger.info("Initializing Neo4j schema constraints and indexes...")
        for constraint_cypher in CypherTemplates.CREATE_CONSTRAINTS:
            try:
                self.connector.run_query(constraint_cypher)
            except Exception as e:
                logger.error("Error creating constraint: %s", e)
        return True

    def build_from_corpus(self, batch_size: int = 200) -> Dict[str, int]:
        """Ingests legal documents and articles from the corpus into Neo4j in batches.
        Reads the corpus file in strictly READ-ONLY mode.
        """
        if not self.connector.is_connected():
            logger.warning("Neo4j not connected. Aborting graph build.")
            return {"documents": 0, "articles": 0, "bridges": 0}

        self.initialize_schema()

        if not self.corpus_path.exists():
            logger.error("Corpus path does not exist: %s", self.corpus_path)
            return {"documents": 0, "articles": 0, "bridges": 0}

        docs_map: Dict[str, Dict[str, Any]] = {}
        articles: List[Dict[str, Any]] = []

        logger.info("Reading corpus from: %s (read-only)", self.corpus_path)
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                doc_id = chunk.get("doc_id")
                if not doc_id:
                    continue

                if doc_id not in docs_map:
                    docs_map[doc_id] = {
                        "doc_id": doc_id,
                        "doc_title": chunk.get("doc_title", doc_id),
                        "document_no": chunk.get("document_no", ""),
                        "document_type": chunk.get("document_type", ""),
                        "issuer": chunk.get("issuer", ""),
                        "effective_from": chunk.get("effective_from", ""),
                        "status": chunk.get("status", ""),
                    }

                art_num = chunk.get("article_number")
                if art_num is not None:
                    try:
                        clean_art_num = int(str(art_num).strip())
                    except ValueError:
                        clean_art_num = None

                    if clean_art_num is not None:
                        articles.append({
                            "chunk_id": chunk.get("chunk_id", f"{doc_id}#art_{clean_art_num}"),
                            "doc_id": doc_id,
                            "number": clean_art_num,
                            "title": chunk.get("article_title") or f"Điều {clean_art_num}",
                            "chapter": chunk.get("chapter") or "",
                            "content": chunk.get("content", ""),
                            "clause_number": chunk.get("clause_number"),
                            "point": chunk.get("point"),
                        })

        # 1. Ingest Documents
        doc_cypher = """
        UNWIND $batch AS doc
        MERGE (d:LegalDocument {doc_id: doc.doc_id})
        SET d.doc_title = doc.doc_title,
            d.document_no = doc.document_no,
            d.document_type = doc.document_type,
            d.issuer = doc.issuer,
            d.effective_from = doc.effective_from,
            d.status = doc.status
        """
        doc_count = self.connector.run_write_batch(doc_cypher, list(docs_map.values()))
        logger.info("Ingested %d LegalDocument nodes.", doc_count)

        # 2. Ingest Articles and Chapter hierarchy
        art_cypher = """
        UNWIND $batch AS art
        MERGE (a:Article {chunk_id: art.chunk_id})
        SET a.doc_id = art.doc_id,
            a.number = art.number,
            a.title = art.title,
            a.content = art.content,
            a.clause_number = art.clause_number,
            a.point = art.point

        WITH a, art
        MATCH (d:LegalDocument {doc_id: art.doc_id})
        MERGE (d)-[:HAS_ARTICLE]->(a)
        """
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            self.connector.run_write_batch(art_cypher, batch)
        logger.info("Ingested %d Article nodes and structural relationships.", len(articles))

        # 3. Ingest Statutory Bridges
        bridge_count = self._ingest_statutory_bridges()

        return {
            "documents": doc_count,
            "articles": len(articles),
            "bridges": bridge_count,
        }

    def _ingest_statutory_bridges(self) -> int:
        """Creates GUIDES and PENALIZES relationships between decrees and framework laws."""
        count = 0
        bridge_cypher = """
        UNWIND $batch AS bridge
        MATCH (src_doc:LegalDocument {doc_id: bridge.source_doc_id})-[:HAS_ARTICLE]->(src_art:Article {number: bridge.source_article})
        MATCH (tgt_doc:LegalDocument {doc_id: bridge.target_doc_id})-[:HAS_ARTICLE]->(tgt_art:Article {number: bridge.target_article})
        MERGE (src_art)-[r:GUIDES]->(tgt_art)
        SET r.description = bridge.description
        """
        penalizes_cypher = """
        UNWIND $batch AS bridge
        MATCH (src_doc:LegalDocument {doc_id: bridge.source_doc_id})-[:HAS_ARTICLE]->(src_art:Article {number: bridge.source_article})
        MATCH (tgt_doc:LegalDocument {doc_id: bridge.target_doc_id})-[:HAS_ARTICLE]->(tgt_art:Article {number: bridge.target_article})
        MERGE (src_art)-[r:PENALIZES]->(tgt_art)
        SET r.description = bridge.description
        """

        # The driver only needs primitives; rel_type is a str Enum.
        plain = [
            {**b, "rel_type": getattr(b.get("rel_type"), "value", b.get("rel_type"))}
            for b in DEFAULT_STATUTORY_BRIDGES
        ]
        guides = [b for b in plain if b.get("rel_type") == "GUIDES"]
        penalties = [b for b in plain if b.get("rel_type") == "PENALIZES"]

        if guides:
            count += self.connector.run_write_batch(bridge_cypher, guides)
        if penalties:
            count += self.connector.run_write_batch(penalizes_cypher, penalties)

        logger.info("Ingested %d Statutory Bridge relationships into Neo4j.", count)
        return count
