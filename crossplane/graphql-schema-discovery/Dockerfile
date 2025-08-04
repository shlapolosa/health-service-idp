FROM alpine:3.18

# Install dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    nodejs \
    npm \
    kubectl

# Install openapi-to-graphql globally
RUN npm install -g openapi-to-graphql

# Create app directory
WORKDIR /app

# Copy schema discovery script
COPY discover-schema.sh /app/
COPY merge-schemas.js /app/

# Make scripts executable
RUN chmod +x /app/discover-schema.sh

# Set entrypoint
ENTRYPOINT ["/app/discover-schema.sh"]