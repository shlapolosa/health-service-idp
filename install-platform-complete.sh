#!/bin/bash

# Complete Platform Installation Script for AKS
# Includes all necessary components and fixes

set -e

echo "=========================================="
echo "Complete Platform Installation for AKS"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Verify kubectl context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "Current kubectl context: $CURRENT_CONTEXT"

if [[ ! "$CURRENT_CONTEXT" == *"aks"* ]]; then
    print_warning "Not on AKS context. Please switch with:"
    echo "kubectl config use-context <your-aks-context>"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it with required variables."
    exit 1
fi

# Load environment variables
export $(grep -E "^(PERSONAL_ACCESS_TOKEN|GITHUB_USERNAME|DOCKER_USERNAME|SLACK_SIGNING_SECRET)=" .env | xargs)

# 1. Install Istio
install_istio() {
    echo ""
    echo "=========================================="
    echo "1. Installing Istio..."
    echo "=========================================="
    
    if kubectl get namespace istio-system &>/dev/null; then
        print_warning "Istio namespace exists, skipping installation"
    else
        istioctl install --set profile=default -y
        print_status "Istio installed"
    fi
    
    # Wait for Istio to be ready
    kubectl rollout status deployment/istiod -n istio-system --timeout=300s
    print_status "Istio control plane ready"
}

# 2. Install Knative
install_knative() {
    echo ""
    echo "=========================================="
    echo "2. Installing Knative Serving..."
    echo "=========================================="
    
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
    print_status "Knative ready"
}

# 3. Install ArgoCD
install_argocd() {
    echo ""
    echo "=========================================="
    echo "3. Installing ArgoCD..."
    echo "=========================================="
    
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    
    # Wait for ArgoCD to be ready
    kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
    print_status "ArgoCD installed"
}

# 4. Install Argo Workflows
install_argo_workflows() {
    echo ""
    echo "=========================================="
    echo "4. Installing Argo Workflows..."
    echo "=========================================="
    
    kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.5/install.yaml
    
    # Apply our custom Argo server configuration with auth-mode
    kubectl apply -f argo-workflows/argo-ui-subdomain.yaml
    
    # Create Argo service account and token
    kubectl create serviceaccount argo-workflows-admin -n argo --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding argo-workflows-admin-binding \
        --clusterrole=admin \
        --serviceaccount=argo:argo-workflows-admin \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create Argo token secret
    kubectl create token argo-workflows-admin -n argo | \
        kubectl create secret generic argo-token -n argo --from-file=token=/dev/stdin --dry-run=client -o yaml | \
        kubectl apply -f -
    
    # Copy token to default namespace for Slack API
    kubectl get secret argo-token -n argo -o yaml | \
        sed 's/namespace: argo/namespace: default/' | \
        kubectl apply -f -
    
    # Apply all workflow templates
    kubectl apply -f argo-workflows/
    
    print_status "Argo Workflows installed and configured"
}

# 5. Install Crossplane
install_crossplane() {
    echo ""
    echo "=========================================="
    echo "5. Installing Crossplane..."
    echo "=========================================="
    
    # Add Crossplane Helm repo
    helm repo add crossplane-stable https://charts.crossplane.io/stable
    helm repo update
    
    # Install Crossplane
    helm upgrade --install crossplane \
        --namespace crossplane-system \
        --create-namespace \
        crossplane-stable/crossplane \
        --version 1.15.1 \
        --wait
    
    print_status "Crossplane installed"
    
    # Wait for Crossplane to be ready
    kubectl wait --for=condition=ready pod -l app=crossplane -n crossplane-system --timeout=300s
    
    # Install Crossplane providers
    print_info "Installing Crossplane providers..."
    kubectl apply -f crossplane/providers.yaml
    
    # Wait for providers to be installed
    print_info "Waiting for providers to be healthy..."
    sleep 30
    
    # Wait for kubernetes provider to be healthy
    kubectl wait --for=condition=healthy provider.pkg.crossplane.io/provider-kubernetes --timeout=120s 2>/dev/null || true
    kubectl wait --for=condition=healthy provider.pkg.crossplane.io/provider-helm --timeout=120s 2>/dev/null || true
    
    # Apply provider configurations
    print_info "Applying provider configurations..."
    kubectl apply -f crossplane/kubernetes-provider-config.yaml
    kubectl apply -f crossplane/helm-provider-config.yaml
    
    # Apply RBAC for providers
    print_info "Applying provider RBAC..."
    kubectl apply -f crossplane/kubernetes-provider-rbac.yaml
    kubectl apply -f crossplane/helm-provider-rbac.yaml
    
    # Restart providers to pick up RBAC
    print_info "Restarting providers to apply RBAC..."
    kubectl delete pod -n crossplane-system -l pkg.crossplane.io/provider=provider-kubernetes --wait=false 2>/dev/null || true
    kubectl delete pod -n crossplane-system -l pkg.crossplane.io/provider=provider-helm --wait=false 2>/dev/null || true
    sleep 10
    
    print_status "Crossplane providers configured"
}

# 6. Install KubeVela
install_kubevela() {
    echo ""
    echo "=========================================="
    echo "6. Installing KubeVela..."
    echo "=========================================="
    
    # Install KubeVela
    helm repo add kubevela https://charts.kubevela.net/core
    helm repo update
    helm upgrade --install --create-namespace \
        --namespace vela-system \
        --version 1.9.11 \
        --wait kubevela \
        kubevela/vela-core
    
    print_status "KubeVela installed"
}

# 7. Install External Secrets Operator
install_external_secrets() {
    echo ""
    echo "=========================================="
    echo "7. Installing External Secrets Operator..."
    echo "=========================================="
    
    helm repo add external-secrets https://charts.external-secrets.io
    helm repo update
    helm upgrade --install external-secrets \
        external-secrets/external-secrets \
        -n external-secrets-system \
        --create-namespace \
        --wait
    
    print_status "External Secrets Operator installed"
}

# 8. Setup Secrets
setup_secrets() {
    echo ""
    echo "=========================================="
    echo "8. Setting up Secrets..."
    echo "=========================================="
    
    # Apply manual secrets
    if [ -f "manual-secrets.yaml" ]; then
        sed -e "s|\${PERSONAL_ACCESS_TOKEN}|${PERSONAL_ACCESS_TOKEN}|g" \
            -e "s|\${GITHUB_USERNAME}|${GITHUB_USERNAME}|g" \
            -e "s|\${DOCKER_USERNAME}|${DOCKER_USERNAME}|g" \
            -e "s|\${SLACK_SIGNING_SECRET}|${SLACK_SIGNING_SECRET}|g" \
            manual-secrets.yaml | kubectl apply -f -
        print_status "Manual secrets applied"
    fi
    
    # Create GitHub provider service account
    kubectl create serviceaccount crossplane-github-provider -n default --dry-run=client -o yaml | kubectl apply -f -
    kubectl create clusterrolebinding crossplane-github-provider-admin \
        --clusterrole=cluster-admin \
        --serviceaccount=default:crossplane-github-provider \
        --dry-run=client -o yaml | kubectl apply -f -
    print_status "GitHub provider service account created"
    
    # Create Azure credentials for GitHub Actions if using Azure
    if [[ "$CURRENT_CONTEXT" == *"aks"* ]]; then
        print_info "Setting up Azure credentials for GitHub Actions..."
        
        # Check if Azure CLI is logged in
        if az account show &>/dev/null; then
            SUBSCRIPTION_ID=$(az account show --query id -o tsv)
            
            # Create service principal if it doesn't exist
            print_info "Creating/updating Azure service principal for GitHub Actions..."
            SP_OUTPUT=$(az ad sp create-for-rbac \
                --name "health-idp-github-actions" \
                --role "Contributor" \
                --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/health-service-idp-uae-rg" \
                --sdk-auth 2>/dev/null || echo "")
            
            if [ ! -z "$SP_OUTPUT" ]; then
                # Save Azure credentials to a file
                echo "$SP_OUTPUT" > /tmp/azure-creds.json
                
                # Extract client ID for ACR permissions
                CLIENT_ID=$(echo "$SP_OUTPUT" | jq -r '.clientId')
                
                # Add ACR permissions
                print_info "Adding ACR permissions to service principal..."
                az role assignment create \
                    --assignee "$CLIENT_ID" \
                    --role "AcrPush" \
                    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/health-service-idp-uae-rg/providers/Microsoft.ContainerRegistry/registries/healthidpuaeacr" \
                    2>/dev/null || true
                
                az role assignment create \
                    --assignee "$CLIENT_ID" \
                    --role "AcrPull" \
                    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/health-service-idp-uae-rg/providers/Microsoft.ContainerRegistry/registries/healthidpuaeacr" \
                    2>/dev/null || true
                
                # Create Kubernetes secret
                kubectl create secret generic azure-credentials \
                    --from-file=azure-creds.json=/tmp/azure-creds.json \
                    -n default \
                    --dry-run=client -o yaml | kubectl apply -f -
                
                print_status "Azure credentials created with ACR permissions"
                
                # Clean up temp file
                rm -f /tmp/azure-creds.json
            else
                print_warning "Could not create Azure service principal - manual setup may be required"
            fi
        else
            print_warning "Azure CLI not logged in - skipping Azure credentials setup"
            print_info "To set up Azure credentials manually:"
            print_info "  1. az login"
            print_info "  2. Run this script again, or manually create service principal"
        fi
    fi
}

# 9. Apply Platform Resources
apply_platform_resources() {
    echo ""
    echo "=========================================="
    echo "9. Applying Platform Resources..."
    echo "=========================================="
    
    # Apply Crossplane XRDs (Custom Resource Definitions)
    print_info "Applying Crossplane XRDs..."
    kubectl apply -f crossplane/app-container-claim-xrd.yaml
    kubectl apply -f crossplane/vcluster-environment-claim-xrd.yaml
    kubectl apply -f crossplane/application-claim-xrd.yaml 2>/dev/null || true
    
    # Note: If experiencing Docker Hub throttling in UAE/Dubai region,
    # consider updating alpine/k8s:1.28.4 image references in compositions
    # to use a local registry or mirror
    
    # Apply Crossplane Compositions
    print_info "Applying Crossplane Compositions..."
    kubectl apply -f crossplane/app-container-claim-composition.yaml
    kubectl apply -f crossplane/vcluster-environment-claim-composition.yaml
    kubectl apply -f crossplane/application-claim-composition.yaml 2>/dev/null || true
    
    # Apply OAM definitions
    print_info "Applying OAM definitions..."
    kubectl apply -f crossplane/oam/consolidated-component-definitions-fixed.yaml
    kubectl apply -f crossplane/oam/
    
    # Apply ArgoCD RBAC for Crossplane
    print_info "Applying ArgoCD RBAC for Crossplane..."
    kubectl apply -f crossplane/argocd-rbac-fix.yaml 2>/dev/null || true
    
    # Apply registry configuration
    kubectl apply -f crossplane/registry-config.yaml
    
    # Apply image pre-pull DaemonSet to avoid Docker Hub throttling
    print_info "Applying image pre-pull DaemonSet..."
    kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: image-prepuller
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: image-prepuller
  template:
    metadata:
      labels:
        name: image-prepuller
    spec:
      initContainers:
      # Pre-pull stedolan/jq
      - name: prepull-jq
        image: stedolan/jq:latest
        command: ["sh", "-c", "echo 'Pre-pulled stedolan/jq'"]
      # Pre-pull alpine/k8s
      - name: prepull-alpine-k8s
        image: alpine/k8s:1.28.4
        command: ["sh", "-c", "echo 'Pre-pulled alpine/k8s:1.28.4'"]
      containers:
      - name: pause
        image: gcr.io/google_containers/pause:3.2
        resources:
          limits:
            cpu: 10m
            memory: 10Mi
EOF
    print_status "Image pre-pull DaemonSet applied"
    
    # Install GitHub provider
    print_info "Installing GitHub provider..."
    kubectl apply -f crossplane/github-upjet-provider.yaml 2>/dev/null || true
    kubectl wait --for=condition=healthy provider.pkg.crossplane.io/provider-upjet-github --timeout=120s 2>/dev/null || true
    
    # Apply GitHub provider config with PAT
    if [ ! -z "$PERSONAL_ACCESS_TOKEN" ]; then
        envsubst < crossplane/github-provider-config.yaml | kubectl apply -f - 2>/dev/null || true
        print_status "GitHub provider configured"
    fi
    
    print_status "Platform resources applied"
}

# 10. Deploy Slack API Server
deploy_slack_api() {
    echo ""
    echo "=========================================="
    echo "10. Deploying Slack API Server..."
    echo "=========================================="
    
    # Apply Istio gateway and virtualservice
    kubectl apply -f slack-api-server/istio-gateway.yaml
    
    # Apply Knative service
    kubectl apply -f slack-api-server/knative-service.yaml
    
    # Add ARGO environment variables
    kubectl patch ksvc slack-api-server -n default --type='json' -p='[
      {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"ARGO_SERVER_URL","value":"http://argo-server.argo:2746"}},
      {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"ARGO_NAMESPACE","value":"argo"}}
    ]' 2>/dev/null || true
    
    print_status "Slack API Server deployed"
    
    # Wait for it to be ready
    kubectl wait --for=condition=ready pod -l serving.knative.dev/service=slack-api-server -n default --timeout=120s
}

# Main installation flow
main() {
    echo ""
    print_info "Starting complete platform installation..."
    echo ""
    
    # Check prerequisites
    command -v istioctl >/dev/null 2>&1 || { print_error "istioctl is required but not installed."; exit 1; }
    command -v helm >/dev/null 2>&1 || { print_error "helm is required but not installed."; exit 1; }
    
    # Run installations
    install_istio
    install_knative
    install_argocd
    install_argo_workflows
    install_crossplane
    install_kubevela
    install_external_secrets
    setup_secrets
    apply_platform_resources
    deploy_slack_api
    
    echo ""
    echo "=========================================="
    echo "✅ Platform Installation Complete!"
    echo "=========================================="
    echo ""
    
    # Verify critical components
    print_info "Verifying installation..."
    
    echo -n "  Istio: "
    kubectl get deployment istiod -n istio-system &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  Knative: "
    kubectl get deployment controller -n knative-serving &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  ArgoCD: "
    kubectl get deployment argocd-server -n argocd &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  Argo Workflows: "
    kubectl get deployment argo-server -n argo &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  Crossplane: "
    kubectl get deployment crossplane -n crossplane-system &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  KubeVela: "
    kubectl get deployment kubevela-vela-core -n vela-system &>/dev/null && echo "✅" || echo "❌"
    
    echo -n "  Slack API: "
    kubectl get ksvc slack-api-server -n default &>/dev/null && echo "✅" || echo "❌"
    
    echo ""
    
    # Get Istio ingress URL
    INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$INGRESS_HOST" ]; then
        INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    echo "Platform endpoints:"
    echo "  Istio Ingress: http://$INGRESS_HOST"
    echo "  Slack API: http://$INGRESS_HOST/slack/command (use Host: slack-api-server.default)"
    echo "  ArgoCD: http://$INGRESS_HOST/argocd"
    echo ""
    echo "To test the platform:"
    echo "  ./scripts/test-functional-multicluster.sh"
    echo ""
    echo "To check infrastructure health:"
    echo "  ./scripts/infrastructure-health-check.sh"
    echo ""
    echo "Important Notes:"
    echo "  - If any components show ❌, check their logs and rerun the specific installation step."
    echo "  - GitHub repositories created by the platform will:"
    echo "    • Use Azure Container Registry (ACR) by default"
    echo "    • Have AZURE_CREDENTIALS secret automatically configured"
    echo "    • Push container images to healthidpuaeacr.azurecr.io"
    echo "  - Image pre-pull DaemonSet installed to mitigate Docker Hub throttling"
    echo "  - Azure service principal created with ACR push/pull permissions"
}

# Run main installation
main "$@"