#!/usr/bin/env bash
set -eo pipefail

# Unit test runner with diagnostic recommendations and failure aggregation
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/unit"
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
declare -a test_files
declare -a failures
declare -a recommendations

# Find all unit test files (pattern: *_test.py or *.test.js)
while IFS= read -r -d $'\0' file; do
  test_files+=("$file")
done < <(find "${TEST_DIR}" -type f \( -name "*_test.py" -o -name "*.test.js" \) -print0)

# Function to run Python tests
run_python_test() {
  local file="$1"
  if ! python3 "${file}" 2>&1 | tee "${OUTPUT_DIR}/$(basename "${file}").log"; then
    failures+=("${file}")
    recommendations+=("python3 -m pytest -v ${file}")
  fi
}

# Function to run JavaScript tests
run_javascript_test() {
  local file="$1"
  if ! node "${file}" 2>&1 | tee "${OUTPUT_DIR}/$(basename "${file}").log"; then
    failures+=("${file}")
    recommendations+=("npm test -- ${file}")
  fi
}

# Execute all unit tests
for test_file in "${test_files[@]}"; do
  echo "Running unit tests in: ${test_file}"
  
  case "${test_file}" in
    *.py) run_python_test "${test_file}" ;;
    *.js) run_javascript_test "${test_file}" ;;
  esac
done

# Process test results
if [ ${#failures[@]} -ne 0 ]; then
  echo -e "\n[TEST SUMMARY]"
  echo "Failed tests: ${#failures[@]} of ${#test_files[@]}"
  
  for ((i=0; i<${#failures[@]}; i++)); do
    echo -e "\n[FAILURE ${i+1}]"
    echo "Test file: ${failures[i]}"
    recommendation="${recommendations[i]}"
    echo "Recommended fix action: ${recommendation}"
    
    if [ "${DRY_RUN}" = false ]; then
      echo "To execute recommendation: ${recommendation}"
    else
      echo "DRY RUN: Recommendation would be '${recommendation}'"
    fi
  done
  
  exit 1  # Exit with error if any tests failed
fi

echo -e "\nAll unit tests passed successfully"
exit 0
