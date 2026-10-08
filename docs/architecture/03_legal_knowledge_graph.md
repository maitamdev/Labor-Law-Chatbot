# Legal Knowledge Graph Schema

The VietLabor AI Knowledge Graph represents explicit relationships between Vietnamese labor statutes, articles, clauses, and administrative sanctions.

## Node Types
- `Statute`: e.g., Bộ luật Lao động 2019, Nghị định 145/2020/NĐ-CP
- `Article`: Individual provisions (Điều 21, Điều 35, Điều 107)
- `LegalIssue`: Categorized disputes (Tiền lương, Kỷ luật sa thải, Thử việc)
- `Sanction`: Penalties defined in Nghị định 12/2022/NĐ-CP

## Edge Relationships
- `(Statute)-[:CONTAINS]->(Article)`
- `(Article)-[:ELABORATED_BY]->(Article)`
- `(Article)-[:SANCTIONED_BY]->(Sanction)`
- `(Article)-[:ADDRESSES]->(LegalIssue)`
