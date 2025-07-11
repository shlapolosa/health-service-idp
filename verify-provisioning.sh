#!/bin/bash

# Verify VCluster and AppContainer Provisioning
# Checks actual Kubernetes resources and status

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

VCLUSTER_NAME="test-production"
NAMESPACE="production-test"
APP_NAME="test-app-prod"

echo "🔍 VERIFYING VCLUSTER + APPCONTAINER PROVISIONING"
echo "================================================"
echo ""

# Check kubectl access
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl to verify resources."
    exit 1
fi

# Test cluster connection
log_info "Testing cluster connection..."
if ! kubectl cluster-info --request-timeout=10s &>/dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    echo "   Make sure you're connected to the right cluster context"
    echo "   Current context: $(kubectl config current-context 2>/dev/null || echo 'none')"
    exit 1
fi
log_success "✅ Connected to cluster"

# Check namespace
log_info "Checking namespace '$NAMESPACE'..."
if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_success "✅ Namespace exists"
    
    # Show namespace labels
    LABELS=$(kubectl get namespace "$NAMESPACE" -o jsonpath='{.metadata.labels}' 2>/dev/null || echo '{}')
    echo "   Labels: $LABELS"
else
    log_error "❌ Namespace '$NAMESPACE' not found"
    echo ""
    echo "Available namespaces:"
    kubectl get namespaces
    exit 1
fi

# Check VClusterEnvironmentClaim
echo ""
log_info "Checking VClusterEnvironmentClaim '$VCLUSTER_NAME'..."
if kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" &>/dev/null; then
    log_success "✅ VClusterEnvironmentClaim exists"
    
    # Get detailed status
    echo ""
    echo "📊 VCluster Status:"
    kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" -o yaml | grep -A 20 "status:" || echo "No status available"
    
    # Check readiness condition
    READY_STATUS=$(kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
    READY_REASON=$(kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null || echo "Unknown")
    
    echo ""
    if [[ "$READY_STATUS" == "True" ]]; then
        log_success "✅ VCluster is READY"
    elif [[ "$READY_STATUS" == "False" ]]; then
        log_error "❌ VCluster is NOT READY - Reason: $READY_REASON"
    else
        log_warning "⚠️ VCluster readiness: $READY_STATUS - Reason: $READY_REASON"
    fi
else
    log_error "❌ VClusterEnvironmentClaim '$VCLUSTER_NAME' not found"
    
    echo ""
    echo "Available VClusterEnvironmentClaims in namespace '$NAMESPACE':"
    kubectl get vclusterenvironmentclaim -n "$NAMESPACE" 2>/dev/null || echo "None found"
fi

# Check AppContainerClaim
echo ""
log_info "Checking AppContainerClaim '$APP_NAME'..."
if kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" &>/dev/null; then
    log_success "✅ AppContainerClaim exists"
    
    # Get detailed status
    echo ""
    echo "📊 AppContainer Status:"
    kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" -o yaml | grep -A 20 "status:" || echo "No status available"
    
    # Check readiness condition
    APP_READY_STATUS=$(kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
    APP_READY_REASON=$(kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null || echo "Unknown")
    
    echo ""
    if [[ "$APP_READY_STATUS" == "True" ]]; then
        log_success "✅ AppContainer is READY"
    elif [[ "$APP_READY_STATUS" == "False" ]]; then
        log_error "❌ AppContainer is NOT READY - Reason: $APP_READY_REASON"
    else
        log_warning "⚠️ AppContainer readiness: $APP_READY_STATUS - Reason: $APP_READY_REASON"
    fi
else
    log_error "❌ AppContainerClaim '$APP_NAME' not found"
    
    echo ""
    echo "Available AppContainerClaims in namespace '$NAMESPACE':"
    kubectl get appcontainerclaim -n "$NAMESPACE" 2>/dev/null || echo "None found"
fi

# Check related resources
echo ""
log_info "Checking related resources in namespace '$NAMESPACE'..."

echo ""
echo "🔍 All resources in namespace:"
kubectl get all -n "$NAMESPACE" 2>/dev/null || echo "No standard resources found"

echo ""
echo "🔍 Custom resources:"
kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get --show-kind --ignore-not-found -n "$NAMESPACE" 2>/dev/null || true

# Summary
echo ""
echo "📋 VERIFICATION SUMMARY"
echo "======================"

# Goal check
VCLUSTER_EXISTS=$(kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" &>/dev/null && echo "true" || echo "false")
VCLUSTER_READY=$(kubectl get vclusterenvironmentclaim "$VCLUSTER_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")

APPCONTAINER_EXISTS=$(kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" &>/dev/null && echo "true" || echo "false")
APPCONTAINER_READY=$(kubectl get appcontainerclaim "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")

echo ""
echo "🎯 GOAL STATUS:"

if [[ "$VCLUSTER_EXISTS" == "true" ]] && [[ "$VCLUSTER_READY" == "True" ]]; then
    log_success "✅ GOAL 1: VCluster successfully provisioned"
elif [[ "$VCLUSTER_EXISTS" == "true" ]]; then
    log_warning "🔄 GOAL 1: VCluster provisioned but not ready (Status: $VCLUSTER_READY)"
else
    log_error "❌ GOAL 1: VCluster not provisioned"
fi

if [[ "$APPCONTAINER_EXISTS" == "true" ]] && [[ "$APPCONTAINER_READY" == "True" ]]; then
    log_success "✅ GOAL 2: AppContainer successfully provisioned"
elif [[ "$APPCONTAINER_EXISTS" == "true" ]]; then
    log_warning "🔄 GOAL 2: AppContainer provisioned but not ready (Status: $APPCONTAINER_READY)"
else
    log_error "❌ GOAL 2: AppContainer not provisioned"
fi

echo ""
if [[ "$VCLUSTER_READY" == "True" ]] && [[ "$APPCONTAINER_READY" == "True" ]]; then
    log_success "🎉 SUCCESS: Both VCluster and AppContainer are fully provisioned!"
    echo ""
    echo "🔗 Next steps:"
    echo "   • Connect to VCluster using generated kubeconfig"
    echo "   • Access observability tools (Grafana, ArgoCD, Jaeger)"
    echo "   • Deploy applications to the AppContainer"
else
    log_warning "⏳ Provisioning may still be in progress. Check again in a few minutes."
    echo ""
    echo "🔗 Troubleshooting:"
    echo "   • Check Crossplane provider status"
    echo "   • Verify infrastructure capacity"
    echo "   • Review controller logs"
fi