# Retrieval Service API Documentation

Provides programmatic interface to the hybrid retrieval engine combining lexical BM25 and vector search.

```python
from rag.hybrid_retriever import HybridRetriever

retriever = HybridRetriever(alpha=0.6, top_k=5)
results = retriever.retrieve(query="Thời giờ làm việc tối đa một ngày")
for r in results:
    print(r.chunk_id, r.article, r.score)
```
