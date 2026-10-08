# Architecture Decision Records (ADR)

## ADR-001: Hybrid Lexical-Dense Retrieval for Vietnamese Legal Code
- **Status**: Accepted
- **Context**: Vietnamese legal texts feature exact statutory article numbering combined with rich colloquial terminology used by workers.
- **Decision**: Combine BM25 lexical token matching with dense multilingual embeddings (BGE-M3) using calibrated alpha weighting.
- **Consequences**: Accurate resolution of both exact article citations (Điều 21, Điều 107) and colloquial phrasing.

## ADR-002: Deterministic Material Premise Gate
- **Status**: Accepted
- **Context**: In labor law, critical outcomes depend on precise premises (e.g. seniority, contract type, notice period).
- **Decision**: Introduce a pre-generation material premise validator that identifies unresolved issues and prevents unjustified conclusions.
- **Consequences**: Zero hallucination on missing factual premises; explicit guidance prompts to user.
