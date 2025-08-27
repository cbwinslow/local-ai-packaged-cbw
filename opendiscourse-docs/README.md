# OpenDiscourse — Media Intelligence, RAG & Civic Accountability

OpenDiscourse is a modular, auditable platform that ingests news media, social media, and government documents; extracts entities/claims; builds a knowledge graph; performs fact-checking and bias analysis; and serves objective insights via APIs and dashboards.

> **Design goals:** transparency, reproducibility, and safety-by-default. All pipelines are testable; every inference is attributed to sources; and model prompts/configuration live in-repo.

## Quick Start (Dev, Docker Compose)

1. **Clone + copy docs**  
   Drop this folder's contents into the repo root. Keep the `.github/` files.
2. **Create env**  
   Copy `.env.example` to `.env` and fill values.
3. **Start services**  
   ```bash
   docker compose -f docker-compose.example.yml up -d
   ```
4. **Open stack**  
   - API (FastAPI): http://localhost:8000/docs  
   - Admin (Next.js): http://localhost:3000  
   - Postgres: localhost:5432 (pgvector enabled)  
   - Neo4j: http://localhost:7474 (Bolt 7687)
   - LiteLLM proxy: http://localhost:4000/v1

See **DEPLOYMENT.md** for Proxmox, Cloudflare Tunnel, GPU notes, and production patterns.

## Core Features
- Multi-source ingestion: RSS/Atom, site scrapers, X/Twitter firehose, and government portals
- NER/EL, relation extraction, claim detection, stance & sentiment, bias estimation
- RAG (document + graph): Postgres + pgvector + Neo4j
- Fact-check pipeline with transparent source citations
- Agentic orchestration with task queues and scheduled jobs
- Dashboards for outlet, journalist, and politician profiles

## Recommended Stack
- **Frontend:** Next.js (App Router) + Tailwind + shadcn/ui
- **API:** FastAPI (Python 3.11+)
- **Workers:** Celery (Redis broker) or Dramatiq (Redis)
- **DB:** PostgreSQL 15+ with **pgvector**
- **Search:** OpenSearch/Elasticsearch (optional, recommended for scale)
- **Graph:** Neo4j 5.x
- **LLM access:** LiteLLM gateway (unified keys for OpenAI, Gemini, Qwen, Mistral, Llama, etc.)
- **Embeddings:** text-embedding-3-large (or open-source alternative) via LiteLLM
- **Orchestration:** Docker Compose for dev, Kubernetes or Coolify for prod
- **Infra:** Cloudflare (DNS, Tunnel), NGINX (optional) or direct Coolify ingress

See **ARCHITECTURE.md** and **AGENTS.md** for details and Mermaid diagrams.
