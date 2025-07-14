#!/bin/bash

# Parameter Contract Validation Tool
# Validates Argo Workflow templates for parameter contract compliance

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTRACT_VERSION="v1.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Usage function
usage() {
    cat <<EOF
Parameter Contract Validation Tool

USAGE:
    $0 [OPTIONS] <template-file.yaml>

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -s, --strict            Enable strict validation mode
    -c, --contract-version  Specify parameter contract version (default: $CONTRACT_VERSION)

EXAMPLES:
    $0 argo-workflows/vcluster-standard-contract.yaml
    $0 --verbose --strict argo-workflows/microservice-standard-contract.yaml
    $0 argo-workflows/*.yaml

DESCRIPTION:
    Validates Argo Workflow templates for compliance with the Standardized Parameter Contract.
    
    Validation includes:
    - Parameter contract version compatibility
    - Required tier 1 (universal) parameters
    - Parameter naming conventions
    - Template metadata compliance
    - Input parameter validation structure
    
    Exit codes:
    0 - All validations passed
    1 - Validation failures found
    2 - Script error or invalid usage
EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
    fi
}

# Validation functions
validate_template_metadata() {
    local template_file="$1"
    local violations=0
    
    log_debug "Validating template metadata for: $template_file"
    
    # Check parameter-contract-version label
    if ! yq eval '.metadata.labels."parameter-contract-version"' "$template_file" | grep -q "$CONTRACT_VERSION"; then
        log_error "Missing or incorrect parameter-contract-version label"
        ((violations++))
    fi
    
    # Check resource-type label
    if ! yq eval '.metadata.labels."resource-type"' "$template_file" | grep -qE '^(microservice|appcontainer|vcluster|database|cache|notification)$'; then
        log_error "Missing or invalid resource-type label"
        ((violations++))
    fi
    
    # Check parameter-contract annotation
    if ! yq eval '.metadata.annotations."parameter-contract"' "$template_file" | grep -q "compliant"; then
        log_error "Missing parameter-contract: compliant annotation"
        ((violations++))
    fi
    
    # Check supported-tiers annotation
    if ! yq eval '.metadata.annotations."supported-tiers"' "$template_file" | grep -qE '^[1-4,]+$'; then
        log_error "Missing or invalid supported-tiers annotation"
        ((violations++))
    fi
    
    return $violations
}

validate_universal_parameters() {
    local template_file="$1"
    local violations=0
    
    log_debug "Validating universal (Tier 1) parameters for: $template_file"
    
    # Required Tier 1 parameters
    local required_params=(
        "resource-name"
        "resource-type" 
        "namespace"
        "user"
        "description"
        "github-org"
        "docker-registry"
        "slack-channel"
        "slack-user-id"
    )
    
    # Check if template has entrypoint (standalone template)
    local has_entrypoint
    has_entrypoint=$(yq eval '.spec.entrypoint' "$template_file")
    
    if [[ "$has_entrypoint" != "null" ]]; then
        log_debug "Validating standalone template arguments"
        
        # Check arguments section for standalone templates
        for param in "${required_params[@]}"; do
            if ! yq eval ".spec.arguments.parameters[] | select(.name == \"$param\")" "$template_file" | grep -q "name: $param"; then
                log_error "Missing required Tier 1 parameter in arguments: $param"
                ((violations++))
            fi
        done
    fi
    
    # Check main template inputs
    local main_template_count
    main_template_count=$(yq eval '.spec.templates | length' "$template_file")
    
    if [[ "$main_template_count" -gt 0 ]]; then
        # Find templates that should have Tier 1 parameters
        local template_names
        template_names=$(yq eval '.spec.templates[].name' "$template_file")
        
        while IFS= read -r template_name; do
            if [[ "$template_name" =~ ^(create-|validate-|main-|ensure-) ]]; then
                log_debug "Checking Tier 1 parameters in template: $template_name"
                
                for param in "${required_params[@]}"; do
                    local param_exists
                    param_exists=$(yq eval ".spec.templates[] | select(.name == \"$template_name\") | .inputs.parameters[]? | select(.name == \"$param\") | .name" "$template_file")
                    
                    if [[ -z "$param_exists" && "${STRICT:-false}" == "true" ]]; then
                        log_warning "Template '$template_name' missing Tier 1 parameter: $param"
                        # Don't increment violations for warnings in strict mode
                    fi
                done
            fi
        done <<< "$template_names"
    fi
    
    return $violations
}

validate_parameter_naming() {
    local template_file="$1"
    local violations=0
    
    log_debug "Validating parameter naming conventions for: $template_file"
    
    # Get all parameter names from the template
    local param_names
    param_names=$(yq eval '.spec.templates[].inputs.parameters[]?.name, .spec.arguments.parameters[]?.name' "$template_file" 2>/dev/null | sort -u)
    
    while IFS= read -r param_name; do
        if [[ -n "$param_name" && "$param_name" != "null" ]]; then
            # Check parameter naming convention (lowercase, hyphens, no underscores)
            if [[ ! "$param_name" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]]; then
                log_error "Invalid parameter name format: '$param_name' (must be lowercase with hyphens)"
                ((violations++))
            fi
            
            # Check for discouraged patterns
            if [[ "$param_name" =~ _+ ]]; then
                log_error "Parameter name contains underscores: '$param_name' (use hyphens instead)"
                ((violations++))
            fi
            
            # Check for tier compliance
            case "$param_name" in
                resource-name|resource-type|namespace|user|description|github-org|docker-registry|slack-channel|slack-user-id)
                    log_debug "✅ Tier 1 parameter: $param_name"
                    ;;
                security-enabled|observability-enabled|backup-enabled|environment-tier|auto-create-dependencies|resource-size)
                    log_debug "✅ Tier 2 parameter: $param_name"
                    ;;
                microservice-*|vcluster-*|database-*|cache-*)
                    log_debug "✅ Tier 3 parameter: $param_name"
                    ;;
                target-*|parent-*|custom-*|feature-flags|workflow-mode|dry-run|force-*)
                    log_debug "✅ Tier 4 parameter: $param_name"
                    ;;
                *)
                    if [[ "${STRICT:-false}" == "true" ]]; then
                        log_warning "Non-standard parameter name: '$param_name' (consider standardizing)"
                    fi
                    ;;
            esac
        fi
    done <<< "$param_names"
    
    return $violations
}

validate_template_structure() {
    local template_file="$1"
    local violations=0
    
    log_debug "Validating template structure for: $template_file"
    
    # Check if file is valid YAML
    if ! yq eval '.' "$template_file" >/dev/null 2>&1; then
        log_error "Invalid YAML syntax"
        ((violations++))
        return $violations
    fi
    
    # Check if it's an Argo WorkflowTemplate
    local kind
    kind=$(yq eval '.kind' "$template_file")
    if [[ "$kind" != "WorkflowTemplate" ]]; then
        log_error "Not a WorkflowTemplate (kind: $kind)"
        ((violations++))
    fi
    
    # Check API version
    local api_version
    api_version=$(yq eval '.apiVersion' "$template_file")
    if [[ "$api_version" != "argoproj.io/v1alpha1" ]]; then
        log_error "Invalid API version: $api_version"
        ((violations++))
    fi
    
    # Check required metadata
    local name
    name=$(yq eval '.metadata.name' "$template_file")
    if [[ -z "$name" || "$name" == "null" ]]; then
        log_error "Missing metadata.name"
        ((violations++))
    fi
    
    # Check namespace
    local namespace
    namespace=$(yq eval '.metadata.namespace' "$template_file")
    if [[ "$namespace" != "argo" ]]; then
        log_warning "Template namespace is not 'argo': $namespace"
    fi
    
    return $violations
}

generate_compliance_report() {
    local template_file="$1"
    local total_violations="$2"
    
    echo
    log_info "=== Parameter Contract Compliance Report ==="
    echo "Template: $template_file"
    echo "Contract Version: $CONTRACT_VERSION"
    echo "Validation Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    
    # Extract metadata
    local resource_type
    resource_type=$(yq eval '.metadata.labels."resource-type"' "$template_file" 2>/dev/null || echo "unknown")
    
    local supported_tiers
    supported_tiers=$(yq eval '.metadata.annotations."supported-tiers"' "$template_file" 2>/dev/null || echo "unknown")
    
    echo "Resource Type: $resource_type"
    echo "Supported Tiers: $supported_tiers"
    echo
    
    if [[ "$total_violations" -eq 0 ]]; then
        log_success "✅ COMPLIANT - All validations passed"
        echo "This template is fully compliant with Parameter Contract $CONTRACT_VERSION"
    else
        log_error "❌ NON-COMPLIANT - $total_violations violation(s) found"
        echo "Please address the violations above to achieve compliance"
    fi
    
    echo
}

# Main validation function
validate_template() {
    local template_file="$1"
    local total_violations=0
    
    log_info "Validating template: $template_file"
    
    # Check if file exists
    if [[ ! -f "$template_file" ]]; then
        log_error "File does not exist: $template_file"
        return 2
    fi
    
    # Run all validations
    validate_template_structure "$template_file"
    total_violations=$((total_violations + $?))
    
    validate_template_metadata "$template_file" 
    total_violations=$((total_violations + $?))
    
    validate_universal_parameters "$template_file"
    total_violations=$((total_violations + $?))
    
    validate_parameter_naming "$template_file"
    total_violations=$((total_violations + $?))
    
    # Generate report
    generate_compliance_report "$template_file" "$total_violations"
    
    return $total_violations
}

# Main script logic
main() {
    local template_files=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -s|--strict)
                STRICT=true
                shift
                ;;
            -c|--contract-version)
                CONTRACT_VERSION="$2"
                shift 2
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 2
                ;;
            *)
                template_files+=("$1")
                shift
                ;;
        esac
    done
    
    # Check if yq is installed
    if ! command -v yq &> /dev/null; then
        log_error "yq is required but not installed. Please install yq to use this tool."
        exit 2
    fi
    
    # Validate input files
    if [[ ${#template_files[@]} -eq 0 ]]; then
        log_error "No template files specified"
        usage
        exit 2
    fi
    
    # Process each template file
    local overall_exit_code=0
    local total_files=0
    local compliant_files=0
    
    for template_file in "${template_files[@]}"; do
        # Handle glob patterns
        for file in $template_file; do
            if [[ -f "$file" ]]; then
                ((total_files++))
                
                if validate_template "$file"; then
                    ((compliant_files++))
                else
                    overall_exit_code=1
                fi
                
                echo "----------------------------------------"
            fi
        done
    done
    
    # Final summary
    echo
    log_info "=== Validation Summary ==="
    echo "Total files validated: $total_files"
    echo "Compliant files: $compliant_files"
    echo "Non-compliant files: $((total_files - compliant_files))"
    
    if [[ "$overall_exit_code" -eq 0 ]]; then
        log_success "All templates are parameter contract compliant!"
    else
        log_error "Some templates have compliance violations"
    fi
    
    exit $overall_exit_code
}

# Run main function with all arguments
main "$@"