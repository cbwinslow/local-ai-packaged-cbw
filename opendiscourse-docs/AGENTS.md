# Agents Playbook

OpenDiscourse uses a small team of specialized agents orchestrated by a queue (Redis) and a scheduler (APScheduler / Beat).

## Catalog

- **NewsIngestor**: Pulls feeds, scrapes full text, deduplicates, normalizes.
- **SocialCrawler**: Pulls posts from X/Twitter and other platforms (via official APIs when possible). Does rate-safe enrichment.
- **GovDocCrawler**: Targets government portals, bulk datasets, and document repositories. Extracts metadata and sanitizes PDFs.
- **NLPAnnotator**: Runs NER/EL, coref, relation extraction, claim detection.
- **FactChecker**: Retrieves corroborating sources, checks consistency, assigns confidence with rationale and citations.
- **GraphBuilder**: Writes entities/claims/relations to Neo4j with versioned provenance.
- **Indexer**: Writes chunks to Postgres (pgvector) + OpenSearch (optional).
- **BiasScorer**: Outlet/journalist/politician bias & accuracy metrics over time (transparent formulas).
- **AlertAgent**: Notifies on new claims, contradictions, or threshold crossings.
- **QAAgent**: Regression tests, data-quality checks, prompt drift detection.

## Agent Message Contract (YAML)

```yaml
agent: FactChecker
input:
  claim_id: "uuid"
  claim_text: "statement under evaluation"
  context_ids: ["doc-uuid-1", "doc-uuid-2"]
  max_tokens: 2048
output:
  verdict: "true|false|unverifiable|mixed"
  confidence: 0.0-1.0
  evidence:
    - source_id: "src-uuid"
      quote: "..."
      url: "https://..."
  rationale: "short explanation"
  updates:
    - graph_upserts: []
    - corrections: []
```

## Orchestration Notes
- All agents communicate via durable queues. Retries with backoff.
- Every output references input IDs for traceability.
- Prompts live in `prompts/` with versioned snapshots and tests.
