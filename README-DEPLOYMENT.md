## OpenDiscourse One-Click Deployment (Patch Bundle)

### Prereqs
- Ubuntu 22/24 host with public IP
- DNS on Cloudflare (optional automation)
- `.env` at repo root with at least:
```
DOMAIN=opendiscourse.net
LETSENCRYPT_EMAIL=you@example.com
SUPABASE_JWT_SECRET=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=supersecret
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=supersecret
FLOWISE_USERNAME=admin
FLOWISE_PASSWORD=supersecret
NEO4J_USER=neo4j
NEO4J_PASSWORD=supersecret
# Optional Cloudflare
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ZONE_ID=...
PUBLIC_IP=...
```

### Run
```bash
chmod +x cbw_oneclick_bootstrap.sh
sudo ./cbw_oneclick_bootstrap.sh --prepare --deploy --validate --dns
```

### Services added
- **Kong** in front of FastAPI at `https://api.${DOMAIN}`
- **FastAPI** with Supabase JWT verify (`/healthz`, `/v1/secure/ping`)
- **LocalAI** + **Qdrant** (RAG building blocks)
- **Neo4j**, **n8n**, **Flowise**, **OpenWebUI**
- **Grafana** + **Loki/Promtail**, optional **Graphite**
- **Traefik** TLS, security headers/basic auth middlewares
- **Cloudflare DNS sync** (`scripts/dns_sync_cloudflare.sh`)
- **Validation** (`scripts/validate_stack.sh`)

### Notes
- Supabase Auth/OAuth recommended for user flow; API validates tokens using `SUPABASE_JWT_SECRET`.
- Host hardening (optional):
```bash
sudo ./cbw_oneclick_bootstrap.sh --harden
```
