# VietLabor AI Architecture Overview

VietLabor AI is an enterprise-grade legal reasoning and retrieval-augmented generation (RAG) assistant specifically calibrated for Vietnamese Labor Law (Bộ luật Lao động 2019 and associated sub-law decrees).

## Core System Layers
1. **Official Legal Data Ingestion**: Rigorously parsed from official gazette PDFs, DOCXs, and signed Government decrees.
2. **Hybrid Retrieval**: Combines BM25 lexical search with dense vector embeddings (BGE-M3) and Knowledge Graph traversal.
3. **Multi-Issue Decomposition**: Dissects complex user narratives into discrete legal questions.
4. **Evidence Sufficiency Gate**: Material premise gate ensuring zero hallucination on missing factual premises.
5. **Interactive Streamlit Interface**: High-performance client-side surface with 0ms view navigation and document attachment.
