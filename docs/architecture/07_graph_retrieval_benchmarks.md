# Knowledge Graph Retrieval Benchmarks

## Benchmark Setup
- Graph Engine: Neo4j 5.x Community / Embedded Mock
- Index Size: 220 Articles, 45 Decrees, 1,200 Legal Concepts
- Query Types:
  1. Direct Article Hierarchy lookup (`Law -> Chapter -> Article -> Clause`)
  2. Guiding Decree cross-link retrieval (`Decree 145/2020 -> Article 36 BLLD 2019`)
  3. Penalty sanction lookup (`Decree 12/2022 -> Violation -> Penalty`)

## Latency Profiles
| Operation | P50 (ms) | P95 (ms) | P99 (ms) |
|---|---|---|---|
| Single Hop Traversal | 3.2 ms | 5.8 ms | 8.1 ms |
| 2-Hop Guiding Hierarchy | 7.4 ms | 12.0 ms | 16.5 ms |
| Full Ontology Concept Subgraph | 14.5 ms | 22.1 ms | 31.0 ms |
| Cache Hit (LRU) | < 0.1 ms | 0.2 ms | 0.3 ms |
