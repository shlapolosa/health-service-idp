#!/bin/bash

# Setup ArgoCD with GitHub Integration
# This script configures ArgoCD to monitor your GitHub repository

set -euo pipefail

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

# Configuration
GITHUB_USERNAME="shlapolosa"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_URL=""

# Prompt for GitHub configuration
get_github_config() {
    log_info "Setting up GitHub integration for ArgoCD..."
    log_info "GitHub username: $GITHUB_USERNAME"
    
    if [[ -z "$GITHUB_TOKEN" ]]; then
        log_error "GITHUB_TOKEN environment variable is not set!"
        log_info "Please set the GITHUB_TOKEN environment variable:"
        log_info "export GITHUB_TOKEN=your_github_token_here"
        exit 1
    fi
    log_success "GitHub token found in environment variable"
    
    if [[ -z "${REPO_URL:-}" ]]; then
        read -p "Enter your repository URL (default: https://github.com/shlapolosa/health-service-idp): " REPO_URL
        if [[ -z "$REPO_URL" ]]; then
            REPO_URL="https://github.com/shlapolosa/health-service-idp"
        fi
    fi
    
    log_success "GitHub configuration: $GITHUB_USERNAME @ $REPO_URL"
}

# Update ArgoCD application manifests with correct repository URL
update_argocd_manifests() {
    log_info "Updating ArgoCD manifests with repository URL..."
    
    # Update all ArgoCD application files
    find argocd-apps -name "*-argocd-app.yaml" -exec sed -i.bak "s|repoURL: https://github.com/your-org/health-service-idp|repoURL: $REPO_URL|g" {} \;
    
    # Update the app-of-apps manifest
    sed -i.bak "s|repoURL: https://github.com/your-org/health-service-idp|repoURL: $REPO_URL|g" argocd-apps/app-of-apps/architecture-tool-app-of-apps.yaml
    
    # Remove backup files
    find argocd-apps -name "*.bak" -delete
    
    log_success "ArgoCD manifests updated with repository URL: $REPO_URL"
}

# Create GitHub repository secret for ArgoCD
create_github_secret() {
    log_info "Creating GitHub repository secret for ArgoCD..."
    
    # Update the repository secret template
    sed "s|YOUR_GITHUB_TOKEN_HERE|$GITHUB_TOKEN|g; s|https://github.com/shlapolosa/health-service-idp|$REPO_URL|g" argocd-setup/repository-secret.yaml > /tmp/repository-secret-updated.yaml
    
    # Apply the secret
    kubectl apply -f /tmp/repository-secret-updated.yaml
    
    # Clean up
    rm /tmp/repository-secret-updated.yaml
    
    log_success "GitHub repository secret created in ArgoCD"
}

# Add and commit all OAM and ArgoCD manifests
commit_manifests() {
    log_info "Adding OAM and ArgoCD manifests to Git..."
    
    # Add all the new directories and files
    git add oam-applications/
    git add argocd-apps/
    git add argocd-setup/
    git add deploy-oam-argocd.sh
    git add setup-argocd-github.sh
    git add redis-deployment.yaml
    
    # Commit the changes
    git commit -m "feat: Add OAM applications and ArgoCD GitOps structure

- Add separate OAM Applications for each microservice with proper dependencies
- Add ArgoCD Application of Applications pattern
- Add GitHub integration setup for ArgoCD
- Add deployment scripts for complete GitOps workflow

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
    
    log_success "Manifests committed to Git"
}

# Push to GitHub
push_to_github() {
    log_info "Pushing manifests to GitHub repository..."
    
    # Check if we have a remote origin
    if git remote get-url origin &> /dev/null; then
        git push origin main
    else
        log_warn "No origin remote found. Please add your repository as origin:"
        log_info "git remote add origin $REPO_URL.git"
        log_info "git push -u origin main"
        return 1
    fi
    
    log_success "Manifests pushed to GitHub"
}

# Deploy the App-of-Apps
deploy_app_of_apps() {
    log_info "Deploying ArgoCD Application of Applications..."
    
    # Wait a moment for the repository secret to be ready
    sleep 10
    
    # Deploy the App-of-Apps
    kubectl apply -f argocd-apps/app-of-apps/architecture-tool-app-of-apps.yaml
    
    log_success "ArgoCD App-of-Apps deployed"
}

# Verify the deployment
verify_deployment() {
    log_info "Verifying ArgoCD deployment..."
    
    # Wait a moment for applications to sync
    sleep 30
    
    log_info "ArgoCD Applications:"
    kubectl get applications.argoproj.io -n argocd
    
    log_info "OAM Applications:"
    kubectl get applications.core.oam.dev
    
    log_info "Knative Services:"
    kubectl get ksvc
    
    log_success "Deployment verification completed"
}

# Get ArgoCD access information
get_argocd_access() {
    log_info "Getting ArgoCD access information..."
    
    # Get admin password
    if kubectl get secret argocd-initial-admin-secret -n argocd &> /dev/null; then
        ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
        log_success "ArgoCD admin password: $ARGOCD_PASSWORD"
    fi
    
    # Port forward information
    log_info "To access ArgoCD UI, run:"
    log_info "kubectl port-forward svc/argocd-server -n argocd 8080:443"
    log_info "Then open: https://localhost:8080"
    log_info "Username: admin"
    log_info "Password: $ARGOCD_PASSWORD"
}

# Main execution
main() {
    log_info "Starting ArgoCD GitHub integration setup..."
    
    get_github_config
    update_argocd_manifests
    create_github_secret
    commit_manifests
    
    if push_to_github; then
        deploy_app_of_apps
        verify_deployment
        get_argocd_access
        log_success "ArgoCD GitHub integration completed successfully!"
    else
        log_warn "Manual push required. After pushing to GitHub, run:"
        log_info "kubectl apply -f argocd-apps/app-of-apps/architecture-tool-app-of-apps.yaml"
    fi
}

# Run main function
main "$@"