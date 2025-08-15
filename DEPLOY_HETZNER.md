# Deployment: Hetzner (opendiscourse.net)

This guide walks you through deploying the all-in-one stack (including full Supabase services) onto a fresh Hetzner VPS.

## 1. Prerequisites

- A Hetzner Cloud server (Ubuntu 22.04+ recommended) with public IP
- Your SSH key added to the server (use `hcloud` or web console)
- Domain `opendiscourse.net` (or your own) pointed:
  - A record: `@ -> <server IP>`
  - Wildcard (optional for many subdomains): `* -> <server IP>`
- Cloudflare (optional) if using Traefik DNS challenge with `CLOUDFLARE_API_TOKEN`

## 2. Initial Server Prep

SSH in:

```bash
ssh root@<server-ip>
```

(Optional) Create a non-root user:

```bash
adduser deploy
usermod -aG sudo deploy
rsync -a ~/.ssh/ /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
```

## 3. Run Automated Deployment Script

From root (or sudo user):

```bash
curl -fsSL https://raw.githubusercontent.com/coleam00/local-ai-packaged/stable/scripts/deploy_hetzner.sh -o deploy.sh
bash deploy.sh opendiscourse.net
```

This will:

1. Install Docker & compose plugin
2. Clone the repository into `/opt/local-ai-packaged`
3. Generate `.env` if absent (based on `.env.production.example`)
4. Create & enable systemd service `local-ai-packaged.service`
5. Open firewall ports 22, 80, 443

## 4. Configure Environment

Edit `/opt/local-ai-packaged/.env`:

```bash
nano /opt/local-ai-packaged/.env
```

Set:

- `BASE_DOMAIN=opendiscourse.net`
- `CLOUDFLARE_API_TOKEN=<token>` (if using Traefik DNS challenge)
- Optional overrides for hostnames (already derived automatically)

Regenerate secrets only if needed:

```bash
cd /opt/local-ai-packaged
python3 scripts/gen_all_in_one_env.py
```

(Backups are created automatically.)

## 5. Start / Restart Stack

Systemd managed:

```bash
systemctl restart local-ai-packaged.service
journalctl -u local-ai-packaged -f
```

Manual (alternative):

```bash
cd /opt/local-ai-packaged
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml up -d --remove-orphans
```

## 6. Verify Services

After a minute, visit (replace domain if different):

- Portal: `https://portal.opendiscourse.net`
- n8n: `https://n8n.opendiscourse.net`
- Flowise: `https://flowise.opendiscourse.net`
- Open WebUI: `https://webui.opendiscourse.net`
- Supabase API (Kong): `https://api.opendiscourse.net`
- Supabase Studio: `https://studio.opendiscourse.net`
- Langfuse: `https://lang.opendiscourse.net`
- Neo4j (browser): `https://graph.opendiscourse.net` (if reverse proxy rule added)
- Traefik dashboard (protect / restrict in production): `https://infra.opendiscourse.net`

docker ps --format 'table {{.Names}}\t{{.Status}}'
Check containers:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

## 7. GPU Enablement (Optional)
If you provision a GPU instance and want Ollama GPU:

```bash
docker compose --profile gpu-nvidia up -d ollama-gpu
```

Or update systemd unit `Environment=COMPOSE_PROFILES=gpu-nvidia` then reload daemon & restart service.

## 8. Updating

## 8. Updating
git pull --ff-only
```bash
cd /opt/local-ai-packaged
git pull --ff-only
systemctl restart local-ai-packaged.service
```

## 9. Logs & Troubleshooting

## 9. Logs & Troubleshooting
- Application logs: `docker logs container_name`
- All: `journalctl -u local-ai-packaged -f`
- Compose config validation: `docker compose config` (should output merged YAML)

ACME/Certificate issues:

- Ensure DNS A (and wildcard) propagate.
- Check Traefik logs: `docker logs traefik`

Supabase migrations not applied:

- Remove only its DB volume (NOT global Postgres) if re-init needed:

```bash
docker compose rm -s -f supabase-db
rm -rf supabase/docker/volumes/db/data
systemctl restart local-ai-packaged.service
```

## 10. Security Hardening Next Steps (Recommended)

## 10. Security Hardening Next Steps (Recommended)
- Restrict Traefik dashboard behind Basic Auth or IP allow-list
- Add fail2ban or crowdsec
- Rotate secrets periodically (re-run generator, update .env, restart)
- Separate Postgres instances for analytics/langfuse vs operational
- Implement backup snapshots (pg_dump + object storage)

## 11. Rollback

## 11. Rollback
git checkout <previous-tag-or-commit>
If an update breaks:

```bash
journalctl -u local-ai-packaged -n 200 --no-pager
# Revert git
cd /opt/local-ai-packaged
git checkout previous_commit_hash
systemctl restart local-ai-packaged.service
```

## 12. Removal

## 12. Removal
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml down -v
```bash
systemctl disable --now local-ai-packaged.service
docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml down -v
rm -rf /opt/local-ai-packaged
```

---
Deployment complete. Proceed with creating users in Supabase Studio and configuring API keys for your applications.
