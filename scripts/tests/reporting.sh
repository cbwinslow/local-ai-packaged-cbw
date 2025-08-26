#!/usr/bin/env bash
set -eo pipefail

# Reporting utilities for test recommendations
TEST_DIR="$(dirname "$0")/.."
REPORT_ROOT="${TEST_DIR}/reports"
mkdir -p "${REPORT_ROOT}"

init_report() {
  local timestamp
  timestamp=$(date +%Y%m%dT%H%M%S)
  REPORT_DIR="${REPORT_ROOT}/${timestamp}"
  mkdir -p "${REPORT_DIR}"
  echo "${REPORT_DIR}/full_report.txt"
}

write_recommendation() {
  local report_file=$1
  local category=$2
  local message=$3
  
  {
    echo "=== ${category} ==="
    echo "TIMESTAMP: $(date --iso-8601=seconds)"
    echo "RECOMMENDATION: ${message}"
    echo
  } >> "${report_file}"
}

archive_report() {
  local report_file=$1
  gzip -9 "${report_file}"
}

# Example usage in test scripts:
# report_file=$(init_report)
# write_recommendation "${report_file}" "unit" "Check database connection"
# archive_report "${report_file}"
