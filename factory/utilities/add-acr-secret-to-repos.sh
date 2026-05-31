#!/bin/bash

# Script to add ACR_PASSWORD secret to existing GitHub repositories

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Get GitHub token from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep '^PERSONAL_ACCESS_TOKEN=' | xargs)
fi

if [ -z "$PERSONAL_ACCESS_TOKEN" ]; then
    print_warning "PERSONAL_ACCESS_TOKEN not found in .env"
    echo "Please enter your GitHub Personal Access Token:"
    read -s PERSONAL_ACCESS_TOKEN
fi

# Get ACR password from Azure
ACR_PASSWORD=$(az acr credential show --name healthidpuaeacr --query "passwords[0].value" -o tsv 2>/dev/null || echo "")

if [ -z "$ACR_PASSWORD" ]; then
    print_warning "Could not get ACR password from Azure CLI"
    # Try to get from Kubernetes secret
    ACR_PASSWORD=$(kubectl get secret acr-credentials -n default -o jsonpath='{.data..dockerconfigjson}' 2>/dev/null | base64 -d | jq -r '.auths."healthidpuaeacr.azurecr.io".password' 2>/dev/null || echo "")
    
    if [ -z "$ACR_PASSWORD" ]; then
        echo "Please enter the ACR password:"
        read -s ACR_PASSWORD
    fi
fi

GITHUB_USER=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" https://api.github.com/user | jq -r '.login')

if [ -z "$GITHUB_USER" ]; then
    echo "Failed to get GitHub username. Check your token."
    exit 1
fi

print_info "GitHub User: $GITHUB_USER"

# Repositories to update
REPOS=(
    "health-service-idp"
    "health-service-idp-gitops"
    "onion-architecture-template"
    "chat-template"
    "graphql-federation-gateway-template"
    "identity-service-template"
)

# Function to add ACR secret to a repository
add_acr_secret() {
    local repo=$1
    
    print_info "Processing $repo..."
    
    # Get public key for secret encryption
    PUBLIC_KEY_DATA=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/actions/secrets/public-key")
    
    if [ "$(echo "$PUBLIC_KEY_DATA" | jq -r '.message' 2>/dev/null)" = "Not Found" ]; then
        print_warning "  Repository $repo not found or no access"
        return
    fi
    
    PUBLIC_KEY=$(echo "$PUBLIC_KEY_DATA" | jq -r .key)
    KEY_ID=$(echo "$PUBLIC_KEY_DATA" | jq -r .key_id)
    
    # Create Python script to encrypt the secret
    cat > /tmp/encrypt_secret.py << 'EOF'
import sys
import base64
from nacl import encoding, public

def encrypt_secret(public_key: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

if __name__ == "__main__":
    print(encrypt_secret(sys.argv[1], sys.argv[2]))
EOF
    
    # Install PyNaCl if not installed
    python3 -m pip install --quiet PyNaCl 2>/dev/null || true
    
    # Encrypt the ACR password
    ENCRYPTED_ACR=$(python3 /tmp/encrypt_secret.py "$PUBLIC_KEY" "$ACR_PASSWORD")
    
    # Create or update the ACR_PASSWORD secret
    RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/actions/secrets/ACR_PASSWORD" \
        -d "{\"encrypted_value\":\"$ENCRYPTED_ACR\",\"key_id\":\"$KEY_ID\"}")
    
    if [ "$(echo "$RESPONSE" | jq -r '.message' 2>/dev/null)" = "Not Found" ]; then
        print_warning "  Could not add secret to $repo"
    else
        print_status "  ACR_PASSWORD secret added to $repo"
    fi
}

# Main execution
main() {
    echo "==========================================="
    echo "   Add ACR Secret to GitHub Repositories"
    echo "==========================================="
    echo ""
    
    for repo in "${REPOS[@]}"; do
        add_acr_secret "$repo"
    done
    
    # Also check for any app containers that might exist
    print_info "Checking for app container repositories..."
    APP_CONTAINERS=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/users/$GITHUB_USER/repos?per_page=100" | \
        jq -r '.[] | select(.name | endswith("-app-container")) | .name')
    
    for repo in $APP_CONTAINERS; do
        add_acr_secret "$repo"
    done
    
    # Clean up
    rm -f /tmp/encrypt_secret.py
    
    echo ""
    echo "==========================================="
    echo "   Complete"
    echo "==========================================="
    echo ""
    echo "ACR_PASSWORD secret has been added to all accessible repositories."
    echo "New repositories created by Crossplane will automatically get this secret."
}

# Run if not sourced
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi