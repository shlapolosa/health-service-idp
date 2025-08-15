#!/bin/bash

# Script to update template repositories with multi-registry support
# This will update all template repos to support both Docker Hub and ACR

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

# Template repositories to update
TEMPLATE_REPOS=(
    "onion-architecture-template"
    "chat-template"
    "graphql-federation-gateway-template"
    "identity-service-template"
)

# GitHub token from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep '^PERSONAL_ACCESS_TOKEN=' | xargs)
fi

if [ -z "$PERSONAL_ACCESS_TOKEN" ]; then
    print_warning "PERSONAL_ACCESS_TOKEN not found in .env"
    echo "Please enter your GitHub Personal Access Token:"
    read -s PERSONAL_ACCESS_TOKEN
fi

GITHUB_USER=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" https://api.github.com/user | jq -r '.login')

if [ -z "$GITHUB_USER" ]; then
    echo "Failed to get GitHub username. Check your token."
    exit 1
fi

print_info "GitHub User: $GITHUB_USER"

# Function to update workflow files
update_workflow() {
    local repo=$1
    local workflow_file=$2
    
    print_info "Updating $workflow_file in $repo..."
    
    # Get current file content
    CURRENT_CONTENT=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/.github/workflows/$workflow_file" | \
        jq -r '.content' | base64 -d 2>/dev/null || echo "")
    
    if [ -z "$CURRENT_CONTENT" ]; then
        print_warning "  $workflow_file not found in $repo"
        return
    fi
    
    # Check if already updated
    if echo "$CURRENT_CONTENT" | grep -q "ACR_REGISTRY"; then
        print_status "  Already updated with multi-registry support"
        return
    fi
    
    # Create updated content
    UPDATED_CONTENT=$(echo "$CURRENT_CONTENT" | \
        sed 's/^env:$/env:\n  # Docker Hub settings (default)\n  DOCKERHUB_REGISTRY: docker.io\n  DOCKERHUB_USERNAME: socrates12345\n  # ACR settings\n  ACR_REGISTRY: healthidpuaeacr.azurecr.io\n  ACR_NAME: healthidpuaeacr\n  # Default registry selection\n  DEFAULT_REGISTRY: dockerhub  # or "acr" or "both"\n  # Legacy variables for backward compatibility/' | \
        sed 's/REGISTRY: docker.io/REGISTRY: docker.io  # Legacy - use DOCKERHUB_REGISTRY/' | \
        sed 's/REGISTRY_USERNAME: socrates12345/REGISTRY_USERNAME: socrates12345  # Legacy - use DOCKERHUB_USERNAME/')
    
    # Get file SHA
    FILE_SHA=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/.github/workflows/$workflow_file" | \
        jq -r '.sha')
    
    # Update file via GitHub API
    ENCODED_CONTENT=$(echo "$UPDATED_CONTENT" | base64 -w 0)
    
    RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/.github/workflows/$workflow_file" \
        -d "{
            \"message\": \"feat: add multi-registry support (Docker Hub and ACR)\",
            \"content\": \"$ENCODED_CONTENT\",
            \"sha\": \"$FILE_SHA\"
        }")
    
    if echo "$RESPONSE" | jq -e '.content' > /dev/null; then
        print_status "  Successfully updated $workflow_file"
    else
        print_warning "  Failed to update $workflow_file"
        echo "$RESPONSE" | jq '.message' 2>/dev/null || echo "$RESPONSE"
    fi
}

# Function to add registry documentation to README
add_registry_docs() {
    local repo=$1
    
    print_info "Adding multi-registry documentation to README in $repo..."
    
    # Get current README
    README_CONTENT=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/README.md" | \
        jq -r '.content' | base64 -d 2>/dev/null || echo "")
    
    if [ -z "$README_CONTENT" ]; then
        print_warning "  README.md not found in $repo"
        return
    fi
    
    # Check if already documented
    if echo "$README_CONTENT" | grep -q "Multi-Registry Support"; then
        print_status "  README already has multi-registry documentation"
        return
    fi
    
    # Add documentation section
    REGISTRY_DOCS="

## Multi-Registry Support

This template supports both Docker Hub and Azure Container Registry (ACR).

### Configuration

Set the \`DEFAULT_REGISTRY\` environment variable in GitHub Actions:
- \`dockerhub\` - Push to Docker Hub only (default)
- \`acr\` - Push to Azure Container Registry only
- \`both\` - Push to both registries

### Required Secrets

For Docker Hub:
- \`DOCKER_PASSWORD\` - Docker Hub password or access token

For ACR:
- \`ACR_PASSWORD\` - Azure Container Registry password

### Usage

The CI/CD pipeline will automatically push images to the configured registry(ies).
Images will be available at:
- Docker Hub: \`docker.io/socrates12345/[service-name]\`
- ACR: \`healthidpuaeacr.azurecr.io/[service-name]\`
"
    
    UPDATED_README="$README_CONTENT$REGISTRY_DOCS"
    
    # Get file SHA
    FILE_SHA=$(curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/README.md" | \
        jq -r '.sha')
    
    # Update README
    ENCODED_CONTENT=$(echo "$UPDATED_README" | base64 -w 0)
    
    RESPONSE=$(curl -s -X PUT \
        -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$GITHUB_USER/$repo/contents/README.md" \
        -d "{
            \"message\": \"docs: add multi-registry support documentation\",
            \"content\": \"$ENCODED_CONTENT\",
            \"sha\": \"$FILE_SHA\"
        }")
    
    if echo "$RESPONSE" | jq -e '.content' > /dev/null; then
        print_status "  Successfully updated README.md"
    else
        print_warning "  Failed to update README.md"
    fi
}

# Main execution
main() {
    echo "==========================================="
    echo "   Template Repositories Registry Update"
    echo "==========================================="
    echo ""
    
    for repo in "${TEMPLATE_REPOS[@]}"; do
        echo ""
        print_info "Processing $repo..."
        
        # Check if repo exists
        if curl -s -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
            "https://api.github.com/repos/$GITHUB_USER/$repo" | jq -e '.name' > /dev/null; then
            
            # Update workflow files
            if [[ "$repo" == "chat-template" ]]; then
                update_workflow "$repo" "chat-gitops.yml"
                update_workflow "$repo" "docker-build.yml"
            else
                update_workflow "$repo" "comprehensive-gitops.yml"
            fi
            
            # Add documentation
            add_registry_docs "$repo"
            
            print_status "Completed $repo"
        else
            print_warning "$repo not found or not accessible"
        fi
    done
    
    echo ""
    echo "==========================================="
    echo "   Update Complete"
    echo "==========================================="
    echo ""
    echo "Template repositories have been updated with multi-registry support."
    echo "Remember to add the ACR_PASSWORD secret to each repository's GitHub secrets."
}

# Run if not sourced
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi