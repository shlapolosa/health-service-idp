#!/bin/bash

# Deploy script for business-analyst-deterministic microservice

set -e

SERVICE_NAME="business-analyst-deterministic"
NAMESPACE="${NAMESPACE:-default}"

echo "Deploying ${SERVICE_NAME} to Knative..."

# Build the image first
echo "Building image..."
./build.sh

# Apply Knative service
echo "Applying Knative service configuration..."
kubectl apply -f knative-service.yaml -n ${NAMESPACE}

# Wait for deployment
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=Ready ksvc/${SERVICE_NAME} -n ${NAMESPACE} --timeout=300s

# Get service URL
SERVICE_URL=$(kubectl get ksvc ${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.status.url}')

echo "Deployment completed successfully!"
echo "Service URL: ${SERVICE_URL}"

# Test the deployed service
echo "Testing deployed service..."
curl -f ${SERVICE_URL}/health || {
    echo "Deployment health check failed"
    exit 1
}

echo "Deployment health check passed!"