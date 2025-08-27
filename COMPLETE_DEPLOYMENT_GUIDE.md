# Local AI Package - Complete Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Python 3.8+ for management scripts
- At least 8GB RAM and 20GB free disk space
- Internet connection for image downloads

### One-Command Deployment
```bash
# Generate secure configuration
python scripts/enhanced_env_generator.py --base-domain localhost --environment local

# Start all services with Traefik (default)
python start_services.py --profile cpu

# Access the management portal
open http://localhost:8085
```

## 📋 Detailed Setup Instructions

### 1. Environment Configuration

#### Automatic Configuration (Recommended)
```bash
# Generate complete configuration with secure passwords
python scripts/enhanced_env_generator.py \
  --base-domain localhost \
  --email admin@localhost \
  --environment local

# For production deployment
python scripts/enhanced_env_generator.py \
  --base-domain yourdomain.com \
  --email admin@yourdomain.com \
  --environment production
```

#### Manual Configuration
Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
# Edit .env with your preferred editor
```

**Important Environment Variables:**
- `BASE_DOMAIN`: Your domain (localhost for local dev)
- `POSTGRES_PASSWORD`: PostgreSQL password (alphanumeric only)
- `JWT_SECRET`: JWT signing secret
- `ACME_EMAIL`: Email for SSL certificates

### 2. Service Deployment

#### Start All Services
```bash
# Default deployment with CPU-based AI
python start_services.py --profile cpu

# GPU-accelerated deployment (NVIDIA)
python start_services.py --profile gpu-nvidia

# AMD GPU deployment
python start_services.py --profile gpu-amd

# Public deployment (external access)
python start_services.py --environment public
```

#### Start Individual Components
```bash
# Only Supabase backend
python start_services.py --skip-neo4j

# With Next.js development server
python start_services.py --start-nextjs
```

### 3. Access Services

#### Local Development (localhost)
Add to `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):
```
127.0.0.1 n8n.localhost flowise.localhost webui.localhost
127.0.0.1 supabase.localhost studio.localhost portal.localhost
127.0.0.1 traefik.localhost searxng.localhost langfuse.localhost
127.0.0.1 neo4j.localhost
```

#### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Portal** | https://portal.localhost | Main management dashboard |
| **n8n** | https://n8n.localhost | Workflow automation |
| **Flowise** | https://flowise.localhost | LLM workflow builder |
| **Open WebUI** | https://webui.localhost | AI chat interface |
| **Supabase** | https://supabase.localhost | Backend API |
| **Studio** | https://studio.localhost | Supabase admin |
| **Langfuse** | https://langfuse.localhost | LLM analytics |
| **SearXNG** | https://searxng.localhost | Privacy search |
| **Neo4j** | https://neo4j.localhost | Graph database |
| **Traefik** | https://traefik.localhost | Proxy dashboard |

## 🔧 Configuration Management

### Web-Based Configuration
Access the enhanced portal at `http://localhost:8085` for:
- Environment variable management
- Secure password generation
- Deployment controls
- Health monitoring
- Real-time service status

### Command-Line Configuration
```bash
# Generate new secure passwords
python scripts/enhanced_env_generator.py --generate-only

# Validate configuration
python scripts/enhanced_env_generator.py --validate-only

# Backup configuration
cp .env ".env.backup.$(date +%Y%m%d)"
```

### Password Management
```bash
# Local secure storage
python scripts/password_manager.py --store service username password

# With Bitwarden integration
python scripts/password_manager.py --bitwarden --store service username password

# Generate and store all environment passwords
python scripts/password_manager.py --generate-env
```

## 🔒 Security Considerations

### Password Requirements
- **PostgreSQL passwords**: Alphanumeric only (compatibility)
- **JWT secrets**: Minimum 48 characters
- **Service passwords**: Minimum 24 characters with mixed case, numbers, symbols
- **API keys**: Minimum 32 characters

### Network Security
- All services use internal Docker networks
- Only Traefik exposes ports 80/443
- SSL/TLS certificates via Let's Encrypt
- Security headers applied by default
- Rate limiting enabled

### Access Control
- Basic authentication on admin interfaces
- JWT-based API authentication
- Database connection encryption
- Secret rotation capabilities

## 🚦 Health Monitoring

### Automated Health Checks
```bash
# Check all services
curl http://localhost:8085/api/health

# Individual service health
curl http://localhost:9999/health  # Supabase Auth
curl http://localhost:8000/rest/v1/  # Supabase REST
curl http://localhost:5678/healthz  # n8n
```

### Monitoring Dashboard
- **Portal Health Page**: Real-time service status
- **Traefik Dashboard**: Load balancer metrics
- **Grafana** (if enabled): System metrics
- **Container Logs**: `docker compose logs -f`

## 🛠️ Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check Docker status
sudo systemctl status docker

# Verify configuration
python start_services.py --preflight

# Check for port conflicts
netstat -tulpn | grep :80
netstat -tulpn | grep :443
```

#### SSL Certificate Issues
```bash
# Check Traefik logs
docker compose logs traefik

# Verify domain DNS resolution
nslookup yourdomain.com

# Manual certificate request
docker compose exec traefik acme --test
```

#### Database Connection Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Test database connection
docker compose exec postgres psql -U postgres

# Verify password in .env
grep POSTGRES_PASSWORD .env
```

#### Memory/Performance Issues
```bash
# Check resource usage
docker stats

# Limit container resources (docker-compose.yml)
deploy:
  resources:
    limits:
      memory: 1g
      cpus: '0.5'
```

### Recovery Procedures

#### Reset All Services
```bash
# Stop and remove all containers
docker compose down -v

# Clean up images (careful!)
docker system prune -a

# Restart fresh
python start_services.py --profile cpu
```

#### Restore Configuration
```bash
# Restore from backup
cp .env.backup.YYYYMMDD .env

# Regenerate if corrupted
python scripts/enhanced_env_generator.py --force
```

#### Database Recovery
```bash
# Backup current data
docker compose exec postgres pg_dump -U postgres > backup.sql

# Restore from backup
docker compose exec -T postgres psql -U postgres < backup.sql
```

## 🌐 Production Deployment

### DNS Configuration
For production deployment with custom domain:

1. **A Records** (point to your server IP):
   ```
   yourdomain.com -> YOUR_SERVER_IP
   *.yourdomain.com -> YOUR_SERVER_IP
   ```

2. **CNAME Records** (alternative):
   ```
   n8n.yourdomain.com -> yourdomain.com
   flowise.yourdomain.com -> yourdomain.com
   # ... etc for each service
   ```

### SSL Certificates
Traefik automatically obtains SSL certificates via Let's Encrypt:
- HTTP-01 challenge for single domains
- DNS-01 challenge for wildcard certificates (requires DNS API)

### Security Hardening
```bash
# Enable firewall (example for Ubuntu)
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Disable password authentication (use SSH keys)
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Regular updates
sudo apt update && sudo apt upgrade -y
```

### Monitoring and Backups
```bash
# Automated backups (add to crontab)
0 2 * * * /path/to/backup-script.sh

# Log rotation
sudo logrotate -f /etc/logrotate.d/docker

# Monitoring alerts
# Set up external monitoring (e.g., UptimeRobot, Pingdom)
```

## 🔄 Maintenance

### Regular Tasks

#### Daily
- Monitor service health via portal
- Check disk space usage
- Review container logs for errors

#### Weekly
- Update Docker images: `docker compose pull`
- Backup configuration: `cp .env .env.backup.$(date +%Y%m%d)`
- Check SSL certificate expiration
- Review security logs

#### Monthly
- Rotate passwords: `python scripts/password_manager.py --generate-env`
- Update base system packages
- Test backup restoration procedures
- Performance optimization review

### Updates and Upgrades
```bash
# Update application
git pull origin main

# Update Docker images
docker compose pull

# Restart services
docker compose up -d

# Verify all services healthy
python start_services.py --preflight
```

## 📚 Additional Resources

### Documentation
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Supabase Self-Hosting](https://supabase.com/docs/guides/self-hosting)
- [n8n Self-Hosting](https://docs.n8n.io/hosting/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

### Community Support
- GitHub Issues: Report bugs and feature requests
- Discord/Matrix: Community chat and support
- Documentation Wiki: Community-maintained guides

### Development
- [Contributing Guide](CONTRIBUTING.md)
- [Development Setup](DEVELOPMENT.md)
- [API Documentation](API.md)

---

**Need Help?** 
- Check the troubleshooting section above
- Review logs: `docker compose logs service-name`
- Visit the management portal: http://localhost:8085
- Open a GitHub issue with details and logs