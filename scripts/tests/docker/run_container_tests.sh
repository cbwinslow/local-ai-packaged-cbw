#!/usr/bin/env bash
set -eo pipefail

# Docker container test runner for service validation
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/docker"
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

# Dependency checks
check_dependencies() {
  if ! command -v docker &> /dev/null; then
    echo "Error: docker is required for container tests" >&2
    exit 1
  fi
  # Prefer local wrapper ./docker-compose (handles 'include:' feature); else
  # accept docker compose / docker-compose CLI if available.
  if [ -x "$(pwd)/docker-compose" ]; then
    DCMD="$(pwd)/docker-compose"
  elif command -v docker-compose &> /dev/null; then
    DCMD="docker-compose"
  elif command -v docker &> /dev/null; then
    DCMD="docker compose"
  else
    echo "Error: docker-compose or docker compose is required for container tests" >&2
    exit 1
  fi
}

# Check container health
check_container_health() {
  local container=$1
  if ! docker inspect --format='{{.State.Health.Status}}' "${container}" | grep -q "healthy"; then
    failures+=("${container}")
    recommendations+=("docker logs ${container} && docker inspect ${container}")
    return 1
  fi
}

# Verify inter-container communication
check_container_communication() {
  local source=$1
  local target=$2
  local port=$3
  
  if ! docker exec "${source}" nc -zv "${target}" "${port}" &> /dev/null; then
    failures+=("${source}_to_${target}_${port}")
    recommendations+=("docker exec -it ${source} sh -c 'nc -zv ${target} ${port}'")
    return 1
  fi
}

main() {
  check_dependencies
  
  echo "Starting Docker compose stack..."
  $DCMD up -d
  
  echo "Waiting for containers to initialize..."
  sleep 30
  
  # Check container health
  for container in $($DCMD ps -q); do
    name=$(docker inspect --format='{{.Name}}' "${container}" | cut -d'/' -f2)
    echo "Checking health of ${name}"
    if ! check_container_health "${container}" 2>&1 | tee "${OUTPUT_DIR}/${name}_health.log"; then
      echo "[WARNING] Container ${name} is unhealthy"
    fi
  done
  
  # Verify container communication
  check_container_communication "app" "db" "5432"  # Example communication check
 
  # Stop containers after tests
  $DCMD down

  # Process test results
  if [ ${#failures[@]} -ne 0 ]; then
    echo -e "\n[TEST SUMMARY]"
    echo "Failed checks: ${#failures[@]}"
    
    for ((i=0; i<${#failures[@]}; i++)); do
      echo -e "\n[FAILURE ${i+1}]"
      echo "Check: ${failures[i]}"
      recommendation="${recommendations[i]}"
      echo "Recommended debug action: ${recommendation}"
      
      if [ "${DRY_RUN}" = false ]; then
        echo "To debug run: ${recommendation}"
      else
        echo "DRY RUN: Recommendation would be '${recommendation}'"
      fi
    done
    
    exit 1
  fi

  echo -e "\nAll container tests passed successfully"
  exit 0
}

main "$@"
