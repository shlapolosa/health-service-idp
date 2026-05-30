#!/bin/bash
set -e

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and fill in the values."
    exit 1
fi

# Load environment variables from .env file (only valid shell variables)
echo "📁 Loading environment variables from .env file..."
export $(grep -v '^#' .env | grep '^[A-Z_][A-Z0-9_]*=' | xargs)

# Validate required variables
required_vars=("PERSONAL_ACCESS_TOKEN" "GITHUB_USERNAME" "DOCKER_USERNAME" "DOCKER_PASSWORD" "DOCKER_AUTH" "SLACK_SIGNING_SECRET" "SLACK_WEBHOOK_URL" "LENSES_LICENSE_KEY" "LENSES_ACCEPT_EULA" "LENSES_HQ_USER" "LENSES_HQ_PASSWORD" "LENSES_DB_USERNAME" "LENSES_DB_PASSWORD" "AUTH0_DOMAIN" "AUTH0_CLIENT_ID" "AUTH0_CLIENT_SECRET" "AUTH0_AUDIENCE")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set in .env file"
        exit 1
    fi
done

echo "✅ All required environment variables found"

# Apply the secrets using envsubst
echo "🔧 Applying secrets from manual-secrets.yaml..."
envsubst < manual-secrets.yaml | kubectl apply -f -

# Create ACR credentials secret if in Azure environment
if [ -n "$ACR_NAME" ]; then
    echo "🔧 Creating ACR credentials secret..."
    
    # Check if Azure CLI is available and logged in
    if command -v az &> /dev/null && az account show &> /dev/null; then
        ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv 2>/dev/null || echo "")
        
        if [ -n "$ACR_PASSWORD" ]; then
            kubectl create secret docker-registry acr-credentials \
                --docker-server="${ACR_NAME}.azurecr.io" \
                --docker-username="$ACR_NAME" \
                --docker-password="$ACR_PASSWORD" \
                -n default --dry-run=client -o yaml | kubectl apply -f -
            echo "✅ ACR credentials secret created"
        else
            echo "⚠️  Could not retrieve ACR password. Skipping ACR credentials creation."
        fi
    else
        echo "⚠️  Azure CLI not available or not logged in. Skipping ACR credentials creation."
        echo "   To create ACR credentials manually, run:"
        echo "   kubectl create secret docker-registry acr-credentials \\"
        echo "     --docker-server=${ACR_NAME}.azurecr.io \\"
        echo "     --docker-username=${ACR_NAME} \\"
        echo "     --docker-password=<password> -n default"
    fi
fi

# Create ConfigMap with namespace-specific agent keys
echo "🔧 Creating agent keys ConfigMap..."
echo "apiVersion: v1
kind: ConfigMap
metadata:
  name: env-agent-keys
  namespace: default
  labels:
    managed-by: manual
data:" > /tmp/agent-keys-configmap.yaml

# Extract all agent key variables from .env file
AGENT_KEYS_FOUND=false
while IFS= read -r line; do
    # Skip comments and empty lines
    if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
        continue
    fi
    
    # Check if line contains an agent key
    if [[ $line =~ ^([a-zA-Z0-9_-]+)-agent-key=(.+)$ ]]; then
        NAMESPACE_KEY="${BASH_REMATCH[1]}-agent-key"
        AGENT_KEY_VALUE="${BASH_REMATCH[2]}"
        echo "  $NAMESPACE_KEY: \"$AGENT_KEY_VALUE\"" >> /tmp/agent-keys-configmap.yaml
        echo "  ✓ Found agent key for: ${BASH_REMATCH[1]}"
        AGENT_KEYS_FOUND=true
    fi
done < .env

if [ "$AGENT_KEYS_FOUND" = false ]; then
    echo "  # No agent keys found in .env file" >> /tmp/agent-keys-configmap.yaml
    echo "⚠️  No agent keys found in .env file"
    echo "    Add keys in format: <namespace>-agent-key=<key>"
else
    echo "✅ Agent keys extracted from .env file"
fi

kubectl apply -f /tmp/agent-keys-configmap.yaml
rm -f /tmp/agent-keys-configmap.yaml

# Copy Argo token from argo namespace to default namespace for workflow trigger jobs
echo "🔐 Copying Argo token to default namespace for workflow triggers..."
if kubectl get secret slack-api-argo-token -n argo > /dev/null 2>&1; then
    kubectl get secret slack-api-argo-token -n argo -o yaml | \
    sed 's/namespace: argo/namespace: default/' | \
    sed 's/name: slack-api-argo-token/name: slack-api-argo-token/' | \
    kubectl apply -f - && echo "✅ Argo token copied to default namespace"
else
    echo "⚠️  Argo token not found in argo namespace - workflow triggers may fail"
fi

# Create Azure service principal credentials for GitHub Actions
echo "🔧 Creating Azure service principal credentials..."
if [ -n "$AZURE_CLIENT_ID" ] && [ -n "$AZURE_CLIENT_SECRET" ] && [ -n "$AZURE_SUBSCRIPTION_ID" ] && [ -n "$AZURE_TENANT_ID" ]; then
    cat <<AZURE_EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: azure-credentials
  namespace: default
  labels:
    managed-by: manual
  annotations:
    argocd.argoproj.io/compare: "false"
    argocd.argoproj.io/sync: "false"
type: Opaque
stringData:
  azure-creds.json: |
    {
      "clientId": "${AZURE_CLIENT_ID}",
      "clientSecret": "${AZURE_CLIENT_SECRET}",
      "subscriptionId": "${AZURE_SUBSCRIPTION_ID}",
      "tenantId": "${AZURE_TENANT_ID}"
    }
AZURE_EOF
    echo "✅ Azure service principal credentials created"
else
    echo "⚠️  Azure service principal variables not set. Skipping Azure credentials creation."
    echo "   To enable Azure integration, add to .env:"
    echo "   AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID"
fi

echo "🎉 All secrets created successfully from .env file!"
echo ""
echo "📋 Created resources:"
echo "  - auth0-credentials (clientId, clientSecret, domain, audience)"
echo "  - github-credentials (token, personal-access-token, user)"
echo "  - github-provider-secret (crossplane provider credentials) in crossplane-system namespace"
echo "  - docker-credentials (registry, username, password)"
echo "  - docker-registry-secret (kubernetes.io/dockerconfigjson for image pulls)"
echo "  - slack-credentials (signing-secret)"
echo "  - slack-webhook (webhook-url) in argo namespace"
echo "  - lenses-credentials (license-key, accept-eula, hq-user, hq-password, db-username, db-password)"
echo "  - env-agent-keys ConfigMap (namespace-specific agent keys)"
echo "  - azure-credentials (if configured - for GitHub Actions Azure login)"
echo ""
echo "⚠️  Remember: .env file is git-ignored for security"