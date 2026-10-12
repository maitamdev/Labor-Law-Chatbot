# Neo4j Legal Knowledge Graph Schema

## Node Labels
- **Law**: Root statutory codes (e.g. `Bộ luật Lao động 2019`).
- **Chapter**: Major chapters within a law (`Chương III: Hợp đồng lao động`).
- **Article**: Individual articles (`Điều 36: Quyền đơn phương chấm dứt hợp đồng lao động của người sử dụng lao động`).
- **Clause**: Specific paragraphs within an article (`Khoản 1`, `Khoản 2`).
- **LegalConcept**: Extracted legal terms (e.g., `Trợ cấp thôi việc`, `Sa thải`, `Hợp đồng dịch vụ`).
- **Decree**: Guiding decrees (`Nghị định 145/2020/NĐ-CP`).
- **PenaltyArticle**: Administrative sanctions from Decree 12/2022/NĐ-CP.

## Relationships
- `(:Law)-[:CONTAINS]->(:Chapter)-[:CONTAINS]->(:Article)`
- `(:Article)-[:HAS_CLAUSE]->(:Clause)`
- `(:Decree)-[:GUIDES]->(:Article)`
- `(:PenaltyArticle)-[:SANCTIONS]->(:Article)`
- `(:Article)-[:MENTIONS]->(:LegalConcept)`
- `(:Article)-[:REFERENCES]->(:Article)`
