#!/usr/bin/env bash
set -eo pipefail

# Performance test runner for load and stress testing
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/performance"
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

# Performance thresholds (adjust based on requirements)
MAX_AVG_RESPONSE_TIME=200  # milliseconds
MAX_P95_RESPONSE_TIME=500  # milliseconds
MAX_CPU_USAGE=80           # percentage
MAX_MEM_USAGE=70           # percentage

# Dependency checks
check_dependencies() {
  if ! command -v wrk &> /dev/null; then
    echo "Error: wrk is required for performance tests" >&2
    exit 1
  fi
  
  if ! command -v vmstat &> /dev/null; then
    echo "Error: vmstat is required for resource monitoring" >&2
    exit 1
  fi
}

# Run load test against endpoint
run_load_test() {
  local url=$1
  local threads=4
  local connections=100
  local duration=30s
  
  echo "Running load test on ${url}"
  wrk --threads "${threads}" --connections "${connections}" --duration "${duration}" \
      --latency "${url}" 2>&1 | tee "${OUTPUT_DIR}/load_test.log"
  
  # Extract metrics from wrk output
  local avg_latency
  avg_latency=$(grep "Latency" "${OUTPUT_DIR}/load_test.log" | awk '{print $2}')
  local p95_latency
  p95_latency=$(grep "99%" "${OUTPUT_DIR}/load_test.log" | awk '{print $2}')
  
  # Remove non-numeric characters
  avg_latency=${avg_latency//[a-zA-Z]/}
  p95_latency=${p95_latency//[a-zA-Z]/}
  
  # Check thresholds
  if (( $(echo "${avg_latency} > ${MAX_AVG_RESPONSE_TIME}" | bc -l | grep -q 1; echo $?) )); then
    failures+=("high_avg_latency")
    recommendations+=("Optimize endpoint ${url} response time, current average: ${avg_latency}ms")
  fi
  
  if (( $(echo "${p95_latency} > ${MAX_P95_RESPONSE_TIME}" | bc -l | grep -q 1; echo $?) )); then
    failures+=("high_p95_latency")
    recommendations+=("Investigate slow requests for ${url}, 95th percentile: ${p95_latency}ms")
  fi
}

# Monitor system resources during tests
monitor_resources() {
  echo "Starting resource monitoring..."
  vmstat 2 15 > "${OUTPUT_DIR}/vmstat.log" &
  
  # Analyze resource usage
  local max_cpu
  max_cpu=$(awk '{print $13}' "${OUTPUT_DIR}/vmstat.log" | sort -nr | head -1)
  local max_mem
  max_mem=$(awk '{print $4}' "${OUTPUT_DIR}/vmstat.log" | sort -n | head -1)
  
  if (( max_cpu > MAX_CPU_USAGE )); then
    failures+=("high_cpu_usage")
    recommendations+=("Consider scaling horizontally or optimizing CPU usage, peak: ${max_cpu}%")
  fi
  
  if (( max_mem > MAX_MEM_USAGE )); then
    failures+=("high_memory_usage")
    recommendations+=("Investigate memory leaks or scale memory resources, peak usage: ${max_mem}%")
  fi
}

main() {
  check_dependencies
  
  # Example endpoint to test (adjust based on actual application)
  local test_url="http://localhost:3000/api/v1/health"
  
  # Start resource monitoring in background
  monitor_resources &
  
  # Run performance tests
  run_load_test "${test_url}"
  
  # Wait for resource monitoring to complete
  wait
  
  # Process test results
  if [ ${#failures[@]} -ne 0 ]; then
    echo -e "\n[PERFORMANCE SUMMARY]"
    echo "Failed checks: ${#failures[@]}"
    
    for ((i=0; i<${#failures[@]}; i++)); do
      echo -e "\n[ISSUE ${i+1}]"
      echo "Problem: ${failures[i]}"
      recommendation="${recommendations[i]}"
      echo "Recommendation: ${recommendation}"
      
      if [ "${DRY_RUN}" = false ]; then
        echo "Action: ${recommendation}"
      else
        echo "DRY RUN: Recommendation would be '${recommendation}'"
      fi
    done
    
    exit 1
  fi

  echo -e "\nAll performance tests passed successfully"
  exit 0
}

main "$@"
