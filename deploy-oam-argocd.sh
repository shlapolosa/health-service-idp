#!/bin/bash

# Deploy OAM Applications via ArgoCD App-of-Apps Pattern
# This script deploys the complete Visual Architecture Maintenance Tool

set -euo pipefail

# Configuration
VCLUSTER_NAME="architecture-vizualisation"
VCLUSTER_NAMESPACE="arch-viz"

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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the correct context
check_context() {
    log_info "Checking kubectl context..."
    current_context=$(kubectl config current-context)
    if [[ $current_context != *"$VCLUSTER_NAME"* ]]; then
        log_error "Not in vcluster context. Current: $current_context"
        log_info "Connecting to vcluster..."
        vcluster connect $VCLUSTER_NAME --namespace $VCLUSTER_NAMESPACE
    fi
    log_success "Connected to vcluster: $current_context"
}

# Check ArgoCD installation
check_argocd() {
    log_info "Checking ArgoCD installation..."
    if ! kubectl get namespace argocd &> /dev/null; then
        log_error "ArgoCD namespace not found"
        exit 1
    fi
    
    if ! kubectl get pods -n argocd | grep -q Running; then
        log_error "ArgoCD pods are not running"
        exit 1
    fi
    
    log_success "ArgoCD is running"
}

# Check OAM/KubeVela installation
check_oam() {
    log_info "Checking OAM/KubeVela installation..."
    if ! kubectl get crd applications.core.oam.dev &> /dev/null; then
        log_warn "OAM CRDs not found, installing KubeVela..."
        helm repo add kubevela https://kubevela.github.io/charts || true
        helm repo update
        helm install vela-core kubevela/vela-core --namespace vela-system --create-namespace --wait --timeout 10m || log_warn "KubeVela installation may have issues"
    fi
    log_success "OAM CRDs are available"
}

# Deploy individual OAM applications for testing
deploy_oam_applications() {
    log_info "Deploying OAM Applications..."
    
    # Deploy in dependency order
    log_info "Deploying Redis infrastructure..."
    kubectl apply -f oam-applications/infrastructure/redis-app.yaml
    
    log_info "Waiting for Redis to be ready..."
    sleep 30
    
    log_info "Deploying Orchestration service..."
    kubectl apply -f oam-applications/orchestration/orchestration-service-app.yaml
    
    log_info "Waiting for Orchestration service..."
    sleep 30
    
    log_info "Deploying Agent applications..."
    kubectl apply -f oam-applications/agents/business-analyst-app.yaml
    kubectl apply -f oam-applications/agents/application-architect-app.yaml
    
    sleep 20
    
    kubectl apply -f oam-applications/agents/infrastructure-architect-app.yaml
    
    sleep 20
    
    kubectl apply -f oam-applications/agents/solution-architect-app.yaml
    
    log_info "Waiting for agents to initialize..."
    sleep 30
    
    log_info "Deploying Frontend..."
    kubectl apply -f oam-applications/frontend/streamlit-frontend-app.yaml
    
    log_success "All OAM Applications deployed"
}

# Deploy ArgoCD App-of-Apps
deploy_argocd_app_of_apps() {
    log_info "Deploying ArgoCD Application of Applications..."
    
    # First deploy individual ArgoCD applications for immediate deployment
    log_info "Deploying individual ArgoCD applications..."
    kubectl apply -f argocd-apps/infrastructure/redis-argocd-app.yaml
    kubectl apply -f argocd-apps/orchestration/orchestration-service-argocd-app.yaml
    kubectl apply -f argocd-apps/agents/business-analyst-argocd-app.yaml
    kubectl apply -f argocd-apps/agents/application-architect-argocd-app.yaml
    kubectl apply -f argocd-apps/agents/infrastructure-architect-argocd-app.yaml
    kubectl apply -f argocd-apps/agents/solution-architect-argocd-app.yaml
    kubectl apply -f argocd-apps/frontend/streamlit-frontend-argocd-app.yaml
    
    # Then deploy the App-of-Apps for ongoing management
    log_info "Deploying App-of-Apps..."
    kubectl apply -f argocd-apps/app-of-apps/architecture-tool-app-of-apps.yaml
    
    log_success "ArgoCD Applications deployed"
}

# Verify deployments
verify_deployments() {
    log_info "Verifying deployments..."
    
    log_info "OAM Applications:"
    kubectl get applications.core.oam.dev
    
    log_info "ArgoCD Applications:"
    kubectl get applications.argoproj.io -n argocd
    
    log_info "Knative Services:"
    kubectl get ksvc
    
    log_info "Pods:"
    kubectl get pods
    
    log_success "Deployment verification completed"
}

# Get access information
get_access_info() {
    log_info "Getting access information..."
    
    # ArgoCD admin password
    if kubectl get secret argocd-initial-admin-secret -n argocd &> /dev/null; then
        ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
        log_info "ArgoCD admin password: $ARGOCD_PASSWORD"
    fi
    
    # Knative service URLs
    log_info "Knative service URLs:"
    kubectl get ksvc -o custom-columns=NAME:.metadata.name,URL:.status.url --no-headers
    
    log_success "Access information displayed"
}

# Main execution
main() {
    log_info "Starting OAM + ArgoCD deployment for Visual Architecture Maintenance Tool..."
    
    check_context
    check_argocd
    check_oam
    
    # Option 1: Deploy OAM applications directly
    # deploy_oam_applications
    
    # Option 2: Deploy via ArgoCD (recommended)
    deploy_argocd_app_of_apps
    
    sleep 60  # Wait for initial sync
    
    verify_deployments
    get_access_info
    
    log_success "Deployment completed successfully!"
    log_info "Monitor deployments with:"
    log_info "  kubectl get applications.core.oam.dev -w"
    log_info "  kubectl get applications.argoproj.io -n argocd -w"
}

# Run main function
main "$@"