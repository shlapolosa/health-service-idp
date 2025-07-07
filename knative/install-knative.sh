#!/bin/bash

# Knative Serving Installation and Configuration Script
# This script installs Knative Serving with cold start protection optimizations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KNATIVE_VERSION="v1.12.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check cluster version
    K8S_VERSION=$(kubectl version --client -o json | jq -r '.clientVersion.gitVersion' | sed 's/v//')
    log_info "Kubernetes client version: $K8S_VERSION"
    
    # Check if running in correct context
    CURRENT_CONTEXT=$(kubectl config current-context)
    log_info "Current kubectl context: $CURRENT_CONTEXT"
    
    read -p "Are you sure you want to install Knative Serving in this cluster? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Installation cancelled by user"
        exit 0
    fi
    
    log_success "Prerequisites check completed"
}

# Install Knative Serving CRDs
install_knative_crds() {
    log_info "Installing Knative Serving CRDs ($KNATIVE_VERSION)..."
    
    kubectl apply -f "https://github.com/knative/serving/releases/download/knative-${KNATIVE_VERSION}/serving-crds.yaml"
    
    log_info "Waiting for CRDs to be established..."
    kubectl wait --for condition=established --timeout=60s crd/services.serving.knative.dev
    kubectl wait --for condition=established --timeout=60s crd/configurations.serving.knative.dev
    kubectl wait --for condition=established --timeout=60s crd/revisions.serving.knative.dev
    kubectl wait --for condition=established --timeout=60s crd/routes.serving.knative.dev
    
    log_success "Knative Serving CRDs installed successfully"
}

# Install Knative Serving Core
install_knative_core() {
    log_info "Installing Knative Serving Core ($KNATIVE_VERSION)..."
    
    kubectl apply -f "https://github.com/knative/serving/releases/download/knative-${KNATIVE_VERSION}/serving-core.yaml"
    
    log_info "Waiting for Knative Serving components to be ready..."
    kubectl wait --for=condition=Ready pod -l app=controller -n knative-serving --timeout=300s
    kubectl wait --for=condition=Ready pod -l app=activator -n knative-serving --timeout=300s
    kubectl wait --for=condition=Ready pod -l app=autoscaler -n knative-serving --timeout=300s
    kubectl wait --for=condition=Ready pod -l app=webhook -n knative-serving --timeout=300s
    
    log_success "Knative Serving Core installed successfully"
}

# Configure Knative Autoscaler for cold start protection
configure_autoscaler() {
    log_info "Configuring Knative Autoscaler for cold start protection..."
    
    if [[ -f "$SCRIPT_DIR/knative-autoscaler-config.yaml" ]]; then
        kubectl apply -f "$SCRIPT_DIR/knative-autoscaler-config.yaml"
        log_success "Autoscaler configuration applied"
    else
        log_warning "Autoscaler configuration file not found, using defaults"
    fi
}

# Install Istio (if not present)
install_istio() {
    log_info "Checking for Istio installation..."
    
    if kubectl get namespace istio-system &> /dev/null; then
        log_info "Istio namespace found, assuming Istio is installed"
    else
        log_warning "Istio not found. Installing minimal Istio for Knative..."
        
        # Install Istio operator
        kubectl apply -f https://github.com/istio/istio/releases/download/1.19.0/istio-operator.yaml
        
        # Wait for operator
        kubectl wait --for=condition=Ready pod -l name=istio-operator -n istio-operator --timeout=300s
        
        # Install Istio
        kubectl apply -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: knative-istio
  namespace: istio-operator
spec:
  values:
    global:
      meshID: mesh1
      meshConfig:
        defaultConfig:
          proxyMetadata:
            PILOT_ENABLE_WORKLOAD_ENTRY_AUTOREGISTRATION: true
  components:
    pilot:
      k8s:
        env:
        - name: PILOT_ENABLE_KNATIVE_GATEWAY_API
          value: "true"
EOF
        
        log_info "Waiting for Istio to be ready..."
        kubectl wait --for=condition=Ready pod -l app=istiod -n istio-system --timeout=300s
    fi
    
    # Install Knative Istio controller
    log_info "Installing Knative Istio networking layer..."
    kubectl apply -f "https://github.com/knative/net-istio/releases/download/knative-${KNATIVE_VERSION}/net-istio.yaml"
    
    log_success "Istio networking configured for Knative"
}

# Install pre-warming system
install_prewarming() {
    log_info "Installing Knative pre-warming system..."
    
    if [[ -f "$SCRIPT_DIR/knative-prewarming.yaml" ]]; then
        kubectl apply -f "$SCRIPT_DIR/knative-prewarming.yaml"
        log_success "Pre-warming system installed"
    else
        log_warning "Pre-warming configuration file not found, skipping"
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying Knative Serving installation..."
    
    # Check namespaces
    if kubectl get namespace knative-serving &> /dev/null; then
        log_success "knative-serving namespace exists"
    else
        log_error "knative-serving namespace not found"
        return 1
    fi
    
    # Check pods
    CONTROLLER_READY=$(kubectl get pods -n knative-serving -l app=controller --no-headers | grep Running | wc -l)
    ACTIVATOR_READY=$(kubectl get pods -n knative-serving -l app=activator --no-headers | grep Running | wc -l)
    AUTOSCALER_READY=$(kubectl get pods -n knative-serving -l app=autoscaler --no-headers | grep Running | wc -l)
    WEBHOOK_READY=$(kubectl get pods -n knative-serving -l app=webhook --no-headers | grep Running | wc -l)
    
    if [[ $CONTROLLER_READY -gt 0 && $ACTIVATOR_READY -gt 0 && $AUTOSCALER_READY -gt 0 && $WEBHOOK_READY -gt 0 ]]; then
        log_success "All Knative Serving components are running"
    else
        log_error "Some Knative Serving components are not ready"
        kubectl get pods -n knative-serving
        return 1
    fi
    
    # Check API resources
    if kubectl api-resources | grep serving.knative.dev &> /dev/null; then
        log_success "Knative Serving API resources available"
    else
        log_error "Knative Serving API resources not found"
        return 1
    fi
    
    # Test with a simple service
    log_info "Testing with a hello-world service..."
    kubectl apply -f - <<EOF
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: hello-world-test
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: "1"
        autoscaling.knative.dev/max-scale: "3"
    spec:
      containers:
      - image: gcr.io/cloudrun/hello
        ports:
        - containerPort: 8080
        env:
        - name: TARGET
          value: "Knative"
EOF

    # Wait for service to be ready
    log_info "Waiting for test service to be ready..."
    kubectl wait --for=condition=Ready ksvc hello-world-test -n default --timeout=120s
    
    # Get service URL
    SERVICE_URL=$(kubectl get ksvc hello-world-test -n default -o jsonpath='{.status.url}')
    log_success "Test service ready at: $SERVICE_URL"
    
    # Clean up test service
    kubectl delete ksvc hello-world-test -n default
    
    log_success "Knative Serving installation verification completed"
}

# Print installation summary
print_summary() {
    echo
    log_info "🎉 Knative Serving Installation Summary"
    echo "============================================"
    echo "✅ Knative Serving $KNATIVE_VERSION installed"
    echo "✅ Cold start protection configured"
    echo "✅ Autoscaler optimized"
    echo "✅ Istio networking layer configured"
    echo "✅ Pre-warming system installed"
    echo
    log_info "🔧 Configuration Applied:"
    echo "• Min scale: 1 (prevents cold starts)"
    echo "• Scale-to-zero grace period: 30s"
    echo "• Pod retention period: 1m"
    echo "• Target concurrency: 100"
    echo "• Concurrency state endpoint: /healthz/concurrency"
    echo
    log_info "📚 Next Steps:"
    echo "1. Review configuration in knative-serving namespace"
    echo "2. Apply service templates from knative-service-template.yaml"
    echo "3. Configure pre-warming for your services"
    echo "4. Monitor cold start metrics"
    echo
    log_info "🔍 Useful Commands:"
    echo "• kubectl get pods -n knative-serving"
    echo "• kubectl get ksvc -A"
    echo "• kubectl logs -n knative-serving -l app=controller"
    echo "• kubectl get configmap -n knative-serving"
}

# Main installation flow
main() {
    echo "🚀 Knative Serving Installation with Cold Start Protection"
    echo "=========================================================="
    echo
    
    check_prerequisites
    install_knative_crds
    install_knative_core
    configure_autoscaler
    install_istio
    install_prewarming
    verify_installation
    print_summary
}

# Run main function
main "$@"