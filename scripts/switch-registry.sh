#!/bin/bash

# Registry Switcher Script
# Easily switch between Docker Hub and Azure Container Registry

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to update registry config
update_registry_config() {
    local registry_type=$1
    local namespace=${2:-"all"}
    
    case $registry_type in
        "dockerhub"|"docker")
            ACTIVE="dockerhub"
            REGISTRY="docker.io"
            PATH="socrates12345"
            ;;
        "acr"|"azure")
            ACTIVE="acr"
            REGISTRY="healthidpuaeacr.azurecr.io"
            PATH=""
            ;;
        *)
            echo "Invalid registry type. Use 'dockerhub' or 'acr'"
            exit 1
            ;;
    esac
    
    if [ "$namespace" = "all" ]; then
        NAMESPACES="default crossplane-system"
    else
        NAMESPACES="$namespace"
    fi
    
    for ns in $NAMESPACES; do
        print_info "Updating registry config in namespace: $ns"
        
        # Check if ConfigMap exists
        if kubectl get configmap registry-config -n $ns &>/dev/null; then
            # Update existing ConfigMap
            kubectl patch configmap registry-config -n $ns --type merge -p "{\"data\":{\"ACTIVE_REGISTRY\":\"$ACTIVE\",\"DEFAULT_REGISTRY\":\"$REGISTRY\",\"DEFAULT_REGISTRY_PATH\":\"$PATH\"}}"
            print_status "Registry config updated in $ns"
        else
            print_warning "Registry config not found in $ns, creating..."
            kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-config
  namespace: $ns
data:
  DEFAULT_REGISTRY: "$REGISTRY"
  DEFAULT_REGISTRY_PATH: "$PATH"
  ACR_REGISTRY: "healthidpuaeacr.azurecr.io"
  ACR_REGISTRY_PATH: ""
  ACTIVE_REGISTRY: "$ACTIVE"
  IMAGE_PULL_POLICY: "IfNotPresent"
  ENABLE_FALLBACK: "true"
  FALLBACK_REGISTRY: "docker.io/socrates12345"
EOF
            print_status "Registry config created in $ns"
        fi
    done
}

# Function to show current registry configuration
show_current_config() {
    echo "Current Registry Configuration:"
    echo "==============================="
    
    for ns in default crossplane-system; do
        if kubectl get configmap registry-config -n $ns &>/dev/null; then
            echo ""
            echo "Namespace: $ns"
            ACTIVE=$(kubectl get configmap registry-config -n $ns -o jsonpath='{.data.ACTIVE_REGISTRY}')
            REGISTRY=$(kubectl get configmap registry-config -n $ns -o jsonpath='{.data.DEFAULT_REGISTRY}')
            PATH=$(kubectl get configmap registry-config -n $ns -o jsonpath='{.data.DEFAULT_REGISTRY_PATH}')
            
            echo "  Active Registry: $ACTIVE"
            echo "  Registry URL: $REGISTRY"
            if [ -n "$PATH" ]; then
                echo "  Registry Path: $PATH"
            fi
        else
            echo ""
            echo "Namespace: $ns"
            echo "  No registry config found"
        fi
    done
}

# Function to restart deployments to pick up new registry
restart_deployments() {
    local namespace=${1:-"default"}
    
    print_info "Restarting deployments in namespace: $namespace"
    
    # Get all deployments
    DEPLOYMENTS=$(kubectl get deployments -n $namespace -o jsonpath='{.items[*].metadata.name}')
    
    if [ -z "$DEPLOYMENTS" ]; then
        print_warning "No deployments found in $namespace"
        return
    fi
    
    for deploy in $DEPLOYMENTS; do
        kubectl rollout restart deployment/$deploy -n $namespace
        print_status "Restarted deployment: $deploy"
    done
    
    # Restart Knative services if any
    if kubectl get ksvc -n $namespace &>/dev/null; then
        KNATIVE_SERVICES=$(kubectl get ksvc -n $namespace -o jsonpath='{.items[*].metadata.name}')
        for ksvc in $KNATIVE_SERVICES; do
            # Touch the service to trigger a new revision
            kubectl annotate ksvc $ksvc -n $namespace registry-switch="$(date +%s)" --overwrite
            print_status "Updated Knative service: $ksvc"
        done
    fi
}

# Main menu
main() {
    echo "==========================================="
    echo "   Multi-Registry Configuration Tool"
    echo "==========================================="
    echo ""
    
    if [ $# -eq 0 ]; then
        show_current_config
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  switch <dockerhub|acr> [namespace]  - Switch to specified registry"
        echo "  show                                 - Show current configuration"
        echo "  restart [namespace]                  - Restart deployments to use new registry"
        echo "  validate                             - Validate registry connectivity"
        echo ""
        echo "Examples:"
        echo "  $0 switch acr                       - Switch all namespaces to ACR"
        echo "  $0 switch dockerhub default         - Switch default namespace to Docker Hub"
        echo "  $0 restart default                  - Restart deployments in default namespace"
        exit 0
    fi
    
    case $1 in
        switch)
            if [ -z "$2" ]; then
                echo "Error: Registry type required (dockerhub or acr)"
                exit 1
            fi
            update_registry_config "$2" "${3:-all}"
            echo ""
            print_status "Registry configuration updated to: $2"
            echo ""
            echo "To apply changes, run:"
            echo "  $0 restart [namespace]"
            ;;
        show)
            show_current_config
            ;;
        restart)
            restart_deployments "${2:-default}"
            ;;
        validate)
            print_info "Validating registry connectivity..."
            
            # Check Docker Hub
            if curl -s https://hub.docker.com/v2/repositories/socrates12345/ >/dev/null; then
                print_status "Docker Hub: Accessible"
            else
                print_warning "Docker Hub: Not accessible or rate limited"
            fi
            
            # Check ACR
            if curl -s https://healthidpuaeacr.azurecr.io/v2/ -o /dev/null -w "%{http_code}" | grep -q "401\|200"; then
                print_status "Azure Container Registry: Accessible"
            else
                print_warning "Azure Container Registry: Not accessible"
            fi
            ;;
        *)
            echo "Unknown command: $1"
            echo "Run '$0' without arguments for help"
            exit 1
            ;;
    esac
}

# Check kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

main "$@"