# VietLabor AI - Retrieval Ablation

- Generated: 2026-10-14T03:29:09
- Gold set: `data/evaluation/retrieval_gold.json` (155 questions; 145 scorable, out-of-scope skipped)
- Metrics are article-level ((doc_id, Điều) pairs) except ChunkR.

| Config | hit@5 | hit@10 | recall@5 | recall@10 | mrr@10 | chunk recall@10 | ms/query |
|---|---|---|---|---|---|---|---|
| bm25 | 0.800 | 0.862 | 0.796 | 0.859 | 0.679 | 0.817 | 1 |
| hybrid | 0.931 | 0.952 | 0.922 | 0.945 | 0.803 | 0.910 | 40 |
| hybrid_norm | 0.931 | 0.959 | 0.922 | 0.952 | 0.804 | 0.917 | 12 |

## Hit@10 by query type

| Config | colloquial | cross_reference | exact_reference | long | numeric | paraphrase | semantic | short |
|---|---|---|---|---|---|---|---|---|
| bm25 | 0.50 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 0.50 (n=8) | 0.92 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 0.85 (n=13) |
| hybrid | 0.88 (n=16) | 1.00 (n=4) | 0.93 (n=27) | 1.00 (n=8) | 0.97 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 1.00 (n=13) |
| hybrid_norm | 0.94 (n=16) | 1.00 (n=4) | 0.93 (n=27) | 1.00 (n=8) | 0.97 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 1.00 (n=13) |
