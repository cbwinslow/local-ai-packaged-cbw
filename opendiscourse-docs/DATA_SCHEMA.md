# Data Schema (Postgres + Neo4j)

## Postgres (tables)
- `documents(id, source_url, outlet, published_at, fetched_at, checksum, language)`
- `chunks(id, document_id, text, tokens, embedding vector)`
- `entities(id, type, canonical_name, aliases, confidence)`
- `claims(id, text, speaker_id, time, context, stance)`
- `statements(id, claim_id, quote, source_document_id, span_start, span_end)`
- `attributions(id, statement_id, source_url, outlet, journalist)`
- `metrics(id, entity_id, bias_score, accuracy_score, updated_at)`

## Neo4j (labels)
- `Person`, `Organization`, `Outlet`, `GovernmentBody`, `Claim`, `Statement`, `Topic`
- Relations: `(Entity)-[:MADE]->(Claim)`, `(Claim)-[:MENTIONED_IN]->(Document)`, `(Entity)-[:MEMBER_OF]->(Org)`

Keep IDs stable across stores and record `provenance_id` on every write.
