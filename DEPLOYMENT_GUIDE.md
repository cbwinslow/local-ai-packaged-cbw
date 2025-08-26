# Local AI Packaged - Deployment Guide

## Overview

This repository provides a comprehensive local AI stack with services including n8n, Flowise, Open WebUI, Supabase, and more. The stack supports both local development and server deployment with automated secret management and service orchestration.

## Quick Start

### One-Click Deployment

For the fastest setup, use the one-click deployment script:

```bash
# Local development deployment
./scripts/oneclick_deploy.sh --mode local --domain localhost --proxy traefik

# Server deployment  
./scripts/oneclick_deploy.sh --mode server --domain yourdomain.com --email admin@yourdomain.com --proxy traefik
```

### Manual Setup

1. **Environment Setup**
   ```bash
   # Generate secure environment configuration
   python3 scripts/fix_env.py
   
   # Or start services with auto-setup
   python3 start_services.py --preflight
   ```

2. **Start Services**
   ```bash
   # With Traefik reverse proxy
   docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml up -d
   
   # Without reverse proxy (direct port access)
   docker compose -f docker-compose.all-in-one.yml up -d
   ```

## Architecture

### Core Components

- **Supabase Stack**: Database, Auth, Storage, Edge Functions, Realtime
- **AI Tools**: n8n, Flowise, Open WebUI
- **Data Storage**: PostgreSQL, Qdrant, Neo4j, Redis
- **Search**: SearXNG
- **Analytics**: Langfuse
- **Reverse Proxy**: Traefik (recommended) or direct access

### Network Architecture

```
Internet
    ↓
Traefik (443/80)
    ↓
┌─────────────────────────────────────────┐
│              Services                    │
├─────────────────────────────────────────┤
│ Portal (8085)     │ n8n (5678)         │
│ Flowise (3001)    │ Open WebUI (8080)  │
│ Supabase (8000)   │ Langfuse (3000)    │
│ SearXNG (8080)    │ Neo4j (7474)       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│            Data Layer                    │
├─────────────────────────────────────────┤
│ PostgreSQL (5432) │ Redis (6379)       │
│ Qdrant (6333)     │ MinIO (9000)       │
└─────────────────────────────────────────┘
```

## Service Access

### Local Development (localhost)

Add to `/etc/hosts`:
```
127.0.0.1 portal.localhost n8n.localhost flowise.localhost webui.localhost
127.0.0.1 supabase.localhost studio.localhost functions.localhost realtime.localhost
127.0.0.1 traefik.localhost searxng.localhost langfuse.localhost neo4j.localhost
```

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Portal | https://portal.localhost | Main dashboard |
| n8n | https://n8n.localhost | Workflow automation |
| Flowise | https://flowise.localhost | LLM workflow builder |
| Open WebUI | https://webui.localhost | AI chat interface |
| Supabase | https://supabase.localhost | Backend services |
| Studio | https://studio.localhost | Supabase admin |
| Functions | https://functions.localhost | Edge functions |
| SearXNG | https://searxng.localhost | Privacy-focused search |
| Langfuse | https://langfuse.localhost | LLM analytics |
| Traefik | https://traefik.localhost | Proxy dashboard |

## Environment Configuration

### Required Variables

The deployment automatically generates secure values for:

- `BASE_DOMAIN` - Base domain for services
- `POSTGRES_PASSWORD` - Database password
- `JWT_SECRET` - Supabase JWT secret
- `ANON_KEY` / `SERVICE_ROLE_KEY` - Supabase API keys
- `CLOUDFLARE_API_TOKEN` - For DNS challenges (server mode)

### Secret Management

- Environment files are automatically secured with 600 permissions
- Automatic backup of existing `.env` files with timestamps
- Secure random generation using Python `secrets` module
- Different secret lengths for different purposes (24-48 characters)

## Deployment Modes

### Local Mode
- Uses `localhost` domain
- Self-signed certificates or HTTP
- Suitable for development and testing
- No external DNS requirements

### Server Mode
- Uses real domain name
- Automatic HTTPS with Let's Encrypt
- Cloudflare DNS challenge for certificates
- Production-ready configuration

## Testing

### Quick Test Suite
```bash
# Run all configuration tests
./scripts/tests/run_comprehensive_tests.sh --quick

# Run full test suite (includes service tests)
./scripts/tests/run_comprehensive_tests.sh

# Run original test suite
cd scripts/tests && bash run_all.sh
```

### Individual Tests
```bash
# Environment validation
bash scripts/tests/00_env_check.sh

# Docker Compose validation  
bash scripts/tests/01_compose_config.sh

# Service-specific tests (requires running stack)
bash scripts/tests/02_pgvector_check.sh
bash scripts/tests/03_storage_smoke.sh
bash scripts/tests/04_function_invoke.sh
python3 scripts/tests/05_realtime_ws_test.py
python3 scripts/tests/06_realtime_postgres_notify.py
```

## Troubleshooting

### Common Issues

1. **Environment Variables Missing**
   ```bash
   # Regenerate environment
   python3 scripts/fix_env.py
   ```

2. **Supabase Not Starting**
   ```bash
   # Check Supabase setup
   ls -la supabase/docker/
   
   # Reinitialize if empty
   rm -rf supabase && python3 start_services.py --preflight
   ```

3. **Service Communication Issues**
   ```bash
   # Check container status
   docker compose ps
   
   # View logs
   docker compose logs [service-name]
   
   # Test network connectivity
   docker exec -it [container] ping [other-service]
   ```

4. **Traefik Certificate Issues**
   ```bash
   # Check Traefik logs
   docker compose logs traefik
   
   # Verify DNS configuration
   dig yourdomain.com
   
   # Check Cloudflare API token
   curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
   ```

### Log Locations

- Application logs: `docker compose logs [service]`
- Traefik access logs: `docker compose logs traefik`
- Database logs: `docker compose logs supabase-db`
- Environment backups: `.env.*.bak`

### Health Checks

```bash
# Check all service status
docker compose ps

# Test service endpoints
curl -k https://portal.localhost
curl -k https://supabase.localhost/health

# Monitor resource usage
docker stats
```

## Advanced Configuration

### Custom Domain Setup

1. Update environment:
   ```bash
   ./scripts/oneclick_deploy.sh --domain yourdomain.com --email admin@yourdomain.com
   ```

2. Configure DNS (Cloudflare):
   ```bash
   # A records for each service
   portal.yourdomain.com -> YOUR_SERVER_IP
   n8n.yourdomain.com -> YOUR_SERVER_IP
   # ... etc
   ```

### Security Hardening

1. **Environment Security**
   - Ensure `.env` has 600 permissions
   - Use strong passwords for all services
   - Regularly rotate secrets

2. **Network Security**
   - Configure firewall (ports 80, 443 only)
   - Use VPN for internal service access
   - Enable Traefik security headers

3. **Backup Strategy**
   - Database: `docker exec supabase-db pg_dump ...`
   - Volumes: `docker run --rm -v volume_name:/data alpine tar czf /backup.tar.gz /data`
   - Environment: Automatic `.env.*.bak` files

## Development

### Adding New Services

1. **Traefik Integration**
   ```yaml
   labels:
     - traefik.enable=true
     - traefik.http.routers.myservice.rule=Host(`myservice.${BASE_DOMAIN}`)
     - traefik.http.routers.myservice.entrypoints=websecure
     - traefik.http.routers.myservice.tls.certresolver=cf
     - traefik.http.services.myservice.loadbalancer.server.port=PORT
   ```

2. **Environment Variables**
   - Add to `scripts/fix_env.py` REQUIRED_VARS
   - Generate hostname: `MYSERVICE_HOSTNAME=myservice.${BASE_DOMAIN}`

3. **Testing**
   - Add test to `scripts/tests/run_comprehensive_tests.sh`
   - Create service-specific test script

### Contributing

1. Fork the repository
2. Create feature branch
3. Run test suite: `./scripts/tests/run_comprehensive_tests.sh`
4. Submit pull request

## Support

- Check existing issues in the repository
- Run diagnostic tests: `./scripts/tests/run_comprehensive_tests.sh --verbose`
- Include logs and environment details when reporting issues
- Test with minimal configuration first