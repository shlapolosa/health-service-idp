#!/bin/bash

# Build script for identity-template-generator Docker image
# This image is used by Argo Workflows to generate Spring Boot identity services

set -e

# Configuration
IMAGE_NAME="identity-template-generator"
IMAGE_TAG="latest"
REGISTRY="socrates12345"
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building identity-template-generator Docker image..."
echo "Image: ${FULL_IMAGE_NAME}"

# Build the Docker image
docker build -t ${FULL_IMAGE_NAME} .

echo "Image built successfully: ${FULL_IMAGE_NAME}"

# Optional: Push to registry
read -p "Do you want to push the image to the registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Pushing image to registry..."
    docker push ${FULL_IMAGE_NAME}
    echo "Image pushed successfully!"
else
    echo "Image not pushed. To push manually, run:"
    echo "  docker push ${FULL_IMAGE_NAME}"
fi

echo ""
echo "To use this image in Argo Workflows:"
echo "  Update argo-workflows/identity-service-generator.yaml"
echo "  Set image to: ${FULL_IMAGE_NAME}"