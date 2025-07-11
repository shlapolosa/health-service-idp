#!/bin/bash

# Build script for slack-api-server
set -e

SERVICE_NAME="slack-api-server"
DOCKER_IMAGE="shlapolosa/${SERVICE_NAME}"
TAG="${TAG:-latest}"

echo "🏗️  Building Docker image for ${SERVICE_NAME}..."

# Build the Docker image
docker build -t "${DOCKER_IMAGE}:${TAG}" .

echo "✅ Docker image built successfully: ${DOCKER_IMAGE}:${TAG}"

# Optional: Push to registry if PUSH=true
if [ "${PUSH}" == "true" ]; then
    echo "📤 Pushing Docker image to registry..."
    docker push "${DOCKER_IMAGE}:${TAG}"
    echo "✅ Docker image pushed successfully"
fi

echo "🎉 Build complete!"