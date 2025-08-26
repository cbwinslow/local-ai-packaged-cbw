#!/usr/bin/env bash
set -eo pipefail

# Network test runner for connectivity and security validation
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/network"
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
  if ! command -v nc &> /dev/null; then
    echo "Error: netcat (nc) is required for network tests" >&2
    exit 1
  fi
  
  if ! command -v curl &> /dev/null; then
    echo "Error: curl is required for network tests" >&2
    exit 1
  fi
}

# Check port connectivity
test_port_connectivity() {
  local host=$1
  local port=$2
  local service=$3
  
  if ! nc -zv -w 5 "${host}" "${port}" 2>&1 | tee -a "${OUTPUT_DIR}/port_${port}.log"; then
    failures+=("port_${port}_connectivity")
    recommendations+=("Check firewall rules for port ${port} and ensure ${service} is running")
    return 1
  fi
}

# Verify HTTPS connectivity and certificate
test_https() {
  local url=$1
  
  if ! curl -sSI --retry 2 --ssl-reqd "${url}" 2>&1 | tee -a "${OUTPUT_DIR}/https.log"; then
    failures+=("https_connectivity")
    recommendations+=("Check SSL/TLS configuration for ${url}")
    return 1
  fi
}

# Measure latency between components
test_latency() {
  local target=$1
  local threshold=$2  # in milliseconds
  
  local latency
  latency=$(ping -c 4 "${target}" | tail -1 | awk '{print $4}' | cut -d '/' -f 2)
  
  if (( $(echo "${latency} > ${threshold}" | bc -l) )); then
    failures+=("high_latency_to_${target}")
    recommendations+=("Investigate network path to ${target}, current latency: ${latency}ms")
    return 1
  fi
}

main() {
  check_dependencies
  
  echo "Running network validation checks..."
  
  # Example network checks (adjust based on actual services)
  test_port_connectivity "localhost" "5432" "PostgreSQL" || true
  test_port_connectivity "localhost" "6379" "Redis" || true
  test_https "https://localhost:3000" || true
  test_latency "database.internal" "100" || true

  # Process test results
  if [ ${#failures[@]} -ne 0 ]; then
    echo -e "\n[TEST SUMMARY]"
    echo "Failed checks: ${#failures[@]}"
    
    for ((i=0; i<${#failures[@]}; i++)); do
      echo -e "\n[FAILURE ${i+1}]"
      echo "Check: ${failures[i]}"
      recommendation="${recommendations[i]}"
      echo "Recommended action: ${recommendation}"
      
      if [ "${DRY_RUN}" = false ]; then
        echo "To investigate: ${recommendation}"
      else
        echo "DRY RUN: Recommendation would be '${recommendation}'"
      fi
    done
    
    exit 1
  fi

  echo -e "\nAll network tests passed successfully"
  exit 0
}

main "$@"
