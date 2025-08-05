# GraphQL Mesh Gateway Docker Image
# Lightweight Node.js container for service discovery and GraphQL federation
FROM node:18-alpine

# Install system dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    kubectl

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev --legacy-peer-deps && npm cache clean --force

# Copy application files
COPY mesh-config-template.yaml ./
COPY generate-mesh-config.sh ./
COPY server.js ./
COPY start.sh ./

# Make scripts executable
RUN chmod +x generate-mesh-config.sh start.sh

# Create non-root user
RUN addgroup -g 1001 -S mesh && \
    adduser -S mesh -u 1001 -G mesh

# Change ownership of the app directory
RUN chown -R mesh:mesh /app

# Switch to non-root user
USER mesh

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/healthz || exit 1

# Start the application
ENTRYPOINT ["./start.sh"]