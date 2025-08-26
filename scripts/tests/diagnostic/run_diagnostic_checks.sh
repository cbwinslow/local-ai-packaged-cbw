#!/usr/bin/env bash
set -eo pipefail

# Diagnostic test runner for system and application health checks
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/diagnostic"
mkdir -p "${OUTPUT_DIR}"

# Dry-run mode for recommendation simulation
DRY_RUN=false
while getopts "d" opt; do
  case $opt in
    d) DRY_RUN=true ;;
    *) echo "Usage: $0 [-d]" >&2; exit 1 ;;
  esac
done

# Initialize variables
declare -a failures
declare -a recommendations

# Thresholds for resource checks
DISK_CRITICAL=90  # percentage
MEM_CRITICAL=90   # percentage

# Dependency checks
check_dependencies() {
  local deps=("docker" "curl" "nc")
  for dep in "${deps[@]}"; do
    if ! command -v "${dep}" &> /dev/null; then
      echo "Error: ${dep} is required for diagnostic tests" >&2
      exit 1
    fi
  done
}

# Check disk space
check_disk_space() {
  local usage
  usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
  if (( usage > DISK_CRITICAL )); then
    failures+=("disk_space")
    recommendations+=("Check disk usage with 'df -h' and clean up unnecessary files")
  fi
}

# Check memory usage
check_memory() {
  local usage
  usage=$(free | awk '/Mem/{printf("%.0f"), $3/$2*100}')
  if (( usage > MEM_CRITICAL )); then
    failures+=("memory_usage")
    recommendations+=("Investigate memory-consuming processes with 'top' or 'htop'")
  fi
}

# Check running containers
check_containers() {
  local expected_containers=("app" "db" "cache")  # Adjust based on actual containers
  for container in "${expected_containers[@]}"; do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}\$"; then
      failures+=("container_${container}_down")
      recommendations+=("Check container logs: 'docker logs ${container}' and start if necessary")
    fi
  done
}

# Search logs for common errors
check_application_logs() {
  local log_patterns=(
    "ERROR" 
    "Exception" 
    "Connection refused" 
    "Timeout" 
    "OutOfMemory"
  )
  if [ -x "$(pwd)/docker-compose" ]; then
    "$(pwd)/docker-compose" logs --no-color > "${OUTPUT_DIR}/app_logs.log"
  else
    docker-compose logs --no-color > "${OUTPUT_DIR}/app_logs.log"
  fi
  for pattern in "${log_patterns[@]}"; do
    if grep -q "${pattern}" "${OUTPUT_DIR}/app_logs.log"; then
      failures+=("log_errors_found")
      recommendations+=("Investigate errors in logs: 'grep -i '${pattern}' ${OUTPUT_DIR}/app_logs.log'")
      break  # Stop at first major error pattern found
    fi
  done
}

main() {
  check_dependencies
  
  echo "Running diagnostic checks..."
  
  check_disk_space || true
  check_memory || true
  check_containers || true
  check_application_logs || true

  # Process test results
  if [ ${#failures[@]} -ne 0 ]; then
    echo -e "\n[DIAGNOSTIC SUMMARY]"
    echo "Issues found: ${#failures[@]}"
    
    for ((i=0; i<${#failures[@]}; i++)); do
      echo -e "\n[ISSUE ${i+1}]"
      echo "Problem: ${failures[i]}"
      recommendation="${recommendations[i]}"
      echo "Recommended action: ${recommendation}"
      
      if [ "${DRY_RUN}" = false ]; then
        echo "Command: ${recommendation}"
      else
        echo "DRY RUN: Recommendation would be '${recommendation}'"
      fi
    done
    
    exit 1
  fi

  echo -e "\nAll diagnostic checks passed successfully"
  exit 0
}

main "$@"
