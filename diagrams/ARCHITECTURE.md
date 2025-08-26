
# Local AI Packaged - System Architecture

```
                                    Internet
                                       |
                                   [Router/Firewall]
                                       |
                              ┌────────────────────┐
                              │   Traefik Proxy    │
                              │   (Port 80/443)    │
                              └────────────────────┘
                                       |
    ┌─────────────────────────────────────────────────────────────────┐
    │                        Service Layer                            │
    ├─────────────────────────────────────────────────────────────────┤
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
    │  │   Portal    │  │     n8n     │  │   Flowise   │  │ Open     │ │
    │  │   :8085     │  │   :5678     │  │   :3001     │  │ WebUI    │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  │ :8080    │ │
    │                                                      └──────────┘ │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
    │  │  Supabase   │  │   Studio    │  │ Functions   │  │ Realtime │ │
    │  │   :8000     │  │   :3000     │  │   :54321    │  │  :4000   │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
    │                                                                  │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
    │  │  SearXNG    │  │  Langfuse   │  │    Neo4j    │  │ Grafana  │ │
    │  │   :8080     │  │   :3000     │  │   :7474     │  │  :3000   │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
    └─────────────────────────────────────────────────────────────────┘
                                       |
    ┌─────────────────────────────────────────────────────────────────┐
    │                        Data Layer                               │
    ├─────────────────────────────────────────────────────────────────┤
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
    │  │ PostgreSQL  │  │    Redis    │  │   Qdrant    │  │  MinIO   │ │
    │  │   :5432     │  │   :6379     │  │   :6333     │  │  :9000   │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
    │                                                                  │
    │  ┌─────────────┐  ┌─────────────┐                                │
    │  │ ClickHouse  │  │   Caddy     │                                │
    │  │   :8123     │  │   :80/443   │                                │
    │  └─────────────┘  └─────────────┘                                │
    └─────────────────────────────────────────────────────────────────┘
                                       |
    ┌─────────────────────────────────────────────────────────────────┐
    │                     Storage Layer                               │
    ├─────────────────────────────────────────────────────────────────┤
    │  Docker Volumes:                                                │
    │  • langfuse_postgres_data  • supabase_db_data                   │
    │  • qdrant_storage          • neo4j_data                         │
    │  • n8n_storage             • flowise_data                       │
    │  • ollama_storage          • traefik_certificates               │
    └─────────────────────────────────────────────────────────────────┘
```

## Service Communication Flow

```
User Request → Traefik → Service Discovery → Service Container → Database/Storage
     ↑                                                ↓
DNS Resolution                                 Internal Network
```

## Data Flow Examples

### n8n Workflow Execution
```
n8n → PostgreSQL (workflow storage)
    → Supabase API (data operations) 
    → External APIs (integrations)
    → Flowise (AI workflows)
```

### AI Chat Flow
```
Open WebUI → Ollama (LLM inference)
          → Qdrant (vector storage)
          → Langfuse (analytics)
          → Supabase (user data)
```

### Real-time Updates
```
Client → Supabase Realtime → PostgreSQL (LISTEN/NOTIFY)
      → WebSocket connections → Live UI updates
```
