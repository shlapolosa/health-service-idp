#!/bin/bash

# Infrastructure Health Check Script
# Validates all critical components for OAM microservice testing

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

echo "================================================"
echo "Infrastructure Health Check"
echo "================================================"
echo

# Function to check resource existence
check_resource() {
    local resource_type=$1
    local resource_name=$2
    local namespace=${3:-"default"}
    local description=$4
    
    if kubectl get $resource_type $resource_name -n $namespace &>/dev/null; then
        log_success "$description: ✅ Found"
        return 0
    else
        log_error "$description: ❌ Missing"
        return 1
    fi
}

# Function to check resource count
check_resource_count() {
    local resource_type=$1
    local namespace=${2:-"default"}
    local expected_min=$3
    local description=$4
    
    local count=$(kubectl get $resource_type -n $namespace --no-headers 2>/dev/null | wc -l)
    if [ $count -ge $expected_min ]; then
        log_success "$description: ✅ Found $count (expected ≥$expected_min)"
        return 0
    else
        log_error "$description: ❌ Found $count (expected ≥$expected_min)"
        return 1
    fi
}

# Function to check pod readiness
check_pod_health() {
    local selector=$1
    local namespace=${2:-"default"}
    local description=$3
    
    local ready_pods=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | grep "Running" | grep "1/1\|2/2\|3/3" | wc -l)
    local total_pods=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | wc -l)
    
    if [ $total_pods -eq 0 ]; then
        log_error "$description: ❌ No pods found"
        return 1
    elif [ $ready_pods -eq $total_pods ]; then
        log_success "$description: ✅ $ready_pods/$total_pods pods ready"
        return 0
    else
        log_warning "$description: ⚠️  $ready_pods/$total_pods pods ready"
        return 1
    fi
}

# Function to test external connectivity
test_external_access() {
    local endpoint=$1
    local description=$2
    
    # Use gtimeout on macOS or timeout on Linux
    local timeout_cmd="timeout"
    if command -v gtimeout &> /dev/null; then
        timeout_cmd="gtimeout"
    fi
    
    if command -v $timeout_cmd &> /dev/null; then
        if $timeout_cmd 10 curl -s -o /dev/null -w "%{http_code}" $endpoint 2>/dev/null | grep -q "200"; then
            log_success "$description: ✅ Accessible"
            return 0
        else
            log_warning "$description: ⚠️  Not accessible (may be expected in some environments)"
            return 0  # Don't fail on external access issues
        fi
    else
        log_warning "$description: ⚠️  Cannot test (timeout command not available)"
        return 0  # Don't fail if we can't test
    fi
}

# Track overall health
HEALTH_ISSUES=0

log_info "🔍 Checking Kubernetes Connection..."
if ! kubectl cluster-info &>/dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi
log_success "Kubernetes connection: ✅ Connected"
echo

# 1. Check Slack API Server
log_info "🤖 Checking Slack API Server..."
check_pod_health "app=slack-api-server" "default" "Slack API pods" || ((HEALTH_ISSUES++))
check_resource "service" "slack-api-server" "default" "Slack API service" || ((HEALTH_ISSUES++))
check_resource "deployment" "slack-api-server" "default" "Slack API deployment" || ((HEALTH_ISSUES++))

# Test external access
INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ -n "$INGRESS_IP" ]; then
    test_external_access "http://$INGRESS_IP/health" "Slack API external access" || ((HEALTH_ISSUES++))
else
    log_warning "Cannot determine ingress IP for external testing"
fi
echo

# 2. Check Essential Secrets
log_info "🔐 Checking Essential Secrets..."
check_resource "secret" "docker-registry-secret" "default" "Docker registry secret" || ((HEALTH_ISSUES++))
check_resource "secret" "slack-api-server-argo-token" "default" "Slack API Argo token" || ((HEALTH_ISSUES++))
check_resource "secret" "slack-credentials" "default" "Slack credentials" || ((HEALTH_ISSUES++))
check_resource "secret" "github-credentials" "default" "GitHub credentials" || ((HEALTH_ISSUES++))
check_resource "secret" "github-provider-secret" "crossplane-system" "GitHub provider secret" || ((HEALTH_ISSUES++))
echo

# 3. Check Service Accounts and RBAC
log_info "👤 Checking Service Accounts and RBAC..."
check_resource "serviceaccount" "knative-docker-sa" "default" "Knative Docker service account" || ((HEALTH_ISSUES++))
check_resource "serviceaccount" "argo-workflows-client" "default" "Argo workflows client (default)" || ((HEALTH_ISSUES++))
check_resource "serviceaccount" "argo-workflows-client" "vela-system" "Argo workflows client (vela-system)" || ((HEALTH_ISSUES++))
check_resource "serviceaccount" "slack-api-server" "default" "Slack API server service account" || ((HEALTH_ISSUES++))
check_resource "serviceaccount" "slack-api-argo-access" "argo" "Slack API Argo access service account" || ((HEALTH_ISSUES++))

# Check RBAC for Slack API server
check_resource "role" "argo-workflow-api-access" "argo" "Argo workflow API access role" || ((HEALTH_ISSUES++))
check_resource "rolebinding" "slack-api-server-argo-access" "argo" "Slack API server Argo access role binding" || ((HEALTH_ISSUES++))
echo

# 4. Check ComponentDefinitions
log_info "🧩 Checking OAM ComponentDefinitions..."
check_resource_count "componentdefinitions" "default" 9 "ComponentDefinitions in default" || ((HEALTH_ISSUES++))

# List specific critical ComponentDefinitions
CRITICAL_COMPONENTS=("webservice" "realtime-platform" "application-infrastructure" "kafka" "redis" "mongodb")
for component in "${CRITICAL_COMPONENTS[@]}"; do
    check_resource "componentdefinition" "$component" "default" "ComponentDefinition: $component" || ((HEALTH_ISSUES++))
done
echo

# 5. Check WorkloadDefinitions
log_info "⚙️  Checking WorkloadDefinitions..."
check_resource "workloaddefinition" "webservice" "default" "Webservice WorkloadDefinition" || ((HEALTH_ISSUES++))
echo

# 6. Check Argo Workflows Infrastructure
log_info "🔄 Checking Argo Workflows..."
check_pod_health "app=argo-server" "argo" "Argo server pods" || ((HEALTH_ISSUES++))
check_pod_health "app=workflow-controller" "argo" "Argo workflow controller pods" || ((HEALTH_ISSUES++))
check_resource "workflowtemplate" "microservice-standard-contract" "argo" "Microservice workflow template" || ((HEALTH_ISSUES++))
check_resource "secret" "slack-api-argo-token" "argo" "Argo token secret" || ((HEALTH_ISSUES++))
echo

# 7. Check Crossplane Infrastructure
log_info "🔗 Checking Crossplane..."
check_resource_count "compositeresourcedefinitions.apiextensions.crossplane.io" "" 4 "Crossplane CRDs" || ((HEALTH_ISSUES++))

# Check specific CRDs
CROSSPLANE_CRDS=("xapplicationclaims.platform.example.org" "xappcontainerclaims.platform.example.org")
for crd in "${CROSSPLANE_CRDS[@]}"; do
    check_resource "compositeresourcedefinition" "$crd" "" "Crossplane CRD: $crd" || ((HEALTH_ISSUES++))
done

# Check Crossplane providers
check_pod_health "pkg.crossplane.io/provider=provider-upjet-github" "crossplane-system" "GitHub provider pods" || ((HEALTH_ISSUES++))
check_resource "providerconfig.github.upbound.io" "github-provider" "" "GitHub provider configuration" || ((HEALTH_ISSUES++))
echo

# 8. Check Istio/Service Mesh
log_info "🌐 Checking Istio Service Mesh..."
check_pod_health "istio=ingressgateway" "istio-system" "Istio ingress gateway" || ((HEALTH_ISSUES++))
check_resource "gateway" "slack-api-gateway" "default" "Slack API Istio gateway" || ((HEALTH_ISSUES++))
check_resource "virtualservice" "slack-api-virtualservice" "default" "Slack API virtual service" || ((HEALTH_ISSUES++))
echo

# 9. Check ArgoCD Applications
log_info "📦 Checking ArgoCD Applications..."
check_resource_count "applications.argoproj.io" "argocd" 1 "ArgoCD applications" || ((HEALTH_ISSUES++))
echo

# Summary
echo "================================================"
echo "HEALTH CHECK SUMMARY"
echo "================================================"

if [ $HEALTH_ISSUES -eq 0 ]; then
    log_success "🎉 All infrastructure components are healthy!"
    echo -e "${GREEN}✅ Ready for OAM microservice testing${NC}"
    exit 0
else
    log_error "⚠️  Found $HEALTH_ISSUES infrastructure issues"
    echo -e "${RED}❌ Address issues before proceeding with testing${NC}"
    echo
    echo "Next steps:"
    echo "1. Review the issues identified above"
    echo "2. Apply missing manifests or fix configurations"
    echo "3. Re-run this script to verify fixes"
    exit 1
fi