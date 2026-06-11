#!/usr/bin/env bash
# HARD-1 (#168): nodejs/graphql-gateway scaffold — heredoc lines 127-164 verbatim.
mscv_scaffold_nodejs_graphql() {
  # Copy GraphQL gateway template structure
  cp -r $TEMPLATE_DIR/microservices/graphql-gateway/* microservices/$SERVICE_NAME/
  cd microservices/$SERVICE_NAME
  
  # Debug: Show what was actually copied
  echo "📋 Files copied from template:"
  ls -la
  echo "📋 Template package.json content:"
  [ -f "package.json" ] && head -20 package.json || echo "❌ package.json not found"
  
  # Customize template for the specific service (handle missing files gracefully)
  [ -f "package.json" ] && sed -i "s/graphql-gateway/$SERVICE_NAME/g" package.json
  [ -f "README.md" ] && sed -i "s/graphql-gateway/$SERVICE_NAME/g" README.md && sed -i "s/GraphQL Gateway/$SERVICE_NAME Gateway/g" README.md
  [ -f "docker-compose.yml" ] && sed -i "s/graphql-gateway/$SERVICE_NAME/g" docker-compose.yml
  [ -f "package.json" ] && sed -i "s/Federation Gateway/$SERVICE_NAME Federation Gateway/g" package.json
  
  # Ensure we have the latest GraphQL Mesh dependencies
  if [ -f "package.json" ]; then
    echo "📦 Verifying GraphQL Mesh dependencies..."
    if ! grep -q "@graphql-mesh/runtime" package.json; then
      echo "⚠️  Missing GraphQL Mesh dependencies - force updating from latest template"
      # Re-copy package.json and package-lock.json from template to ensure latest dependencies
      cp $TEMPLATE_DIR/microservices/graphql-gateway/package.json .
      cp $TEMPLATE_DIR/microservices/graphql-gateway/package-lock.json .
      # Re-apply service name customization
      sed -i "s/graphql-gateway/$SERVICE_NAME/g" package.json
      sed -i "s/Federation Gateway/$SERVICE_NAME Federation Gateway/g" package.json
      echo "✅ Updated package.json with latest GraphQL Mesh dependencies"
    else
      echo "✅ GraphQL Mesh dependencies already present"
    fi
  fi
  
  # Update Kubernetes manifests
  find . -name "*.yaml" -exec sed -i "s/graphql-gateway/$SERVICE_NAME/g" {} \;
  find . -name "*.yaml" -exec sed -i "s/APP_CONTAINER_PLACEHOLDER/$APP_CONTAINER/g" {} \;
  
  echo "✅ Successfully created GraphQL federation gateway microservice from template"
}
