# Identity Service Template Generator Docker Image
# Used by Argo Workflows to generate Spring Boot identity services from templates

FROM ubuntu:22.04

# Install required tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    bash \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workspace

# Copy the identity-service-template repository
# Note: In production, this would be cloned from git or mounted as a volume
# For MVP, we'll clone it at runtime in the Argo Workflow

# Set up git config for the generator
RUN git config --global user.email "oam-generator@health-platform.io" && \
    git config --global user.name "OAM Identity Generator"

# Default command
CMD ["/bin/bash"]