#!/bin/bash

# Optimized AKS Platform Installation Script
# Uses existing local tools when available

set -e

echo "=========================================="
echo "Optimized AKS Platform Installation"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 1. Install Istio using existing installation
install_istio() {
    echo "Installing Istio..."
    
    # Check if istioctl exists locally
    if command -v istioctl &> /dev/null; then
        print_status "Using existing istioctl"
        istioctl install --set profile=demo -y
    elif [ -d "/Users/socrateshlapolosa/Development/health-service-idp/istio-1.20.1" ]; then
        print_status "Using local Istio 1.20.1"
        cd /Users/socrateshlapolosa/Development/health-service-idp/istio-1.20.1
        export PATH=$PWD/bin:$PATH
        istioctl install --set profile=demo -y
        cd -
    else
        print_warning "Istio not found, downloading..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.1 sh -
        cd istio-1.20.1
        export PATH=$PWD/bin:$PATH
        istioctl install --set profile=demo -y
        cd ..
    fi
    
    # Note: Not enabling istio-injection on default namespace to avoid breaking jobs
    # kubectl label namespace default istio-injection=enabled --overwrite
    print_status "Istio installed"
}

# 2. Quick install all other components
quick_install() {
    echo ""
    echo "Installing platform components..."
    
    # Knative Serving
    echo "Installing Knative Serving..."
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-crds.yaml || true
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-core.yaml || true
    kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.12.0/net-istio.yaml || true
    
    # Configure Knative
    kubectl patch configmap/config-network \
      --namespace knative-serving \
      --type merge \
      --patch '{"data":{"ingress-class":"istio.ingress.networking.knative.dev"}}' || true
    
    print_status "Knative installed"
    
    # ArgoCD
    echo "Installing ArgoCD..."
    kubectl create namespace argocd || true
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml || true
    print_status "ArgoCD installed"
    
    # Argo Workflows  
    echo "Installing Argo Workflows..."
    kubectl create namespace argo || true
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.5/install.yaml || true
    kubectl create rolebinding default-admin --clusterrole=admin --serviceaccount=argo:default -n argo || true
    print_status "Argo Workflows installed"
    
    # Argo Events
    echo "Installing Argo Events..."
    kubectl create namespace argo-events || true
    kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml || true
    kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/examples/eventbus/native.yaml || true
    print_status "Argo Events installed"
    
    # Crossplane via Helm
    echo "Installing Crossplane..."
    kubectl create namespace crossplane-system || true
    helm repo add crossplane-stable https://charts.crossplane.io/stable || true
    helm repo update
    helm upgrade --install crossplane \
      --namespace crossplane-system \
      crossplane-stable/crossplane \
      --version 1.14.0 \
      --wait --timeout 5m || true
    print_status "Crossplane installed"
    
    # KubeVela via Helm
    echo "Installing KubeVela..."
    helm repo add kubevela https://charts.kubevela.net/core || true
    helm repo update
    helm upgrade --install --create-namespace -n vela-system kubevela kubevela/vela-core --version 1.9.7 --wait --timeout 5m || true
    print_status "KubeVela installed"
    
    # PostgreSQL for testing
    echo "Installing PostgreSQL..."
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: slackapi
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          value: postgres123
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: default
spec:
  ports:
  - port: 5432
  selector:
    app: postgres
EOF
    print_status "PostgreSQL installed"
}

# 3. Install Crossplane Providers
install_providers() {
    echo ""
    echo "Installing Crossplane Providers..."
    
    kubectl apply -f - <<EOF
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-aws:v0.46.0
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-kubernetes
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-kubernetes:v0.9.0
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-helm
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-helm:v0.15.0
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-upjet-github
spec:
  package: xpkg.upbound.io/upbound/provider-github:v0.13.0
EOF
    print_status "Crossplane providers configured"
}

# 4. Install External Secrets Operator
install_external_secrets() {
    echo ""
    echo "Installing External Secrets Operator..."
    
    helm repo add external-secrets https://charts.external-secrets.io || true
    helm repo update
    helm upgrade --install external-secrets \
      external-secrets/external-secrets \
      -n external-secrets-system \
      --create-namespace \
      --set installCRDs=true \
      --wait --timeout 5m || true
    print_status "External Secrets Operator installed"
}

# 5. Note: Platform-specific resources are installed separately
# Use ./install-platform-resources.sh to install:
#   - ComponentDefinitions (15 working: excluding application-infrastructure, clickhouse)
#   - TraitDefinitions (4 specific ones from AWS)
#   - Crossplane XRDs (7 specific ones from AWS)
#   - Istio Gateways and VirtualServices
#   - Argo Workflow Templates
#   - Secrets and Service Accounts

# 10. Quick verification
verify() {
    echo ""
    echo "=========================================="
    echo "Verification"
    echo "=========================================="
    
    echo "Checking pod status..."
    kubectl get pods -n istio-system --no-headers | wc -l | xargs -I {} echo "Istio pods: {}"
    kubectl get pods -n knative-serving --no-headers | wc -l | xargs -I {} echo "Knative pods: {}"
    kubectl get pods -n argocd --no-headers | wc -l | xargs -I {} echo "ArgoCD pods: {}"
    kubectl get pods -n argo --no-headers | wc -l | xargs -I {} echo "Argo Workflows pods: {}"
    kubectl get pods -n argo-events --no-headers | wc -l | xargs -I {} echo "Argo Events pods: {}"
    kubectl get pods -n crossplane-system --no-headers | wc -l | xargs -I {} echo "Crossplane pods: {}"
    kubectl get pods -n vela-system --no-headers | wc -l | xargs -I {} echo "KubeVela pods: {}"
    
    echo ""
    print_status "Installation complete!"
    echo ""
    echo "Access points:"
    echo "  ArgoCD: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "  Argo Workflows: kubectl port-forward svc/argo-server -n argo 2746:2746"
}

# Main execution
main() {
    echo "=========================================="
    echo "Starting AKS Platform Installation"
    echo "=========================================="
    echo ""
    
    # Core platform components
    install_istio
    quick_install
    install_providers
    install_external_secrets
    
    # Verification
    verify
    
    echo ""
    echo "=========================================="
    echo "Platform installation complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Run platform resources installation:"
    echo "   ./install-platform-resources.sh"
    echo "2. Create necessary secrets (Docker, GitHub, Slack)"
    echo "3. Deploy Slack API server"
    echo "4. Run infrastructure health check:"
    echo "   ./scripts/infrastructure-health-check-enhanced.sh"
    echo ""
}

main