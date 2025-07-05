#!/bin/bash

# Manual test script for GitOps repository dispatch events
# This tests the dispatch event before integrating into the main pipeline

set -e

echo "🧪 Testing GitOps Repository Dispatch Event..."

# Test parameters - simulate a real deployment
SERVICES="streamlit-frontend"
VERSION_INFO="streamlit-frontend:1.1.54082e9"
SOURCE_COMMIT="54082e9"
COMMIT_SHA="54082e9"
REGISTRY="docker.io/socrates12345"
NEW_IMAGE="$REGISTRY/streamlit-frontend:$COMMIT_SHA"

echo "📋 Test Parameters:"
echo "  Services: $SERVICES"
echo "  Version Info: $VERSION_INFO"
echo "  Source Commit: $SOURCE_COMMIT"
echo "  New Image: $NEW_IMAGE"
echo ""

# Create the dispatch payload
PAYLOAD=$(cat <<EOF
{
  "event_type": "update-deployments",
  "client_payload": {
    "services": "$SERVICES",
    "version_info": "$VERSION_INFO",
    "source_commit": "$SOURCE_COMMIT",
    "deployments": {
      "streamlit-frontend": {
        "image": "$NEW_IMAGE",
        "commit": "$COMMIT_SHA"
      }
    },
    "registry": "$REGISTRY",
    "branch": "main",
    "workflow_run": "test-manual-dispatch"
  }
}
EOF
)

echo "📤 Payload to send:"
echo "$PAYLOAD" | jq .
echo ""

# Check if token is available
if [ -z "$GITHUB_TOKEN" ]; then
  echo "❌ Error: GITHUB_TOKEN environment variable is not set"
  echo "Please set it with: export GITHUB_TOKEN=your_token_here"
  exit 1
fi

# Send the dispatch event
echo "🚀 Sending repository dispatch event to health-service-idp-gitops..."

RESPONSE=$(curl -s -w "\n%{http_code}" -L \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/shlapolosa/health-service-idp-gitops/dispatches \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

echo "Response: $RESPONSE_BODY"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "204" ]; then
  echo "✅ Dispatch event sent successfully!"
elif [ "$HTTP_CODE" = "401" ]; then
  echo "❌ Authentication failed - check your GITHUB_TOKEN"
  echo "Token should have 'repo' scope and access to health-service-idp-gitops"
  exit 1
else
  echo "❌ Request failed with HTTP code: $HTTP_CODE"
  exit 1
fi

echo ""
echo "✅ Dispatch event sent successfully!"
echo "🔗 Check the GitOps repository Actions tab to see the workflow execution"
echo "📍 Repository: https://github.com/shlapolosa/health-service-idp-gitops/actions"