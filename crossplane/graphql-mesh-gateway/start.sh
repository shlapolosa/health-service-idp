#!/bin/bash
set -e

echo "🚀 Starting GraphQL Mesh Gateway"
echo "===================================="

# Environment variables with defaults
GATEWAY_NAME="${GATEWAY_NAME:-api-gateway}"
NAMESPACE="${NAMESPACE:-default}"
SERVICE_SELECTOR="${SERVICE_SELECTOR:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
MESH_CONFIG_FILE="${MESH_CONFIG_FILE:-/app/.meshrc.yaml}"
AUTO_DISCOVERY="${AUTO_DISCOVERY:-true}"
DISCOVERY_INTERVAL="${DISCOVERY_INTERVAL:-300}"  # 5 minutes

echo "📋 Configuration:"
echo "  Gateway Name: $GATEWAY_NAME"
echo "  Namespace: $NAMESPACE"
echo "  Service Selector: $SERVICE_SELECTOR"
echo "  Auto Discovery: $AUTO_DISCOVERY"
echo "  Discovery Interval: ${DISCOVERY_INTERVAL}s"
echo ""

# Function to run service discovery
run_discovery() {
    echo "🔍 Running service discovery..."
    if ./generate-mesh-config.sh; then
        echo "✅ Service discovery completed successfully"
        return 0
    else
        echo "⚠️  Service discovery failed, continuing with existing config"
        return 1
    fi
}

# Function to check if mesh config exists and is valid
check_mesh_config() {
    if [[ -f "$MESH_CONFIG_FILE" ]]; then
        echo "📄 Found existing mesh configuration"
        # Basic validation - check if it's valid YAML
        if yq eval '.' "$MESH_CONFIG_FILE" > /dev/null 2>&1; then
            echo "✅ Mesh configuration is valid"
            return 0
        else
            echo "❌ Mesh configuration is invalid"
            return 1
        fi
    else
        echo "📝 No mesh configuration found"
        return 1
    fi
}

# Function to create minimal fallback config
create_fallback_config() {
    echo "🔧 Creating fallback mesh configuration..."
    cat > "$MESH_CONFIG_FILE" << 'EOF'
# Fallback GraphQL Mesh Configuration
serve:
  port: 8080
  hostname: "0.0.0.0"
  cors:
    origin: "*"
    credentials: false
  playground: true
  endpoint: "/graphql"
  healthCheckEndpoint: "/healthz"

sources: []

additionalTypeDefs: |
  type Query {
    _gateway: String!
    _health: String!
    _status: String!
  }

cache:
  inmemory: {}

logger:
  level: info
  format: json
EOF
    echo "✅ Fallback configuration created"
}

# Function to run background discovery
run_background_discovery() {
    while true; do
        echo "🔄 Running scheduled service discovery (every ${DISCOVERY_INTERVAL}s)"
        if run_discovery; then
            echo "📊 Discovery successful, configuration updated"
        else
            echo "⚠️  Discovery failed, keeping current configuration"
        fi
        sleep "$DISCOVERY_INTERVAL"
    done
}

# Initial setup
echo "🔧 Initial setup..."

# Check if we can access Kubernetes API
if ! kubectl auth can-i get services --quiet 2>/dev/null; then
    echo "⚠️  Warning: Cannot access Kubernetes API. Service discovery will be limited."
    echo "   Make sure the pod has proper RBAC permissions."
fi

# Run initial discovery if auto-discovery is enabled
if [[ "$AUTO_DISCOVERY" == "true" ]]; then
    echo "🔍 Running initial service discovery..."
    if ! run_discovery; then
        echo "⚠️  Initial discovery failed"
        if ! check_mesh_config; then
            echo "🔧 Creating fallback configuration..."
            create_fallback_config
        fi
    fi
else
    echo "⏭️  Auto-discovery disabled, checking for existing config..."
    if ! check_mesh_config; then
        echo "🔧 No valid config found, creating fallback..."
        create_fallback_config
    fi
fi

# Start background discovery if enabled
if [[ "$AUTO_DISCOVERY" == "true" ]] && [[ "$DISCOVERY_INTERVAL" -gt 0 ]]; then
    echo "🔄 Starting background service discovery..."
    run_background_discovery &
    DISCOVERY_PID=$!
    echo "📡 Background discovery started (PID: $DISCOVERY_PID)"
fi

# Function to handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down GraphQL Mesh Gateway..."
    
    # Kill background discovery process
    if [[ -n "$DISCOVERY_PID" ]]; then
        echo "🔄 Stopping background discovery..."
        kill "$DISCOVERY_PID" 2>/dev/null || true
        wait "$DISCOVERY_PID" 2>/dev/null || true
        echo "✅ Background discovery stopped"
    fi
    
    # Kill the main server process
    if [[ -n "$SERVER_PID" ]]; then
        echo "🛡️  Stopping server..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        echo "✅ Server stopped"
    fi
    
    echo "👋 Goodbye!"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Validate final configuration
echo "🔍 Validating mesh configuration..."
if [[ -f "$MESH_CONFIG_FILE" ]]; then
    if yq eval '.' "$MESH_CONFIG_FILE" > /dev/null 2>&1; then
        sources_count=$(yq eval '.sources | length' "$MESH_CONFIG_FILE" 2>/dev/null || echo "0")
        echo "✅ Configuration valid with $sources_count sources"
    else
        echo "❌ Configuration invalid, creating emergency fallback..."
        create_fallback_config
    fi
else
    echo "❌ No configuration file found, creating emergency fallback..."
    create_fallback_config
fi

echo ""
echo "🚀 Starting GraphQL Mesh Gateway Server..."
echo "===================================="

# Start the main server
node server.js &
SERVER_PID=$!

echo "📡 Server started (PID: $SERVER_PID)"
echo "🏥 Health endpoint: http://localhost:8080/healthz"
echo "🎮 GraphQL endpoint: http://localhost:8080/graphql"
echo "ℹ️  Info endpoint: http://localhost:8080/info"
echo ""
echo "✨ Gateway is ready!"

# Wait for the server process
wait "$SERVER_PID"