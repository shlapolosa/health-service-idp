#!/bin/bash

# Force Delete Terminating Namespaces Script
# This script handles namespaces stuck in "Terminating" status by:
# 1. Identifying root causes (finalizers, stuck resources)
# 2. Removing finalizers from resources
# 3. Force deleting namespaces
# 4. Providing detailed logging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "kubectl connection verified"
}

# Function to get terminating namespaces
get_terminating_namespaces() {
    kubectl get ns --field-selector=status.phase=Terminating --no-headers | awk '{print $1}' 2>/dev/null || true
}

# Function to analyze why namespace is stuck
analyze_namespace() {
    local namespace=$1
    log_info "Analyzing namespace: $namespace"
    
    # Check remaining resources
    echo "  Resources still present:"
    kubectl get all,secrets,configmaps,pv,pvc -n "$namespace" 2>/dev/null | sed 's/^/    /' || echo "    No resources found"
    
    # Check namespace status and conditions
    echo "  Namespace conditions:"
    kubectl get ns "$namespace" -o json 2>/dev/null | jq -r '.status.conditions[]? | "    Type: \(.type), Status: \(.status), Reason: \(.reason), Message: \(.message)"' || echo "    Could not get conditions"
    
    # Check finalizers on the namespace itself
    echo "  Namespace finalizers:"
    kubectl get ns "$namespace" -o json 2>/dev/null | jq -r '.spec.finalizers[]?' | sed 's/^/    /' || echo "    No finalizers found"
}

# Function to remove finalizers from all resources in namespace
remove_resource_finalizers() {
    local namespace=$1
    log_info "Removing finalizers from all resources in namespace: $namespace"
    
    # Remove finalizers from secrets (common Crossplane issue)
    local secrets
    secrets=$(kubectl get secrets -n "$namespace" --no-headers 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$secrets" ]]; then
        for secret in $secrets; do
            log_info "  Removing finalizers from secret: $secret"
            kubectl patch secret "$secret" -n "$namespace" --type='merge' -p='{"metadata":{"finalizers":null}}' 2>/dev/null || log_warning "  Failed to patch secret: $secret"
        done
    fi
    
    # Remove finalizers from configmaps
    local configmaps
    configmaps=$(kubectl get configmaps -n "$namespace" --no-headers 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$configmaps" ]]; then
        for cm in $configmaps; do
            log_info "  Removing finalizers from configmap: $cm"
            kubectl patch configmap "$cm" -n "$namespace" --type='merge' -p='{"metadata":{"finalizers":null}}' 2>/dev/null || log_warning "  Failed to patch configmap: $cm"
        done
    fi
    
    # Remove finalizers from PVCs (can block namespace deletion)
    local pvcs
    pvcs=$(kubectl get pvc -n "$namespace" --no-headers 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$pvcs" ]]; then
        for pvc in $pvcs; do
            log_info "  Removing finalizers from PVC: $pvc"
            kubectl patch pvc "$pvc" -n "$namespace" --type='merge' -p='{"metadata":{"finalizers":null}}' 2>/dev/null || log_warning "  Failed to patch PVC: $pvc"
        done
    fi
    
    # Force delete stuck pods
    local pods
    pods=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | awk '{print $1}' || true)
    if [[ -n "$pods" ]]; then
        for pod in $pods; do
            log_info "  Force deleting stuck pod: $pod"
            kubectl delete pod "$pod" -n "$namespace" --force --grace-period=0 2>/dev/null || log_warning "  Failed to force delete pod: $pod"
        done
    fi
}

# Function to force delete namespace
force_delete_namespace() {
    local namespace=$1
    log_info "Force deleting namespace: $namespace"
    
    # First try: Remove finalizers and let Kubernetes handle deletion
    kubectl get ns "$namespace" -o json 2>/dev/null | \
        jq '.spec.finalizers = []' | \
        kubectl replace --raw "/api/v1/namespaces/$namespace/finalize" -f - 2>/dev/null || {
            log_warning "  Standard finalize API call failed, namespace may already be deleted"
            return 0
        }
    
    # Wait a moment for deletion to process
    sleep 2
    
    # Check if namespace still exists
    if kubectl get ns "$namespace" &>/dev/null; then
        log_warning "  Namespace still exists after force delete attempt"
        return 1
    else
        log_success "  Namespace successfully deleted"
        return 0
    fi
}

# Function to wait for namespace deletion with timeout
wait_for_deletion() {
    local namespace=$1
    local timeout=${2:-30}
    local count=0
    
    log_info "Waiting for namespace deletion (timeout: ${timeout}s): $namespace"
    
    while kubectl get ns "$namespace" &>/dev/null && [ $count -lt $timeout ]; do
        echo -n "."
        sleep 1
        ((count++))
    done
    echo
    
    if kubectl get ns "$namespace" &>/dev/null; then
        log_warning "  Namespace still exists after ${timeout}s timeout"
        return 1
    else
        log_success "  Namespace deleted successfully"
        return 0
    fi
}

# Main function to process a single namespace
process_namespace() {
    local namespace=$1
    
    echo "=============================================="
    log_info "Processing terminating namespace: $namespace"
    echo "=============================================="
    
    # Step 1: Analyze the namespace
    analyze_namespace "$namespace"
    echo
    
    # Step 2: Remove finalizers from resources
    remove_resource_finalizers "$namespace"
    echo
    
    # Step 3: Force delete the namespace
    if force_delete_namespace "$namespace"; then
        log_success "Namespace processing completed: $namespace"
    else
        log_error "Failed to delete namespace: $namespace"
        return 1
    fi
    
    echo
}

# Main script execution
main() {
    echo "================================================"
    echo "Force Delete Terminating Namespaces Script"
    echo "================================================"
    echo
    
    # Check prerequisites
    check_kubectl
    echo
    
    # Get terminating namespaces
    log_info "Checking for terminating namespaces..."
    terminating_namespaces=$(get_terminating_namespaces)
    
    if [[ -z "$terminating_namespaces" ]]; then
        log_success "No namespaces found in Terminating status"
        exit 0
    fi
    
    # Show found namespaces
    log_warning "Found terminating namespaces:"
    echo "$terminating_namespaces" | sed 's/^/  /'
    echo
    
    # Process each namespace
    failed_namespaces=()
    for namespace in $terminating_namespaces; do
        if ! process_namespace "$namespace"; then
            failed_namespaces+=("$namespace")
        fi
    done
    
    # Final summary
    echo "================================================"
    echo "SUMMARY"
    echo "================================================"
    
    final_terminating=$(get_terminating_namespaces)
    if [[ -z "$final_terminating" ]]; then
        log_success "All terminating namespaces have been successfully deleted"
    else
        log_error "Some namespaces are still in terminating status:"
        echo "$final_terminating" | sed 's/^/  /'
        
        echo
        log_info "For persistent namespaces, consider:"
        echo "  1. Check for admission controllers blocking deletion"
        echo "  2. Verify no custom finalizers from operators"
        echo "  3. Check for stuck persistent volumes"
        echo "  4. Review cluster-wide resources referencing the namespace"
    fi
    
    if [[ ${#failed_namespaces[@]} -gt 0 ]]; then
        log_error "Failed to process: ${failed_namespaces[*]}"
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
Force Delete Terminating Namespaces Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help      Show this help message
    -d, --dry-run   Show what would be done without making changes
    -v, --verbose   Enable verbose output
    -n, --namespace NAMESPACE   Process only specific namespace

EXAMPLES:
    $0                          # Process all terminating namespaces
    $0 -n my-stuck-namespace   # Process only 'my-stuck-namespace'
    $0 --dry-run               # Show what would be done
    $0 -v                      # Verbose output

DESCRIPTION:
    This script identifies and force-deletes Kubernetes namespaces stuck in 
    'Terminating' status. It handles common causes including:
    
    - Crossplane finalizers on secrets/configmaps
    - Stuck pods preventing namespace deletion
    - PVC finalizers blocking cleanup
    - Namespace finalizers
    
    The script safely removes finalizers and uses the Kubernetes finalize API
    to force namespace deletion.

EOF
}

# Parse command line arguments
DRY_RUN=false
VERBOSE=false
SPECIFIC_NAMESPACE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--namespace)
            SPECIFIC_NAMESPACE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Handle dry-run mode
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "DRY RUN MODE - No changes will be made"
    terminating_namespaces=$(get_terminating_namespaces)
    if [[ -z "$terminating_namespaces" ]]; then
        log_success "No namespaces found in Terminating status"
    else
        log_info "Would process these terminating namespaces:"
        echo "$terminating_namespaces" | sed 's/^/  /'
    fi
    exit 0
fi

# Handle specific namespace mode
if [[ -n "$SPECIFIC_NAMESPACE" ]]; then
    if kubectl get ns "$SPECIFIC_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null | grep -q "Terminating"; then
        process_namespace "$SPECIFIC_NAMESPACE"
    else
        log_error "Namespace '$SPECIFIC_NAMESPACE' is not in Terminating status"
        exit 1
    fi
    exit 0
fi

# Run main function
main "$@"