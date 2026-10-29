# -*- coding: utf-8 -*-
"""
Tests for VietLabor AI Knowledge Graph & Hybrid GraphRAG Structure.
Verifies schema definitions, connector fallback behavior, cypher query templates,
and HybridGraphRetriever instantiation.
"""
from __future__ import annotations

from graph.connector import Neo4jConnector
from graph.cypher_templates import CypherTemplates
from graph.retriever import LegalGraphRetriever
from graph.schema import DEFAULT_STATUTORY_BRIDGES, LegalNodeLabel, LegalRelationType


def test_legal_ontology_schema():
    """Verify Node labels and Relation types exist and conform to ontology."""
    assert LegalNodeLabel.DOCUMENT.value == "LegalDocument"
    assert LegalNodeLabel.ARTICLE.value == "Article"
    assert LegalNodeLabel.PENALTY.value == "Penalty"

    assert LegalRelationType.GUIDES.value == "GUIDES"
    assert LegalRelationType.PENALIZES.value == "PENALIZES"
    assert LegalRelationType.HAS_ARTICLE.value == "HAS_ARTICLE"

    assert len(DEFAULT_STATUTORY_BRIDGES) >= 5
    first_bridge = DEFAULT_STATUTORY_BRIDGES[0]
    assert "source_doc_id" in first_bridge
    assert "target_doc_id" in first_bridge
    assert first_bridge["rel_type"] in (LegalRelationType.GUIDES, LegalRelationType.PENALIZES)


def test_neo4j_connector_graceful_offline_fallback():
    """Verify that when Neo4j server is not reachable, connector does not crash."""
    connector = Neo4jConnector(
        uri="bolt://127.0.0.1:9999",  # unreachable port
        user="test",
        password="test",
        enabled=True,
    )
    # Must report False, not raise unhandled exception
    assert connector.is_connected() is False

    # Queries should safely return empty lists
    results = connector.run_query("MATCH (n) RETURN n")
    assert results == []

    # Batch writes should safely return 0
    batch_res = connector.run_write_batch("UNWIND $batch AS x RETURN x", [{"a": 1}])
    assert batch_res == 0

    connector.close()


def test_cypher_templates_syntax_and_placeholders():
    """Verify Cypher query templates contain required placeholders."""
    assert "$doc_id" in CypherTemplates.GET_STATUTORY_BRIDGE
    assert "$article_number" in CypherTemplates.GET_STATUTORY_BRIDGE
    assert "$article_number" in CypherTemplates.GET_PENALTIES_FOR_ARTICLE
    assert "$article_number" in CypherTemplates.MULTI_HOP_LEGAL_CHAIN
    assert len(CypherTemplates.CREATE_CONSTRAINTS) >= 2


def test_graph_retriever_offline_resilience():
    """Verify LegalGraphRetriever handles offline database gracefully."""
    mock_connector = Neo4jConnector(enabled=False)
    retriever = LegalGraphRetriever(connector=mock_connector)

    assert retriever.is_available() is False
    assert retriever.get_statutory_bridges("VBHN_18_2026", 35) == []
    assert retriever.get_penalties("VBHN_18_2026", 97) == []
    assert retriever.retrieve_multi_hop_chain("VBHN_18_2026", 35) is None
    assert retriever.format_graph_context({}) == ""


def test_format_graph_context():
    """Verify formatting of graph context for LLM prompt."""
    retriever = LegalGraphRetriever(connector=Neo4jConnector(enabled=False))
    dummy_chain = {
        "framework_doc_id": "VBHN_18_2026",
        "framework_article_number": 35,
        "framework_title": "Quyền đơn phương chấm dứt HĐLĐ",
        "guiding_articles": [
            {
                "doc_id": "ND_145_2020",
                "article": 7,
                "content": "Ngành, nghề, công việc đặc thù thời hạn báo trước ít nhất 120 ngày.",
            }
        ],
        "penalty_articles": [],
    }
    formatted = retriever.format_graph_context(dummy_chain)
    assert "Knowledge Graph Subgraph" in formatted
    assert "VBHN_18_2026" in formatted
    assert "ND_145_2020" in formatted
    assert "120 ngày" in formatted


def test_automated_statutory_references_extraction():
    """Verify automated extraction of intra- and inter-document REFERENCES from corpus."""
    from graph.builder import KnowledgeGraphBuilder
    from graph.schema import LegalRelationType

    builder = KnowledgeGraphBuilder(connector=Neo4jConnector(enabled=False))
    refs = builder.extract_references_from_corpus()

    assert len(refs) >= 500, f"Expected at least 500 extracted references, got {len(refs)}"
    assert all(r["rel_type"] == LegalRelationType.REFERENCES.value for r in refs)
    assert all(r["source_doc_id"] and r["target_doc_id"] for r in refs)
    assert all(isinstance(r["source_article"], int) and isinstance(r["target_article"], int) for r in refs)

    # Must contain both intra-doc (e.g. within BLLĐ) and inter-doc (e.g. Decree -> Law) references
    intra_refs = [r for r in refs if r["source_doc_id"] == r["target_doc_id"]]
    inter_refs = [r for r in refs if r["source_doc_id"] != r["target_doc_id"]]
    assert len(intra_refs) >= 300
    assert len(inter_refs) >= 100
