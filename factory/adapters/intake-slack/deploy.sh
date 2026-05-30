#!/bin/bash

# Deploy script for slack-api-server
set -e

SERVICE_NAME="slack-api-server"
NAMESPACE="${NAMESPACE:-default}"

echo "🚀 Deploying ${SERVICE_NAME} to Kubernetes..."

# Check for required environment variables
if [ -z "$PERSONAL_ACCESS_TOKEN" ]; then
    echo "❌ PERSONAL_ACCESS_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$SLACK_SIGNING_SECRET" ]; then
    echo "❌ SLACK_SIGNING_SECRET environment variable is required"
    exit 1
fi

# Apply RBAC and secrets first with environment variable substitution
echo "📋 Setting up RBAC and secrets..."
echo "🔐 Substituting environment variables in secrets..."
sed -e "s|\${PERSONAL_ACCESS_TOKEN}|${PERSONAL_ACCESS_TOKEN}|g" \
    -e "s|\${SLACK_SIGNING_SECRET}|${SLACK_SIGNING_SECRET}|g" \
    rbac.yaml | kubectl apply -f -

# Apply deployment and service
echo "🚀 Deploying application..."
kubectl apply -f deployment.yaml

# Apply Istio Gateway and VirtualService
echo "🌐 Setting up Istio Gateway and VirtualService..."
kubectl apply -f istio-gateway.yaml

echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=Available deployment/"${SERVICE_NAME}" --timeout=300s

echo "✅ ${SERVICE_NAME} deployed successfully!"

# Get deployment info
kubectl get deployment "${SERVICE_NAME}" -o wide
kubectl get service "${SERVICE_NAME}" -o wide

# Get Istio Gateway info
GATEWAY_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Not available")
GATEWAY_HOSTNAME=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Not available")

echo "🌍 Istio Gateway IP: ${GATEWAY_IP}"
echo "🌍 Istio Gateway Hostname: ${GATEWAY_HOSTNAME}"
echo "🔗 Access via: http://${GATEWAY_HOSTNAME} or https://${GATEWAY_HOSTNAME}"

echo "📝 Don't forget to:"
echo "  1. Set PERSONAL_ACCESS_TOKEN environment variable before deployment"
echo "  2. Set SLACK_SIGNING_SECRET environment variable before deployment"
echo "  3. Configure TLS certificate for the Istio Gateway"
echo "  4. Use the Istio Gateway hostname for Slack webhook URLs"

echo "🎉 Deployment complete!"