#!/bin/bash
set -e

NAMESPACE=${NAMESPACE:-"default"}

# Get the service URL
SERVICE_URL=$(kubectl get ksvc business-analyst-anthropic \
    --namespace=${NAMESPACE} \
    -o jsonpath='{.status.url}')

if [ -z "$SERVICE_URL" ]; then
    echo "❌ Could not get service URL. Is the service deployed?"
    exit 1
fi

echo "🧪 Testing Business Analyst Anthropic microservice..."
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""

# Test the health endpoint
echo "1️⃣  Testing health endpoint..."
health_response=$(curl -s ${SERVICE_URL}/health)
echo "Response: ${health_response}"

# Verify health response
if echo "$health_response" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

echo ""

# Test the analyze-requirements endpoint
echo "2️⃣  Testing analyze-requirements endpoint..."
requirements_payload='{
    "query": "User should be able to create and manage their profile and update billing information",
    "parameters": {
        "domain": "ecommerce"
    }
}'

echo "📤 Sending request:"
echo "$requirements_payload" | jq .

requirements_response=$(curl -s -X POST ${SERVICE_URL}/analyze-requirements \
    -H "Content-Type: application/json" \
    -d "$requirements_payload")

echo ""
echo "📥 Response:"
echo "$requirements_response" | jq .

# Verify requirements response
if echo "$requirements_response" | grep -q "result"; then
    echo "✅ Requirements analysis test passed"
else
    echo "❌ Requirements analysis test failed"
    exit 1
fi

echo ""

# Test the extract-entities endpoint
echo "3️⃣  Testing extract-entities endpoint..."
entities_payload='{
    "query": "The customer wants to update their billing address and payment method"
}'

echo "📤 Sending request:"
echo "$entities_payload" | jq .

entities_response=$(curl -s -X POST ${SERVICE_URL}/extract-entities \
    -H "Content-Type: application/json" \
    -d "$entities_payload")

echo ""
echo "📥 Response:"
echo "$entities_response" | jq .

# Verify entities response
if echo "$entities_response" | grep -q "entities"; then
    echo "✅ Entity extraction test passed"
else
    echo "❌ Entity extraction test failed"
    exit 1
fi

echo ""
echo "🎉 All tests passed!"
echo "🚀 Business Analyst Anthropic microservice is working correctly"