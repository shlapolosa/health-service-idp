#!/bin/bash
set -e

# Build and push the GraphQL schema discovery image
IMAGE_NAME="socrates12345/graphql-schema-discovery"
VERSION="${VERSION:-latest}"

echo "🔨 Building GraphQL schema discovery image: ${IMAGE_NAME}:${VERSION}"

# Build the Docker image
docker build -t "${IMAGE_NAME}:${VERSION}" .

# Tag as latest if not already
if [[ "$VERSION" != "latest" ]]; then
    docker tag "${IMAGE_NAME}:${VERSION}" "${IMAGE_NAME}:latest"
fi

echo "📤 Pushing image to registry..."
docker push "${IMAGE_NAME}:${VERSION}"

if [[ "$VERSION" != "latest" ]]; then
    docker push "${IMAGE_NAME}:latest"
fi

echo "✅ GraphQL schema discovery image built and pushed successfully!"
echo "   Image: ${IMAGE_NAME}:${VERSION}"