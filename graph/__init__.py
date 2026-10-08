# -*- coding: utf-8 -*-
"""
VietLabor AI - Knowledge Graph & GraphRAG Module
Provides Neo4j connectivity, Legal Ontology definitions, Cypher traversal templates,
and Graph-based retrieval for Vietnamese Labor Law.
"""
from __future__ import annotations

from graph.schema import LegalNodeLabel, LegalRelationType, LegalEntity
from graph.connector import Neo4jConnector, get_neo4j_connector
from graph.cypher_templates import CypherTemplates
from graph.retriever import LegalGraphRetriever

__all__ = [
    "LegalNodeLabel",
    "LegalRelationType",
    "LegalEntity",
    "Neo4jConnector",
    "get_neo4j_connector",
    "CypherTemplates",
    "LegalGraphRetriever",
]
