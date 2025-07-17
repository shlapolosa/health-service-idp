#!/bin/bash

# Slack API Server Secrets Setup
# This script sets up the required secrets for the slack-api-server
# Run this once manually to configure secrets in the cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo "🔐 Slack API Server Secrets Setup"
echo "=================================="
echo ""

# Check if environment variables are set
if [ -z "$PERSONAL_ACCESS_TOKEN" ]; then
    log_error "PERSONAL_ACCESS_TOKEN environment variable is not set"
    echo ""
    echo "Please set it with:"
    echo "export PERSONAL_ACCESS_TOKEN='your_github_token_here'"
    echo ""
    exit 1
fi

if [ -z "$SLACK_SIGNING_SECRET" ]; then
    log_error "SLACK_SIGNING_SECRET environment variable is not set"
    echo ""
    echo "Please set it with:"
    echo "export SLACK_SIGNING_SECRET='your_slack_signing_secret_here'"
    echo ""
    echo "To get your Slack signing secret:"
    echo "1. Go to https://api.slack.com/apps"
    echo "2. Select your app"
    echo "3. Go to 'Basic Information'"
    echo "4. Copy the 'Signing Secret' from 'App Credentials'"
    echo ""
    exit 1
fi

# Check kubectl connectivity
log_info "Checking Kubernetes connectivity..."
if ! kubectl cluster-info --request-timeout=5s &>/dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    echo ""
    echo "Please ensure:"
    echo "1. kubectl is installed and configured"
    echo "2. You have access to the cluster"
    echo "3. Run: aws eks update-kubeconfig --region us-west-2 --name your-cluster-name"
    echo ""
    exit 1
fi

log_success "Kubernetes connectivity verified"

# Check if we're in the right directory
if [ ! -f "rbac.yaml" ] || [ ! -f "../manual-secrets.yaml" ]; then
    log_error "rbac.yaml or ../manual-secrets.yaml not found. Please run this script from the slack-api-server directory"
    exit 1
fi

log_info "Environment variables validated:"
echo "  PERSONAL_ACCESS_TOKEN: ${PERSONAL_ACCESS_TOKEN:0:10}..."
echo "  SLACK_SIGNING_SECRET: ${SLACK_SIGNING_SECRET:0:10}..."
echo ""

# Apply secrets using manual-secrets.yaml template
log_info "Applying secrets to cluster..."

# Apply RBAC first
kubectl apply -f rbac.yaml

# Apply manual secrets with environment variable substitution
sed -e "s|\${PERSONAL_ACCESS_TOKEN}|${PERSONAL_ACCESS_TOKEN}|g" \
    -e "s|\${SLACK_SIGNING_SECRET}|${SLACK_SIGNING_SECRET}|g" \
    ../manual-secrets.yaml | kubectl apply -f -

log_success "Secrets applied successfully!"

# Verify secrets were created
log_info "Verifying secrets..."

if kubectl get secret github-credentials -n default &>/dev/null; then
    log_success "✅ github-credentials secret exists"
else
    log_error "❌ github-credentials secret not found"
fi

if kubectl get secret slack-credentials -n default &>/dev/null; then
    log_success "✅ slack-credentials secret exists"
else
    log_error "❌ slack-credentials secret not found"
fi

# Check if pods need to be restarted to pick up new secrets
log_info "Checking if slack-api-server pods need restart..."
if kubectl get pods -l app=slack-api-server -n default &>/dev/null; then
    log_warning "Existing slack-api-server pods detected"
    echo ""
    echo "To apply the new secrets, you may need to restart the pods:"
    echo "kubectl rollout restart deployment/slack-api-server -n default"
    echo ""
    
    read -p "Would you like to restart the deployment now? (y/N): " restart_choice
    if [[ $restart_choice =~ ^[Yy]$ ]]; then
        log_info "Restarting slack-api-server deployment..."
        kubectl rollout restart deployment/slack-api-server -n default
        kubectl rollout status deployment/slack-api-server -n default --timeout=300s
        log_success "Deployment restarted successfully!"
    fi
else
    log_info "No existing slack-api-server pods found - secrets will be used on next deployment"
fi

echo ""
log_success "🎉 Secret setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test the /vcluster command in Slack"
echo "2. Monitor logs: kubectl logs -l app=slack-api-server -n default -f"
echo "3. Check health: kubectl get pods -l app=slack-api-server -n default"
echo ""