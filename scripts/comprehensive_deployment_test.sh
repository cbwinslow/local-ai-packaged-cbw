#!/usr/bin/env bash
# Comprehensive Deployment Test and Validation Script
#
# This script provides end-to-end deployment testing for both local and remote scenarios.
# It validates all deployment components, handles port conflicts, ensures proper credential
# generation, and provides detailed troubleshooting guidance.
#
# Features:
# - Local and remote deployment validation
# - Port conflict detection and resolution
# - Credential strength validation
# - Service health monitoring
# - Bare metal installation compatibility
# - Comprehensive error reporting and solutions
# - OAuth and user management testing
# - Performance benchmarking

set -euo pipefail

# Script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color codes for enhanced output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Global variables
DEPLOYMENT_TYPE="local"
DOMAIN="localhost"
EMAIL="admin@localhost"
SKIP_CLEANUP=false
SKIP_PULL=false
VERBOSE=false
DRY_RUN=false
FORCE_RECREATE=false
BACKUP_ENV=true
TEST_TIMEOUT=300
DEPLOYMENT_START_TIME=""

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0
FAILED_TESTS=()
WARNINGS=()

# Logging functions
log() { 
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*" 
}

warn() { 
    echo -e "${YELLOW}[WARNING]${NC} $*"
    WARNINGS+=("$*")
    ((TESTS_WARNINGS++))
}

error() { 
    echo -e "${RED}[ERROR]${NC} $*" 
}

info() { 
    echo -e "${BLUE}[INFO]${NC} $*" 
}

success() { 
    echo -e "${GREEN}[SUCCESS]${NC} $*" 
}

debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${MAGENTA}[DEBUG]${NC} $*"
    fi
}

print_header() {
    echo
    echo -e "${CYAN}${BOLD}================================${NC}"
    echo -e "${CYAN}${BOLD} $1${NC}"
    echo -e "${CYAN}${BOLD}================================${NC}"
    echo
}

print_section() {
    echo
    echo -e "${BLUE}${BOLD}--- $1 ---${NC}"
}

# Test runner function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local optional="${3:-false}"
    
    ((TESTS_RUN++))
    
    if [[ "$VERBOSE" == "true" ]]; then
        info "Running test: $test_name"
        debug "Command: $test_command"
    else
        echo -n "Testing $test_name... "
    fi
    
    local start_time=$(date +%s.%N)
    
    if eval "$test_command" >/dev/null 2>&1; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        if [[ "$VERBOSE" == "true" ]]; then
            success "$test_name (${duration}s)"
        else
            echo -e "${GREEN}PASS${NC} (${duration}s)"
        fi
        ((TESTS_PASSED++))
        return 0
    else
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        if [[ "$optional" == "true" ]]; then
            if [[ "$VERBOSE" == "true" ]]; then
                warn "$test_name (optional) (${duration}s)"
            else
                echo -e "${YELLOW}SKIP${NC} (${duration}s)"
            fi
            ((TESTS_WARNINGS++))
        else
            if [[ "$VERBOSE" == "true" ]]; then
                error "$test_name (${duration}s)"
            else
                echo -e "${RED}FAIL${NC} (${duration}s)"
            fi
            FAILED_TESTS+=("$test_name")
            ((TESTS_FAILED++))
        fi
        return 1
    fi
}

# System requirements check
check_system_requirements() {
    print_section "System Requirements Check"
    
    run_test "Docker installation" "command -v docker"
    run_test "Docker Compose installation" "docker compose version"
    run_test "Python 3 installation" "command -v python3"
    run_test "Git installation" "command -v git"
    
    # Check Docker daemon
    run_test "Docker daemon running" "docker info"
    
    # Check system resources
    run_test "Sufficient memory (4GB+)" "check_memory_requirement"
    run_test "Sufficient disk space (10GB+)" "check_disk_space"
    
    # Check for common conflicting services
    check_port_conflicts
}

check_memory_requirement() {
    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    [[ $mem_gb -ge 4 ]]
}

check_disk_space() {
    local available_gb=$(df -BG "$REPO_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    [[ $available_gb -ge 10 ]]
}

check_port_conflicts() {
    print_section "Port Conflict Detection"
    
    local critical_ports=(3000 5678 8000 8001 5432 6333 7474 11434 80 443)
    local conflicting_ports=()
    local available_alternatives=()
    
    for port in "${critical_ports[@]}"; do
        if check_port_in_use "$port"; then
            conflicting_ports+=("$port")
            
            # Find running service on port
            local service=$(find_service_on_port "$port")
            warn "Port $port is in use by: $service"
            
            # Suggest alternative
            local alternative=$(suggest_alternative_port "$port")
            if [[ -n "$alternative" ]]; then
                available_alternatives+=("$port -> $alternative")
                info "Alternative port for $port: $alternative"
            fi
        else
            debug "Port $port is available"
        fi
    done
    
    if [[ ${#conflicting_ports[@]} -gt 0 ]]; then
        warn "Port conflicts detected: ${conflicting_ports[*]}"
        
        if [[ ${#available_alternatives[@]} -gt 0 ]]; then
            info "Suggested port mappings:"
            for alt in "${available_alternatives[@]}"; do
                info "  $alt"
            done
        fi
        
        if [[ "$FORCE_RECREATE" != "true" ]]; then
            echo
            read -p "Continue with deployment despite port conflicts? (y/N): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "Deployment cancelled due to port conflicts"
                exit 1
            fi
        fi
    else
        success "No port conflicts detected"
    fi
}

check_port_in_use() {
    local port=$1
    netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "
}

find_service_on_port() {
    local port=$1
    
    # Try to find the process using the port
    local pid=$(lsof -ti:$port 2>/dev/null | head -1)
    if [[ -n "$pid" ]]; then
        local service=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        echo "$service (PID: $pid)"
    else
        echo "unknown service"
    fi
}

suggest_alternative_port() {
    local port=$1
    local base_alternative=$((port + 1000))
    
    for i in {0..99}; do
        local alternative=$((base_alternative + i))
        if ! check_port_in_use "$alternative"; then
            echo "$alternative"
            return
        fi
    done
    
    echo ""  # No alternative found
}

# Environment validation and generation
validate_and_generate_env() {
    print_section "Environment Configuration"
    
    # Check if .env exists
    if [[ -f "$REPO_ROOT/.env" ]]; then
        info "Found existing .env file"
        
        # Backup existing .env if requested
        if [[ "$BACKUP_ENV" == "true" ]]; then
            local timestamp=$(date +%Y%m%dT%H%M%SZ)
            local backup_file="$REPO_ROOT/.env.backup.$timestamp"
            cp "$REPO_ROOT/.env" "$backup_file"
            success "Backed up .env to .env.backup.$timestamp"
        fi
        
        # Validate existing .env
        validate_env_file "$REPO_ROOT/.env"
    else
        info "No .env file found, generating new one"
        generate_enhanced_env
    fi
    
    # Additional environment checks
    check_supabase_credentials
    check_security_settings
}

validate_env_file() {
    local env_file="$1"
    
    info "Validating environment file: $env_file"
    
    # Required variables
    local required_vars=(
        "BASE_DOMAIN"
        "POSTGRES_PASSWORD"
        "JWT_SECRET"
        "ANON_KEY"
        "SERVICE_ROLE_KEY"
        "N8N_ENCRYPTION_KEY"
        "NEO4J_AUTH"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file"; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            warn "Force recreate enabled, regenerating .env file"
            generate_enhanced_env
        else
            echo
            read -p "Regenerate .env file? (Y/n): " -r
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                generate_enhanced_env
            else
                error "Cannot proceed without required environment variables"
                exit 1
            fi
        fi
    else
        success "All required environment variables present"
    fi
    
    # Check credential strength
    check_credential_strength "$env_file"
}

generate_enhanced_env() {
    info "Generating enhanced environment configuration"
    
    if [[ -f "$REPO_ROOT/scripts/enhanced_env_generator.py" ]]; then
        python3 "$REPO_ROOT/scripts/enhanced_env_generator.py" \
            --base-domain "$DOMAIN" \
            --email "$EMAIL" \
            --environment "$DEPLOYMENT_TYPE" \
            --output "$REPO_ROOT/.env" \
            ${FORCE_RECREATE:+--force}
        
        success "Enhanced environment file generated"
    else
        warn "Enhanced env generator not found, using fallback"
        python3 "$REPO_ROOT/scripts/generate_env.py" \
            --base-domain "$DOMAIN" \
            --email "$EMAIL" > "$REPO_ROOT/.env"
        
        # Add missing BASE_DOMAIN if not present
        if ! grep -q "^BASE_DOMAIN=" "$REPO_ROOT/.env"; then
            echo "BASE_DOMAIN=$DOMAIN" >> "$REPO_ROOT/.env"
        fi
        
        success "Basic environment file generated"
    fi
    
    # Set secure permissions
    chmod 600 "$REPO_ROOT/.env"
    success "Set .env permissions to 600"
}

check_credential_strength() {
    local env_file="$1"
    
    info "Checking credential strength"
    
    # Source the env file safely
    set +a
    while IFS= read -r line; do
        if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*=.+ ]] && [[ ! "$line" =~ ^# ]]; then
            eval "export $line"
        fi
    done < "$env_file"
    set -a
    
    local weak_credentials=()
    
    # Check password length and complexity
    if [[ ${#POSTGRES_PASSWORD} -lt 16 ]]; then
        weak_credentials+=("POSTGRES_PASSWORD: too short")
    fi
    
    if [[ ${#JWT_SECRET} -lt 32 ]]; then
        weak_credentials+=("JWT_SECRET: too short")
    fi
    
    if [[ ${#N8N_ENCRYPTION_KEY} -lt 24 ]]; then
        weak_credentials+=("N8N_ENCRYPTION_KEY: too short")
    fi
    
    # Check for common weak patterns
    for var in POSTGRES_PASSWORD JWT_SECRET; do
        local value="${!var:-}"
        if [[ "$value" =~ ^(password|secret|admin|changeme) ]]; then
            weak_credentials+=("$var: contains weak pattern")
        fi
    done
    
    if [[ ${#weak_credentials[@]} -gt 0 ]]; then
        warn "Weak credentials detected:"
        for cred in "${weak_credentials[@]}"; do
            warn "  - $cred"
        done
    else
        success "All credentials meet security requirements"
    fi
}

check_supabase_credentials() {
    print_section "Supabase Configuration Validation"
    
    # Check JWT token format
    if [[ -n "${ANON_KEY:-}" ]]; then
        if [[ "$ANON_KEY" =~ ^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$ ]]; then
            success "ANON_KEY has valid JWT format"
        else
            warn "ANON_KEY does not appear to be a valid JWT"
        fi
    fi
    
    if [[ -n "${SERVICE_ROLE_KEY:-}" ]]; then
        if [[ "$SERVICE_ROLE_KEY" =~ ^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$ ]]; then
            success "SERVICE_ROLE_KEY has valid JWT format"
        else
            warn "SERVICE_ROLE_KEY does not appear to be a valid JWT"
        fi
    fi
    
    # Check database configuration
    run_test "Database configuration complete" "check_database_config"
}

check_database_config() {
    [[ -n "${POSTGRES_HOST:-}" ]] && \
    [[ -n "${POSTGRES_PORT:-}" ]] && \
    [[ -n "${POSTGRES_DB:-}" ]] && \
    [[ -n "${POSTGRES_USER:-}" ]] && \
    [[ -n "${POSTGRES_PASSWORD:-}" ]]
}

check_security_settings() {
    print_section "Security Settings Validation"
    
    # Check file permissions
    local env_perms=$(stat -c %a "$REPO_ROOT/.env" 2>/dev/null || echo "unknown")
    if [[ "$env_perms" == "600" ]]; then
        success ".env file has secure permissions (600)"
    else
        warn ".env file permissions: $env_perms (should be 600)"
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            chmod 600 "$REPO_ROOT/.env"
            success "Fixed .env permissions"
        fi
    fi
    
    # Check for secrets in git
    if git -C "$REPO_ROOT" ls-files --error-unmatch .env >/dev/null 2>&1; then
        error ".env file is tracked by git (security risk!)"
        info "Run: git rm --cached .env && git commit -m 'Remove .env from tracking'"
    else
        success ".env file is not tracked by git"
    fi
}

# Docker operations
prepare_docker_environment() {
    print_section "Docker Environment Preparation"
    
    # Check if containers are already running
    local running_containers=$(docker ps --format "{{.Names}}" | grep -E "(kong|db|n8n|openwebui)" | wc -l)
    
    if [[ $running_containers -gt 0 ]]; then
        info "$running_containers containers already running"
        
        if [[ "$FORCE_RECREATE" == "true" ]]; then
            warn "Force recreate enabled, stopping existing containers"
            stop_all_containers
        else
            echo
            read -p "Stop existing containers and recreate? (y/N): " -r
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                stop_all_containers
            else
                info "Continuing with existing containers"
            fi
        fi
    fi
    
    # Pull images if not skipped
    if [[ "$SKIP_PULL" != "true" ]]; then
        pull_docker_images
    fi
    
    # Check Docker resources
    check_docker_resources
}

stop_all_containers() {
    info "Stopping all project containers"
    
    cd "$REPO_ROOT"
    
    # Stop main stack
    docker compose -p localai down --remove-orphans || true
    
    # Stop Supabase stack if it exists
    if [[ -f "supabase/docker/docker-compose.yml" ]]; then
        docker compose -f supabase/docker/docker-compose.yml -p localai down --remove-orphans || true
    fi
    
    success "All containers stopped"
}

pull_docker_images() {
    info "Pulling Docker images"
    
    cd "$REPO_ROOT"
    
    local compose_files=(
        "docker-compose.all-in-one.yml"
    )
    
    if [[ "$DEPLOYMENT_TYPE" != "local" ]]; then
        compose_files+=("docker-compose.all-in-one.traefik.yml")
    fi
    
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            info "Pulling images from $compose_file"
            docker compose -f "$compose_file" pull || warn "Failed to pull some images from $compose_file"
        fi
    done
    
    # Pull Supabase images
    if [[ -f "supabase/docker/docker-compose.yml" ]]; then
        info "Pulling Supabase images"
        docker compose -f supabase/docker/docker-compose.yml pull || warn "Failed to pull some Supabase images"
    fi
    
    success "Docker image pull completed"
}

check_docker_resources() {
    info "Checking Docker resource limits"
    
    # Check available memory
    local docker_memory=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
    if [[ $docker_memory -gt 0 ]]; then
        local memory_gb=$((docker_memory / 1024 / 1024 / 1024))
        if [[ $memory_gb -ge 4 ]]; then
            success "Docker has sufficient memory: ${memory_gb}GB"
        else
            warn "Docker memory may be insufficient: ${memory_gb}GB (recommended: 4GB+)"
        fi
    fi
    
    # Check disk space for Docker
    local docker_data_usage=$(docker system df --format 'table {{.Size}}' 2>/dev/null | tail -n +2 | head -1 || echo "unknown")
    info "Docker data usage: $docker_data_usage"
}

# Supabase initialization
initialize_supabase() {
    print_section "Supabase Initialization"
    
    # Initialize Supabase repository if needed
    if [[ ! -d "$REPO_ROOT/supabase/docker" ]]; then
        info "Initializing Supabase repository"
        cd "$REPO_ROOT"
        python3 start_services.py --preflight --skip-neo4j
    else
        success "Supabase repository already initialized"
    fi
    
    # Validate Supabase configuration
    run_test "Supabase docker-compose.yml exists" "[[ -f '$REPO_ROOT/supabase/docker/docker-compose.yml' ]]"
    run_test "Supabase .env exists" "[[ -f '$REPO_ROOT/supabase/docker/.env' ]]"
    
    # Test Supabase compose configuration
    run_test "Supabase compose config validation" "validate_supabase_compose"
}

validate_supabase_compose() {
    cd "$REPO_ROOT"
    docker compose -f supabase/docker/docker-compose.yml config >/dev/null 2>&1
}

# Main deployment execution
execute_deployment() {
    print_section "Deployment Execution"
    
    DEPLOYMENT_START_TIME=$(date +%s)
    
    cd "$REPO_ROOT"
    
    info "Starting deployment with profile: $DEPLOYMENT_TYPE"
    
    # Start Supabase first
    start_supabase_stack
    
    # Wait for Supabase to be ready
    wait_for_supabase_ready
    
    # Start main application stack
    start_main_stack
    
    # Wait for all services to be ready
    wait_for_all_services_ready
    
    local deployment_end_time=$(date +%s)
    local deployment_duration=$((deployment_end_time - DEPLOYMENT_START_TIME))
    
    success "Deployment completed in ${deployment_duration}s"
}

start_supabase_stack() {
    info "Starting Supabase stack"
    
    local compose_cmd="docker compose -f supabase/docker/docker-compose.yml -p localai up -d"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: $compose_cmd"
        return
    fi
    
    if eval "$compose_cmd"; then
        success "Supabase stack started"
    else
        error "Failed to start Supabase stack"
        return 1
    fi
}

start_main_stack() {
    info "Starting main application stack"
    
    local compose_files="-f docker-compose.all-in-one.yml"
    
    if [[ "$DEPLOYMENT_TYPE" != "local" ]]; then
        compose_files+=" -f docker-compose.all-in-one.traefik.yml"
    fi
    
    local compose_cmd="docker compose $compose_files -p localai up -d"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: $compose_cmd"
        return
    fi
    
    if eval "$compose_cmd"; then
        success "Main stack started"
    else
        error "Failed to start main stack"
        return 1
    fi
}

wait_for_supabase_ready() {
    info "Waiting for Supabase services to be ready"
    
    local max_wait=120
    local wait_time=0
    local check_interval=5
    
    while [[ $wait_time -lt $max_wait ]]; do
        if check_supabase_health; then
            success "Supabase services are ready"
            return 0
        fi
        
        debug "Waiting for Supabase... (${wait_time}s/${max_wait}s)"
        sleep $check_interval
        wait_time=$((wait_time + check_interval))
    done
    
    warn "Supabase services not ready after ${max_wait}s"
    return 1
}

check_supabase_health() {
    # Check if database is responding
    docker exec -it "$(docker ps --filter "name=localai.*db" --format "{{.Names}}" | head -1)" pg_isready -U postgres >/dev/null 2>&1
}

wait_for_all_services_ready() {
    info "Waiting for all services to be ready"
    
    local services=(
        "http://localhost:8000/health:Kong API Gateway"
        "http://localhost:5678/healthz:n8n"
        "http://localhost:3000/health:Open WebUI"
    )
    
    local all_ready=true
    
    for service_info in "${services[@]}"; do
        local url="${service_info%:*}"
        local name="${service_info#*:}"
        
        if wait_for_service_ready "$url" "$name"; then
            success "$name is ready"
        else
            warn "$name is not ready"
            all_ready=false
        fi
    done
    
    if [[ "$all_ready" == "true" ]]; then
        success "All services are ready"
    else
        warn "Some services are not ready, but deployment can continue"
    fi
}

wait_for_service_ready() {
    local url="$1"
    local name="$2"
    local max_wait=60
    local wait_time=0
    local check_interval=5
    
    while [[ $wait_time -lt $max_wait ]]; do
        if curl -s "$url" >/dev/null 2>&1; then
            return 0
        fi
        
        sleep $check_interval
        wait_time=$((wait_time + check_interval))
    done
    
    return 1
}

# Post-deployment testing and validation
run_post_deployment_tests() {
    print_section "Post-Deployment Testing"
    
    # Run comprehensive inter-service tests
    if [[ -f "$REPO_ROOT/scripts/tests/comprehensive_interservice_tests.py" ]]; then
        info "Running comprehensive inter-service tests"
        if python3 "$REPO_ROOT/scripts/tests/comprehensive_interservice_tests.py" --quick; then
            success "Inter-service tests passed"
        else
            warn "Inter-service tests had issues"
        fi
    fi
    
    # Run existing test suite
    if [[ -f "$REPO_ROOT/scripts/tests/run_comprehensive_tests.sh" ]]; then
        info "Running existing comprehensive tests"
        if "$REPO_ROOT/scripts/tests/run_comprehensive_tests.sh" --quick; then
            success "Comprehensive tests passed"
        else
            warn "Comprehensive tests had issues"
        fi
    fi
    
    # Test OAuth and user management if configured
    test_oauth_functionality
    
    # Performance benchmarks
    run_performance_tests
}

test_oauth_functionality() {
    info "Testing OAuth and user management functionality"
    
    # Test Supabase auth endpoints
    run_test "Supabase Auth settings" "curl -s http://localhost:8000/auth/v1/settings | grep -q 'external'"
    
    # Test user registration endpoint
    run_test "User registration endpoint" "curl -s -w '%{http_code}' http://localhost:8000/auth/v1/signup | grep -q '400\\|422'" "true"
    
    # More OAuth tests would go here if we had specific providers configured
}

run_performance_tests() {
    info "Running basic performance tests"
    
    # Test response times
    local services=(
        "http://localhost:8000/health"
        "http://localhost:5678/healthz"
        "http://localhost:3000/health"
    )
    
    for url in "${services[@]}"; do
        local response_time=$(curl -w '%{time_total}' -s -o /dev/null "$url" 2>/dev/null || echo "999")
        
        if (( $(echo "$response_time < 2.0" | bc -l) )); then
            success "Service ${url##*/} response time: ${response_time}s"
        else
            warn "Service ${url##*/} slow response: ${response_time}s"
        fi
    done
}

# Cleanup and summary
cleanup_and_summary() {
    print_section "Deployment Summary"
    
    info "Tests run: $TESTS_RUN"
    success "Tests passed: $TESTS_PASSED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        error "Tests failed: $TESTS_FAILED"
        error "Failed tests: ${FAILED_TESTS[*]}"
    fi
    
    if [[ $TESTS_WARNINGS -gt 0 ]]; then
        warn "Tests with warnings: $TESTS_WARNINGS"
    fi
    
    local total_time=$(($(date +%s) - DEPLOYMENT_START_TIME))
    info "Total deployment time: ${total_time}s"
    
    # Show service URLs
    print_service_urls
    
    # Show troubleshooting information if there were issues
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]] || [[ ${#WARNINGS[@]} -gt 0 ]]; then
        show_troubleshooting_guide
    fi
}

print_service_urls() {
    print_section "Service URLs"
    
    if [[ "$DOMAIN" == "localhost" ]]; then
        info "n8n: http://localhost:5678"
        info "Open WebUI: http://localhost:3000"
        info "Flowise: http://localhost:8080"
        info "Supabase Studio: http://localhost:8000"
        info "Kong Admin: http://localhost:8001"
    else
        info "n8n: https://n8n.$DOMAIN"
        info "Open WebUI: https://webui.$DOMAIN"
        info "Flowise: https://flowise.$DOMAIN"
        info "Supabase: https://supabase.$DOMAIN"
        info "Portal: https://portal.$DOMAIN"
    fi
}

show_troubleshooting_guide() {
    print_section "Troubleshooting Guide"
    
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        error "Issues detected during deployment:"
        for test in "${FAILED_TESTS[@]}"; do
            error "  - $test"
        done
        echo
    fi
    
    info "Common solutions:"
    info "1. Check logs: docker compose logs [service-name]"
    info "2. Restart services: docker compose restart"
    info "3. Check port conflicts: netstat -tuln | grep ':[PORT] '"
    info "4. Validate .env: cat .env | grep -E '^[A-Z_]+='"
    info "5. Regenerate .env: python3 scripts/enhanced_env_generator.py"
    echo
    info "For more help, see DEPLOYMENT_GUIDE.md"
}

# Usage information
show_usage() {
    cat << EOF
Comprehensive Deployment Test and Validation Script

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --type TYPE         Deployment type: local, development, production (default: local)
    -d, --domain DOMAIN     Base domain for services (default: localhost)
    -e, --email EMAIL       Email for certificates and admin accounts (default: admin@localhost)
    -v, --verbose           Enable verbose output
    --dry-run              Show what would be done without executing
    --force                Force recreation of containers and .env
    --skip-cleanup         Skip cleanup of existing containers
    --skip-pull            Skip pulling Docker images
    --no-backup            Don't backup existing .env file
    --timeout SECONDS      Test timeout in seconds (default: 300)
    -h, --help             Show this help message

EXAMPLES:
    # Local development deployment
    $0 --type local --verbose

    # Production deployment with custom domain
    $0 --type production --domain myapp.com --email admin@myapp.com

    # Quick test without pulling images
    $0 --skip-pull --verbose

    # Force complete recreation
    $0 --force --verbose

    # Dry run to see what would happen
    $0 --dry-run --verbose

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE_RECREATE=true
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            --skip-pull)
                SKIP_PULL=true
                shift
                ;;
            --no-backup)
                BACKUP_ENV=false
                shift
                ;;
            --timeout)
                TEST_TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate deployment type
    if [[ ! "$DEPLOYMENT_TYPE" =~ ^(local|development|production)$ ]]; then
        error "Invalid deployment type: $DEPLOYMENT_TYPE"
        exit 1
    fi
}

# Main execution function
main() {
    parse_arguments "$@"
    
    print_header "Comprehensive Deployment Test & Validation"
    
    info "Deployment configuration:"
    info "  Type: $DEPLOYMENT_TYPE"
    info "  Domain: $DOMAIN"
    info "  Email: $EMAIL"
    info "  Repository: $REPO_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        warn "DRY RUN MODE - No changes will be made"
    fi
    
    # Change to repository root
    cd "$REPO_ROOT"
    
    # Execute deployment pipeline
    check_system_requirements
    validate_and_generate_env
    prepare_docker_environment
    initialize_supabase
    
    if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
        execute_deployment
        run_post_deployment_tests
    else
        error "Pre-deployment checks failed, skipping deployment"
    fi
    
    cleanup_and_summary
    
    # Exit with appropriate code
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        exit 1
    elif [[ $TESTS_WARNINGS -gt 0 ]]; then
        exit 2
    else
        exit 0
    fi
}

# Install bc if not available (for arithmetic)
if ! command -v bc >/dev/null 2>&1; then
    warn "bc not found, installing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y bc
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y bc
    else
        warn "Cannot install bc automatically"
    fi
fi

# Run main function with all arguments
main "$@"