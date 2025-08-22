# Reverse Proxy Options (Lean First)

Start minimal. Do NOT enable hardening (security headers, rate limits, DNS plugins) until the stack is confirmed healthy externally. This file focuses on lean startup; hardening becomes a final deployment step.


## Lean-Oriented Files

- `docker-compose.override.proxies.yml` – Adds proxy services with profiles (original compose untouched).
- `caddy-addon/Caddyfile.lean` – Minimal Caddy (raw reverse proxy only).
- `traefik/traefik.yml` – Base Traefik (ACME settings can be left as-is or trimmed; still works lean).
- `traefik/dynamic/middlewares.lean.yml` – Empty dynamic config (no middlewares).
- `quickstart_proxy.sh` – Selects proxy profile (`caddy_ext` or `traefik`). Use it even in lean mode.
- `.env.proxy.example` – Example domain variables (merge, do not overwrite existing secrets).

HARDENING FILES (IGNORE FOR NOW):

- `caddy-addon/Caddyfile.ext`
- `traefik/dynamic/middlewares.yml`
- `caddy-addon/Dockerfile.xcaddy` (plugins only needed when hardening stage begins)

 
## Domain & Hostnames
All hostnames default to `<service>.<BASE_DOMAIN>`. Set `BASE_DOMAIN` in `.env`:

```bash
BASE_DOMAIN=opendiscourse.net
```
Override any individual service via explicit `*_HOSTNAME` if required.

 
## Lean Caddy Start

```bash
BASE_DOMAIN=opendiscourse.net REVERSE_PROXY=caddy_ext ./quickstart_proxy.sh
```
Portal (after DNS): `http://portal.${BASE_DOMAIN}` (TLS comes later if desired).

 
## Lean Traefik Start

```bash
BASE_DOMAIN=opendiscourse.net REVERSE_PROXY=traefik ./quickstart_proxy.sh
```
(You can postpone Cloudflare token & ACME email; Traefik will still route HTTP.)

 
## Validation Checklist (Complete BEFORE Hardening)

1. All service hostnames resolve externally.
1. Supabase core endpoints respond (auth, rest, realtime where applicable).
1. Websocket / streaming features function (no unexpected disconnects).
1. Portal lists reachable links without error.
1. No recurring 4xx/5xx from proxy when browsing or using APIs.

Only when ALL pass should you move to the hardening phase.

 
## Adding a New Service (Lean)

 
### Caddy (lean)

1. Pick hostname: `SERVICE_HOSTNAME=myservice.${BASE_DOMAIN}`.
1. Add to `caddy-addon/Caddyfile.lean`:

```caddyfile
{env.SERVICE_HOSTNAME} {
  reverse_proxy myservice-container:PORT
}
```

1. Reload:

```bash
docker compose up -d caddy_ext
```

 
### Traefik (lean)

Add labels (in an override or directly) to the service:

```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.myservice.rule=Host(`myservice.${BASE_DOMAIN}`)
  - traefik.http.services.myservice.loadbalancer.server.port=PORT
```

Recreate service:

```bash
docker compose up -d myservice traefik
```

 
## Switching Proxies (Lean)
Run only one proxy profile at a time:
```bash
docker compose -f docker-compose.yml -f docker-compose.override.proxies.yml \
  --profile cpu --profile public --profile caddy_ext up -d --remove-orphans

# Or Traefik

docker compose -f docker-compose.yml -f docker-compose.override.proxies.yml \
  --profile cpu --profile public --profile traefik up -d --remove-orphans
```

 
## Hardening Phase (DEFERRED)
After validation, reintroduce:
- Security headers (swap to `Caddyfile.ext` or Traefik middlewares file).
- Rate limiting (Caddy plugin or Traefik rate-limit middleware).
- DNS-01 ACME (Cloudflare token) for wildcard certs.
- Forward auth / OIDC, CSP tightening, logging enrichment.

 
## Rollback Simplicity
Delete / ignore override compose + proxy files to revert. No core file modifications were made.

---
Lean-first mode reduces moving parts; stability comes before security polish.
