#!/usr/bin/env python3
"""
Generate architecture diagrams for the local AI stack
Creates ASCII and mermaid diagrams showing system architecture
"""

def generate_ascii_architecture():
    """Generate ASCII architecture diagram"""
    diagram = """
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
"""
    return diagram

def generate_mermaid_diagram():
    """Generate Mermaid diagram for web rendering"""
    diagram = """
# Mermaid Architecture Diagrams

## Overall System Architecture

```mermaid
graph TB
    Internet([Internet]) --> Traefik[Traefik Proxy<br/>:80/:443]
    
    Traefik --> Portal[Portal<br/>:8085]
    Traefik --> N8N[n8n<br/>:5678]
    Traefik --> Flowise[Flowise<br/>:3001]
    Traefik --> WebUI[Open WebUI<br/>:8080]
    Traefik --> Supabase[Supabase<br/>:8000]
    Traefik --> Studio[Studio<br/>:3000]
    Traefik --> Functions[Functions<br/>:54321]
    Traefik --> Realtime[Realtime<br/>:4000]
    Traefik --> SearXNG[SearXNG<br/>:8080]
    Traefik --> Langfuse[Langfuse<br/>:3000]
    Traefik --> Neo4j[Neo4j<br/>:7474]
    
    Portal --> PostgreSQL[(PostgreSQL<br/>:5432)]
    N8N --> PostgreSQL
    Supabase --> PostgreSQL
    Studio --> PostgreSQL
    Langfuse --> PostgreSQL
    
    Flowise --> Qdrant[(Qdrant<br/>:6333)]
    WebUI --> Qdrant
    
    N8N --> Redis[(Redis<br/>:6379)]
    Realtime --> Redis
    
    Langfuse --> ClickHouse[(ClickHouse<br/>:8123)]
    Langfuse --> MinIO[(MinIO<br/>:9000)]
    
    Functions --> Storage[Docker Volumes]
    PostgreSQL --> Storage
    Qdrant --> Storage
    Neo4j --> Storage
```

## Service Dependencies

```mermaid
graph LR
    subgraph "Frontend Services"
        Portal
        WebUI[Open WebUI]
        Studio
    end
    
    subgraph "API Services"
        Supabase
        Functions[Edge Functions]
        Realtime
        N8N
        Flowise
    end
    
    subgraph "Data Services"
        PostgreSQL
        Redis
        Qdrant
        Neo4j
        ClickHouse
        MinIO
    end
    
    subgraph "Infrastructure"
        Traefik
        SearXNG
        Langfuse
    end
    
    Portal --> Supabase
    WebUI --> Supabase
    WebUI --> Flowise
    Studio --> Supabase
    
    Supabase --> PostgreSQL
    Functions --> PostgreSQL
    Realtime --> PostgreSQL
    Realtime --> Redis
    N8N --> PostgreSQL
    Flowise --> Qdrant
    
    Langfuse --> PostgreSQL
    Langfuse --> ClickHouse
    Langfuse --> MinIO
    
    Traefik --> Portal
    Traefik --> WebUI
    Traefik --> Studio
    Traefik --> Supabase
    Traefik --> Functions
    Traefik --> Realtime
    Traefik --> N8N
    Traefik --> Flowise
    Traefik --> SearXNG
    Traefik --> Langfuse
    Traefik --> Neo4j
```

## Deployment Flow

```mermaid
flowchart TD
    Start([Start Deployment]) --> CheckReqs{Check Requirements}
    CheckReqs -->|Docker Missing| InstallDocker[Install Docker]
    CheckReqs -->|Python Missing| InstallPython[Install Python]
    CheckReqs -->|Ready| InitEnv[Initialize Environment]
    
    InstallDocker --> CheckReqs
    InstallPython --> CheckReqs
    
    InitEnv --> GenSecrets[Generate Secrets]
    GenSecrets --> SetupSupabase[Setup Supabase]
    SetupSupabase --> ValidateConfig[Validate Configurations]
    
    ValidateConfig -->|Invalid| FixConfig[Fix Configuration]
    FixConfig --> ValidateConfig
    ValidateConfig -->|Valid| StartServices[Start Services]
    
    StartServices --> HealthCheck{Health Check}
    HealthCheck -->|Unhealthy| CheckLogs[Check Logs]
    CheckLogs --> FixIssues[Fix Issues]
    FixIssues --> StartServices
    
    HealthCheck -->|Healthy| RunTests[Run Tests]
    RunTests -->|Pass| Success([Deployment Complete])
    RunTests -->|Fail| CheckLogs
```
"""
    return diagram

def generate_network_diagram():
    """Generate network architecture diagram"""
    diagram = """
# Network Architecture

## Local Development Network

```
┌─────────────────────────────────────────────┐
│                 Host System                 │
│  ┌─────────────────────────────────────────┐│
│  │           Docker Engine             ││
│  │  ┌─────────────────────────────────┐ ││
│  │  │        Docker Networks          │ ││
│  │  │                                 │ ││
│  │  │  ┌─────────┐    ┌─────────┐    │ ││
│  │  │  │ backend │    │ public  │    │ ││
│  │  │  │ network │    │ network │    │ ││
│  │  │  └─────────┘    └─────────┘    │ ││
│  │  └─────────────────────────────────┘ ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
             │                    │
    ┌────────┴────────┐  ┌────────┴────────┐
    │   Host :80/443  │  │  Host :various  │
    │   (Traefik)     │  │ (Direct Access) │
    └─────────────────┘  └─────────────────┘
```

## Server Deployment Network

```
Internet
    │
┌───▼────┐      ┌─────────────┐      ┌──────────────┐
│   CDN  │ ──── │  Firewall   │ ──── │    Server    │
│ (opt.) │      │  :80, :443  │      │ :80/:443     │
└────────┘      └─────────────┘      └──────────────┘
                                            │
                                    ┌───────▼──────┐
                                    │   Traefik    │
                                    │   Proxy      │
                                    └───────┬──────┘
                                            │
                            ┌───────────────▼───────────────┐
                            │        Docker Networks        │
                            │                               │
                            │  Services ←→ Data Storage     │
                            │                               │
                            └───────────────────────────────┘
```

## Security Zones

```
┌─────────────────────────────────────────────────────────┐
│                     Public Zone                        │
│  • Traefik Dashboard (auth required)                  │
│  • Application Frontends                              │
│  • API Endpoints (with auth)                          │
└─────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────┐
│                   Application Zone                     │
│  • Service-to-service communication                   │
│  • Internal APIs                                      │
│  • Business logic                                     │
└─────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────┐
│                     Data Zone                          │
│  • Databases (no external access)                     │
│  • Message queues                                     │
│  • File storage                                       │
└─────────────────────────────────────────────────────────┘
```
"""
    return diagram

def main():
    """Generate all diagrams"""
    
    # Create diagrams directory if it doesn't exist
    import os
    os.makedirs('diagrams', exist_ok=True)
    
    # Generate ASCII architecture
    with open('diagrams/ARCHITECTURE.md', 'w') as f:
        f.write(generate_ascii_architecture())
    
    # Generate Mermaid diagrams
    with open('diagrams/MERMAID_DIAGRAMS.md', 'w') as f:
        f.write(generate_mermaid_diagram())
    
    # Generate network diagrams
    with open('diagrams/NETWORK_ARCHITECTURE.md', 'w') as f:
        f.write(generate_network_diagram())
    
    print("✅ Generated architecture diagrams:")
    print("   📁 diagrams/ARCHITECTURE.md")
    print("   📁 diagrams/MERMAID_DIAGRAMS.md") 
    print("   📁 diagrams/NETWORK_ARCHITECTURE.md")

if __name__ == '__main__':
    main()