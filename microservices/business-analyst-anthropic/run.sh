#!/bin/bash
set -e

echo "Running business-analyst-anthropic microservice..."
docker run -p 8080:8080 \
  -e LOG_LEVEL=INFO \
  -e AGENT_TYPE=business-analyst \
  -e IMPLEMENTATION_TYPE=anthropic \
  business-analyst-anthropic:latest