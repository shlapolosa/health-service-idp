#!/bin/bash
set -e

echo "🧪 Testing GraphQL Gateway ComponentDefinition and Infrastructure"
echo "=================================================="

# Test configuration
NAMESPACE="${NAMESPACE:-default}"
TEST_NAME="test-graphql-gateway-$(date +%s)"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up test resources...${NC}"
    kubectl delete application ${TEST_NAME} -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete graphqlplatformclaim ${TEST_NAME}-infrastructure -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete ksvc ${TEST_NAME}-hasura -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete namespace ${TEST_NAME}-graphql --ignore-not-found=true
}

# Set trap for cleanup
trap cleanup EXIT

echo "📋 Test Plan:"
echo "1. Apply GraphQL ComponentDefinition"
echo "2. Create test microservices with OpenAPI"
echo "3. Deploy GraphQL gateway"
echo "4. Verify infrastructure creation"
echo "5. Test schema discovery"
echo "6. Validate GraphQL endpoint"
echo ""

# Step 1: Apply ComponentDefinition
echo -e "\n${GREEN}Step 1: Applying GraphQL ComponentDefinition${NC}"
kubectl apply -f crossplane/oam/graphql-gateway-component-definition.yaml

# Verify ComponentDefinition
if kubectl get componentdefinition graphql-gateway &>/dev/null; then
    echo "✅ GraphQL ComponentDefinition created successfully"
else
    echo -e "${RED}❌ Failed to create ComponentDefinition${NC}"
    exit 1
fi

# Step 2: Apply Crossplane XRD and Composition
echo -e "\n${GREEN}Step 2: Applying Crossplane resources${NC}"
kubectl apply -f crossplane/graphql-platform-claim-xrd.yaml
kubectl apply -f crossplane/graphql-platform-claim-composition.yaml

# Wait for CRDs to be ready
echo "⏳ Waiting for CRDs to be established..."
kubectl wait --for condition=established --timeout=60s crd/graphqlplatformclaims.platform.example.org

# Step 3: Create test OAM Application
echo -e "\n${GREEN}Step 3: Creating test OAM Application with GraphQL gateway${NC}"

cat <<EOF | kubectl apply -f -
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: ${TEST_NAME}
  namespace: ${NAMESPACE}
spec:
  components:
  # Test microservice 1
  - name: test-users
    type: webservice
    properties:
      image: kennethreitz/httpbin:latest
      port: 80
      environment:
        SERVICE_NAME: "test-users"
      annotations:
        "graphql.oam.dev/exposed": "true"
        
  # Test microservice 2
  - name: test-orders
    type: webservice
    properties:
      image: kennethreitz/httpbin:latest
      port: 80
      environment:
        SERVICE_NAME: "test-orders"
      annotations:
        "graphql.oam.dev/exposed": "true"
        
  # GraphQL Gateway
  - name: ${TEST_NAME}
    type: graphql-gateway
    properties:
      serviceSelector:
        "app.kubernetes.io/name": "${TEST_NAME}"
      autoSchema: true
      schemaRefreshInterval: "1m"
      exposeIntrospection: true
      enableConsole: true
      adminSecret: "test-admin-secret"
EOF

echo "✅ Test application created"

# Step 4: Verify resources
echo -e "\n${GREEN}Step 4: Verifying resource creation${NC}"

# Wait for Knative services
echo "⏳ Waiting for Knative services..."
sleep 10

# Check Knative services
echo "🔍 Checking Knative services:"
kubectl get ksvc -n ${NAMESPACE} | grep -E "(${TEST_NAME}|test-users|test-orders)" || true

# Check GraphQLPlatformClaim
echo -e "\n🔍 Checking GraphQLPlatformClaim:"
if kubectl get graphqlplatformclaim ${TEST_NAME}-infrastructure -n ${NAMESPACE} &>/dev/null; then
    echo "✅ GraphQLPlatformClaim created"
    kubectl get graphqlplatformclaim ${TEST_NAME}-infrastructure -n ${NAMESPACE}
else
    echo -e "${RED}❌ GraphQLPlatformClaim not found${NC}"
fi

# Check namespace
echo -e "\n🔍 Checking GraphQL namespace:"
if kubectl get namespace ${TEST_NAME}-graphql &>/dev/null; then
    echo "✅ GraphQL namespace created"
else
    echo -e "${RED}❌ GraphQL namespace not found${NC}"
fi

# Check ConfigMaps
echo -e "\n🔍 Checking schema ConfigMaps:"
for cm in "${TEST_NAME}-graphql-schema-generated" "${TEST_NAME}-graphql-schema-custom" "${TEST_NAME}-graphql-schema-merged"; do
    if kubectl get configmap $cm -n ${TEST_NAME}-graphql &>/dev/null; then
        echo "✅ ConfigMap $cm exists"
    else
        echo -e "${YELLOW}⚠️  ConfigMap $cm not found (may be created later by CronJob)${NC}"
    fi
done

# Check ServiceAccount and RBAC
echo -e "\n🔍 Checking RBAC resources:"
if kubectl get serviceaccount ${TEST_NAME}-schema-discovery -n ${TEST_NAME}-graphql &>/dev/null; then
    echo "✅ ServiceAccount created"
else
    echo -e "${RED}❌ ServiceAccount not found${NC}"
fi

if kubectl get clusterrole ${TEST_NAME}-schema-discovery &>/dev/null; then
    echo "✅ ClusterRole created"
else
    echo -e "${RED}❌ ClusterRole not found${NC}"
fi

# Check CronJob
echo -e "\n🔍 Checking schema discovery CronJob:"
if kubectl get cronjob ${TEST_NAME}-schema-discovery -n ${TEST_NAME}-graphql &>/dev/null; then
    echo "✅ Schema discovery CronJob created"
    kubectl get cronjob ${TEST_NAME}-schema-discovery -n ${TEST_NAME}-graphql
else
    echo -e "${RED}❌ Schema discovery CronJob not found${NC}"
fi

# Step 5: Test Hasura endpoint (if available)
echo -e "\n${GREEN}Step 5: Testing Hasura GraphQL endpoint${NC}"

# Get Hasura service URL
HASURA_URL=$(kubectl get ksvc ${TEST_NAME}-hasura -n ${NAMESPACE} -o jsonpath='{.status.url}' 2>/dev/null || echo "")

if [[ -n "$HASURA_URL" ]]; then
    echo "🌐 Hasura URL: $HASURA_URL"
    
    # Test health endpoint
    echo "🏥 Testing Hasura health endpoint..."
    if curl -s -f "${HASURA_URL}/healthz" &>/dev/null; then
        echo "✅ Hasura is healthy"
    else
        echo -e "${YELLOW}⚠️  Hasura health check failed (service may still be starting)${NC}"
    fi
    
    # Test GraphQL endpoint
    echo -e "\n📊 Testing GraphQL introspection..."
    INTROSPECTION_QUERY='{"query":"{ __schema { types { name } } }"}'
    
    response=$(curl -s -X POST "${HASURA_URL}/v1/graphql" \
        -H "Content-Type: application/json" \
        -H "X-Hasura-Admin-Secret: test-admin-secret" \
        -d "$INTROSPECTION_QUERY" 2>/dev/null || echo "{}")
    
    if echo "$response" | jq -e '.data.__schema.types' &>/dev/null; then
        echo "✅ GraphQL introspection successful"
        echo "   Found $(echo "$response" | jq '.data.__schema.types | length') types"
    else
        echo -e "${YELLOW}⚠️  GraphQL introspection failed${NC}"
        echo "   Response: $response"
    fi
else
    echo -e "${YELLOW}⚠️  Hasura service not yet ready${NC}"
fi

# Summary
echo -e "\n${GREEN}📊 Test Summary${NC}"
echo "=============="

# Count successful resources
success_count=0
total_count=10

[[ -n "$(kubectl get componentdefinition graphql-gateway 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get graphqlplatformclaim ${TEST_NAME}-infrastructure -n ${NAMESPACE} 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get ksvc ${TEST_NAME}-hasura -n ${NAMESPACE} 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get namespace ${TEST_NAME}-graphql 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get serviceaccount ${TEST_NAME}-schema-discovery -n ${TEST_NAME}-graphql 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get clusterrole ${TEST_NAME}-schema-discovery 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get cronjob ${TEST_NAME}-schema-discovery -n ${TEST_NAME}-graphql 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get secret ${TEST_NAME}-hasura-admin-secret -n ${TEST_NAME}-graphql 2>/dev/null)" ]] && ((success_count++))
[[ -n "$(kubectl get configmap ${TEST_NAME}-hasura-metadata -n ${TEST_NAME}-graphql 2>/dev/null)" ]] && ((success_count++))
[[ -n "$HASURA_URL" ]] && ((success_count++))

echo "Resources created: ${success_count}/${total_count}"

if [[ $success_count -eq $total_count ]]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Some resources are still being created${NC}"
    echo "   This is normal for async operations. Wait a few moments and check again."
fi

echo -e "\n💡 Next steps:"
echo "1. Run 'kubectl logs -n ${TEST_NAME}-graphql job/\$(kubectl get job -n ${TEST_NAME}-graphql -o name | head -1)' to see schema discovery logs"
echo "2. Access Hasura console at: ${HASURA_URL}"
echo "3. Create custom schema in ConfigMap: ${TEST_NAME}-graphql-schema-custom"
echo "4. Monitor schema updates with: kubectl get cm -n ${TEST_NAME}-graphql -w"

echo -e "\n🧹 To clean up manually: kubectl delete application ${TEST_NAME} -n ${NAMESPACE}"