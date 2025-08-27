# Architecture

```mermaid
flowchart LR
  subgraph Ingestion
    A[RSS/Feeds] --> C[NewsIngestor]
    B[Social APIs] --> C
    G[Gov Portals] --> C
  end
  C --> D[Extractor/NLP Annotator]
  D --> E[(Postgres + pgvector)]
  D --> F[(Neo4j)]
  E <--> H[Indexer/Search]
  F <--> I[Graph RAG]
  subgraph Serving
    J[FastAPI] --> K[Next.js UI]
    J --> L[Exports/Webhooks]
  end
  E --> J
  F --> J
  J --> M[LiteLLM Gateway]
```

## C4 Context (Simplified)

```mermaid
graph TD
  user[Analyst/Admin] --> web[Next.js Admin]
  web --> api[FastAPI API]
  api --> db[(Postgres)]
  api --> graph[(Neo4j)]
  api --> llm[LiteLLM]
  workers[Agents/Workers] --> db
  workers --> graph
  workers --> llm
```

See **DATA_SCHEMA.md**, **RAG_PIPELINE.md**, **NEWS_INGESTION.md**, **GOVDOC_CRAWLER.md**.
