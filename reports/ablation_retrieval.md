# VietLabor AI - Retrieval Ablation

- Generated: 2026-10-08T08:52:39
- Gold set: `data/evaluation/retrieval_gold.json` (155 questions; 145 scorable, out-of-scope skipped)
- Metrics are article-level ((doc_id, Điều) pairs) except ChunkR.

| Config | hit@5 | hit@10 | recall@5 | recall@10 | mrr@10 | chunk recall@10 | ms/query |
|---|---|---|---|---|---|---|---|
| bm25 | 0.814 | 0.855 | 0.809 | 0.852 | 0.664 | 0.810 | 1 |
| dense | 0.828 | 0.883 | 0.828 | 0.877 | 0.729 | 0.824 | 182 |
| hybrid | 0.924 | 0.959 | 0.919 | 0.955 | 0.807 | 0.921 | 199 |
| hybrid_graph | 0.924 | 0.959 | 0.919 | 0.955 | 0.807 | 0.921 | 170 |
| hybrid_norm | 0.959 | 0.979 | 0.953 | 0.976 | 0.835 | 0.941 | 169 |

**Notes**

- `hybrid_graph`: Neo4j offline/disabled → equals hybrid

## Hit@10 by query type

| Config | colloquial | cross_reference | exact_reference | long | numeric | paraphrase | semantic | short |
|---|---|---|---|---|---|---|---|---|
| bm25 | 0.50 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 0.50 (n=8) | 0.92 (n=39) | 0.86 (n=7) | 0.94 (n=31) | 0.85 (n=13) |
| dense | 0.81 (n=16) | 1.00 (n=4) | 0.63 (n=27) | 1.00 (n=8) | 0.97 (n=39) | 1.00 (n=7) | 0.94 (n=31) | 0.92 (n=13) |
| hybrid | 0.75 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 1.00 (n=8) | 1.00 (n=39) | 1.00 (n=7) | 0.97 (n=31) | 1.00 (n=13) |
| hybrid_graph | 0.75 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 1.00 (n=8) | 1.00 (n=39) | 1.00 (n=7) | 0.97 (n=31) | 1.00 (n=13) |
| hybrid_norm | 1.00 (n=16) | 1.00 (n=4) | 0.96 (n=27) | 1.00 (n=8) | 0.97 (n=39) | 1.00 (n=7) | 0.97 (n=31) | 1.00 (n=13) |
