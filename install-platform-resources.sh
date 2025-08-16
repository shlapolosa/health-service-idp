#!/bin/bash

# Platform Resources Installation Script
# Installs ONLY the specific resources from AWS EKS cluster to AKS

set -e

echo "=========================================="
echo "Platform Resources Installation"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verify kubectl context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current kubectl context: $CURRENT_CONTEXT"

if [[ ! "$CURRENT_CONTEXT" == *"health-service-idp-aks"* ]] && [[ ! "$CURRENT_CONTEXT" == *"health-idp-uae-aks"* ]]; then
    print_warning "Not on AKS context. Please switch with:"
    echo "kubectl config use-context health-service-idp-aks or health-idp-uae-aks"
    exit 1
fi

# 1. Export ComponentDefinitions from project (17 specific ones)
install_component_definitions() {
    echo ""
    echo "Installing ComponentDefinitions..."
    
    # These are the 17 ComponentDefinitions from AWS cluster
    COMPONENT_DEFS=(
        "auth0-idp"
        "camunda-orchestrator"
        "graphql-gateway"
        "graphql-platform"
        "identity-service"
        "kafka"
        "mongodb"
        "neon-postgres"
        "postgresql"
        "rasa-chatbot"
        "realtime-platform"
        "redis"
        "vcluster"
        "webservice"
        "webservice-k8s"
    )
    
    # First, try to find and apply existing definitions
    for comp in "${COMPONENT_DEFS[@]}"; do
        echo "  Looking for $comp ComponentDefinition..."
        
        # Search for the file in the project
        FILE=$(find /Users/socrateshlapolosa/Development/health-service-idp -name "*${comp}*" -path "*component*" -name "*.yaml" 2>/dev/null | head -1)
        
        if [ -n "$FILE" ]; then
            echo "    Found: $FILE"
            kubectl apply -f "$FILE" || print_warning "    Failed to apply $comp"
        else
            print_warning "    File not found for $comp"
        fi
    done
    
    print_status "ComponentDefinitions processed"
}

# 2. Install TraitDefinitions (4 specific ones)
install_trait_definitions() {
    echo ""
    echo "Installing TraitDefinitions..."
    
    TRAIT_DEFS=(
        "autoscaler"
        "ingress"
        "kafka-consumer"
        "kafka-producer"
    )
    
    for trait in "${TRAIT_DEFS[@]}"; do
        echo "  Looking for $trait TraitDefinition..."
        
        FILE=$(find /Users/socrateshlapolosa/Development/health-service-idp -name "*${trait}*" -path "*trait*" -name "*.yaml" 2>/dev/null | head -1)
        
        if [ -n "$FILE" ]; then
            echo "    Found: $FILE"
            kubectl apply -f "$FILE" || print_warning "    Failed to apply $trait"
        else
            print_warning "    File not found for $trait"
        fi
    done
    
    print_status "TraitDefinitions processed"
}

# 3. Install Crossplane XRDs (7 specific ones)
install_crossplane_xrds() {
    echo ""
    echo "Installing Crossplane XRDs..."
    
    # Map of XRD names to likely file names
    declare -A XRD_FILES
    XRD_FILES["xappcontainerclaims.platform.example.org"]="app-container-claim-xrd.yaml"
    XRD_FILES["xapplicationclaims.platform.example.org"]="application-claim-xrd.yaml"
    XRD_FILES["xgraphqlplatformclaims.platform.example.org"]="graphql-platform-claim-xrd.yaml"
    XRD_FILES["xinfrastructureclaims.platform.io"]="infrastructure-claim-xrd.yaml"
    XRD_FILES["xorchestrationplatformclaims.platform.example.org"]="orchestration-platform-claim-xrd.yaml"
    XRD_FILES["xrealtimeplatformclaims.platform.example.org"]="realtime-platform-claim-xrd.yaml"
    XRD_FILES["xvclusterenvironmentclaims.platform.example.org"]="vcluster-environment-claim-xrd.yaml"
    
    for xrd in "${!XRD_FILES[@]}"; do
        FILE_NAME="${XRD_FILES[$xrd]}"
        echo "  Looking for $FILE_NAME..."
        
        FILE="/Users/socrateshlapolosa/Development/health-service-idp/crossplane/$FILE_NAME"
        
        if [ -f "$FILE" ]; then
            echo "    Found: $FILE"
            kubectl apply -f "$FILE" || print_warning "    Failed to apply $xrd"
        else
            print_warning "    File not found: $FILE"
        fi
    done
    
    # Also install the compositions
    echo "  Installing Crossplane Compositions..."
    for comp_file in /Users/socrateshlapolosa/Development/health-service-idp/crossplane/*-composition.yaml; do
        if [ -f "$comp_file" ]; then
            kubectl apply -f "$comp_file" || print_warning "    Failed to apply $(basename $comp_file)"
        fi
    done
    
    print_status "Crossplane XRDs and Compositions processed"
}

# 4. Install ClusterGateway CRDs for Multi-cluster Support
install_clustergateway_crds() {
    echo ""
    echo "Installing ClusterGateway CRDs for Multi-cluster Support..."
    
    CRD_DIR="/Users/socrateshlapolosa/Development/health-service-idp/crossplane/cluster-gateway"
    
    if [ -d "$CRD_DIR" ]; then
        echo "  Applying ClusterGateway CRDs..."
        kubectl apply -f "$CRD_DIR/clustergateway-cluster-crd.yaml" || print_warning "Failed to apply cluster CRD"
        kubectl apply -f "$CRD_DIR/clustergateway-core-crd.yaml" || print_warning "Failed to apply core CRD"
        print_status "ClusterGateway CRDs installed"
    else
        print_warning "ClusterGateway CRD directory not found: $CRD_DIR"
    fi
}

# 5. Install Istio Gateways and VirtualServices
install_istio_resources() {
    echo ""
    echo "Installing Istio Resources..."
    
    # Create manifest files instead of applying directly
    ISTIO_DIR="/Users/socrateshlapolosa/Development/health-service-idp/istio-resources"
    mkdir -p "$ISTIO_DIR"
    
    # Argo Workflows Gateway and VirtualService
    cat <<EOF > "$ISTIO_DIR/argo-workflows-gateway.yaml"
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: argo-workflows-gateway
  namespace: argo
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
  name: argo-workflows-ui
  namespace: argo
spec:
  hosts:
  - "*"
  gateways:
  - argo-workflows-gateway
  http:
  - match:
    - uri:
        prefix: /argo/
    rewrite:
      uri: /
    route:
    - destination:
        host: argo-server
        port:
          number: 2746
EOF
    
    kubectl apply -f "$ISTIO_DIR/argo-workflows-gateway.yaml" || true
    
    # ArgoCD Gateway and VirtualService
    cat <<EOF > "$ISTIO_DIR/argocd-gateway.yaml"
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: argocd-gateway
  namespace: argocd
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
  name: argocd-virtualservice
  namespace: argocd
spec:
  hosts:
  - "*"
  gateways:
  - argocd-gateway
  http:
  - match:
    - uri:
        prefix: /argocd
    rewrite:
      uri: /
    route:
    - destination:
        host: argocd-server
        port:
          number: 80
EOF
    kubectl apply -f "$ISTIO_DIR/argocd-gateway.yaml" || true
    
    # Slack API Gateway and VirtualService
    cat <<EOF > "$ISTIO_DIR/slack-api-gateway.yaml"
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
        host: slack-api-server
        port:
          number: 8000
EOF
    kubectl apply -f "$ISTIO_DIR/slack-api-gateway.yaml" || true
    
    print_status "Istio resources installed"
}

# 5. Install Argo Workflow Templates
install_argo_templates() {
    echo ""
    echo "Installing Argo Workflow Templates..."
    
    if [ -d "/Users/socrateshlapolosa/Development/health-service-idp/argo-workflows" ]; then
        for template in /Users/socrateshlapolosa/Development/health-service-idp/argo-workflows/*.yaml; do
            if [ -f "$template" ]; then
                echo "  Applying $(basename $template)..."
                kubectl apply -f "$template" -n argo || print_warning "    Failed to apply $(basename $template)"
            fi
        done
    else
        print_warning "Argo workflows directory not found"
    fi
    
    print_status "Argo workflow templates processed"
}

# 6. Configure Provider RBAC
configure_provider_rbac() {
    echo ""
    echo "Configuring Provider RBAC..."
    
    # Apply provider-kubernetes RBAC if manifest exists
    if [ -f "/Users/socrateshlapolosa/Development/health-service-idp/crossplane/provider-kubernetes-rbac.yaml" ]; then
        kubectl apply -f /Users/socrateshlapolosa/Development/health-service-idp/crossplane/provider-kubernetes-rbac.yaml || true
        print_status "Provider Kubernetes RBAC configured"
    else
        # Create RBAC manifest if it doesn't exist
        cat <<'EOF' > /Users/socrateshlapolosa/Development/health-service-idp/crossplane/provider-kubernetes-rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: crossplane-provider-kubernetes-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: crossplane-provider-kubernetes-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: crossplane-provider-kubernetes-admin
subjects:
- kind: ServiceAccount
  name: provider-kubernetes-fd7ab5be249e
  namespace: crossplane-system
EOF
        kubectl apply -f /Users/socrateshlapolosa/Development/health-service-idp/crossplane/provider-kubernetes-rbac.yaml || true
        print_status "Provider Kubernetes RBAC created and configured"
    fi
}

# 7. Install GitHub Provider
install_github_provider() {
    echo ""
    echo "Installing GitHub Provider..."
    
    # Install the provider
    cat <<EOF | kubectl apply -f - || true
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-upjet-github
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-upjet-github:v0.18.0
EOF
    
    # Wait for provider to be healthy
    echo "  Waiting for GitHub provider to be healthy..."
    kubectl wait --for=condition=healthy provider/provider-upjet-github --timeout=120s || true
    
    # Create ProviderConfigs if secret exists
    if kubectl get secret github-provider-secret -n crossplane-system &>/dev/null; then
        cat <<EOF | kubectl apply -f - || true
apiVersion: github.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: github-provider
spec:
  credentials:
    source: Secret
    secretRef:
      name: github-provider-secret
      namespace: crossplane-system
      key: credentials
---
apiVersion: github.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: Secret
    secretRef:
      name: github-provider-secret
      namespace: crossplane-system
      key: credentials
EOF
        print_status "GitHub provider and configs installed"
    else
        print_warning "GitHub provider secret not found. Run setup-secrets.sh first"
    fi
}

# 8. Install Service Accounts and Secrets
install_service_accounts() {
    echo ""
    echo "Installing Service Accounts..."
    
    # Create Knative Docker service account
    kubectl create serviceaccount knative-docker-sa -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl patch serviceaccount knative-docker-sa -n default -p '{"imagePullSecrets": [{"name": "docker-credentials"}]}' || true
    
    # Create Crossplane GitHub Provider service account
    kubectl create serviceaccount crossplane-github-provider -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding crossplane-github-provider-admin \
        --clusterrole=cluster-admin \
        --serviceaccount=default:crossplane-github-provider \
        --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Create Crossplane Admin service account for job execution
    kubectl create serviceaccount crossplane-admin -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding crossplane-admin-default-binding \
        --clusterrole=cluster-admin \
        --serviceaccount=default:crossplane-admin \
        --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Create Slack API Argo token if not exists
    if ! kubectl get secret slack-api-server-argo-token -n default &>/dev/null; then
        kubectl create secret generic slack-api-server-argo-token -n default \
            --from-literal=token=$(openssl rand -hex 32) || true
    fi
    
    print_status "Service accounts and tokens configured"
}

# 9. Install Registry Configuration
install_registry_config() {
    echo ""
    echo "Installing Multi-Registry Configuration..."
    
    # Apply registry configuration
    cat <<'EOF' | kubectl apply -f - || true
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-config
  namespace: default
data:
  # Primary registry configuration
  DEFAULT_REGISTRY: "docker.io"
  DEFAULT_REGISTRY_PATH: "socrates12345"
  
  # Azure Container Registry configuration
  ACR_REGISTRY: "healthidpuaeacr.azurecr.io"
  ACR_REGISTRY_PATH: ""
  
  # Region-specific registry selection
  # Set to "dockerhub" or "acr" based on deployment region
  ACTIVE_REGISTRY: "dockerhub"
  
  # Image pull policy
  IMAGE_PULL_POLICY: "IfNotPresent"
  
  # Fallback configuration
  ENABLE_FALLBACK: "true"
  FALLBACK_REGISTRY: "docker.io/socrates12345"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-config
  namespace: crossplane-system
data:
  # Primary registry configuration
  DEFAULT_REGISTRY: "docker.io"
  DEFAULT_REGISTRY_PATH: "socrates12345"
  
  # Azure Container Registry configuration
  ACR_REGISTRY: "healthidpuaeacr.azurecr.io"
  ACR_REGISTRY_PATH: ""
  
  # Region-specific registry selection
  # Set to "dockerhub" or "acr" based on deployment region
  ACTIVE_REGISTRY: "dockerhub"
  
  # Image pull policy
  IMAGE_PULL_POLICY: "IfNotPresent"
  
  # Fallback configuration
  ENABLE_FALLBACK: "true"
  FALLBACK_REGISTRY: "docker.io/socrates12345"
EOF
    
    print_status "Registry configuration installed"
}

# 10. Verification
verify_resources() {
    echo ""
    echo "=========================================="
    echo "Verification"
    echo "=========================================="
    
    echo "ComponentDefinitions:"
    kubectl get componentdefinitions --no-headers | wc -l | xargs -I {} echo "  Count: {}"
    
    echo "TraitDefinitions:"
    kubectl get traitdefinitions --no-headers | wc -l | xargs -I {} echo "  Count: {}"
    
    echo "Crossplane XRDs:"
    kubectl get xrd --no-headers | wc -l | xargs -I {} echo "  Count: {}"
    
    echo "ClusterGateway CRDs:"
    kubectl get crd | grep -c "clustergateways.*oam.dev" | xargs -I {} echo "  Count: {}"
    
    echo "Istio Gateways:"
    kubectl get gateway -A --no-headers | wc -l | xargs -I {} echo "  Count: {}"
    
    echo "VirtualServices:"
    kubectl get virtualservice -A --no-headers | wc -l | xargs -I {} echo "  Count: {}"
    
    echo "Argo WorkflowTemplates:"
    kubectl get workflowtemplate -n argo --no-headers 2>/dev/null | wc -l | xargs -I {} echo "  Count: {}"
}

# Main execution
main() {
    echo "This script will install the following specific resources from AWS cluster:"
    echo "  - 15 ComponentDefinitions (excluding application-infrastructure, clickhouse)"
    echo "  - 4 TraitDefinitions"
    echo "  - 7 Crossplane XRDs with Compositions"
    echo "  - 2 ClusterGateway CRDs for multi-cluster support"
    echo "  - 5 Istio Gateways (3 custom + 2 Knative)"
    echo "  - 3 VirtualServices"
    echo "  - Argo Workflow Templates"
    echo "  - Provider Kubernetes RBAC permissions"
    echo "  - GitHub Provider and ProviderConfigs"
    echo "  - Service Accounts and Secrets"
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
    
    install_component_definitions
    install_trait_definitions
    install_crossplane_xrds
    install_clustergateway_crds
    install_istio_resources
    install_argo_templates
    configure_provider_rbac
    install_github_provider
    install_service_accounts
    install_registry_config
    verify_resources
    
    echo ""
    print_status "Platform resources installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Create necessary secrets (Docker, GitHub, Slack)"
    echo "2. Deploy the Slack API server"
    echo "3. Run infrastructure health check"
}

main