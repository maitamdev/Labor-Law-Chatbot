# Multi-Stage RAG Pipeline Architecture Flow

```
[User Query]
      │
      ▼
[1. Issue Decomposer & Normalizer]
      │
      ├──────────────────────────────┐
      ▼                              ▼
[2a. Hybrid Retriever (Chroma+BM25)] [2b. Knowledge Graph (Neo4j)]
      │                              │
      └──────────────┬───────────────┘
                     ▼
          [3. Candidate Aggregator]
                     │
                     ▼
          [4. Material Premise Gate]
                     │
                     ▼
          [5. High-Precision Evidence Selector]
                     │
                     ▼
          [6. Context Builder & Attributions]
                     │
                     ▼
          [7. LLM Synthesis (Qwen / DeepSeek)]
                     │
                     ▼
          [8. Output Validator & Grounding Guard]
                     │
                     ▼
          [Final Legal Advisory Response]
```
