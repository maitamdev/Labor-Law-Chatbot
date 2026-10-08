# -*- coding: utf-8 -*-
"""
VietLabor AI - Cypher Query Templates
Pre-compiled, parameterized Cypher queries for Legal Knowledge Graph retrieval,
multi-hop traversal, hierarchical context assembly, and statutory bridge lookups.
"""
from __future__ import annotations


class CypherTemplates:
    """Library of standard Cypher queries designed for legal domain reasoning."""

    # 1. Statutory Bridge: Find guiding decrees/circulars for a framework article
    GET_STATUTORY_BRIDGE = """
    MATCH (doc:LegalDocument)-[:HAS_ARTICLE]->(art:Article)
    WHERE doc.doc_id = $doc_id AND art.number = $article_number
    MATCH (guiding_doc:LegalDocument)-[:HAS_ARTICLE]->(guiding_art:Article)-[r:GUIDES]->(art)
    RETURN guiding_doc.doc_id AS guiding_doc_id,
           guiding_doc.doc_title AS guiding_doc_title,
           guiding_art.number AS guiding_article_number,
           guiding_art.title AS guiding_article_title,
           guiding_art.content AS guiding_content,
           type(r) AS relation_type
    """

    # 2. Reverse Statutory Bridge: Find framework articles guided by a decree article
    GET_FRAMEWORK_FROM_DECREE = """
    MATCH (guiding_doc:LegalDocument)-[:HAS_ARTICLE]->(guiding_art:Article)
    WHERE guiding_doc.doc_id = $guiding_doc_id AND guiding_art.number = $guiding_article_number
    MATCH (guiding_art)-[r:GUIDES]->(framework_art:Article)<-[:HAS_ARTICLE]-(framework_doc:LegalDocument)
    RETURN framework_doc.doc_id AS framework_doc_id,
           framework_doc.doc_title AS framework_doc_title,
           framework_art.number AS framework_article_number,
           framework_art.title AS framework_article_title,
           framework_art.content AS framework_content
    """

    # 3. Penalties & Enforcement: Find Decree 12/2022 penalties linked to a violated article
    GET_PENALTIES_FOR_ARTICLE = """
    MATCH (violated_art:Article {doc_id: $doc_id, number: $article_number})
    MATCH (penalty_art:Article)-[r:PENALIZES]->(violated_art)
    MATCH (penalty_doc:LegalDocument)-[:HAS_ARTICLE]->(penalty_art)
    RETURN penalty_doc.doc_id AS penalty_doc_id,
           penalty_doc.doc_title AS penalty_doc_title,
           penalty_art.number AS penalty_article_number,
           penalty_art.title AS penalty_article_title,
           penalty_art.content AS penalty_content
    """

    # 4. Multi-hop Statutory Chain: Concept / Violation -> Framework Law -> Guiding Decree -> Penalty
    MULTI_HOP_LEGAL_CHAIN = """
    MATCH (doc:LegalDocument {doc_id: $doc_id})-[:HAS_ARTICLE]->(art:Article {number: $article_number})
    OPTIONAL MATCH (guiding_art:Article)-[:GUIDES]->(art)
    OPTIONAL MATCH (guiding_doc:LegalDocument)-[:HAS_ARTICLE]->(guiding_art)
    OPTIONAL MATCH (penalty_art:Article)-[:PENALIZES]->(art)
    OPTIONAL MATCH (penalty_doc:LegalDocument)-[:HAS_ARTICLE]->(penalty_art)
    RETURN art.doc_id AS framework_doc_id,
           art.number AS framework_article_number,
           art.title AS framework_title,
           art.content AS framework_content,
           collect(DISTINCT {
               doc_id: guiding_doc.doc_id,
               article: guiding_art.number,
               content: guiding_art.content
           }) AS guiding_articles,
           collect(DISTINCT {
               doc_id: penalty_doc.doc_id,
               article: penalty_art.number,
               content: penalty_art.content
           }) AS penalty_articles
    """

    # 5. Full Hierarchical Path: Trace an article to its parent Chapter and Document
    GET_ARTICLE_LINEAGE = """
    MATCH (doc:LegalDocument)-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_ARTICLE]->(art:Article)
    WHERE doc.doc_id = $doc_id AND art.number = $article_number
    RETURN doc.doc_id AS doc_id,
           doc.doc_title AS doc_title,
           ch.title AS chapter_title,
           art.number AS article_number,
           art.title AS article_title,
           art.content AS article_content
    """

    # 5b. Batch graph expansion used by the live retrieval pipeline.
    # Given seed articles (from BM25 + dense hits), return the corpus chunk_ids of
    # articles linked through GUIDES / PENALIZES in either direction. Returning
    # chunk_ids (not free text) lets graph hits flow through the same evidence
    # locking and citation validation as every other candidate.
    RELATED_ARTICLE_CHUNKS = """
    UNWIND $seeds AS seed
    MATCH (a:Article {doc_id: seed.doc_id, number: seed.number})-[r:GUIDES|PENALIZES]-(b:Article)
    WHERE NOT (b.doc_id = seed.doc_id AND b.number = seed.number)
    WITH seed, b, type(r) AS relation, startNode(r) = b AS b_is_source
    RETURN DISTINCT seed.doc_id AS seed_doc_id,
           seed.number AS seed_article,
           b.chunk_id AS chunk_id,
           b.doc_id AS doc_id,
           b.number AS article_number,
           relation,
           b_is_source
    LIMIT $limit
    """

    # 6. Schema Initialization & Constraints
    CREATE_CONSTRAINTS = [
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:LegalDocument) REQUIRE d.doc_id IS UNIQUE",
        "CREATE CONSTRAINT article_id_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.chunk_id IS UNIQUE",
        "CREATE INDEX article_doc_number IF NOT EXISTS FOR (a:Article) ON (a.doc_id, a.number)",
    ]
