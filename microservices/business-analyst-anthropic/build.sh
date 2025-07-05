#!/bin/bash
set -e

echo "Building business-analyst-anthropic microservice..."

# Copy shared-libs temporarily
cp -r ../shared-libs ./shared-libs

# Build the Docker image
docker build -t business-analyst-anthropic:latest .

# Clean up temporary copy
rm -rf ./shared-libs

echo "Build completed successfully!"
echo "To run: ./run.sh"
echo "To test: docker-compose up"