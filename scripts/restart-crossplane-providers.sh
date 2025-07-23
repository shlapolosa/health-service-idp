#!/bin/bash
# Crossplane Provider Restart Script
# 
# This script restarts Crossplane providers to resolve the "one-shot" behavior
# where providers process initial resources then go idle.
#
# Usage: ./restart-crossplane-providers.sh [provider-name]
# Examples:
#   ./restart-crossplane-providers.sh                    # Restart all providers
#   ./restart-crossplane-providers.sh kubernetes        # Restart only kubernetes provider
#   ./restart-crossplane-providers.sh github           # Restart only github provider

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to restart a specific provider
restart_provider() {
    local provider_name="$1"
    local provider_label="$2"
    
    print_status "Restarting $provider_name provider..."
    
    # Check if provider pods exist
    local pod_count=$(kubectl get pods -n crossplane-system -l "$provider_label" --no-headers 2>/dev/null | wc -l)
    
    if [ "$pod_count" -eq 0 ]; then
        print_warning "No $provider_name provider pods found with label: $provider_label"
        return 1
    fi
    
    # Delete provider pods
    kubectl delete pod -n crossplane-system -l "$provider_label"
    
    # Wait for pods to restart
    print_status "Waiting for $provider_name provider to restart..."
    local timeout=60
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        local ready_pods=$(kubectl get pods -n crossplane-system -l "$provider_label" --no-headers 2>/dev/null | grep "1/1.*Running" | wc -l)
        
        if [ "$ready_pods" -gt 0 ]; then
            print_success "$provider_name provider restarted successfully"
            kubectl get pods -n crossplane-system -l "$provider_label"
            return 0
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    
    echo ""
    print_error "$provider_name provider failed to restart within $timeout seconds"
    kubectl get pods -n crossplane-system -l "$provider_label"
    return 1
}

# Function to check provider health after restart
check_provider_health() {
    local provider_name="$1"
    local provider_label="$2"
    
    print_status "Checking $provider_name provider health..."
    
    # Get provider pod logs for any errors
    local pods=$(kubectl get pods -n crossplane-system -l "$provider_label" -o name --no-headers 2>/dev/null)
    
    for pod in $pods; do
        local pod_name=$(echo "$pod" | cut -d'/' -f2)
        print_status "Checking logs for $pod_name..."
        
        # Check for recent errors in logs
        local error_count=$(kubectl logs "$pod" -n crossplane-system --tail=50 | grep -i "error\|failed\|panic" | wc -l)
        
        if [ "$error_count" -gt 0 ]; then
            print_warning "Found $error_count potential errors in $pod_name logs"
            echo "Recent errors:"
            kubectl logs "$pod" -n crossplane-system --tail=50 | grep -i "error\|failed\|panic" | tail -5
        else
            print_success "$pod_name appears healthy"
        fi
    done
}

# Main execution
main() {
    local target_provider="$1"
    
    print_status "Crossplane Provider Restart Script"
    print_status "==================================="
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl command not found. Please install kubectl and ensure it's in your PATH."
        exit 1
    fi
    
    # Check if we can access the cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Unable to access Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if crossplane-system namespace exists
    if ! kubectl get namespace crossplane-system &> /dev/null; then
        print_error "crossplane-system namespace not found. Is Crossplane installed?"
        exit 1
    fi
    
    # Define providers to restart
    declare -A providers=(
        ["kubernetes"]="pkg.crossplane.io/provider=provider-kubernetes"
        ["github"]="pkg.crossplane.io/provider=provider-upjet-github"
        ["helm"]="pkg.crossplane.io/provider=provider-helm"
        ["aws"]="pkg.crossplane.io/provider=provider-aws"
        ["terraform"]="pkg.crossplane.io/provider=provider-terraform"
    )
    
    if [ -n "$target_provider" ]; then
        # Restart specific provider
        if [[ ${providers[$target_provider]+_} ]]; then
            restart_provider "$target_provider" "${providers[$target_provider]}"
            check_provider_health "$target_provider" "${providers[$target_provider]}"
        else
            print_error "Unknown provider: $target_provider"
            print_status "Available providers: ${!providers[*]}"
            exit 1
        fi
    else
        # Restart all providers
        print_status "Restarting all Crossplane providers..."
        
        local success_count=0
        local total_count=0
        
        for provider in "${!providers[@]}"; do
            total_count=$((total_count + 1))
            echo ""
            if restart_provider "$provider" "${providers[$provider]}"; then
                success_count=$((success_count + 1))
                check_provider_health "$provider" "${providers[$provider]}"
            fi
        done
        
        echo ""
        print_status "Restart Summary:"
        print_status "Successfully restarted: $success_count/$total_count providers"
        
        if [ "$success_count" -eq "$total_count" ]; then
            print_success "All providers restarted successfully!"
        else
            print_warning "Some providers failed to restart. Check the output above for details."
            exit 1
        fi
    fi
    
    echo ""
    print_status "Provider restart completed. Providers should now be able to process new resources."
    print_status "Note: This resolves the 'one-shot' behavior where providers go idle after initial processing."
}

# Run main function with all arguments
main "$@"