#!/bin/bash

# Build script for business-analyst-deterministic microservice

set -e

SERVICE_NAME="business-analyst-deterministic"
IMAGE_TAG="${SERVICE_NAME}:latest"

echo "Building ${SERVICE_NAME} microservice..."

# Build Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_TAG} .

# Test the image
echo "Testing Docker image..."
docker run --rm -d --name ${SERVICE_NAME}-test -p 8081:8080 ${IMAGE_TAG}

# Wait for service to start
echo "Waiting for service to start..."
sleep 10

# Health check
echo "Performing health check..."
curl -f http://localhost:8081/health || {
    echo "Health check failed"
    docker stop ${SERVICE_NAME}-test
    exit 1
}

echo "Health check passed"

# Clean up test container
docker stop ${SERVICE_NAME}-test

echo "Build completed successfully!"
echo "Image: ${IMAGE_TAG}"