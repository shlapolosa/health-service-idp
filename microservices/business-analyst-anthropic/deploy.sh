#!/bin/bash
set -e

# Set variables
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"ghcr.io/health-service-idp"}
IMAGE_NAME="business-analyst-anthropic"
IMAGE_TAG=${IMAGE_TAG:-"latest"}
NAMESPACE=${NAMESPACE:-"default"}

echo "🚀 Deploying Business Analyst Anthropic microservice..."
echo "📦 Registry: ${DOCKER_REGISTRY}"
echo "🏷️  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "🎯 Namespace: ${NAMESPACE}"

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag the image for the registry
echo "🏷️  Tagging image for registry..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

# Push the image to the registry
echo "📤 Pushing image to registry..."
docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}

# Create namespace if it doesn't exist
echo "📂 Creating namespace if needed..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Create Anthropic API key secret if ANTHROPIC_API_KEY is set
if [ ! -z "$ANTHROPIC_API_KEY" ]; then
    echo "🔐 Creating Anthropic API key secret..."
    kubectl create secret generic anthropic-api-key \
        --from-literal=api-key="$ANTHROPIC_API_KEY" \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
else
    echo "⚠️  ANTHROPIC_API_KEY not set - creating empty secret"
    kubectl create secret generic anthropic-api-key \
        --from-literal=api-key="" \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
fi

# Replace the image placeholder in the Knative service file
echo "📝 Generating deployment configuration..."
sed -e "s|\${DOCKER_REGISTRY}|${DOCKER_REGISTRY}|g" \
    -e "s|namespace: default|namespace: ${NAMESPACE}|g" \
    knative-service.yaml > knative-service-deploy.yaml

# Apply the Knative service
echo "🚀 Deploying Knative service..."
kubectl apply -f knative-service-deploy.yaml

# Wait for the service to be ready
echo "⏳ Waiting for Knative service to be ready..."
kubectl wait --for=condition=Ready ksvc/business-analyst-anthropic \
    --namespace=${NAMESPACE} \
    --timeout=300s

# Get the service URL
SERVICE_URL=$(kubectl get ksvc business-analyst-anthropic \
    --namespace=${NAMESPACE} \
    -o jsonpath='{.status.url}')

echo "✅ Service deployed successfully!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "🔍 Health check: ${SERVICE_URL}/health"
echo ""
echo "🧪 Test with:"
echo "curl -X POST ${SERVICE_URL}/analyze-requirements \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"query\": \"User should be able to create and manage their profile\", \"parameters\": {\"domain\": \"ecommerce\"}}'"

# Cleanup temporary file
rm -f knative-service-deploy.yaml