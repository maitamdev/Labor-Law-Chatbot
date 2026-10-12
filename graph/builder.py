# -*- coding: utf-8 -*-
"""
VietLabor AI - Knowledge Graph Builder
Builds and populates the Neo4j Legal Knowledge Graph directly from processed
corpus data (READ-ONLY) and predefined statutory bridges without altering source files.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config.settings import PRODUCTION_CORPUS_PATH
from graph.connector import Neo4jConnector, get_neo4j_connector
from graph.cypher_templates import CypherTemplates
from graph.schema import DEFAULT_STATUTORY_BRIDGES, LegalRelationType

logger = logging.getLogger(__name__)

# Canonical name and number mappings for automated statutory cross-referencing
STATUTORY_DOC_MAPPING: Dict[str, str] = {
    "bộ luật lao động": "VBHN_18_2026",
    "bllđ": "VBHN_18_2026",
    "luật an toàn, vệ sinh lao động": "L_84_2015",
    "luật an toàn vệ sinh lao động": "L_84_2015",
    "luật bảo hiểm xã hội": "LUAT_113_2025",
    "luật việc làm": "LVL_74_2025",
    "luật người lao động việt nam đi làm việc ở nước ngoài": "LUAT_69_2020",
    "nghị định số 145/2020/nđ-cp": "ND_145_2020",
    "nghị định 145/2020/nđ-cp": "ND_145_2020",
    "nghị định số 12/2022/nđ-cp": "ND_12_2022",
    "nghị định 12/2022/nđ-cp": "ND_12_2022",
    "nghị định số 283/2026/nđ-cp": "ND_283_2026",
    "nghị định 283/2026/nđ-cp": "ND_283_2026",
    "nghị định số 135/2020/nđ-cp": "ND_135_2020",
    "nghị định 135/2020/nđ-cp": "ND_135_2020",
    "thông tư số 10/2020/tt-bldtbxh": "TT_10_2020",
    "thông tư 10/2020/tt-bldtbxh": "TT_10_2020",
    "nghị định số 39/2016/nđ-cp": "ND_39_2016",
    "nghị định 39/2016/nđ-cp": "ND_39_2016",
    "nghị định số 44/2016/nđ-cp": "ND_44_2016",
    "nghị định 44/2016/nđ-cp": "ND_44_2016",
    "nghị định số 24/2018/nđ-cp": "ND_24_2018",
    "nghị định 24/2018/nđ-cp": "ND_24_2018",
    "thông tư số 09/2020/tt-bldtbxh": "TT_09_2020",
    "thông tư 09/2020/tt-bldtbxh": "TT_09_2020",
}

STATUTORY_REF_PATTERN = re.compile(
    r'(?:quy định tại|theo quy định tại|áp dụng theo|theo|tại)\s+(?:[Kk]hoản\s+\d+\s+)?Điều\s+(\d+)'
    r'(?:\s+(?:của\s+)?(Bộ luật Lao động(?: năm 2019)?|Luật An toàn, vệ sinh lao động|Luật Bảo hiểm xã hội|Luật Việc làm|'
    r'Nghị định số\s+\d+/\d+/NĐ-CP|Nghị định\s+\d+/\d+/NĐ-CP|Thông tư số\s+\d+/\d+/TT-[A-Z]+|Thông tư\s+\d+/\d+/TT-[A-Z]+|'
    r'Bộ luật này|Luật này|Nghị định này|Thông tư này))?',
    re.IGNORECASE,
)


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

        # 4. Ingest Automated Cross-References (REFERENCES)
        ref_count = self._ingest_references(batch_size=batch_size)

        return {
            "documents": doc_count,
            "articles": len(articles),
            "bridges": bridge_count,
            "references": ref_count,
        }

    def extract_references_from_corpus(self) -> List[Dict[str, Any]]:
        """Extracts intra- and inter-document statutory REFERENCES from the corpus.
        Reads the corpus in strictly READ-ONLY mode and validates both source
        and target articles exist to guarantee zero dangling edges.
        """
        if not self.corpus_path.exists():
            return []

        # 1. Collect valid (doc_id, article_number) pairs to ensure reference integrity
        valid_articles: Set[Tuple[str, int]] = set()
        chunks: List[Dict[str, Any]] = []

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                d = c.get("doc_id")
                a = c.get("article_number")
                if d and a is not None:
                    try:
                        valid_articles.add((d, int(str(a).strip())))
                    except ValueError:
                        pass
                chunks.append(c)

        extracted: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, int, str, int]] = set()

        for c in chunks:
            doc_id = c.get("doc_id")
            src_art = c.get("article_number")
            if not doc_id or src_art is None:
                continue
            try:
                src_art = int(str(src_art).strip())
            except ValueError:
                continue

            content = c.get("content", "")
            for match in STATUTORY_REF_PATTERN.finditer(content):
                tgt_art = int(match.group(1))
                law_ref = match.group(2)
                if law_ref:
                    clean_ref = law_ref.lower().strip()
                    if clean_ref in ("bộ luật này", "luật này", "nghị định này", "thông tư này"):
                        tgt_doc_id = doc_id
                    else:
                        tgt_doc_id = STATUTORY_DOC_MAPPING.get(clean_ref)
                        if not tgt_doc_id:
                            for k, v in STATUTORY_DOC_MAPPING.items():
                                if k in clean_ref or clean_ref in k:
                                    tgt_doc_id = v
                                    break
                else:
                    tgt_doc_id = doc_id

                if tgt_doc_id and (tgt_doc_id, tgt_art) in valid_articles:
                    if not (tgt_doc_id == doc_id and tgt_art == src_art):
                        key = (doc_id, src_art, tgt_doc_id, tgt_art)
                        if key not in seen:
                            seen.add(key)
                            extracted.append({
                                "source_doc_id": doc_id,
                                "source_article": src_art,
                                "target_doc_id": tgt_doc_id,
                                "target_article": tgt_art,
                                "rel_type": LegalRelationType.REFERENCES.value,
                                "citation": match.group(0),
                            })
        logger.info("Extracted %d validated statutory REFERENCES from corpus.", len(extracted))
        return extracted

    def _ingest_references(self, batch_size: int = 200, references: Optional[List[Dict[str, Any]]] = None) -> int:
        """Ingests automated statutory REFERENCES edges between articles into Neo4j."""
        if references is None:
            references = self.extract_references_from_corpus()
        if not references:
            return 0

        ref_cypher = """
        UNWIND $batch AS ref
        MATCH (src_doc:LegalDocument {doc_id: ref.source_doc_id})-[:HAS_ARTICLE]->(src_art:Article {number: ref.source_article})
        MATCH (tgt_doc:LegalDocument {doc_id: ref.target_doc_id})-[:HAS_ARTICLE]->(tgt_art:Article {number: ref.target_article})
        MERGE (src_art)-[r:REFERENCES]->(tgt_art)
        SET r.citation = ref.citation
        """
        count = 0
        for i in range(0, len(references), batch_size):
            batch = references[i:i + batch_size]
            count += self.connector.run_write_batch(ref_cypher, batch)
        logger.info("Ingested %d REFERENCES relationships into Neo4j.", count)
        return count

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
