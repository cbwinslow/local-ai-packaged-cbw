#!/usr/bin/env bash
set -euo pipefail

# One-click deployment script for local AI packaged stack
# Handles secrets, containers, and DNS for both local and server modes
# Usage: ./scripts/oneclick_deploy.sh [--mode local|server] [--domain example.com] [--email admin@example.com]

# Default values
MODE="local"
DOMAIN="localhost"
EMAIL="admin@localhost"
PROXY="traefik"
SKIP_PULL=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --proxy)
            PROXY="$2"
            shift 2
            ;;
        --skip-pull)
            SKIP_PULL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mode local|server    Deployment mode (default: local)"
            echo "  --domain DOMAIN        Base domain (default: localhost)"
            echo "  --email EMAIL          Admin email for ACME (default: admin@localhost)"
            echo "  --proxy traefik|none   Reverse proxy (default: traefik)"
            echo "  --skip-pull           Skip pulling Docker images"
            echo "  -v, --verbose         Verbose output"
            echo "  --help                Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Color output functions
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $*"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $*"
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $*"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Validation functions
validate_requirements() {
    log "Validating requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed. Please install Python 3."
        exit 1
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git."
        exit 1
    fi
    
    # Validate mode
    if [[ "$MODE" != "local" && "$MODE" != "server" ]]; then
        error "Invalid mode: $MODE. Must be 'local' or 'server'."
        exit 1
    fi
    
    # Validate proxy
    if [[ "$PROXY" != "traefik" && "$PROXY" != "none" ]]; then
        error "Invalid proxy: $PROXY. Must be 'traefik' or 'none'."
        exit 1
    fi
    
    log "Requirements validation passed"
}

# Initialize environment
init_environment() {
    log "Initializing environment..."
    
    # Update BASE_DOMAIN and EMAIL in the environment fix script
    cat > "$SCRIPT_DIR/fix_env.py" << 'EOF'
#!/usr/bin/env python3
"""
Fix and complete the .env file with all required variables for the local AI stack.
This script ensures all missing environment variables are populated with secure defaults.
"""

import os
import sys
import secrets
import string
from pathlib import Path

# Required environment variables that the stack expects
REQUIRED_VARS = {
    # Base configuration - will be overridden by deploy script
    'BASE_DOMAIN': 'localhost',
    'ACME_EMAIL': 'admin@localhost',
    'CLOUDFLARE_API_TOKEN': 'change_me_cf_token',
    
    # Supabase specific
    'SUPABASE_DB_PASSWORD': None,  # Will generate
    'SECRET_KEY_BASE': None,       # Will generate
    'VAULT_ENC_KEY': None,         # Will generate
    'LOGFLARE_PUBLIC_ACCESS_TOKEN': None,   # Will generate
    'LOGFLARE_PRIVATE_ACCESS_TOKEN': None,  # Will generate
    
    # Docker configuration
    'DOCKER_SOCKET_LOCATION': '/var/run/docker.sock',
    
    # Hostnames (will be derived from BASE_DOMAIN)
    'N8N_HOSTNAME': None,
    'FLOWISE_HOSTNAME': None,
    'WEBUI_HOSTNAME': None,
    'PORTAL_HOSTNAME': None,
    'SEARXNG_HOSTNAME': None,
    'SUPABASE_HOSTNAME': None,
    'LANGFUSE_HOSTNAME': None,
    'OLLAMA_HOSTNAME': None,
    'NEO4J_HOSTNAME': None,
    'TRAEFIK_DASHBOARD_HOST': None,
    'SUPABASE_STUDIO_HOSTNAME': None,
    'FUNCTIONS_HOSTNAME': None,
    'REALTIME_HOSTNAME': None,
}

def generate_secure_secret(length=32):
    """Generate a secure random string."""
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_secret(length=32):
    """Generate a secure hex string."""
    return secrets.token_hex(length)

def read_existing_env(env_path):
    """Read existing .env file and return as dict."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    return env_vars

def write_env_file(env_path, env_vars):
    """Write environment variables to .env file."""
    with open(env_path, 'w') as f:
        f.write("############\n")
        f.write("# Complete environment file for local AI stack\n")
        f.write("# Generated by scripts/oneclick_deploy.sh\n")
        f.write("############\n\n")
        
        # Group variables by category
        base_config = ['BASE_DOMAIN', 'ACME_EMAIL', 'CLOUDFLARE_API_TOKEN']
        hostnames = [k for k in env_vars.keys() if k.endswith('_HOSTNAME') or k.endswith('_HOST')]
        db_supabase = [k for k in env_vars.keys() if 'POSTGRES' in k or 'SUPABASE' in k or 'JWT' in k or 'ANON' in k or 'SERVICE_ROLE' in k]
        app_secrets = [k for k in env_vars.keys() if any(word in k for word in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']) and not any(word in k for word in ['POSTGRES', 'JWT', 'ANON', 'SERVICE_ROLE', 'CLOUDFLARE'])]
        
        categories = {
            'Base Configuration': base_config,
            'Hostnames': hostnames,
            'Database & Supabase': db_supabase,
            'Application Secrets': app_secrets,
            'Other Configuration': [k for k in env_vars.keys() if k not in (base_config + hostnames + db_supabase + app_secrets)]
        }
        
        written_keys = set()
        for category, keys in categories.items():
            if keys:
                f.write(f"# {category}\n")
                for key in sorted(keys):
                    if key in env_vars and key not in written_keys:
                        f.write(f"{key}={env_vars[key]}\n")
                        written_keys.add(key)
                f.write("\n")
        
        # Write any remaining keys
        remaining = [k for k in sorted(env_vars.keys()) if k not in written_keys]
        if remaining:
            f.write("# Additional Variables\n")
            for key in remaining:
                f.write(f"{key}={env_vars[key]}\n")

def main():
    repo_root = Path(__file__).parent.parent
    env_path = repo_root / '.env'
    
    # Read domain and email from command line args or environment
    domain = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DEPLOY_DOMAIN', 'localhost')
    email = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('DEPLOY_EMAIL', 'admin@localhost')
    
    print(f"Fixing environment file: {env_path}")
    print(f"Using domain: {domain}, email: {email}")
    
    # Read existing .env
    existing_vars = read_existing_env(env_path)
    print(f"Found {len(existing_vars)} existing variables")
    
    # Start with existing variables
    env_vars = existing_vars.copy()
    
    # Override base configuration
    env_vars['BASE_DOMAIN'] = domain
    env_vars['ACME_EMAIL'] = email
    
    # Add missing required variables
    missing_count = 0
    
    for var, default in REQUIRED_VARS.items():
        if var not in env_vars or not env_vars[var] or env_vars[var].startswith('change_me'):
            missing_count += 1
            
            if var == 'BASE_DOMAIN':
                env_vars[var] = domain
            elif var == 'ACME_EMAIL':
                env_vars[var] = email
            elif var.endswith('_HOSTNAME') or var.endswith('_HOST'):
                # Generate hostname based on service name
                service = var.replace('_HOSTNAME', '').replace('_HOST', '').lower()
                if service == 'traefik_dashboard':
                    service = 'traefik'
                elif service == 'supabase_studio':
                    service = 'studio'
                env_vars[var] = f"{service}.{domain}"
            elif 'SECRET' in var or 'KEY' in var or 'TOKEN' in var:
                if 'HEX' in var or var in ['VAULT_ENC_KEY', 'SECRET_KEY_BASE']:
                    env_vars[var] = generate_hex_secret(32)
                else:
                    env_vars[var] = generate_secure_secret(48)
            elif 'PASSWORD' in var:
                env_vars[var] = generate_secure_secret(24)
            elif default is not None:
                env_vars[var] = default
            else:
                env_vars[var] = generate_secure_secret(32)
    
    print(f"Added/updated {missing_count} variables")
    
    # Backup existing .env if it exists
    if env_path.exists():
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%SZ")
        backup_path = env_path.with_suffix(f'.{timestamp}.bak')
        env_path.rename(backup_path)
        print(f"Backed up existing .env to {backup_path.name}")
    
    # Write the complete .env file
    write_env_file(env_path, env_vars)
    print(f"Generated complete .env file with {len(env_vars)} variables")
    
    # Set appropriate permissions
    os.chmod(env_path, 0o600)
    print("Set .env permissions to 600 (owner read/write only)")

if __name__ == '__main__':
    main()
EOF
    
    # Generate/update environment file
    export DEPLOY_DOMAIN="$DOMAIN"
    export DEPLOY_EMAIL="$EMAIL"
    python3 "$SCRIPT_DIR/fix_env.py" "$DOMAIN" "$EMAIL"
    
    log "Environment initialized"
}

# Setup Supabase
setup_supabase() {
    log "Setting up Supabase..."
    
    # Initialize Supabase repo if needed
    python3 start_services.py --preflight --skip-neo4j
    
    # Check if supabase directory is properly populated
    if [[ ! -f "supabase/docker/docker-compose.yml" ]]; then
        error "Supabase setup failed - docker-compose.yml not found"
        exit 1
    fi
    
    log "Supabase setup complete"
}

# Deploy stack
deploy_stack() {
    log "Deploying stack in $MODE mode with $PROXY proxy..."
    
    # Stop any existing containers
    info "Stopping existing containers..."
    docker compose down --remove-orphans || true
    
    # Pull images if not skipped
    if [[ "$SKIP_PULL" != "true" ]]; then
        info "Pulling Docker images..."
        if [[ "$PROXY" == "traefik" ]]; then
            docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml pull
        else
            docker compose -f docker-compose.all-in-one.yml pull
        fi
    fi
    
    # Start the stack
    info "Starting the stack..."
    if [[ "$PROXY" == "traefik" ]]; then
        docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml up -d
    else
        docker compose -f docker-compose.all-in-one.yml up -d
    fi
    
    log "Stack deployment complete"
}

# Health checks
wait_for_services() {
    log "Waiting for services to become healthy..."
    
    local max_wait=300
    local wait_time=0
    local check_interval=10
    
    while [[ $wait_time -lt $max_wait ]]; do
        local healthy_count=0
        local total_count=0
        
        # Count healthy vs total containers
        while IFS= read -r container; do
            if [[ -n "$container" ]]; then
                total_count=$((total_count + 1))
                health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health")
                status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
                
                if [[ "$health" == "healthy" ]] || [[ "$health" == "no-health" && "$status" == "running" ]]; then
                    healthy_count=$((healthy_count + 1))
                fi
            fi
        done < <(docker compose ps -q)
        
        if [[ $total_count -gt 0 ]]; then
            info "Health check: $healthy_count/$total_count containers healthy/running"
            
            if [[ $healthy_count -eq $total_count ]]; then
                log "All services are healthy!"
                return 0
            fi
        fi
        
        sleep $check_interval
        wait_time=$((wait_time + check_interval))
    done
    
    warn "Not all services became healthy within ${max_wait}s, but continuing..."
    return 0
}

# Display access information
show_access_info() {
    log "Deployment complete! Access information:"
    echo
    
    if [[ "$PROXY" == "traefik" ]]; then
        if [[ "$MODE" == "local" ]]; then
            echo "🌐 Access URLs (add to /etc/hosts if using localhost):"
            echo "   127.0.0.1 portal.$DOMAIN n8n.$DOMAIN flowise.$DOMAIN webui.$DOMAIN"
            echo "   127.0.0.1 supabase.$DOMAIN studio.$DOMAIN functions.$DOMAIN"
            echo "   127.0.0.1 traefik.$DOMAIN searxng.$DOMAIN langfuse.$DOMAIN"
            echo
        fi
        
        echo "📋 Service URLs:"
        echo "   Portal:      https://portal.$DOMAIN"
        echo "   n8n:         https://n8n.$DOMAIN"
        echo "   Flowise:     https://flowise.$DOMAIN"
        echo "   Open WebUI:  https://webui.$DOMAIN"
        echo "   Supabase:    https://supabase.$DOMAIN"
        echo "   Studio:      https://studio.$DOMAIN"
        echo "   Functions:   https://functions.$DOMAIN"
        echo "   Traefik:     https://traefik.$DOMAIN"
        echo "   SearXNG:     https://searxng.$DOMAIN"
        echo "   Langfuse:    https://langfuse.$DOMAIN"
    else
        echo "📋 Service URLs (direct access):"
        echo "   Portal:      http://localhost:8085"
        echo "   n8n:         http://localhost:5678"
        echo "   Flowise:     http://localhost:3001"
        echo "   Open WebUI:  http://localhost:8080"
        echo "   Supabase:    http://localhost:8000"
    fi
    
    echo
    echo "🔍 Management:"
    echo "   Docker logs: docker compose logs -f [service-name]"
    echo "   Stop stack:  docker compose down"
    echo "   View status: docker compose ps"
    echo
    
    # Show environment file location
    echo "⚙️  Configuration:"
    echo "   Environment: .env (secured with 600 permissions)"
    echo "   Backup configs in: .env.*.bak"
    echo
}

# Run tests
run_tests() {
    if [[ "$VERBOSE" == "true" ]]; then
        log "Running test suite..."
        cd scripts/tests
        bash run_all.sh || warn "Some tests failed - this is expected if services are still starting"
        cd ../..
    fi
}

# Cleanup function
cleanup() {
    if [[ $? -ne 0 ]]; then
        error "Deployment failed!"
        echo
        echo "🔧 Troubleshooting:"
        echo "   Check logs: docker compose logs"
        echo "   Check status: docker compose ps"
        echo "   Check environment: cat .env"
        echo "   Manual start: python3 start_services.py"
    fi
}

# Main execution
main() {
    trap cleanup EXIT
    
    echo "🚀 Local AI Packaged - One-Click Deployment"
    echo "   Mode: $MODE"
    echo "   Domain: $DOMAIN"
    echo "   Email: $EMAIL"
    echo "   Proxy: $PROXY"
    echo
    
    validate_requirements
    init_environment
    setup_supabase
    deploy_stack
    wait_for_services
    run_tests
    show_access_info
    
    log "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"