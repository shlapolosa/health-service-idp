#!/bin/bash

# Enhanced Infrastructure Health Check Script with Remediation
# Validates all critical components for OAM microservice testing and provides automatic fixes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTO_REMEDIATE=${AUTO_REMEDIATE:-false}

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

log_remediation() {
    echo -e "${YELLOW}[REMEDIATION]${NC} $1"
}

echo "================================================"
echo "Enhanced Infrastructure Health Check with Remediation"
echo "================================================"
echo "Auto-remediation: $([ "$AUTO_REMEDIATE" = "true" ] && echo "ENABLED" || echo "DISABLED")"
echo "Use AUTO_REMEDIATE=true to enable automatic fixes"
echo

# Function to check resource existence with remediation
check_resource_with_fix() {
    local resource_type=$1
    local resource_name=$2
    local namespace=${3:-"default"}
    local description=$4
    local fix_command=$5
    local fix_description=$6
    
    if kubectl get $resource_type $resource_name -n $namespace &>/dev/null; then
        log_success "$description: ✅ Found"
        return 0
    else
        log_error "$description: ❌ Missing"
        if [ -n "$fix_command" ]; then
            log_remediation "Fix: $fix_description"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_info "Executing: $fix_command"
                eval "$fix_command"
                sleep 2
                if kubectl get $resource_type $resource_name -n $namespace &>/dev/null; then
                    log_success "$description: ✅ Fixed"
                    return 0
                else
                    log_error "$description: ❌ Fix failed"
                fi
            else
                echo "  Command: $fix_command"
            fi
        fi
        return 1
    fi
}

# Function to check resource count with remediation
check_resource_count_with_fix() {
    local resource_type=$1
    local namespace=${2:-"default"}
    local expected_min=$3
    local description=$4
    local fix_command=$5
    local fix_description=$6
    
    local count=$(kubectl get $resource_type -n $namespace --no-headers 2>/dev/null | wc -l)
    if [ $count -ge $expected_min ]; then
        log_success "$description: ✅ Found $count (expected ≥$expected_min)"
        return 0
    else
        log_error "$description: ❌ Found $count (expected ≥$expected_min)"
        if [ -n "$fix_command" ]; then
            log_remediation "Fix: $fix_description"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_info "Executing: $fix_command"
                eval "$fix_command"
                sleep 5
                local new_count=$(kubectl get $resource_type -n $namespace --no-headers 2>/dev/null | wc -l)
                if [ $new_count -ge $expected_min ]; then
                    log_success "$description: ✅ Fixed ($new_count found)"
                    return 0
                else
                    log_error "$description: ❌ Fix failed ($new_count found)"
                fi
            else
                echo "  Command: $fix_command"
            fi
        fi
        return 1
    fi
}

# Function to check pod health with restart capability
check_pod_health_with_fix() {
    local selector=$1
    local namespace=${2:-"default"}
    local description=$3
    local fix_command=$4
    local fix_description=$5
    
    local ready_pods=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | grep "Running" | grep -E "1/1|2/2|3/3" | wc -l)
    local total_pods=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | wc -l)
    
    if [ $total_pods -eq 0 ]; then
        log_error "$description: ❌ No pods found"
        if [ -n "$fix_command" ]; then
            log_remediation "Fix: $fix_description"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_info "Executing: $fix_command"
                eval "$fix_command"
                sleep 10
                local new_total=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | wc -l)
                if [ $new_total -gt 0 ]; then
                    log_success "$description: ✅ Fixed (pods created)"
                    return 0
                fi
            else
                echo "  Command: $fix_command"
            fi
        fi
        return 1
    elif [ $ready_pods -eq $total_pods ]; then
        log_success "$description: ✅ $ready_pods/$total_pods pods ready"
        return 0
    else
        log_warning "$description: ⚠️  $ready_pods/$total_pods pods ready"
        if [ -n "$fix_command" ]; then
            log_remediation "Fix: $fix_description"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_info "Executing: $fix_command"
                eval "$fix_command"
                sleep 10
                local new_ready=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | grep "Running" | grep -E "1/1|2/2|3/3" | wc -l)
                local new_total=$(kubectl get pods -l $selector -n $namespace --no-headers 2>/dev/null | wc -l)
                if [ $new_ready -eq $new_total ] && [ $new_total -gt 0 ]; then
                    log_success "$description: ✅ Fixed ($new_ready/$new_total ready)"
                    return 0
                fi
            else
                echo "  Command: $fix_command"
            fi
        fi
        return 1
    fi
}

# Function to test external connectivity with fix
test_external_access_with_fix() {
    local endpoint=$1
    local description=$2
    local fix_command=$3
    local fix_description=$4
    
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
            log_warning "$description: ⚠️  Not accessible"
            if [ -n "$fix_command" ]; then
                log_remediation "Fix: $fix_description"
                if [ "$AUTO_REMEDIATE" = "true" ]; then
                    log_info "Executing: $fix_command"
                    eval "$fix_command"
                    sleep 5
                    if $timeout_cmd 10 curl -s -o /dev/null -w "%{http_code}" $endpoint 2>/dev/null | grep -q "200"; then
                        log_success "$description: ✅ Fixed"
                        return 0
                    fi
                else
                    echo "  Command: $fix_command"
                fi
            fi
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
    log_remediation "Ensure kubectl is configured and cluster is accessible"
    log_remediation "Try: kubectl config get-contexts"
    exit 1
fi
log_success "Kubernetes connection: ✅ Connected"
echo

# 0. Ensure all secrets are properly configured
log_info "🔐 Ensuring all secrets are properly configured..."
if [ "$AUTO_REMEDIATE" = "true" ] || [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_info "Running setup-secrets.sh to ensure proper secret configuration..."
    if [ -f "$PROJECT_ROOT/setup-secrets.sh" ]; then
        "$PROJECT_ROOT/setup-secrets.sh"
        log_success "✅ Secrets configuration completed"
    else
        log_error "❌ setup-secrets.sh not found"
        log_remediation "Ensure setup-secrets.sh exists in project root"
        ((HEALTH_ISSUES++))
    fi
else
    log_info "Skipping secret setup (AUTO_REMEDIATE=false and .env exists)"
    log_info "Run with AUTO_REMEDIATE=true to force secret reconfiguration"
fi
echo

# 1. Check Slack API Server
log_info "🤖 Checking Slack API Server..."
check_pod_health_with_fix "app=slack-api-server" "default" "Slack API pods" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/deployment.yaml" \
    "Deploy Slack API server" || ((HEALTH_ISSUES++))

check_resource_with_fix "service" "slack-api-server" "default" "Slack API service" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/deployment.yaml" \
    "Deploy Slack API service" || ((HEALTH_ISSUES++))

check_resource_with_fix "deployment" "slack-api-server" "default" "Slack API deployment" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/deployment.yaml" \
    "Deploy Slack API deployment" || ((HEALTH_ISSUES++))

# Test external access with improved endpoint detection
INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -z "$INGRESS_IP" ]; then
    INGRESS_IP=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
fi

if [ -n "$INGRESS_IP" ]; then
    # Try different endpoints for health check
    for endpoint in "/health" "/api/health" "/"; do
        if test_external_access_with_fix "http://$INGRESS_IP$endpoint" "Slack API external access ($endpoint)" \
            "kubectl get pods -n default -l app=slack-api-server" \
            "Check pod status"; then
            break
        fi
    done
else
    log_warning "Cannot determine ingress IP for external testing"
    log_remediation "Check if Istio ingress gateway is properly configured"
    log_remediation "Command: kubectl get svc -n istio-system istio-ingressgateway"
fi
echo

# 2. Check Essential Secrets
log_info "🔐 Checking Essential Secrets..."
check_resource_with_fix "secret" "docker-registry-secret" "default" "Docker registry secret" \
    "$PROJECT_ROOT/setup-secrets.sh" \
    "Run setup-secrets.sh script" || ((HEALTH_ISSUES++))

check_resource_with_fix "secret" "slack-api-server-argo-token" "default" "Slack API Argo token" \
    "$PROJECT_ROOT/setup-secrets.sh" \
    "Run setup-secrets.sh script" || ((HEALTH_ISSUES++))

check_resource_with_fix "secret" "slack-credentials" "default" "Slack credentials" \
    "$PROJECT_ROOT/setup-secrets.sh" \
    "Run setup-secrets.sh script" || ((HEALTH_ISSUES++))

check_resource_with_fix "secret" "github-credentials" "default" "GitHub credentials" \
    "$PROJECT_ROOT/setup-secrets.sh" \
    "Run setup-secrets.sh script" || ((HEALTH_ISSUES++))

check_resource_with_fix "secret" "github-provider-secret" "crossplane-system" "GitHub provider secret" \
    "$PROJECT_ROOT/setup-secrets.sh" \
    "Run setup-secrets.sh script" || ((HEALTH_ISSUES++))
echo

# 3. Check Service Accounts and RBAC
log_info "👤 Checking Service Accounts and RBAC..."
check_resource_with_fix "serviceaccount" "knative-docker-sa" "default" "Knative Docker service account" \
    "kubectl apply -f $PROJECT_ROOT/knative-docker-config.yaml" \
    "Apply Knative Docker configuration" || ((HEALTH_ISSUES++))

check_resource_with_fix "serviceaccount" "argo-workflows-client" "default" "Argo workflows client (default)" \
    "kubectl apply -f $PROJECT_ROOT/crossplane/oam/argo-workflows-client-rbac.yaml" \
    "Apply Argo workflows RBAC" || ((HEALTH_ISSUES++))

check_resource_with_fix "serviceaccount" "argo-workflows-client" "vela-system" "Argo workflows client (vela-system)" \
    "kubectl apply -f $PROJECT_ROOT/crossplane/oam/argo-workflows-client-rbac.yaml" \
    "Apply Argo workflows RBAC" || ((HEALTH_ISSUES++))

check_resource_with_fix "serviceaccount" "slack-api-server" "default" "Slack API server service account" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/rbac.yaml" \
    "Apply Slack API RBAC" || ((HEALTH_ISSUES++))

check_resource_with_fix "serviceaccount" "slack-api-argo-access" "argo" "Slack API Argo access service account" \
    "kubectl apply -f $PROJECT_ROOT/argo-workflows/workflow-rbac.yaml" \
    "Apply workflow RBAC" || ((HEALTH_ISSUES++))

check_resource_with_fix "serviceaccount" "crossplane-installer" "crossplane-system" "Crossplane installer service account" \
    "kubectl create serviceaccount crossplane-installer -n crossplane-system" \
    "Create crossplane-installer service account" || ((HEALTH_ISSUES++))

# Check RBAC for Slack API server
check_resource_with_fix "role" "argo-workflow-api-access" "argo" "Argo workflow API access role" \
    "kubectl apply -f $PROJECT_ROOT/argo-workflows/workflow-rbac.yaml" \
    "Apply workflow RBAC" || ((HEALTH_ISSUES++))

check_resource_with_fix "rolebinding" "slack-api-server-argo-access" "argo" "Slack API server Argo access role binding" \
    "kubectl create rolebinding slack-api-server-argo-access --role=argo-workflow-api-access --serviceaccount=default:slack-api-server --namespace=argo" \
    "Create cross-namespace role binding" || ((HEALTH_ISSUES++))
echo

# 4. Check ComponentDefinitions
log_info "🧩 Checking OAM ComponentDefinitions..."
check_resource_count_with_fix "componentdefinitions" "default" 11 "ComponentDefinitions in default" \
    "kubectl apply -f $PROJECT_ROOT/crossplane/oam/consolidated-component-definitions.yaml && kubectl apply -f $PROJECT_ROOT/crossplane/oam/realtime-platform-component-definition.yaml && kubectl apply -f $PROJECT_ROOT/crossplane/oam/rasa-chatbot-component-definition.yaml" \
    "Apply consolidated ComponentDefinitions, realtime-platform, and rasa-chatbot" || ((HEALTH_ISSUES++))

# List all available ComponentDefinitions
ALL_COMPONENTS=("webservice" "realtime-platform" "rasa-chatbot" "kafka" "redis" "mongodb" "application-infrastructure" "vcluster" "neon-postgres" "auth0-idp" "clickhouse")
for component in "${ALL_COMPONENTS[@]}"; do
    if [ "$component" = "realtime-platform" ]; then
        check_resource_with_fix "componentdefinition" "$component" "default" "ComponentDefinition: $component" \
            "kubectl apply -f $PROJECT_ROOT/crossplane/oam/realtime-platform-component-definition.yaml" \
            "Apply realtime-platform ComponentDefinition" || ((HEALTH_ISSUES++))
    elif [ "$component" = "rasa-chatbot" ]; then
        check_resource_with_fix "componentdefinition" "$component" "default" "ComponentDefinition: $component" \
            "kubectl apply -f $PROJECT_ROOT/crossplane/oam/rasa-chatbot-component-definition.yaml" \
            "Apply rasa-chatbot ComponentDefinition" || ((HEALTH_ISSUES++))
    else
        check_resource_with_fix "componentdefinition" "$component" "default" "ComponentDefinition: $component" \
            "kubectl apply -f $PROJECT_ROOT/crossplane/oam/consolidated-component-definitions.yaml" \
            "Apply consolidated ComponentDefinitions" || ((HEALTH_ISSUES++))
    fi
done

# 4b. Check Rasa Chatbot Template Resources
log_info "🤖 Checking Rasa Chatbot Template Resources..."
if [ -d "$PROJECT_ROOT/health-service-chat-template" ]; then
    log_success "✅ Rasa chatbot template directory exists"
    
    # Check essential template files
    TEMPLATE_FILES=("docker/rasa/Dockerfile" "docker/rasa-actions/Dockerfile" "endpoints.yml" "credentials.yml" "config.yml" "domain.yml" "pyproject.toml")
    for file in "${TEMPLATE_FILES[@]}"; do
        if [ -f "$PROJECT_ROOT/health-service-chat-template/$file" ]; then
            log_success "✅ Template file: $file"
        else
            log_error "❌ Missing template file: $file"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_remediation "Template file $file would need manual creation"
            fi
            ((HEALTH_ISSUES++))
        fi
    done
    
    # Check OAM sample applications
    if [ -f "$PROJECT_ROOT/health-service-chat-template/oam/sample-applications.yaml" ]; then
        log_success "✅ OAM sample applications available"
    else
        log_warning "⚠️  OAM sample applications not found (optional)"
    fi
else
    log_error "❌ Rasa chatbot template directory not found at $PROJECT_ROOT/health-service-chat-template"
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        log_remediation "Creating rasa chatbot template directory would require manual setup"
    fi
    ((HEALTH_ISSUES++))
fi
echo

# 5. Check WorkloadDefinitions
log_info "⚙️  Checking WorkloadDefinitions..."
check_resource_with_fix "workloaddefinition" "webservice" "default" "Webservice WorkloadDefinition" \
    "kubectl apply -f $PROJECT_ROOT/webservice-workload-definition.yaml" \
    "Apply webservice WorkloadDefinition" || ((HEALTH_ISSUES++))
echo

# 5b. Check TraitDefinitions and PolicyDefinitions
log_info "🎯 Checking OAM TraitDefinitions and PolicyDefinitions..."
TRAIT_DEFINITIONS=("ingress" "autoscaler" "kafka-producer" "kafka-consumer")
for trait in "${TRAIT_DEFINITIONS[@]}"; do
    check_resource_with_fix "traitdefinition" "$trait" "default" "TraitDefinition: $trait" \
        "kubectl apply -f $PROJECT_ROOT/crossplane/oam/traits-and-policies.yaml" \
        "Apply TraitDefinitions and PolicyDefinitions" || ((HEALTH_ISSUES++))
done

POLICY_DEFINITIONS=("health" "security-policy" "override")
for policy in "${POLICY_DEFINITIONS[@]}"; do
    check_resource_with_fix "policydefinition" "$policy" "default" "PolicyDefinition: $policy" \
        "kubectl apply -f $PROJECT_ROOT/crossplane/oam/traits-and-policies.yaml" \
        "Apply TraitDefinitions and PolicyDefinitions" || ((HEALTH_ISSUES++))
done
echo

# 6. Check Argo Workflows Infrastructure
log_info "🔄 Checking Argo Workflows..."
check_pod_health_with_fix "app=argo-server" "argo" "Argo server pods" \
    "kubectl rollout restart deployment/argo-server -n argo" \
    "Restart Argo server deployment" || ((HEALTH_ISSUES++))

check_pod_health_with_fix "app=workflow-controller" "argo" "Argo workflow controller pods" \
    "kubectl rollout restart deployment/workflow-controller -n argo" \
    "Restart workflow controller" || ((HEALTH_ISSUES++))

check_resource_with_fix "workflowtemplate" "microservice-standard-contract" "argo" "Microservice workflow template" \
    "kubectl apply -f $PROJECT_ROOT/argo-workflows/microservice-standard-contract.yaml" \
    "Apply microservice workflow template" || ((HEALTH_ISSUES++))

check_resource_with_fix "secret" "slack-api-argo-token" "argo" "Argo token secret" \
    "kubectl get secret slack-api-server-argo-token -n default -o yaml | sed 's/namespace: default/namespace: argo/' | kubectl apply -f -" \
    "Copy Argo token to argo namespace" || ((HEALTH_ISSUES++))
echo

# 7. Check Crossplane Infrastructure
log_info "🔗 Checking Crossplane..."
check_resource_count_with_fix "compositeresourcedefinitions.apiextensions.crossplane.io" "" 4 "Crossplane CRDs" \
    "kubectl apply -f $PROJECT_ROOT/crossplane/application-claim-xrd.yaml -f $PROJECT_ROOT/crossplane/app-container-claim-xrd.yaml -f $PROJECT_ROOT/crossplane/vcluster-environment-claim-xrd.yaml -f $PROJECT_ROOT/crossplane/realtime-platform-claim-xrd.yaml" \
    "Apply Crossplane XRDs" || ((HEALTH_ISSUES++))

# Check specific CRDs
CROSSPLANE_CRDS=("xapplicationclaims.platform.example.org" "xappcontainerclaims.platform.example.org")
for crd in "${CROSSPLANE_CRDS[@]}"; do
    check_resource_with_fix "compositeresourcedefinition" "$crd" "" "Crossplane CRD: $crd" \
        "kubectl apply -f $PROJECT_ROOT/crossplane/application-claim-xrd.yaml -f $PROJECT_ROOT/crossplane/app-container-claim-xrd.yaml" \
        "Apply Crossplane XRDs" || ((HEALTH_ISSUES++))
done

# Check Crossplane providers
check_pod_health_with_fix "pkg.crossplane.io/provider=provider-upjet-github" "crossplane-system" "GitHub provider pods" \
    "$PROJECT_ROOT/scripts/restart-crossplane-providers.sh" \
    "Restart Crossplane providers" || ((HEALTH_ISSUES++))

check_resource_with_fix "providerconfig.github.upbound.io" "github-provider" "" "GitHub provider configuration" \
    "kubectl apply -f $PROJECT_ROOT/crossplane/github-provider-config.yaml" \
    "Apply GitHub provider config" || ((HEALTH_ISSUES++))

# Comprehensive GitHub provider validation with remediation
log_info "🔧 Validating GitHub Provider Configuration..."

# Check if GitHub provider is properly installed
if ! kubectl get providers.pkg.crossplane.io provider-upjet-github &>/dev/null; then
    log_error "GitHub provider not installed"
    log_remediation "Install GitHub provider"
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        log_info "Installing GitHub provider..."
        kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-upjet-github
spec:
  package: xpkg.upbound.io/upbound/provider-github:v0.4.0
EOF
        sleep 10
    else
        echo "  Command: kubectl apply -f <github-provider.yaml>"
    fi
    ((HEALTH_ISSUES++))
fi

# Check provider health
if kubectl get providers.pkg.crossplane.io provider-upjet-github -o jsonpath='{.status.conditions[?(@.type=="Healthy")].status}' 2>/dev/null | grep -q "True"; then
    log_success "GitHub provider: ✅ Healthy"
else
    log_error "GitHub provider: ❌ Not healthy"
    log_remediation "Check provider logs and restart if needed"
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        log_info "Restarting GitHub provider..."
        kubectl delete pods -n crossplane-system -l pkg.crossplane.io/provider=provider-upjet-github --force --grace-period=0
        sleep 15
    else
        echo "  Command: kubectl delete pods -n crossplane-system -l pkg.crossplane.io/provider=provider-upjet-github"
    fi
    ((HEALTH_ISSUES++))
fi

# Validate GitHub provider config exists and is configured
if kubectl get providerconfig.github.upbound.io github-provider &>/dev/null; then
    log_success "GitHub ProviderConfig: ✅ Exists"
    
    # Check if the secret referenced by ProviderConfig exists
    SECRET_NAME=$(kubectl get providerconfig.github.upbound.io github-provider -o jsonpath='{.spec.credentials.secretRef.name}' 2>/dev/null)
    SECRET_NAMESPACE=$(kubectl get providerconfig.github.upbound.io github-provider -o jsonpath='{.spec.credentials.secretRef.namespace}' 2>/dev/null)
    
    if [ -n "$SECRET_NAME" ] && [ -n "$SECRET_NAMESPACE" ]; then
        if kubectl get secret "$SECRET_NAME" -n "$SECRET_NAMESPACE" &>/dev/null; then
            log_success "GitHub provider secret: ✅ Found ($SECRET_NAME in $SECRET_NAMESPACE)"
            
            # Validate secret has required key
            if kubectl get secret "$SECRET_NAME" -n "$SECRET_NAMESPACE" -o jsonpath='{.data.token}' | base64 -d | grep -q "^ghp_\|^github_pat_"; then
                log_success "GitHub token format: ✅ Valid"
            else
                log_error "GitHub token format: ❌ Invalid or missing"
                log_remediation "Ensure GitHub token starts with 'ghp_' or 'github_pat_'"
                log_remediation "Update secret: kubectl create secret generic $SECRET_NAME -n $SECRET_NAMESPACE --from-literal=token=YOUR_GITHUB_TOKEN --dry-run=client -o yaml | kubectl apply -f -"
                ((HEALTH_ISSUES++))
            fi
        else
            log_error "GitHub provider secret: ❌ Missing ($SECRET_NAME in $SECRET_NAMESPACE)"
            log_remediation "Create GitHub provider secret"
            if [ "$AUTO_REMEDIATE" = "true" ]; then
                log_info "Creating GitHub provider secret..."
                if [ -f "$PROJECT_ROOT/setup-secrets.sh" ]; then
                    "$PROJECT_ROOT/setup-secrets.sh"
                else
                    log_error "setup-secrets.sh not found for auto-remediation"
                fi
            else
                echo "  Command: $PROJECT_ROOT/setup-secrets.sh"
            fi
            ((HEALTH_ISSUES++))
        fi
    else
        log_error "GitHub ProviderConfig: ❌ No secret reference configured"
        log_remediation "Configure ProviderConfig with secret reference"
        ((HEALTH_ISSUES++))
    fi
else
    log_error "GitHub ProviderConfig: ❌ Missing"
    log_remediation "Create GitHub ProviderConfig"
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        log_info "Creating GitHub ProviderConfig..."
        kubectl apply -f "$PROJECT_ROOT/crossplane/github-provider-config.yaml"
    else
        echo "  Command: kubectl apply -f $PROJECT_ROOT/crossplane/github-provider-config.yaml"
    fi
    ((HEALTH_ISSUES++))
fi

# Test GitHub provider functionality by checking if repositories can be managed
log_info "🧪 Testing GitHub Provider Functionality..."
TEST_REPO_COUNT=$(kubectl get repositories.repo.github.upbound.io 2>/dev/null | wc -l)
if [ $TEST_REPO_COUNT -gt 1 ]; then  # Header + at least one repo
    # Check if any repositories are failing
    FAILED_REPOS=$(kubectl get repositories.repo.github.upbound.io -o jsonpath='{.items[?(@.status.conditions[0].status=="False")].metadata.name}' 2>/dev/null)
    if [ -n "$FAILED_REPOS" ]; then
        log_error "GitHub repositories: ❌ Some repositories failing: $FAILED_REPOS"
        log_remediation "Check repository status and GitHub provider configuration"
        for repo in $FAILED_REPOS; do
            log_info "Checking failed repository: $repo"
            kubectl describe repository.repo.github.upbound.io "$repo" | grep -A 5 "Conditions:"
        done
        ((HEALTH_ISSUES++))
    else
        log_success "GitHub repositories: ✅ All repositories healthy"
    fi
else
    log_warning "GitHub repositories: ⚠️  No repositories found (this is normal for new installations)"
fi
echo

# 8. Check Istio/Service Mesh
log_info "🌐 Checking Istio Service Mesh..."
check_pod_health_with_fix "istio=ingressgateway" "istio-system" "Istio ingress gateway" \
    "kubectl rollout restart deployment/istio-ingressgateway -n istio-system" \
    "Restart Istio ingress gateway" || ((HEALTH_ISSUES++))

check_resource_with_fix "gateway" "slack-api-gateway" "default" "Slack API Istio gateway" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/istio-gateway.yaml" \
    "Apply Slack API Istio gateway" || ((HEALTH_ISSUES++))

check_resource_with_fix "virtualservice" "slack-api-virtualservice" "default" "Slack API virtual service" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/istio-gateway.yaml" \
    "Apply Slack API virtual service" || ((HEALTH_ISSUES++))
echo

# 9. Check ArgoCD Applications
log_info "📦 Checking ArgoCD Applications..."
check_resource_count_with_fix "applications.argoproj.io" "argocd" 1 "ArgoCD applications" \
    "kubectl apply -f $PROJECT_ROOT/slack-api-server/argocd-application.yaml" \
    "Apply ArgoCD application" || ((HEALTH_ISSUES++))
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
    if [ "$AUTO_REMEDIATE" = "true" ]; then
        echo -e "${YELLOW}🔧 Auto-remediation was attempted${NC}"
        echo -e "${BLUE}ℹ️  Re-run the script to verify fixes${NC}"
    else
        echo -e "${RED}❌ Enable auto-remediation with AUTO_REMEDIATE=true${NC}"
        echo
        echo "Next steps:"
        echo "1. Review the issues and suggested fixes above"
        echo "2. Run with AUTO_REMEDIATE=true for automatic fixes:"
        echo "   AUTO_REMEDIATE=true $0"
        echo "3. Or apply fixes manually using the provided commands"
        echo "4. Re-run this script to verify fixes"
    fi
    exit 1
fi