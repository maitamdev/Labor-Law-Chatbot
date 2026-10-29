# VietLabor AI - Retrieval Ablation

- Generated: 2026-10-13T16:58:32
- Gold set: `data/evaluation/retrieval_gold.json` (155 questions; 145 scorable, out-of-scope skipped)
- Metrics are article-level ((doc_id, Điều) pairs) except ChunkR.

| Config | hit@5 | hit@10 | recall@5 | recall@10 | mrr@10 | chunk recall@10 | ms/query |
|---|---|---|---|---|---|---|---|
| bm25 | 0.807 | 0.869 | 0.803 | 0.866 | 0.688 | 0.831 | 8 |
| dense | N/A | N/A | N/A | N/A | N/A | N/A | - |
| hybrid | 0.807 | 0.869 | 0.803 | 0.866 | 0.676 | 0.831 | 3 |
| hybrid_norm | 0.848 | 0.910 | 0.844 | 0.908 | 0.703 | 0.872 | 3 |

**Notes**

- `dense`: N/A - dense unavailable (RuntimeError: Chroma index incomplete or stale)
- `hybrid`: dense unavailable → equals BM25 only

## Hit@10 by query type

| Config | colloquial | cross_reference | exact_reference | long | numeric | paraphrase | semantic | short |
|---|---|---|---|---|---|---|---|---|
| bm25 | 0.56 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 0.50 (n=8) | 0.92 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 0.85 (n=13) |
| hybrid | 0.56 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 0.50 (n=8) | 0.92 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 0.85 (n=13) |
| hybrid_norm | 0.94 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 0.50 (n=8) | 0.92 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 0.85 (n=13) |
