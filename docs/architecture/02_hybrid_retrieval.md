# Hybrid Retrieval Architecture

VietLabor AI combines dense vector search with sparse lexical matching using Reciprocal Rank Fusion (RRF) and tuned alpha weighting.

## Scoring Formula
$$Score(d) = \alpha \cdot DenseScore(d) + (1 - \alpha) \cdot BM25Score(d)$$

- **Dense Model**: BGE-M3 (multilingual embeddings optimized for Vietnamese legal terms).
- **BM25s**: Tokenized using Vietnamese word segmentation with specialized legal synonym expansion.
- **Top-K Reranking**: Contextually selects provisions with statutory hierarchy priority (Law > Decree > Circular).
