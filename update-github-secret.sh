#!/bin/bash

# Update GitHub secret with new AWS Role ARN
# Usage: ./update-github-secret.sh

set -e

NEW_ROLE_ARN="arn:aws:iam::263350857079:role/VClusterAutomationRole"
REPO="shlapolosa/health-service-idp"

echo "🔄 Updating GitHub secret AWS_ROLE_ARN..."
echo "New value: $NEW_ROLE_ARN"

# Try using GitHub CLI first
if command -v gh &> /dev/null; then
    echo "Using GitHub CLI..."
    gh secret set AWS_ROLE_ARN --body "$NEW_ROLE_ARN" --repo "$REPO"
    echo "✅ Secret updated via GitHub CLI"
else
    echo "GitHub CLI not found. Please update manually:"
    echo ""
    echo "1. Go to: https://github.com/$REPO/settings/secrets/actions"
    echo "2. Click on AWS_ROLE_ARN secret"
    echo "3. Update value to: $NEW_ROLE_ARN"
    echo "4. Click 'Update secret'"
fi

echo ""
echo "🧪 After updating the secret, test with:"
echo "   ./test-slack-vcluster.sh basic"