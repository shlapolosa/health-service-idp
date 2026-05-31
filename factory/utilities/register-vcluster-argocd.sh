#!/bin/bash
# Script to register vCluster with ArgoCD for OAM application deployment
# This implements ADR-035: OAM-driven vCluster Infrastructure Architecture
# Updated with fixes from testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ArgoCD Configuration
ARGOCD_INGRESS_URL="${ARGOCD_INGRESS_URL:-af433f091b55640038c23af3a641d716-112208284.us-west-2.elb.amazonaws.com}"
ARGOCD_GRPC_WEB_ROOT="/argocd"

# Function to print colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check required parameters
if [ $# -lt 2 ]; then
    echo "Usage: $0 <vcluster-name> <vcluster-namespace> [application-name]"
    echo "Example: $0 customer-service customer-service customer-service-app"
    exit 1
fi

VCLUSTER_NAME=$1
VCLUSTER_NAMESPACE=$2
APP_NAME=${3:-$VCLUSTER_NAME-app}

log_info "Registering vCluster '$VCLUSTER_NAME' with ArgoCD..."

# Check if vCluster exists (could be named differently)
if ! kubectl get pods -n ${VCLUSTER_NAMESPACE} | grep -q "${VCLUSTER_NAME}"; then
    log_error "No vCluster pods found in namespace '${VCLUSTER_NAMESPACE}'"
    exit 1
fi

# Wait for vCluster to be ready
log_info "Waiting for vCluster to be ready..."
kubectl wait --for=condition=ready pod -l app=vcluster -n ${VCLUSTER_NAMESPACE} --timeout=300s || {
    log_warn "vCluster pods not ready yet, continuing anyway..."
}

# Get vCluster kubeconfig
log_info "Extracting vCluster kubeconfig..."
# Try different secret naming patterns
for SECRET_NAME in "vc-${VCLUSTER_NAME}-vcluster" "vc-${VCLUSTER_NAME}" "vc-config-${VCLUSTER_NAME}"; do
    if kubectl get secret ${SECRET_NAME} -n ${VCLUSTER_NAMESPACE} &>/dev/null; then
        KUBECONFIG_SECRET=${SECRET_NAME}
        log_info "Found kubeconfig secret: ${KUBECONFIG_SECRET}"
        break
    fi
done

if [ -z "${KUBECONFIG_SECRET}" ]; then
    log_error "vCluster kubeconfig secret not found"
    log_info "Available secrets:"
    kubectl get secrets -n ${VCLUSTER_NAMESPACE} | grep -E "vc-|vcluster|kubeconfig"
    exit 1
fi

# Extract kubeconfig
TEMP_KUBECONFIG="/tmp/vcluster-${VCLUSTER_NAME}.kubeconfig"
kubectl get secret ${KUBECONFIG_SECRET} -n ${VCLUSTER_NAMESPACE} -o jsonpath='{.data.config}' | base64 -d > ${TEMP_KUBECONFIG}

# Get vCluster server URL and CA data
log_info "Extracting vCluster connection details..."
VCLUSTER_SERVER=$(grep "server:" ${TEMP_KUBECONFIG} | awk '{print $2}')
VCLUSTER_CA_DATA=$(grep "certificate-authority-data:" ${TEMP_KUBECONFIG} | awk '{print $2}')

# Get service account token for vCluster access
log_info "Creating service account for ArgoCD access..."
export KUBECONFIG=${TEMP_KUBECONFIG}

# Create service account in vCluster
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-manager
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-manager
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: argocd-manager
  namespace: kube-system
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-manager-token
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: argocd-manager
type: kubernetes.io/service-account-token
EOF

# Wait for token to be generated
sleep 5

# Get the token
VCLUSTER_TOKEN=$(kubectl get secret argocd-manager-token -n kube-system -o jsonpath='{.data.token}' | base64 -d)

# Switch back to host cluster context
unset KUBECONFIG

# Get vCluster external endpoint (LoadBalancer)
log_info "Getting vCluster external endpoint..."
VCLUSTER_ENDPOINT=$(kubectl get clustergateway ${VCLUSTER_NAME} -o jsonpath='{.spec.access.endpoint.const.address}' 2>/dev/null || \
                    kubectl get svc ${VCLUSTER_NAME} -n ${VCLUSTER_NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

if [ -z "${VCLUSTER_ENDPOINT}" ]; then
    log_error "Could not determine vCluster endpoint"
    exit 1
fi

# Login to ArgoCD first
log_info "Logging into ArgoCD..."
ARGOCD_PASSWORD=$(kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d)

# Use plaintext for HTTP connection
argocd login ${ARGOCD_INGRESS_URL}:80 \
    --grpc-web-root-path ${ARGOCD_GRPC_WEB_ROOT} \
    --username admin \
    --password ${ARGOCD_PASSWORD} \
    --insecure \
    --plaintext || {
        log_error "Failed to login to ArgoCD"
        log_info "Make sure ArgoCD is accessible at: http://${ARGOCD_INGRESS_URL}${ARGOCD_GRPC_WEB_ROOT}"
        exit 1
    }

log_info "Successfully logged into ArgoCD"

# Use vcluster CLI to connect and get proper kubeconfig
log_info "Connecting to vCluster using vcluster CLI..."
vcluster connect ${VCLUSTER_NAME} -n ${VCLUSTER_NAMESPACE} --print > ${TEMP_KUBECONFIG} || {
    log_warn "vcluster CLI failed, using extracted kubeconfig"
}

# Register vCluster with ArgoCD using CLI
log_info "Adding vCluster to ArgoCD..."

# Check if cluster already exists
if argocd cluster list | grep -q "${VCLUSTER_NAME}"; then
    log_info "Cluster ${VCLUSTER_NAME} already registered, removing old registration"
    argocd cluster rm ${VCLUSTER_NAME} -y 2>/dev/null || true
fi

# Add the cluster using kubeconfig context
CONTEXT_NAME=$(kubectl config get-contexts --kubeconfig=${TEMP_KUBECONFIG} -o name | head -1)
argocd cluster add ${CONTEXT_NAME} \
    --kubeconfig ${TEMP_KUBECONFIG} \
    --name ${VCLUSTER_NAME} \
    --yes || {
        log_error "Failed to add vCluster to ArgoCD"
        exit 1
    }

log_info "✅ vCluster successfully registered with ArgoCD"

# Create ArgoCD Application for OAM deployment
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ${VCLUSTER_NAME}-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    vcluster.loft.sh/vcluster-name: ${VCLUSTER_NAME}
    vcluster.loft.sh/namespace: ${VCLUSTER_NAMESPACE}
type: Opaque
stringData:
  name: ${VCLUSTER_NAME}
  server: ${VCLUSTER_SERVER_INTERNAL}
  config: |
    {
      "bearerToken": "${VCLUSTER_TOKEN}",
      "tlsClientConfig": {
        "insecure": false,
        "caData": "${VCLUSTER_CA_DATA}"
      }
    }
EOF

log_info "Creating ArgoCD Application for OAM deployment..."

# Create ArgoCD Application that targets the vCluster (optional)
if [ "${CREATE_APP:-true}" = "true" ]; then
    cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ${APP_NAME}-oam
  namespace: argocd
  labels:
    app.kubernetes.io/managed-by: oam-platform
    app.kubernetes.io/part-of: ${APP_NAME}
    vcluster.loft.sh/target: ${VCLUSTER_NAME}
spec:
  project: default
  source:
    repoURL: https://github.com/shlapolosa/${APP_NAME}-gitops
    targetRevision: main
    path: oam/applications
  destination:
    name: ${VCLUSTER_NAME}  # Reference to the cluster secret we just created
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - ServerSideApply=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF
fi

log_info "Verifying ArgoCD cluster registration..."

# Check if cluster is registered using ArgoCD CLI
if argocd cluster list | grep -q "${VCLUSTER_NAME}"; then
    log_info "✅ vCluster successfully registered with ArgoCD"
    
    # Check ArgoCD application status if created
    if [ "${CREATE_APP:-true}" = "true" ] && kubectl get application ${APP_NAME}-oam -n argocd &>/dev/null; then
        log_info "✅ ArgoCD Application created"
        
        # Get sync status
        SYNC_STATUS=$(argocd app get ${APP_NAME}-oam -o json | jq -r '.status.sync.status' 2>/dev/null || echo "Unknown")
        log_info "Application sync status: ${SYNC_STATUS}"
    fi
else
    log_error "Failed to register vCluster with ArgoCD"
    exit 1
fi

# Clean up temporary files
rm -f ${TEMP_KUBECONFIG}

log_info "✅ vCluster '${VCLUSTER_NAME}' successfully registered with ArgoCD!"
log_info "📋 Summary:"
log_info "   vCluster Name: ${VCLUSTER_NAME}"
log_info "   Namespace: ${VCLUSTER_NAMESPACE}"
log_info "   ArgoCD Cluster: ${VCLUSTER_NAME}"
log_info "   ArgoCD App: ${APP_NAME}-oam"
log_info "   Server URL: ${VCLUSTER_SERVER_INTERNAL}"
log_info ""
log_info "🔗 Next steps:"
log_info "   1. Push OAM applications to: https://github.com/shlapolosa/${APP_NAME}-gitops/oam/applications/"
log_info "   2. Monitor sync: kubectl get application ${APP_NAME}-oam -n argocd"
log_info "   3. Access ArgoCD UI to view deployment status"