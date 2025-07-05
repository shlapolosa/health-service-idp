#!/bin/bash

# Test deployment script for business-analyst-deterministic

set -e

SERVICE_NAME="business-analyst-deterministic"
BASE_URL="${BASE_URL:-http://localhost:8081}"

echo "Testing ${SERVICE_NAME} deployment..."

# Test health endpoint
echo "Testing health endpoint..."
curl -f "${BASE_URL}/health" || {
    echo "Health check failed"
    exit 1
}
echo "✓ Health check passed"

# Test analyze-requirements endpoint
echo "Testing analyze-requirements endpoint..."
curl -X POST "${BASE_URL}/analyze-requirements" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "User should be able to create and manage their profile",
        "parameters": {"domain": "general"}
    }' || {
    echo "Analyze requirements test failed"
    exit 1
}
echo "✓ Analyze requirements test passed"

# Test extract-entities endpoint
echo "Testing extract-entities endpoint..."
curl -X POST "${BASE_URL}/extract-entities" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "The customer wants to purchase products from the online store"
    }' || {
    echo "Extract entities test failed"
    exit 1
}
echo "✓ Extract entities test passed"

echo "All tests passed! ✅"