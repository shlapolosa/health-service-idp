#!/bin/bash

# Unified Platform Installation Script for AKS
# Consolidates install-platform-complete.sh and install-platform-resources.sh
# Installs all necessary platform components and resources

set -e

echo "=========================================="
echo "Unified Platform Installation for AKS"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Verify kubectl context
verify_context() {
    CURRENT_CONTEXT=$(kubectl config current-context)
    echo "Current kubectl context: $CURRENT_CONTEXT"
    
    if [[ ! "$CURRENT_CONTEXT" == *"aks"* ]] && [[ ! "$CURRENT_CONTEXT" == *"health-idp"* ]]; then
        print_warning "Not on AKS context. Please switch with:"
        echo "kubectl config use-context <your-aks-context>"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it with required variables."
        exit 1
    fi
    
    # Load environment variables
    export $(grep -E "^(PERSONAL_ACCESS_TOKEN|GITHUB_USERNAME|DOCKER_USERNAME|SLACK_SIGNING_SECRET|GITHUB_TOKEN)=" .env | xargs)
    
    # Check required tools
    command -v kubectl >/dev/null 2>&1 || { print_error "kubectl is required but not installed."; exit 1; }
    command -v helm >/dev/null 2>&1 || { print_error "helm is required but not installed."; exit 1; }
    command -v istioctl >/dev/null 2>&1 || { print_error "istioctl is required but not installed."; exit 1; }
}

# ========== CORE PLATFORM COMPONENTS ==========

# 1. Install Istio
install_istio() {
    echo ""
    echo "=========================================="
    echo "Installing Istio Service Mesh..."
    echo "=========================================="
    
    if kubectl get namespace istio-system &>/dev/null; then
        print_warning "Istio namespace exists, checking installation..."
        if kubectl get deployment istiod -n istio-system &>/dev/null; then
            print_status "Istio already installed"
            return
        fi
    fi
    
    istioctl install --set profile=default -y
    print_status "Istio installed"
    
    # Wait for Istio to be ready
    kubectl rollout status deployment/istiod -n istio-system --timeout=300s
    print_status "Istio control plane ready"
}

# 2. Install Knative
install_knative() {
    echo ""
    echo "=========================================="
    echo "Installing Knative Serving..."
    echo "=========================================="
    
    if kubectl get namespace knative-serving &>/dev/null; then
        print_warning "Knative already installed, skipping..."
        return
    fi
    
    # Install Knative Serving CRDs
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.13.0/serving-crds.yaml
    
    # Install Knative Serving core
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.13.0/serving-core.yaml
    
    # Install Knative Istio controller
    kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.13.0/net-istio.yaml
    
    # Configure Knative to use Istio
    kubectl patch configmap/config-network \
      --namespace knative-serving \
      --type merge \
      --patch '{"data":{"ingress-class":"istio.ingress.networking.knative.dev"}}'
    
    print_status "Knative Serving installed"
    
    # Wait for Knative to be ready
    kubectl rollout status deployment/controller -n knative-serving --timeout=300s
    kubectl rollout status deployment/webhook -n knative-serving --timeout=300s
}

# 3. Install ArgoCD
install_argocd() {
    echo ""
    echo "=========================================="
    echo "Installing ArgoCD..."
    echo "=========================================="
    
    if kubectl get namespace argocd &>/dev/null; then
        print_warning "ArgoCD namespace exists, skipping installation"
        return
    fi
    
    kubectl create namespace argocd
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    # Wait for ArgoCD to be ready
    kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
    print_status "ArgoCD installed"
    
    # Patch ArgoCD server to disable internal TLS
    kubectl patch deployment argocd-server -n argocd --type='json' \
      -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--insecure"}]'
    
    print_status "ArgoCD configured for HTTP access"
}

# 4. Install Argo Workflows
install_argo_workflows() {
    echo ""
    echo "=========================================="
    echo "Installing Argo Workflows..."
    echo "=========================================="
    
    if kubectl get namespace argo &>/dev/null; then
        print_warning "Argo namespace exists, checking installation..."
        if kubectl get deployment argo-server -n argo &>/dev/null; then
            print_status "Argo Workflows already installed"
            return
        fi
    fi
    
    kubectl create namespace argo || true
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.4/install.yaml
    
    # Configure Argo server for auth mode
    kubectl patch deployment argo-server -n argo --type='json' \
      -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--auth-mode=server"}]'
    
    # Wait for Argo to be ready
    kubectl rollout status deployment/argo-server -n argo --timeout=300s
    print_status "Argo Workflows installed"
}

# 5. Install Crossplane
install_crossplane() {
    echo ""
    echo "=========================================="
    echo "Installing Crossplane..."
    echo "=========================================="
    
    if helm list -n crossplane-system | grep -q crossplane; then
        print_warning "Crossplane already installed"
        return
    fi
    
    # Add Crossplane Helm repository
    helm repo add crossplane-stable https://charts.crossplane.io/stable
    helm repo update
    
    # Install Crossplane
    helm install crossplane \
      --namespace crossplane-system \
      --create-namespace \
      crossplane-stable/crossplane \
      --wait
    
    print_status "Crossplane installed"
    
    # Wait for Crossplane to be ready
    kubectl wait --for=condition=Ready pod -l app=crossplane -n crossplane-system --timeout=300s
}

# 6. Install KubeVela
install_kubevela() {
    echo ""
    echo "=========================================="
    echo "Installing KubeVela..."
    echo "=========================================="
    
    if helm list -n vela-system | grep -q kubevela; then
        print_warning "KubeVela already installed"
        return
    fi
    
    # Add KubeVela Helm repository
    helm repo add kubevela https://kubevela.github.io/charts
    helm repo update
    
    # Install KubeVela core
    helm install --create-namespace -n vela-system kubevela kubevela/vela-core --wait
    
    print_status "KubeVela installed"
    
    # Install VelaUX (optional UI)
    vela addon enable velaux || print_warning "VelaUX addon installation failed (optional)"
}

# 7. Install External Secrets Operator
install_external_secrets() {
    echo ""
    echo "=========================================="
    echo "Installing External Secrets Operator..."
    echo "=========================================="
    
    if helm list -n external-secrets | grep -q external-secrets; then
        print_warning "External Secrets already installed"
        return
    fi
    
    helm repo add external-secrets https://charts.external-secrets.io
    helm repo update
    
    helm install external-secrets \
      external-secrets/external-secrets \
      -n external-secrets \
      --create-namespace \
      --wait
    
    print_status "External Secrets Operator installed"
}

# ========== PLATFORM RESOURCES ==========

# 8. Install Component Definitions
install_component_definitions() {
    echo ""
    echo "=========================================="
    echo "Installing OAM Component Definitions..."
    echo "=========================================="
    
    COMPONENT_DIR="/Users/socrateshlapolosa/Development/health-service-idp/crossplane/oam"
    
    if [ -f "$COMPONENT_DIR/consolidated-component-definitions-fixed.yaml" ]; then
        kubectl apply -f "$COMPONENT_DIR/consolidated-component-definitions-fixed.yaml"
        print_status "Component Definitions installed"
    else
        print_warning "Component Definitions file not found"
    fi
}

# 9. Install Trait Definitions
install_trait_definitions() {
    echo ""
    echo "=========================================="
    echo "Installing OAM Trait Definitions..."
    echo "=========================================="
    
    TRAIT_DIR="/Users/socrateshlapolosa/Development/health-service-idp/crossplane/oam"
    
    if [ -f "$TRAIT_DIR/trait-definitions.yaml" ]; then
        kubectl apply -f "$TRAIT_DIR/trait-definitions.yaml"
        print_status "Trait Definitions installed"
    else
        print_warning "Trait Definitions file not found"
    fi
}

# 10. Install Crossplane XRDs and Compositions
install_crossplane_xrds() {
    echo ""
    echo "=========================================="
    echo "Installing Crossplane XRDs and Compositions..."
    echo "=========================================="
    
    CROSSPLANE_DIR="/Users/socrateshlapolosa/Development/health-service-idp/crossplane"
    
    # Install XRDs
    for xrd_file in $CROSSPLANE_DIR/*-xrd.yaml; do
        if [ -f "$xrd_file" ]; then
            kubectl apply -f "$xrd_file" || print_warning "Failed to apply $(basename $xrd_file)"
        fi
    done
    
    # Install Compositions
    for comp_file in $CROSSPLANE_DIR/*-composition.yaml; do
        if [ -f "$comp_file" ]; then
            kubectl apply -f "$comp_file" || print_warning "Failed to apply $(basename $comp_file)"
        fi
    done
    
    print_status "Crossplane XRDs and Compositions installed"
}

# 11. Install ClusterGateway CRDs
install_clustergateway_crds() {
    echo ""
    echo "=========================================="
    echo "Installing ClusterGateway CRDs..."
    echo "=========================================="
    
    CRD_DIR="/Users/socrateshlapolosa/Development/health-service-idp/crossplane/cluster-gateway"
    
    if [ -d "$CRD_DIR" ]; then
        kubectl apply -f "$CRD_DIR/clustergateway-cluster-crd.yaml" || print_warning "Failed to apply cluster CRD"
        kubectl apply -f "$CRD_DIR/clustergateway-core-crd.yaml" || print_warning "Failed to apply core CRD"
        print_status "ClusterGateway CRDs installed"
    else
        print_warning "ClusterGateway CRD directory not found"
    fi
}

# 12. Install Istio Resources
install_istio_resources() {
    echo ""
    echo "=========================================="
    echo "Installing Istio Gateways and VirtualServices..."
    echo "=========================================="
    
    # Create Slack API Gateway
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: slack-api-gateway
  namespace: default
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: slack-api-virtualservice
  namespace: default
spec:
  hosts:
  - "*"
  gateways:
  - slack-api-gateway
  http:
  - match:
    - uri:
        prefix: /slack/
    rewrite:
      uri: /
    route:
    - destination:
        host: slack-api
        port:
          number: 8000
EOF
    
    print_status "Istio resources configured"
}

# 13. Install Argo Workflow Templates
install_argo_templates() {
    echo ""
    echo "=========================================="
    echo "Installing Argo Workflow Templates..."
    echo "=========================================="
    
    ARGO_DIR="/Users/socrateshlapolosa/Development/health-service-idp/argo-workflows"
    
    if [ -f "$ARGO_DIR/microservice-standard-contract.yaml" ]; then
        kubectl apply -f "$ARGO_DIR/microservice-standard-contract.yaml" -n argo
        print_status "Argo Workflow Templates installed"
    else
        print_warning "Workflow template file not found"
    fi
}

# 14. Configure Provider RBAC
configure_provider_rbac() {
    echo ""
    echo "=========================================="
    echo "Configuring Provider Kubernetes RBAC..."
    echo "=========================================="
    
    kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: provider-kubernetes-system
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: provider-kubernetes-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: provider-kubernetes-system
subjects:
- kind: ServiceAccount
  name: provider-kubernetes
  namespace: crossplane-system
EOF
    
    print_status "Provider Kubernetes RBAC configured"
}

# 15. Install GitHub Provider
install_github_provider() {
    echo ""
    echo "=========================================="
    echo "Installing Crossplane GitHub Provider..."
    echo "=========================================="
    
    # Install provider
    kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-github
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-github:v0.13.0
EOF
    
    # Wait for provider to be healthy
    kubectl wait --for=condition=Healthy provider/provider-github --timeout=300s || print_warning "Provider might not be healthy"
    
    # Create ProviderConfig
    if [ -n "$GITHUB_TOKEN" ]; then
        kubectl create secret generic github-credentials \
          --from-literal=token="$GITHUB_TOKEN" \
          -n crossplane-system \
          --dry-run=client -o yaml | kubectl apply -f -
        
        kubectl apply -f - <<EOF
apiVersion: github.crossplane.io/v1alpha1
kind: ProviderConfig
metadata:
  name: github-provider-config
spec:
  credentials:
    source: Secret
    secretRef:
      name: github-credentials
      namespace: crossplane-system
      key: token
EOF
        print_status "GitHub Provider configured"
    else
        print_warning "GITHUB_TOKEN not found in .env, skipping GitHub provider config"
    fi
}

# 16. Setup Secrets
setup_secrets() {
    echo ""
    echo "=========================================="
    echo "Setting up Platform Secrets..."
    echo "=========================================="
    
    # Docker registry secret
    if [ -n "$DOCKER_USERNAME" ]; then
        kubectl create secret docker-registry regcred \
          --docker-server=docker.io \
          --docker-username="$DOCKER_USERNAME" \
          --docker-password="$PERSONAL_ACCESS_TOKEN" \
          --docker-email="${DOCKER_USERNAME}@users.noreply.github.com" \
          --dry-run=client -o yaml | kubectl apply -f -
        print_status "Docker registry secret created"
    fi
    
    # GitHub credentials
    if [ -n "$GITHUB_TOKEN" ]; then
        kubectl create secret generic github-credentials \
          --from-literal=token="$GITHUB_TOKEN" \
          --from-literal=username="$GITHUB_USERNAME" \
          --dry-run=client -o yaml | kubectl apply -f -
        print_status "GitHub credentials secret created"
    fi
    
    # Slack credentials
    if [ -n "$SLACK_SIGNING_SECRET" ]; then
        kubectl create secret generic slack-credentials \
          --from-literal=signing-secret="$SLACK_SIGNING_SECRET" \
          --dry-run=client -o yaml | kubectl apply -f -
        print_status "Slack credentials secret created"
    fi
}

# 17. Deploy Slack API Server
deploy_slack_api() {
    echo ""
    echo "=========================================="
    echo "Deploying Slack API Server..."
    echo "=========================================="
    
    SLACK_DIR="/Users/socrateshlapolosa/Development/health-service-idp/slack-api-server"
    
    if [ -f "$SLACK_DIR/k8s-deployment.yaml" ]; then
        kubectl apply -f "$SLACK_DIR/k8s-deployment.yaml"
        print_status "Slack API Server deployed"
    else
        print_warning "Slack API deployment file not found"
    fi
}

# 18. Verification
verify_installation() {
    echo ""
    echo "=========================================="
    echo "Verifying Installation..."
    echo "=========================================="
    
    echo "Core Components:"
    kubectl get pods -n istio-system --no-headers | grep -c Running | xargs -I {} echo "  Istio pods running: {}"
    kubectl get pods -n knative-serving --no-headers | grep -c Running | xargs -I {} echo "  Knative pods running: {}"
    kubectl get pods -n argocd --no-headers | grep -c Running | xargs -I {} echo "  ArgoCD pods running: {}"
    kubectl get pods -n argo --no-headers | grep -c Running | xargs -I {} echo "  Argo Workflows pods running: {}"
    kubectl get pods -n crossplane-system --no-headers | grep -c Running | xargs -I {} echo "  Crossplane pods running: {}"
    kubectl get pods -n vela-system --no-headers | grep -c Running | xargs -I {} echo "  KubeVela pods running: {}"
    
    echo ""
    echo "Platform Resources:"
    kubectl get componentdefinitions --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  ComponentDefinitions: {}"
    kubectl get traitdefinitions --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  TraitDefinitions: {}"
    kubectl get xrd --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  Crossplane XRDs: {}"
    kubectl get crd | grep -c "clustergateways.*oam.dev" | xargs -I {} echo "  ClusterGateway CRDs: {}"
    kubectl get gateway -A --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  Istio Gateways: {}"
    kubectl get virtualservice -A --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  VirtualServices: {}"
    
    echo ""
    echo "Services:"
    kubectl get svc -n istio-system istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null | xargs -I {} echo "  Istio Ingress IP: {}"
    kubectl get deployment slack-api 2>/dev/null && echo "  Slack API: Deployed" || echo "  Slack API: Not deployed"
}

# Main execution
main() {
    echo "This unified script will install:"
    echo ""
    echo "Core Platform Components:"
    echo "  - Istio Service Mesh"
    echo "  - Knative Serving"
    echo "  - ArgoCD"
    echo "  - Argo Workflows"
    echo "  - Crossplane"
    echo "  - KubeVela"
    echo "  - External Secrets Operator"
    echo ""
    echo "Platform Resources:"
    echo "  - OAM Component Definitions"
    echo "  - OAM Trait Definitions"
    echo "  - Crossplane XRDs and Compositions"
    echo "  - ClusterGateway CRDs"
    echo "  - Istio Gateways and VirtualServices"
    echo "  - Argo Workflow Templates"
    echo "  - Provider configurations"
    echo "  - Platform secrets"
    echo "  - Slack API Server"
    echo ""
    
    read -p "Continue with installation? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
    
    # Pre-flight checks
    verify_context
    check_prerequisites
    
    # Install core components
    install_istio
    install_knative
    install_argocd
    install_argo_workflows
    install_crossplane
    install_kubevela
    install_external_secrets
    
    # Install platform resources
    install_component_definitions
    install_trait_definitions
    install_crossplane_xrds
    install_clustergateway_crds
    install_istio_resources
    install_argo_templates
    configure_provider_rbac
    install_github_provider
    setup_secrets
    deploy_slack_api
    
    # Verify installation
    verify_installation
    
    echo ""
    echo "=========================================="
    echo "Platform Installation Complete!"
    echo "=========================================="
    echo ""
    print_info "Next steps:"
    echo "  1. Get ArgoCD admin password:"
    echo "     kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
    echo "  2. Access ArgoCD UI via port-forward:"
    echo "     kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "  3. Access Argo Workflows UI:"
    echo "     kubectl port-forward svc/argo-server -n argo 2746:2746"
    echo "  4. Get Istio Ingress Gateway IP:"
    echo "     kubectl get svc -n istio-system istio-ingressgateway"
}

# Run main function
main "$@"