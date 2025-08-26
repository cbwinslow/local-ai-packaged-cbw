#!/usr/bin/env bash
set -eo pipefail

# Load reporting functions
source "$(dirname "$0")/reporting.sh"

# Comprehensive test suite runner with diagnostic recommendations

# Master test runner with comprehensive test categories
TEST_DIR="$(dirname "$0")"
OUTPUT_DIR="${TEST_DIR}/results"
mkdir -p "${OUTPUT_DIR}"

# Dry-run mode for recommendation simulation
DRY_RUN=false
while getopts "d" opt; do
  case $opt in
    d) DRY_RUN=true ;;
    *) echo "Usage: $0 [-d]"; exit 1 ;;
  esac
done

run_tests() {
  local category=$1
  local test_script=$2
  echo "Running ${category} tests..."
  
  # Execute test and capture output
  if ! "${TEST_DIR}/${test_script}" 2>&1 | tee "${OUTPUT_DIR}/${category}_results.log"; then
    echo "[ERROR] ${category} tests failed"
    generate_recommendation "${category}"
    return 1
  fi
}

generate_recommendation() {
  local category=$1
  local recommendation=""
  
  case "${category}" in
    unit)
      recommendation="make run-unit-tests-verbose"
      ;;
    integration)
      recommendation="scripts/tests/integration/analyze_failures.sh"
      ;;
    docker)
      recommendation="docker-compose logs --tail=100"
      ;;
    deployment)
      recommendation="make redeploy && make smoke-test"
      ;;
    *)
      recommendation="check ${OUTPUT_DIR}/${category}_results.log for details"
      ;;
  esac

  # Write recommendation to report
  write_recommendation "${report_file}" "${category}" "${recommendation}"

  echo "Recommended fix action: ${recommendation}"
  if [ "${DRY_RUN}" = false ]; then
    echo "To execute recommendation run: ${recommendation}"
  else
    echo "DRY RUN: Recommendation would be '${recommendation}'"
  fi
}

main() {
  # Initialize report
  local report_file
  report_file=$(init_report)

  declare -A test_categories=(
    ["unit"]="unit/run_unit_tests.sh"
    ["integration"]="integration/run_integration_tests.sh"
    ["e2e"]="e2e/run_e2e_tests.sh"
    ["docker"]="docker/run_container_tests.sh"
    ["deployment"]="deployment/run_deployment_tests.sh"
    ["network"]="network/run_network_tests.sh"
    ["performance"]="performance/run_performance_tests.sh"
    ["diagnostic"]="diagnostic/run_diagnostic_checks.sh"
)

  for category in "${!test_categories[@]}"; do
    # Skip performance tests if `wrk` is not available (optional tooling)
    if [ "${category}" = "performance" ] && ! command -v wrk >/dev/null 2>&1; then
      echo "Skipping performance tests: 'wrk' not found"
      continue
    fi
    run_tests "${category}" "${test_categories[$category]}" || true
  done

  # Archive the report
  archive_report "${report_file}"
}

main "$@"
