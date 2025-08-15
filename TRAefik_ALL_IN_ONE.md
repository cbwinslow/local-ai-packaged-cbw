# Traefik All-in-One Stack Usage

This document explains how to run the hardened Traefik variant of the all-in-one stack while keeping Supabase's Kong gateway internal (but proxied externally by Traefik).

## Files Introduced

- `docker-compose.all-in-one.yml` (base consolidated services)
- `docker-compose.all-in-one.traefik.yml` (Traefik + routing labels)
- `.env.all-in-one.example` (template of required env vars)
- `scripts/gen_all_in_one_env.py` (auto-generates a filled `.env` with strong random secrets)

## Generate Environment

```bash
python scripts/gen_all_in_one_env.py  # creates .env (backs up existing .env if present)
```
Edit `.env` to adjust `BASE_DOMAIN`, `ACME_EMAIL`, and any hostnames.

## Start Stack (Traefik variant)

```bash
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml up -d
```

Traefik will obtain certificates via Cloudflare DNS challenge. Ensure:

- `CLOUDFLARE_API_TOKEN` has DNS edit rights for the zone of `BASE_DOMAIN`.
- Port 80/443 reachable from the internet.

## Access URLs

Subdomains derive from environment (override in `.env`):

- Portal: `https://portal.${BASE_DOMAIN}`
- n8n: `https://n8n.${BASE_DOMAIN}`
- Flowise: `https://flowise.${BASE_DOMAIN}`
- Open WebUI: `https://webui.${BASE_DOMAIN}`
- Supabase API (Kong): `https://supabase.${BASE_DOMAIN}`
- Langfuse: `https://langfuse.${BASE_DOMAIN}`
- SearXNG: `https://searxng.${BASE_DOMAIN}`
- Ollama API: `https://ollama.${BASE_DOMAIN}`
- Neo4j Browser: `https://neo4j.${BASE_DOMAIN}`
- Traefik Dashboard: `https://traefik.${BASE_DOMAIN}`

## Hardened Middlewares

Applied to all routers:

- `security-headers@file` – HSTS, frame deny, referrer policy, COOP/COEP/CORP.
- `rate-limit@file` – Average 100 req/s, burst 50.
Adjust by editing `traefik/dynamic/middlewares.yml`.

## Optional GPU Profile

Bring up GPU Ollama instead of CPU (compose first brings base services):

```bash
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml --profile gpu-nvidia up -d ollama-gpu
```

(Ensure NVIDIA runtime present.)

## Regenerate Secrets

If you need to rotate secrets:

```bash
python scripts/gen_all_in_one_env.py .env.new
mv .env .env.old
mv .env.new .env
# Then restart:
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml up -d --force-recreate
```

## Notes

- Supabase roles are simplified (single Postgres superuser). Harden later by creating distinct DB roles and updating service env vars.
- Only Traefik publishes ports. Base compose `caddy` can be omitted when using Traefik (do not include its ports simultaneously).
- To remove a public route, delete or disable the service labels in the Traefik compose file.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| 404 on subdomain | Confirm label Host() matches env var and DNS record exists (wildcard acceptable). |
| Cert not issued | Cloudflare token scope & DNS propagation. |
| 502 Bad Gateway | Target container healthy? Correct `loadbalancer.server.port`? |
| Rate limited unexpectedly | Adjust `average` / `burst` in `middlewares.yml`. |

## Removal

```bash
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml down
```

Add `-v` to remove volumes if you want a clean slate.
