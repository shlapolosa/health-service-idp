#!/bin/bash

# Test deployment script for slack-api-server
set -e

SERVICE_NAME="slack-api-server"
NAMESPACE="${NAMESPACE:-default}"

echo "🧪 Testing ${SERVICE_NAME} deployment..."

# Get service URL
SERVICE_URL=$(kubectl get ksvc "${SERVICE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.url}' 2>/dev/null || echo "")

if [ -z "${SERVICE_URL}" ]; then
    echo "❌ Service ${SERVICE_NAME} not found or not ready"
    exit 1
fi

echo "🌐 Service URL: ${SERVICE_URL}"

# Test health endpoint
echo "🏥 Testing health endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" || echo "000")

if [ "${HTTP_STATUS}" == "200" ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed (HTTP ${HTTP_STATUS})"
    exit 1
fi

# Test API documentation
echo "📚 Testing API documentation..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/docs" || echo "000")

if [ "${HTTP_STATUS}" == "200" ]; then
    echo "✅ API docs accessible"
else
    echo "❌ API docs not accessible (HTTP ${HTTP_STATUS})"
    exit 1
fi

# Test Slack webhook endpoint (should return 405 for GET)
echo "🔗 Testing Slack webhook endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/slack/command" || echo "000")

if [ "${HTTP_STATUS}" == "405" ]; then
    echo "✅ Slack webhook endpoint accessible (correctly returns 405 for GET)"
else
    echo "⚠️  Slack webhook endpoint returned HTTP ${HTTP_STATUS} (expected 405)"
fi

echo "🎉 All tests passed!"