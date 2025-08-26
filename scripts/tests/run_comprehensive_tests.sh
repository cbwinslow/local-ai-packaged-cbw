#!/usr/bin/env bash
set -euo pipefail

# Comprehensive test suite runner for local AI stack
# Tests environment setup, configuration, services, and connectivity
# Usage: ./scripts/tests/run_comprehensive_tests.sh [--quick] [--verbose]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Parse arguments
QUICK_MODE=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--quick] [--verbose]"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Test runner function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local optional="${3:-false}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    echo
    log "Running test: $test_name"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Command: $test_command"
    fi
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        if [[ "$optional" == "true" ]]; then
            echo -e "${YELLOW}⚠ SKIP${NC}: $test_name (optional test failed)"
        else
            echo -e "${RED}✗ FAIL${NC}: $test_name"
            FAILED_TESTS+=("$test_name")
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Individual test functions
test_environment_setup() {
    [[ -f .env ]] && \
    grep -q "BASE_DOMAIN=" .env && \
    grep -q "POSTGRES_PASSWORD=" .env && \
    grep -q "JWT_SECRET=" .env
}

test_environment_variables() {
    source .env
    [[ -n "$BASE_DOMAIN" ]] && \
    [[ -n "$POSTGRES_PASSWORD" ]] && \
    [[ -n "$JWT_SECRET" ]] && \
    [[ -n "$ANON_KEY" ]] && \
    [[ -n "$SERVICE_ROLE_KEY" ]]
}

test_supabase_directory() {
    [[ -d supabase/docker ]] && \
    [[ -f supabase/docker/docker-compose.yml ]] && \
    [[ -f supabase/docker/.env ]]
}

test_compose_configs() {
    # Test main compose files
    docker compose -f docker-compose.all-in-one.yml config > /dev/null && \
    docker compose -f docker-compose.all-in-one.yml -f docker-compose.all-in-one.traefik.yml config > /dev/null && \
    docker compose -f supabase/docker/docker-compose.yml config > /dev/null
}

test_docker_dependencies() {
    command -v docker > /dev/null && \
    docker --version > /dev/null && \
    docker compose version > /dev/null
}

test_python_dependencies() {
    python3 -c "import websockets, psycopg2, requests" 2>/dev/null
}

test_scripts_executable() {
    [[ -x scripts/oneclick_deploy.sh ]] && \
    [[ -x scripts/fix_env.py ]] && \
    [[ -x scripts/tests/run_all.sh ]]
}

test_searxng_config() {
    [[ -f searxng/settings.yml ]] && \
    [[ ! $(grep -c "ultrasecretkey" searxng/settings.yml) -gt 0 ]]
}

test_traefik_config() {
    [[ -f traefik/traefik.yml ]] && \
    [[ -d traefik/dynamic ]] && \
    [[ -f traefik/dynamic/middlewares.yml ]]
}

test_git_repository() {
    git status > /dev/null && \
    [[ -d .git ]]
}

# Service-specific tests (only run if --quick is not specified)
test_minimal_stack_start() {
    if [[ "$QUICK_MODE" == "true" ]]; then
        return 0
    fi
    
    # Try to start just the database and verify it starts
    timeout 30s docker compose -f supabase/docker/docker-compose.yml up -d db
    sleep 10
    docker compose -f supabase/docker/docker-compose.yml ps db | grep -q "running"
    local result=$?
    docker compose -f supabase/docker/docker-compose.yml down
    return $result
}

# Main test execution
main() {
    log "Starting comprehensive test suite"
    log "Repository: $REPO_ROOT"
    log "Quick mode: $QUICK_MODE"
    log "Verbose: $VERBOSE"
    echo
    
    # Core infrastructure tests
    info "=== Core Infrastructure Tests ==="
    run_test "Git repository" "test_git_repository"
    run_test "Docker availability" "test_docker_dependencies"
    run_test "Python dependencies" "test_python_dependencies"
    run_test "Scripts executable" "test_scripts_executable"
    
    # Configuration tests
    info "=== Configuration Tests ==="
    run_test "Environment setup" "test_environment_setup"
    run_test "Environment variables" "test_environment_variables"
    run_test "Supabase directory structure" "test_supabase_directory"
    run_test "Docker Compose configurations" "test_compose_configs"
    run_test "SearXNG configuration" "test_searxng_config"
    run_test "Traefik configuration" "test_traefik_config"
    
    # Service tests (optional for quick mode)
    if [[ "$QUICK_MODE" != "true" ]]; then
        info "=== Service Tests ==="
        run_test "Minimal stack start" "test_minimal_stack_start" "true"
    fi
    
    # Original test suite
    info "=== Original Test Suite ==="
    cd scripts/tests
    for test_script in 00_env_check.sh 01_compose_config.sh; do
        if [[ -f "$test_script" ]]; then
            run_test "Original: $test_script" "bash $test_script" "true"
        fi
    done
    cd "$REPO_ROOT"
    
    # Results summary
    echo
    log "=== Test Results Summary ==="
    echo "Tests run: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
        echo
        warn "Failed tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
    fi
    
    echo
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log "🎉 All tests passed!"
        exit 0
    elif [[ $TESTS_PASSED -gt $TESTS_FAILED ]]; then
        warn "⚠️  Most tests passed but some failed"
        exit 1
    else
        error "❌ Multiple test failures detected"
        exit 2
    fi
}

# Run main function
main "$@"