# Changelog - VietLabor AI

## [2.5.0] - 2026-10-12
### Major Upgrade Milestone (100 Discrete Commits)
- **RAG & Evidence Precision**: Fixed explicit chunk ownership attribution, resolved false fallback on cross-issue tokens, and implemented automated markdown heading synthesis.
- **Statutory Guardrails**: Added explicit legal constraints for labor vs service contracts, temporal validity tracking, and citation deduplication.
- **Knowledge Graph Integration**: Enhanced Neo4j ontology constructor, Cypher sanitizers, synonym expansion, and LRU traversal caching.
- **Evaluation Benchmark**: Achieved 100% grounded score (11/11 Gold Questions, 0 hallucinations, 0 false fallbacks).
- **UI/UX Modernization**: Revamped Streamlit dashboard with approved layout components, glassmorphism dark theme, quick suggestion chips, and exportable consultation reports.
- **Fine-Tuning Assets**: Packaged 1,000 ChatML/Alpaca SFT records, Can Tho situations, Thai Nguyen dispute dataset, and Colab fine-tuning notebook for Qwen 2.5 7B.
- **Cleanups & Infrastructure**: Production multi-stage Dockerfile, docker-compose, and removal of deprecated legacy archives.
