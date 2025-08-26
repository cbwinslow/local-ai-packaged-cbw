#!/usr/bin/env bash
set -eo pipefail

# Deployment test runner for infrastructure validation
TEST_DIR="$(dirname "$0")/.."
OUTPUT_DIR="${TEST_DIR}/results/deployment"
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
  if ! command -v terraform &> /dev/null; then
    echo "Error: terraform is required for deployment tests" >&2
    exit 1
  fi
  
  if ! command -v ansible &> /dev/null; then
    echo "Error: ansible is required for deployment tests" >&2
    exit 1
  fi
}

# Validate Terraform configuration
validate_terraform() {
  if ! terraform validate 2>&1 | tee "${OUTPUT_DIR}/terraform_validate.log"; then
    failures+=("terraform_validate")
    recommendations+=("terraform init && terraform validate")
    return 1
  fi
}

# Check Ansible playbook syntax
validate_ansible() {
  if ! ansible-playbook --syntax-check deployment/setup.yml 2>&1 | tee "${OUTPUT_DIR}/ansible_syntax.log"; then
    failures+=("ansible_syntax")
    recommendations+=("ansible-lint deployment/setup.yml")
    return 1
  fi
}

# Verify deployment scripts
check_deployment_scripts() {
  local script_path="scripts/deploy_hetzner.sh"
  
  if ! bash -n "${script_path}" 2>&1 | tee "${OUTPUT_DIR}/script_validation.log"; then
    failures+=("deployment_script")
    recommendations+=("shellcheck ${script_path}")
    return 1
  fi
}

main() {
  check_dependencies
  
  echo "Running deployment validation checks..."
  
  validate_terraform || true
  validate_ansible || true
  check_deployment_scripts || true

  # Process test results
  if [ ${#failures[@]} -ne 0 ]; then
    echo -e "\n[TEST SUMMARY]"
    echo "Failed checks: ${#failures[@]}"
    
    for ((i=0; i<${#failures[@]}; i++)); do
      echo -e "\n[FAILURE ${i+1}]"
      echo "Check: ${failures[i]}"
      recommendation="${recommendations[i]}"
      echo "Recommended fix action: ${recommendation}"
      
      if [ "${DRY_RUN}" = false ]; then
        echo "To execute recommendation: ${recommendation}"
      else
        echo "DRY RUN: Recommendation would be '${recommendation}'"
      fi
    done
    
    exit 1
  fi

  echo -e "\nAll deployment tests passed successfully"
  exit 0
}

main "$@"
