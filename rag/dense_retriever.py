# -*- coding: utf-8 -*-
"""
VietLabor AI - Dense Vector Retriever
Performs dense retrieval using BAAI/bge-m3 embeddings and ChromaDB vector store.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from rag.vectorstore import LegalVectorStore

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Dense retriever wrapping LegalVectorStore."""

    def __init__(self, vectorstore: Optional[LegalVectorStore] = None):
        self.vectorstore = vectorstore or LegalVectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves top-k chunks semantically closest to the query string.
        
        Args:
            query: Vietnamese natural language query.
            top_k: Number of chunks to retrieve.
            where: Optional metadata filter for ChromaDB.
            
        Returns:
            List of dicts containing:
                - chunk_id: str
                - score: float (cosine similarity in [0, 1])
                - content: str (original clause/point content)
                - retrieval_text: str (enriched hierarchical legal text)
                - metadata: dict
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return []

        return self.vectorstore.query(
            query_text=clean_query,
            top_k=top_k,
            where=where,
        )
