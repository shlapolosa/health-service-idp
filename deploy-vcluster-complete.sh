#!/bin/bash

# Complete vcluster deployment script with all tools
# This script creates a vcluster with Istio, ArgoCD, Knative, and KubeVela

set -euo pipefail

# Configuration
CLUSTER_NAME="socrateshlapolosa-karpenter-demo"
VCLUSTER_NAME="architecture-vizualisation"
VCLUSTER_NAMESPACE="arch-viz"
AWS_REGION="us-west-2"

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

# Check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    check_command kubectl
    check_command helm
    check_command vcluster
    check_command aws
    log_success "All prerequisites are installed"
}

# Check and set context to host cluster
ensure_host_context() {
    log_info "Ensuring we're in the host cluster context..."
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    
    current_context=$(kubectl config current-context)
    if [[ $current_context != *"$CLUSTER_NAME"* ]]; then
        log_error "Not in the correct context. Expected: $CLUSTER_NAME, Got: $current_context"
        exit 1
    fi
    log_success "Connected to host cluster: $current_context"
}

# Check if managed node group is ready
check_managed_nodes() {
    log_info "Checking managed node group status..."
    
    # Wait for at least one ready node
    timeout=300
    elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        ready_nodes=$(kubectl get nodes --no-headers | grep Ready | wc -l)
        if [[ $ready_nodes -gt 0 ]]; then
            log_success "Managed node group is ready with $ready_nodes nodes"
            return 0
        fi
        log_info "Waiting for managed nodes to be ready... ($elapsed/$timeout seconds)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    log_error "Managed nodes are not ready after $timeout seconds"
    exit 1
}

# Create vcluster namespace
create_vcluster_namespace() {
    log_info "Creating vcluster namespace: $VCLUSTER_NAMESPACE"
    
    if kubectl get namespace $VCLUSTER_NAMESPACE &> /dev/null; then
        log_warn "Namespace $VCLUSTER_NAMESPACE already exists"
    else
        kubectl create namespace $VCLUSTER_NAMESPACE
        log_success "Created namespace: $VCLUSTER_NAMESPACE"
    fi
}

# Create vcluster values file with Karpenter configuration
create_vcluster_values() {
    log_info "Creating vcluster values file..."
    
    cat > vcluster-values.yaml << EOF
# Minimal vcluster configuration that works with latest chart version
sync:
  toHost:
    pods:
      enabled: true
      enforceTolerations:
        - vclusterID=architecture-vizualisation:NoSchedule
    persistentVolumes:
      enabled: true
    persistentVolumeClaims:
      enabled: true
    storageClasses:
      enabled: true
    ingresses:
      enabled: true

# Enable CoreDNS (not embedded - that's pro only)
controlPlane:
  coredns:
    enabled: true
    embedded: false

# Service CIDR
serviceCIDR: "10.96.0.0/12"
EOF

    log_success "Created vcluster-values.yaml"
}

# Deploy vcluster
deploy_vcluster() {
    log_info "Deploying vcluster: $VCLUSTER_NAME"
    
    # Add Loft Helm repository
    helm repo add loft https://charts.loft.sh || log_warn "Loft repo already added"
    helm repo update
    
    # Check if vcluster already exists
    if helm list -n $VCLUSTER_NAMESPACE | grep -q $VCLUSTER_NAME; then
        log_warn "vcluster $VCLUSTER_NAME already exists, upgrading..."
        helm upgrade $VCLUSTER_NAME loft/vcluster \
            --namespace $VCLUSTER_NAMESPACE \
            --values vcluster-values.yaml \
            --wait --timeout 10m
    else
        helm install $VCLUSTER_NAME loft/vcluster \
            --namespace $VCLUSTER_NAMESPACE \
            --values vcluster-values.yaml \
            --wait --timeout 10m
    fi
    
    log_success "vcluster deployed successfully"
}

# Wait for vcluster to be ready
wait_for_vcluster() {
    log_info "Waiting for vcluster to be ready..."
    
    timeout=600
    elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if kubectl get pod -n $VCLUSTER_NAMESPACE -l app=vcluster | grep -q Running; then
            log_success "vcluster is running"
            break
        fi
        log_info "Waiting for vcluster pod to be ready... ($elapsed/$timeout seconds)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log_error "vcluster did not become ready within $timeout seconds"
        exit 1
    fi
}

# Connect to vcluster
connect_to_vcluster() {
    log_info "Connecting to vcluster..."
    
    # Disconnect any existing vcluster connection
    vcluster disconnect 2>/dev/null || true
    
    # Connect to the new vcluster
    vcluster connect $VCLUSTER_NAME --namespace $VCLUSTER_NAMESPACE
    
    # Verify connection
    current_context=$(kubectl config current-context)
    if [[ $current_context != *"vcluster_${VCLUSTER_NAME}"* ]]; then
        log_error "Failed to connect to vcluster. Current context: $current_context"
        exit 1
    fi
    
    log_success "Connected to vcluster: $current_context"
}

# Install Istio
install_istio() {
    log_info "Installing Istio..."
    
    # Download and install istioctl if not present
    if ! command -v istioctl &> /dev/null; then
        log_info "Downloading istioctl..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.1 sh -
        export PATH="$PWD/istio-1.20.1/bin:$PATH"
    fi
    
    # Install Istio
    istioctl install --set values.defaultRevision=default -y
    
    # Enable Istio injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    # Verify installation
    kubectl wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
    
    log_success "Istio installed successfully"
}

# Install Knative
install_knative() {
    log_info "Installing Knative Serving..."
    
    # Install Knative Serving CRDs
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.3/serving-crds.yaml
    
    # Install Knative Serving core
    kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.3/serving-core.yaml
    
    # Install Knative Istio controller
    kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.12.0/net-istio.yaml
    
    # Wait for Knative to be ready
    kubectl wait --for=condition=ready pod -l app=controller -n knative-serving --timeout=300s
    kubectl wait --for=condition=ready pod -l app=activator -n knative-serving --timeout=300s
    
    log_success "Knative Serving installed successfully"
}

# Install ArgoCD
install_argocd() {
    log_info "Installing ArgoCD..."
    
    # Create ArgoCD namespace
    kubectl create namespace argocd || log_warn "ArgoCD namespace already exists"
    
    # Install ArgoCD
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    # Wait for ArgoCD to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=600s
    
    # Get initial admin password
    log_info "Getting ArgoCD admin password..."
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d > argocd-admin-password.txt
    
    log_success "ArgoCD installed successfully. Admin password saved to argocd-admin-password.txt"
}

# Install KubeVela
install_kubevela() {
    log_info "Installing KubeVela..."
    
    # Add KubeVela Helm repository
    helm repo add kubevela https://kubevela.github.io/charts || log_warn "KubeVela repo already added"
    helm repo update
    
    # Install KubeVela
    helm install vela-core kubevela/vela-core \
        --namespace vela-system \
        --create-namespace \
        --wait --timeout 10m
    
    # Wait for KubeVela to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=vela-core -n vela-system --timeout=300s
    
    log_success "KubeVela installed successfully"
}

# Create Docker Hub secret for image pulls
create_docker_secret() {
    log_info "Creating Docker Hub secret..."
    
    # Prompt for Docker Hub credentials if not set in environment
    if [[ -z "${DOCKER_USERNAME:-}" ]]; then
        read -p "Enter Docker Hub username: " DOCKER_USERNAME
    fi
    
    if [[ -z "${DOCKER_PASSWORD:-}" ]]; then
        read -s -p "Enter Docker Hub password/token: " DOCKER_PASSWORD
        echo
    fi
    
    # Create Docker registry secret
    kubectl create secret docker-registry docker-hub-secret \
        --docker-server=docker.io \
        --docker-username=$DOCKER_USERNAME \
        --docker-password=$DOCKER_PASSWORD \
        --docker-email=$DOCKER_USERNAME@docker.io \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Docker Hub secret created"
}

# Configure external access
configure_external_access() {
    log_info "Configuring external access..."
    
    # Get Istio ingress gateway load balancer hostname
    LB_HOSTNAME=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    if [[ -z "$LB_HOSTNAME" ]]; then
        log_warn "Load balancer hostname not available yet. Waiting..."
        sleep 30
        LB_HOSTNAME=$(kubectl get service istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    if [[ -n "$LB_HOSTNAME" ]]; then
        # Configure Knative domain
        kubectl patch configmap config-domain -n knative-serving --patch "{\"data\":{\"$LB_HOSTNAME\":\"\"}}"
        log_success "Configured external access with hostname: $LB_HOSTNAME"
        
        # Save the hostname for reference
        echo $LB_HOSTNAME > external-hostname.txt
        log_info "External hostname saved to external-hostname.txt"
    else
        log_warn "Could not get load balancer hostname"
    fi
}

# Deploy sample microservices
deploy_sample_services() {
    log_info "Deploying sample microservices..."
    
    # Deploy Redis
    kubectl apply -f redis-deployment.yaml || log_warn "Redis deployment file not found, skipping"
    
    # Deploy microservices if their Knative service files exist
    for service in orchestration-service streamlit-frontend application-architect-anthropic business-architect-anthropic; do
        if [[ -f "microservices/$service/knative-service.yaml" ]]; then
            log_info "Deploying $service..."
            kubectl apply -f "microservices/$service/knative-service.yaml"
        else
            log_warn "Knative service file for $service not found, skipping"
        fi
    done
    
    log_success "Sample microservices deployed"
}

# Verify all components
verify_installation() {
    log_info "Verifying installation..."
    
    # Check vcluster
    kubectl get pod -n $VCLUSTER_NAMESPACE -l app=vcluster
    
    # Check Istio
    kubectl get pod -n istio-system
    
    # Check Knative
    kubectl get pod -n knative-serving
    
    # Check ArgoCD
    kubectl get pod -n argocd
    
    # Check KubeVela
    kubectl get pod -n vela-system
    
    log_success "All components appear to be running"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f vcluster-values.yaml
}

# Main execution
main() {
    log_info "Starting complete vcluster deployment..."
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    check_prerequisites
    ensure_host_context
    check_managed_nodes
    create_vcluster_namespace
    create_vcluster_values
    deploy_vcluster
    wait_for_vcluster
    connect_to_vcluster
    
    # Install all tools in vcluster
    install_istio
    install_knative
    install_argocd
    install_kubevela
    
    # Configure access and deploy services
    create_docker_secret
    configure_external_access
    deploy_sample_services
    verify_installation
    
    log_success "Complete vcluster deployment finished successfully!"
    log_info "You can now use: vcluster connect $VCLUSTER_NAME --namespace $VCLUSTER_NAMESPACE"
    
    # Show access information
    if [[ -f external-hostname.txt ]]; then
        hostname=$(cat external-hostname.txt)
        log_info "External access hostname: $hostname"
        log_info "Add to your hosts file: <ip> <service-name>.default.$hostname"
    fi
    
    if [[ -f argocd-admin-password.txt ]]; then
        log_info "ArgoCD admin password: $(cat argocd-admin-password.txt)"
    fi
}

# Run main function
main "$@"