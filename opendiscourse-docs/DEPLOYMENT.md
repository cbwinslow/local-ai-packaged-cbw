# Deployment

## Dev (Docker Compose)
Use `docker-compose.example.yml` and `.env`. Edit services as needed.

## Proxmox VM / Bare Metal
- Provision Ubuntu/Debian VM with Docker + Compose.
- Expose ports 3000, 8000, 4000, 5432, 7474/7687 (or tunnel).
- Persist volumes for Postgres/Neo4j. Configure backups.

## Cloudflare Tunnel
- Map public subdomains (e.g., `api.opendiscourse.net`) to local services.
- Enforce Zero Trust policies and IP allowlists for admin endpoints.

## GPU & Local Models
- Use **Ollama** or **vLLM**; route via LiteLLM.
- For NVIDIA, ensure `--gpus all` and images include CUDA; for AMD, prefer ROCm builds.
