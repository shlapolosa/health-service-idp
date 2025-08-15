#!/bin/bash

# AKS Platform Installation Script
# Installs all platform tools from AWS EKS to Azure AKS

set -e

echo "=========================================="
echo "AKS Platform Installation Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Verify kubectl context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current kubectl context: $CURRENT_CONTEXT"
echo ""

if [[ ! "$CURRENT_CONTEXT" == *"health-service-idp-aks"* ]]; then
    print_warning "Not on AKS context. Switch context with:"
    echo "kubectl config use-context health-service-idp-aks"
    exit 1
fi

# 1. Install Istio (Service Mesh)
install_istio() {
    echo ""
    echo "=========================================="
    echo "Installing Istio Service Mesh..."
    echo "=========================================="
    
    # Download and install Istio
    curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.1 sh -
    cd istio-1.20.1
    export PATH=$PWD/bin:$PATH
    
    # Install Istio with default configuration
    istioctl install --set profile=demo -y
    
    # Enable sidecar injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    cd ..
    print_status "Istio installed successfully"
}

# 2. Install Knative Serving
install_knative() {
    echo ""
    echo "=========================================="
    echo "Installing Knative Serving..."
    echo "=========================================="
    
    # Install Knative Serving CRDs
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-crds.yaml
    
    # Install Knative Serving core
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-core.yaml
    
    # Install Knative Istio controller
    kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.12.0/net-istio.yaml
    
    # Configure Knative to use Istio
    kubectl patch configmap/config-network \
      --namespace knative-serving \
      --type merge \
      --patch '{"data":{"ingress-class":"istio.ingress.networking.knative.dev"}}'
    
    # Configure domain
    kubectl patch configmap/config-domain \
      --namespace knative-serving \
      --type merge \
      --patch '{"data":{"example.com":""}}'
    
    print_status "Knative Serving installed successfully"
}

# 3. Install ArgoCD
install_argocd() {
    echo ""
    echo "=========================================="
    echo "Installing ArgoCD..."
    echo "=========================================="
    
    kubectl create namespace argocd || true
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    # Wait for ArgoCD to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
    
    print_status "ArgoCD installed successfully"
    print_warning "To access ArgoCD UI, run: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    print_warning "Default admin password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}

# 4. Install Argo Workflows
install_argo_workflows() {
    echo ""
    echo "=========================================="
    echo "Installing Argo Workflows..."
    echo "=========================================="
    
    kubectl create namespace argo || true
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.5/install.yaml
    
    # Create service account for workflows
    kubectl create rolebinding default-admin --clusterrole=admin --serviceaccount=argo:default -n argo || true
    
    # Patch argo-server to disable auth for development
    kubectl patch deployment argo-server -n argo --patch='{"spec":{"template":{"spec":{"containers":[{"name":"argo-server","args":["server","--auth-mode=server"]}]}}}}'
    
    print_status "Argo Workflows installed successfully"
}

# 5. Install Argo Events
install_argo_events() {
    echo ""
    echo "=========================================="
    echo "Installing Argo Events..."
    echo "=========================================="
    
    kubectl create namespace argo-events || true
    
    # Install Argo Events
    kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
    
    # Install EventBus
    kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/examples/eventbus/native.yaml
    
    print_status "Argo Events installed successfully"
}

# 6. Install Crossplane
install_crossplane() {
    echo ""
    echo "=========================================="
    echo "Installing Crossplane..."
    echo "=========================================="
    
    kubectl create namespace crossplane-system || true
    
    # Add Crossplane Helm repository
    helm repo add crossplane-stable https://charts.crossplane.io/stable
    helm repo update
    
    # Install Crossplane
    helm install crossplane \
      --namespace crossplane-system \
      --create-namespace \
      crossplane-stable/crossplane \
      --version 1.14.0 \
      --wait
    
    print_status "Crossplane core installed successfully"
    
    # Install providers after Crossplane is ready
    echo "Installing Crossplane providers..."
    
    # Wait for Crossplane to be ready
    kubectl wait --for=condition=healthy --timeout=300s provider/crossplane -n crossplane-system 2>/dev/null || true
    
    # Install AWS Provider
    cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-aws:v0.46.0
EOF
    
    # Install Kubernetes Provider
    cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-kubernetes
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-kubernetes:v0.9.0
EOF
    
    # Install Helm Provider
    cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-helm
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-helm:v0.15.0
EOF
    
    # Install GitHub Provider
    cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-upjet-github
spec:
  package: xpkg.upbound.io/upbound/provider-github:v0.13.0
EOF
    
    print_status "Crossplane providers configured"
}

# 7. Install KubeVela
install_kubevela() {
    echo ""
    echo "=========================================="
    echo "Installing KubeVela (OAM Implementation)..."
    echo "=========================================="
    
    # Install Vela core
    helm repo add kubevela https://charts.kubevela.net/core
    helm repo update
    helm install --create-namespace -n vela-system kubevela kubevela/vela-core --version 1.9.7 --wait
    
    # Install VelaUX (Optional UI)
    helm install velaux kubevela/velaux -n vela-system --version 1.9.7
    
    print_status "KubeVela installed successfully"
}

# 8. Create necessary namespaces and configs
setup_namespaces() {
    echo ""
    echo "=========================================="
    echo "Setting up namespaces and configurations..."
    echo "=========================================="
    
    # Create default namespace if not exists
    kubectl create namespace default || true
    
    # Label default namespace for Istio injection
    kubectl label namespace default istio-injection=enabled --overwrite
    
    print_status "Namespaces configured"
}

# 9. Install Custom Components (Slack API Server prerequisites)
install_custom_components() {
    echo ""
    echo "=========================================="
    echo "Installing custom components..."
    echo "=========================================="
    
    # Create a simple PostgreSQL deployment for Slack API server
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
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
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: default
spec:
  ports:
  - port: 5432
    targetPort: 5432
  selector:
    app: postgres
EOF
    
    print_status "Custom components installed"
}

# 10. Verification function
verify_installation() {
    echo ""
    echo "=========================================="
    echo "Verifying installations..."
    echo "=========================================="
    
    # Check Istio
    kubectl get pods -n istio-system --no-headers 2>/dev/null | head -1 > /dev/null && print_status "Istio: OK" || print_error "Istio: Failed"
    
    # Check Knative
    kubectl get pods -n knative-serving --no-headers 2>/dev/null | head -1 > /dev/null && print_status "Knative: OK" || print_error "Knative: Failed"
    
    # Check ArgoCD
    kubectl get pods -n argocd --no-headers 2>/dev/null | head -1 > /dev/null && print_status "ArgoCD: OK" || print_error "ArgoCD: Failed"
    
    # Check Argo Workflows
    kubectl get pods -n argo --no-headers 2>/dev/null | head -1 > /dev/null && print_status "Argo Workflows: OK" || print_error "Argo Workflows: Failed"
    
    # Check Argo Events
    kubectl get pods -n argo-events --no-headers 2>/dev/null | head -1 > /dev/null && print_status "Argo Events: OK" || print_error "Argo Events: Failed"
    
    # Check Crossplane
    kubectl get pods -n crossplane-system --no-headers 2>/dev/null | head -1 > /dev/null && print_status "Crossplane: OK" || print_error "Crossplane: Failed"
    
    # Check KubeVela
    kubectl get pods -n vela-system --no-headers 2>/dev/null | head -1 > /dev/null && print_status "KubeVela: OK" || print_error "KubeVela: Failed"
    
    echo ""
    echo "=========================================="
    echo "Platform Component Status:"
    echo "=========================================="
    kubectl get pods -A | grep -E "istio|knative|argo|crossplane|vela|postgres" | head -20
}

# Main installation flow
main() {
    echo "This script will install the following components:"
    echo "  - Istio (Service Mesh)"
    echo "  - Knative Serving (Serverless)"
    echo "  - ArgoCD (GitOps)"
    echo "  - Argo Workflows (Workflow Engine)"
    echo "  - Argo Events (Event-driven Automation)"
    echo "  - Crossplane (Infrastructure as Code)"
    echo "  - KubeVela (OAM Implementation)"
    echo "  - PostgreSQL (Database)"
    echo ""
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
    
    # Run installations in order
    setup_namespaces
    install_istio
    install_knative
    install_argocd
    install_argo_workflows
    install_argo_events
    install_crossplane
    install_kubevela
    install_custom_components
    
    # Verify all installations
    verify_installation
    
    echo ""
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Configure Crossplane providers with credentials"
    echo "2. Deploy OAM ComponentDefinitions and TraitDefinitions"
    echo "3. Configure ArgoCD to watch your GitOps repository"
    echo "4. Deploy the Slack API server"
    echo ""
    echo "Access points:"
    echo "  ArgoCD UI: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "  Argo Workflows: kubectl port-forward svc/argo-server -n argo 2746:2746"
    echo "  VelaUX: kubectl port-forward svc/velaux -n vela-system 8090:80"
}

# Run main function
main