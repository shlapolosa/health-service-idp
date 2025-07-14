#!/bin/bash

# Parameter Contract Documentation Generator
# Generates comprehensive documentation for Argo Workflow templates

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/docs/parameter-contracts"

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
Parameter Contract Documentation Generator

USAGE:
    $0 [OPTIONS] <template-file.yaml>

OPTIONS:
    -h, --help              Show this help message
    -o, --output-dir DIR    Output directory for documentation (default: $OUTPUT_DIR)
    -f, --format FORMAT     Output format: markdown, json, yaml (default: markdown)
    -a, --all               Generate documentation for all templates in argo-workflows/
    --include-examples      Include usage examples in documentation

EXAMPLES:
    $0 argo-workflows/vcluster-standard-contract.yaml
    $0 --format json --output-dir /tmp/docs argo-workflows/*.yaml
    $0 --all --include-examples

DESCRIPTION:
    Generates comprehensive documentation for Argo Workflow templates based on
    the Standardized Parameter Contract. Documentation includes:
    
    - Parameter specifications by tier
    - Usage examples
    - Template metadata
    - Validation rules
    - Cross-references
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

# Documentation generation functions
extract_template_metadata() {
    local template_file="$1"
    
    # Extract metadata
    local name
    name=$(yq eval '.metadata.name' "$template_file")
    
    local description
    description=$(yq eval '.metadata.annotations.description' "$template_file" 2>/dev/null || echo "No description available")
    
    local resource_type
    resource_type=$(yq eval '.metadata.labels."resource-type"' "$template_file" 2>/dev/null || echo "unknown")
    
    local contract_version
    contract_version=$(yq eval '.metadata.labels."parameter-contract-version"' "$template_file" 2>/dev/null || echo "unknown")
    
    local supported_tiers
    supported_tiers=$(yq eval '.metadata.annotations."supported-tiers"' "$template_file" 2>/dev/null || echo "unknown")
    
    local maintainer
    maintainer=$(yq eval '.metadata.annotations.maintainer' "$template_file" 2>/dev/null || echo "platform-team")
    
    echo "name=$name"
    echo "description=$description"
    echo "resource_type=$resource_type"
    echo "contract_version=$contract_version"
    echo "supported_tiers=$supported_tiers"
    echo "maintainer=$maintainer"
}

extract_parameters_by_tier() {
    local template_file="$1"
    local tier="$2"
    
    # Define tier patterns
    local tier1_params="resource-name|resource-type|namespace|user|description|github-org|docker-registry|slack-channel|slack-user-id"
    local tier2_params="security-enabled|observability-enabled|backup-enabled|environment-tier|auto-create-dependencies|resource-size"
    local tier3_params="microservice-.*|vcluster-.*|database-.*|cache-.*"
    local tier4_params="target-.*|parent-.*|custom-.*|feature-flags|workflow-mode|dry-run|force-.*"
    
    local pattern
    case "$tier" in
        1) pattern="^($tier1_params)$" ;;
        2) pattern="^($tier2_params)$" ;;
        3) pattern="^($tier3_params)$" ;;
        4) pattern="^($tier4_params)$" ;;
        *) pattern=".*" ;;
    esac
    
    # Extract parameters from arguments section (standalone templates)
    yq eval '.spec.arguments.parameters[]? | [.name, (.value // ""), (.default // ""), (.description // "")] | @tsv' "$template_file" 2>/dev/null | \
    while IFS=$'\t' read -r name value default description; do
        if [[ "$name" =~ $pattern ]]; then
            echo "ARGUMENT|$name|$value|$default|$description"
        fi
    done
    
    # Extract parameters from template inputs
    yq eval '.spec.templates[]? | .name as $template_name | .inputs.parameters[]? | [$template_name, .name, (.default // ""), (.description // "")] | @tsv' "$template_file" 2>/dev/null | \
    while IFS=$'\t' read -r template_name name default description; do
        if [[ "$name" =~ $pattern ]]; then
            echo "INPUT|$template_name|$name|$default|$description"
        fi
    done
}

generate_markdown_docs() {
    local template_file="$1"
    local output_file="$2"
    
    log_info "Generating Markdown documentation for: $(basename "$template_file")"
    
    # Extract metadata
    local metadata
    metadata=$(extract_template_metadata "$template_file")
    
    local name description resource_type contract_version supported_tiers maintainer
    eval "$metadata"
    
    # Start Markdown generation
    cat > "$output_file" <<EOF
# $name

**Resource Type:** $resource_type  
**Parameter Contract Version:** $contract_version  
**Supported Tiers:** $supported_tiers  
**Maintainer:** $maintainer  

## Description

$description

## Parameter Contract Compliance

This template is compliant with Parameter Contract **$contract_version** and supports parameter tiers: **$supported_tiers**.

EOF
    
    # Generate parameter documentation by tier
    for tier in 1 2 3 4; do
        local tier_params
        tier_params=$(extract_parameters_by_tier "$template_file" "$tier")
        
        if [[ -n "$tier_params" ]]; then
            case "$tier" in
                1) echo "## Tier 1: Universal Parameters (Required)" >> "$output_file" ;;
                2) echo "## Tier 2: Platform Parameters (Common)" >> "$output_file" ;;
                3) echo "## Tier 3: Context-Specific Parameters" >> "$output_file" ;;
                4) echo "## Tier 4: Advanced Parameters" >> "$output_file" ;;
            esac
            
            echo "" >> "$output_file"
            echo "| Parameter | Default | Description | Context |" >> "$output_file"
            echo "|-----------|---------|-------------|---------|" >> "$output_file"
            
            echo "$tier_params" | while IFS='|' read -r type template_name param_name default description; do
                if [[ "$type" == "ARGUMENT" ]]; then
                    context="Workflow Arguments"
                    default_value="$default"
                else
                    context="Template: $template_name"
                    default_value="$default"
                fi
                
                # Clean up values for table
                param_name=${param_name//|/}
                default_value=${default_value//|/}
                description=${description//|/}
                
                if [[ -z "$description" ]]; then
                    description="*No description provided*"
                fi
                
                if [[ -z "$default_value" ]]; then
                    default_value="*Required*"
                fi
                
                echo "| \`$param_name\` | \`$default_value\` | $description | $context |" >> "$output_file"
            done
            
            echo "" >> "$output_file"
        fi
    done
    
    # Add usage examples if requested
    if [[ "${INCLUDE_EXAMPLES:-false}" == "true" ]]; then
        cat >> "$output_file" <<EOF

## Usage Examples

### Standalone Usage

\`\`\`yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: $name-
  namespace: argo
spec:
  workflowTemplateRef:
    name: $name
  arguments:
    parameters:
    - name: resource-name
      value: "my-$resource_type"
    - name: namespace
      value: "default"
    - name: user
      value: "developer"
    # Add other required parameters...
\`\`\`

### Template Reference Usage

\`\`\`yaml
steps:
- - name: create-$resource_type
    templateRef:
      name: $name
      template: create-$resource_type
    arguments:
      parameters:
      - name: resource-name
        value: "{{workflow.parameters.resource-name}}"
      - name: namespace
        value: "{{workflow.parameters.namespace}}"
      # Add other required parameters...
\`\`\`

EOF
    fi
    
    # Add template structure
    cat >> "$output_file" <<EOF

## Template Structure

\`\`\`yaml
$(yq eval '.spec.templates[].name' "$template_file" | sed 's/^/- /')
\`\`\`

## Validation

This template includes built-in parameter validation for:

- Parameter naming conventions
- Required parameter presence
- Value format validation
- Resource type compliance

## Related Templates

EOF
    
    # Find related templates
    local related_templates
    related_templates=$(find "$PROJECT_ROOT/argo-workflows" -name "*$resource_type*.yaml" -not -path "*/$name.yaml" | sort)
    
    if [[ -n "$related_templates" ]]; then
        echo "$related_templates" | while read -r related_file; do
            local related_name
            related_name=$(yq eval '.metadata.name' "$related_file" 2>/dev/null || echo "$(basename "$related_file" .yaml)")
            echo "- [$related_name](./$related_name.md)" >> "$output_file"
        done
    else
        echo "*No related templates found*" >> "$output_file"
    fi
    
    # Add footer
    cat >> "$output_file" <<EOF

---

**Generated by:** Parameter Contract Documentation Generator  
**Generated at:** $(date -u +%Y-%m-%dT%H:%M:%SZ)  
**Template file:** $template_file  
EOF
    
    log_success "Documentation generated: $output_file"
}

generate_json_docs() {
    local template_file="$1"
    local output_file="$2"
    
    log_info "Generating JSON documentation for: $(basename "$template_file")"
    
    # Extract metadata
    local metadata
    metadata=$(extract_template_metadata "$template_file")
    
    local name description resource_type contract_version supported_tiers maintainer
    eval "$metadata"
    
    # Generate JSON structure
    cat > "$output_file" <<EOF
{
  "metadata": {
    "name": "$name",
    "description": "$description",
    "resourceType": "$resource_type",
    "contractVersion": "$contract_version",
    "supportedTiers": "$supported_tiers",
    "maintainer": "$maintainer",
    "generatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "templateFile": "$template_file"
  },
  "parameters": {
EOF
    
    # Add parameters by tier
    local first_tier=true
    for tier in 1 2 3 4; do
        local tier_params
        tier_params=$(extract_parameters_by_tier "$template_file" "$tier")
        
        if [[ -n "$tier_params" ]]; then
            if [[ "$first_tier" == "false" ]]; then
                echo "    }," >> "$output_file"
            fi
            first_tier=false
            
            echo "    \"tier$tier\": {" >> "$output_file"
            
            local first_param=true
            echo "$tier_params" | while IFS='|' read -r type template_name param_name default description; do
                if [[ "$first_param" == "false" ]]; then
                    echo "," >> "$output_file"
                fi
                first_param=false
                
                # Clean up JSON values
                param_name=${param_name//\"/\\\"}
                default=${default//\"/\\\"}
                description=${description//\"/\\\"}
                
                cat >> "$output_file" <<EOF
      "$param_name": {
        "default": "$default",
        "description": "$description",
        "context": "$type:$template_name"
      }
EOF
            done
        fi
    done
    
    if [[ "$first_tier" == "false" ]]; then
        echo "    }" >> "$output_file"
    fi
    
    cat >> "$output_file" <<EOF
  }
}
EOF
    
    # Validate JSON
    if jq empty "$output_file" 2>/dev/null; then
        log_success "JSON documentation generated: $output_file"
    else
        log_error "Generated invalid JSON: $output_file"
        return 1
    fi
}

# Main documentation generation function
generate_docs() {
    local template_file="$1"
    local format="${FORMAT:-markdown}"
    
    # Validate template file
    if [[ ! -f "$template_file" ]]; then
        log_error "Template file does not exist: $template_file"
        return 1
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Determine output filename
    local base_name
    base_name=$(basename "$template_file" .yaml)
    
    local output_file
    case "$format" in
        markdown)
            output_file="$OUTPUT_DIR/$base_name.md"
            generate_markdown_docs "$template_file" "$output_file"
            ;;
        json)
            output_file="$OUTPUT_DIR/$base_name.json"
            generate_json_docs "$template_file" "$output_file"
            ;;
        yaml)
            output_file="$OUTPUT_DIR/$base_name.yml"
            # YAML format would be similar to JSON but in YAML syntax
            log_warning "YAML format not yet implemented, using JSON"
            output_file="$OUTPUT_DIR/$base_name.json"
            generate_json_docs "$template_file" "$output_file"
            ;;
        *)
            log_error "Unsupported format: $format"
            return 1
            ;;
    esac
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
            -o|--output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -f|--format)
                FORMAT="$2"
                shift 2
                ;;
            -a|--all)
                template_files=("$PROJECT_ROOT"/argo-workflows/*-standard-contract.yaml)
                shift
                ;;
            --include-examples)
                INCLUDE_EXAMPLES=true
                shift
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
    
    # Check dependencies
    if ! command -v yq &> /dev/null; then
        log_error "yq is required but not installed"
        exit 2
    fi
    
    if [[ "${FORMAT:-markdown}" == "json" ]] && ! command -v jq &> /dev/null; then
        log_error "jq is required for JSON format but not installed"
        exit 2
    fi
    
    # Validate input
    if [[ ${#template_files[@]} -eq 0 ]]; then
        log_error "No template files specified. Use -a for all templates or specify files."
        usage
        exit 2
    fi
    
    # Generate documentation for each template
    local total_files=0
    local successful_files=0
    
    for template_file in "${template_files[@]}"; do
        # Handle glob patterns
        for file in $template_file; do
            if [[ -f "$file" ]]; then
                ((total_files++))
                
                if generate_docs "$file"; then
                    ((successful_files++))
                fi
            fi
        done
    done
    
    # Summary
    echo
    log_info "=== Documentation Generation Summary ==="
    echo "Total files processed: $total_files"
    echo "Successful generations: $successful_files"
    echo "Output directory: $OUTPUT_DIR"
    echo "Format: ${FORMAT:-markdown}"
    
    if [[ "$successful_files" -eq "$total_files" ]]; then
        log_success "All documentation generated successfully!"
    else
        log_warning "Some files failed to generate documentation"
    fi
}

# Run main function
main "$@"