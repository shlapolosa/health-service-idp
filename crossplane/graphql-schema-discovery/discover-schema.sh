#!/bin/bash
set -e

echo "🔍 Starting GraphQL schema discovery for platform: ${GRAPHQL_PLATFORM_NAME}"

# Environment variables
NAMESPACE="${NAMESPACE:-default}"
SERVICE_SELECTOR="${SERVICE_SELECTOR:-{\"app.kubernetes.io/managed-by\":\"kubevela\"}}"
SCHEMA_GENERATED="${SCHEMA_CONFIGMAP_GENERATED}"
SCHEMA_CUSTOM="${SCHEMA_CONFIGMAP_CUSTOM}"
SCHEMA_MERGED="${SCHEMA_CONFIGMAP_MERGED}"

# Function to fetch OpenAPI spec from a service
fetch_openapi_spec() {
    local service_name=$1
    local namespace=$2
    local port=${3:-8080}
    
    echo "  📡 Fetching OpenAPI spec from ${service_name}.${namespace}:${port}"
    
    # Try multiple common OpenAPI endpoints
    for endpoint in "/openapi" "/swagger" "/openapi.json" "/swagger.json" "/api/openapi" "/api/swagger" "/docs/openapi.json"; do
        response=$(curl -s -w "\n%{http_code}" "http://${service_name}.${namespace}.svc.cluster.local:${port}${endpoint}" 2>/dev/null || echo "000")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')
        
        if [[ "$http_code" == "200" ]]; then
            echo "  ✅ Found OpenAPI spec at ${endpoint}"
            echo "$body"
            return 0
        fi
    done
    
    echo "  ⚠️  No OpenAPI spec found for ${service_name}"
    return 1
}

# Function to convert OpenAPI to GraphQL schema
convert_to_graphql() {
    local service_name=$1
    local openapi_spec=$2
    
    echo "  🔄 Converting OpenAPI to GraphQL for ${service_name}"
    
    # Save OpenAPI spec to temporary file
    echo "$openapi_spec" > "/tmp/${service_name}-openapi.json"
    
    # Convert using openapi-to-graphql
    if openapi-to-graphql "/tmp/${service_name}-openapi.json" \
        --save "/tmp/${service_name}-graphql.json" \
        --operationIdFieldNames \
        --fillEmptyResponses 2>/dev/null; then
        
        # Extract just the schema part
        cat "/tmp/${service_name}-graphql.json" | jq -r '.schema // empty'
        return 0
    else
        echo "  ⚠️  Failed to convert OpenAPI to GraphQL for ${service_name}"
        return 1
    fi
}

# Function to create Hasura remote schema config
create_remote_schema_config() {
    local service_name=$1
    local namespace=$2
    local port=${3:-8080}
    
    cat <<EOF
{
  "name": "${service_name}_remote",
  "definition": {
    "url": "http://${service_name}.${namespace}.svc.cluster.local:${port}/graphql",
    "timeout_seconds": 60,
    "customization": {
      "root_fields_namespace": "${service_name}"
    }
  }
}
EOF
}

# Main discovery process
echo "📊 Discovering Knative services with selector: ${SERVICE_SELECTOR}"

# Get all Knative services matching the selector
services=$(kubectl get ksvc -A -l "$(echo $SERVICE_SELECTOR | jq -r 'to_entries | map("\(.key)=\(.value)") | join(",")' 2>/dev/null || echo "")" -o json)

# Also check for services with GraphQL exposure annotation
graphql_services=$(kubectl get ksvc -A -l "graphql.oam.dev/exposed=true" -o json 2>/dev/null || echo '{"items":[]}')

# Combine and deduplicate services
all_services=$(echo "$services" "$graphql_services" | jq -s '.[0].items + .[1].items | unique_by(.metadata.name)')

# Initialize arrays for schemas and remote schemas
declare -a graphql_schemas
declare -a remote_schemas

# Process each service
echo "$all_services" | jq -c '.[]' | while read -r service; do
    name=$(echo "$service" | jq -r '.metadata.name')
    namespace=$(echo "$service" | jq -r '.metadata.namespace')
    
    # Skip if it's the GraphQL gateway itself
    if [[ "$name" == *"-hasura"* ]] || [[ "$name" == *"graphql-gateway"* ]]; then
        continue
    fi
    
    echo "🔍 Processing service: ${name} in namespace: ${namespace}"
    
    # Check if service has GraphQL endpoint annotation
    has_graphql=$(echo "$service" | jq -r '.metadata.annotations["graphql.oam.dev/has-graphql"] // "false"')
    
    if [[ "$has_graphql" == "true" ]]; then
        # Service already exposes GraphQL, add as remote schema
        echo "  ✨ Service exposes native GraphQL endpoint"
        remote_schema=$(create_remote_schema_config "$name" "$namespace")
        remote_schemas+=("$remote_schema")
    else
        # Try to fetch OpenAPI spec and convert to GraphQL
        if openapi_spec=$(fetch_openapi_spec "$name" "$namespace"); then
            if graphql_schema=$(convert_to_graphql "$name" "$openapi_spec"); then
                graphql_schemas+=("$graphql_schema")
                
                # Also create remote schema config for REST endpoint wrapping
                cat <<EOF > "/tmp/${name}-remote-schema.json"
{
  "name": "${name}_rest",
  "definition": {
    "url": "http://${name}.${namespace}.svc.cluster.local:8080",
    "timeout_seconds": 60,
    "customization": {
      "root_fields_namespace": "${name}"
    },
    "forward_client_headers": true
  },
  "comment": "Auto-generated REST wrapper for ${name}"
}
EOF
                remote_schemas+=("$(cat /tmp/${name}-remote-schema.json)")
            fi
        fi
    fi
done

# Generate consolidated GraphQL schema
echo "📝 Generating consolidated GraphQL schema"

cat > /tmp/generated-schema.graphql <<'EOF'
# Auto-generated GraphQL Schema
# Generated at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Platform: ${GRAPHQL_PLATFORM_NAME}
# Discovered services: $(echo "$all_services" | jq length)

schema {
  query: Query
  mutation: Mutation
}

type Query {
  _service: String
EOF

# Add discovered schemas
for schema in "${graphql_schemas[@]}"; do
    echo "$schema" >> /tmp/generated-schema.graphql
done

# Close the schema
echo "}" >> /tmp/generated-schema.graphql
echo "" >> /tmp/generated-schema.graphql
echo "type Mutation {" >> /tmp/generated-schema.graphql
echo "  _placeholder: String" >> /tmp/generated-schema.graphql
echo "}" >> /tmp/generated-schema.graphql

# Generate Hasura metadata
echo "🔧 Generating Hasura metadata"

cat > /tmp/hasura-metadata.json <<EOF
{
  "version": 3,
  "sources": [],
  "remote_schemas": [
EOF

# Add remote schemas
first=true
for remote in "${remote_schemas[@]}"; do
    if [[ "$first" == "true" ]]; then
        first=false
    else
        echo "," >> /tmp/hasura-metadata.json
    fi
    echo "$remote" >> /tmp/hasura-metadata.json
done

cat >> /tmp/hasura-metadata.json <<EOF
  ],
  "query_collections": [],
  "allowlist": [],
  "custom_types": {
    "input_objects": [],
    "objects": [],
    "scalars": [],
    "enums": []
  },
  "actions": [],
  "cron_triggers": []
}
EOF

# Merge with custom schema if exists
echo "🔀 Merging with custom schema overrides"

# Get custom schema from ConfigMap
custom_schema=$(kubectl get configmap "${SCHEMA_CUSTOM}" -n "${NAMESPACE}" -o jsonpath='{.data.schema\.graphql}' 2>/dev/null || echo "")

if [[ -n "$custom_schema" ]]; then
    echo "  ✅ Found custom schema, merging..."
    # Use Node.js script to merge schemas
    node /app/merge-schemas.js /tmp/generated-schema.graphql <(echo "$custom_schema") > /tmp/merged-schema.graphql
else
    echo "  ℹ️  No custom schema found, using generated schema"
    cp /tmp/generated-schema.graphql /tmp/merged-schema.graphql
fi

# Update ConfigMaps
echo "💾 Updating ConfigMaps"

# Update generated schema ConfigMap
kubectl create configmap "${SCHEMA_GENERATED}" \
    --from-file=schema.graphql=/tmp/generated-schema.graphql \
    --from-file=hasura-metadata.json=/tmp/hasura-metadata.json \
    -n "${NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "  ✅ Updated ${SCHEMA_GENERATED}"

# Update merged schema ConfigMap
kubectl create configmap "${SCHEMA_MERGED}" \
    --from-file=schema.graphql=/tmp/merged-schema.graphql \
    --from-file=hasura-metadata.json=/tmp/hasura-metadata.json \
    -n "${NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "  ✅ Updated ${SCHEMA_MERGED}"

# Update metadata ConfigMap for Hasura
kubectl create configmap "${GRAPHQL_PLATFORM_NAME}-hasura-metadata" \
    --from-file=metadata.json=/tmp/hasura-metadata.json \
    -n "${NAMESPACE}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "  ✅ Updated Hasura metadata"

echo "✨ Schema discovery completed successfully!"
echo "📊 Summary:"
echo "  - Services discovered: $(echo "$all_services" | jq length)"
echo "  - GraphQL schemas generated: ${#graphql_schemas[@]}"
echo "  - Remote schemas configured: ${#remote_schemas[@]}"
echo "  - Schema version: $(date -u +"%Y%m%d%H%M%S")"