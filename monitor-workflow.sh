#!/bin/bash

# Monitor GitHub Action workflow progress
# Usage: ./monitor-workflow.sh

set -e

echo "🔍 Monitoring GitHub Action workflows..."

while true; do
    # Get the latest workflow run
    LATEST_RUN=$(curl -s "https://api.github.com/repos/shlapolosa/health-service-idp/actions/runs" \
        -H "Authorization: token $PERSONAL_ACCESS_TOKEN" | \
        jq -r '.workflow_runs[0] | {id: .id, status: .status, conclusion: .conclusion, created_at: .created_at}')
    
    RUN_ID=$(echo "$LATEST_RUN" | jq -r '.id')
    STATUS=$(echo "$LATEST_RUN" | jq -r '.status')
    CONCLUSION=$(echo "$LATEST_RUN" | jq -r '.conclusion')
    CREATED_AT=$(echo "$LATEST_RUN" | jq -r '.created_at')
    
    echo "📊 Latest Run: $RUN_ID"
    echo "   Status: $STATUS"
    echo "   Conclusion: $CONCLUSION"
    echo "   Created: $CREATED_AT"
    echo "   URL: https://github.com/shlapolosa/health-service-idp/actions/runs/$RUN_ID"
    echo ""
    
    if [[ "$STATUS" == "completed" ]]; then
        if [[ "$CONCLUSION" == "success" ]]; then
            echo "✅ Workflow completed successfully!"
            break
        else
            echo "❌ Workflow failed with conclusion: $CONCLUSION"
            break
        fi
    fi
    
    echo "⏳ Workflow still running... checking again in 30 seconds"
    sleep 30
done