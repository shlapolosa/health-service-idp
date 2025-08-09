#!/bin/bash

# Functional test for multi-cluster deployment system
# Tests complete flow from Slack API to vCluster deployment with database and Redis
# Uses random names to allow multiple test runs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Generate random suffix for unique naming
RANDOM_SUFFIX=$(head -c 100 /dev/urandom | base64 | tr -dc 'a-z0-9' | head -c 8)
TIMESTAMP=$(date +%s)
SERVICE_NAME="test-svc-${RANDOM_SUFFIX}"
SLACK_USER="test-user"
SLACK_CHANNEL="test"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}      Functional Test: Multi-Cluster System with DB & Redis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Test Configuration:${NC}"
echo "  Service Name: $SERVICE_NAME"
echo "  Random Suffix: $RANDOM_SUFFIX"
echo "  Timestamp: $TIMESTAMP"
echo ""

# Step 1: Get Istio Ingress Gateway URL
echo -e "${YELLOW}Step 1: Getting Istio Ingress Gateway URL...${NC}"
INGRESS_HOST=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [ -z "$INGRESS_HOST" ]; then
    echo -e "${RED}❌ Failed to get Istio ingress host${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Ingress Host: $INGRESS_HOST${NC}"

# Step 2: Send request to Slack API with database and Redis
echo -e "${YELLOW}Step 2: Sending request to Slack API...${NC}"
SLACK_URL="http://${INGRESS_HOST}/slack/command"
SLACK_COMMAND="create $SERVICE_NAME python with database with redis"

echo -e "${CYAN}Request Details:${NC}"
echo "  Command: /microservice $SLACK_COMMAND"
echo "  Service: $SERVICE_NAME"
echo "  Language: python"
echo "  Framework: fastapi (auto-detected)"
echo "  Database: postgres"
echo "  Cache: redis"
echo ""

RESPONSE=$(curl -s -X POST "$SLACK_URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=test-token&team_id=T12345&team_domain=test-team&channel_id=C12345&channel_name=$SLACK_CHANNEL&user_id=U12345&user_name=$SLACK_USER&command=/microservice&text=$SLACK_COMMAND&response_url=https://hooks.slack.com/commands/test&trigger_id=test-trigger-${TIMESTAMP}")

echo -e "${GREEN}✅ Request sent${NC}"
if echo "$RESPONSE" | grep -q "creation started"; then
    echo -e "${GREEN}✅ Slack API accepted the request${NC}"
else
    echo -e "${YELLOW}Response: $RESPONSE${NC}"
fi

# Step 3: Wait for workflow to complete
echo -e "${YELLOW}Step 3: Waiting for Argo workflow to complete...${NC}"
sleep 10

WORKFLOW=$(kubectl get workflow -n argo --sort-by=.metadata.creationTimestamp | tail -1 | awk '{print $1}')
echo "Workflow: $WORKFLOW"

# Monitor workflow
TIMEOUT=360
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(kubectl get workflow $WORKFLOW -n argo -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    
    if [ "$STATUS" == "Succeeded" ]; then
        echo -e "${GREEN}✅ Workflow completed successfully${NC}"
        break
    elif [ "$STATUS" == "Failed" ] || [ "$STATUS" == "Error" ]; then
        echo -e "${RED}❌ Workflow failed with status: $STATUS${NC}"
        kubectl logs -n argo workflow/$WORKFLOW --all-containers=true | tail -50
        exit 1
    else
        echo "   Status: $STATUS (${ELAPSED}s)"
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    fi
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${RED}❌ Workflow timed out after ${TIMEOUT}s${NC}"
    exit 1
fi

# Step 4: Wait for ApplicationClaim to be ready
echo -e "${YELLOW}Step 4: Waiting for ApplicationClaim to be ready...${NC}"
TIMEOUT=180
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    READY=$(kubectl get applicationclaim $SERVICE_NAME -n default -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    
    if [ "$READY" == "True" ]; then
        echo -e "${GREEN}✅ ApplicationClaim is ready${NC}"
        break
    else
        echo "   Waiting... (${ELAPSED}s)"
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    fi
done

# Step 5: Get and display all endpoints
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}                     Created Endpoints${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}"

# Get target vCluster
TARGET_VCLUSTER=$(kubectl get applicationclaim $SERVICE_NAME -n default -o jsonpath='{.spec.targetVCluster}')
echo -e "${CYAN}Target vCluster:${NC} $TARGET_VCLUSTER"

# Get GitOps repository
GITOPS_URL=$(kubectl get appcontainerclaim $SERVICE_NAME -n default -o jsonpath='{.status.gitopsRepository.cloneUrl}' 2>/dev/null)
if [ ! -z "$GITOPS_URL" ]; then
    echo -e "${CYAN}GitOps Repository:${NC} $GITOPS_URL"
    GITOPS_HTTPS=$(echo $GITOPS_URL | sed 's/\.git$//')
    echo -e "${CYAN}GitHub URL:${NC} $GITOPS_HTTPS"
fi

# Get vCluster LoadBalancer endpoint
VCLUSTER_LB=$(kubectl get svc -n $TARGET_VCLUSTER $TARGET_VCLUSTER -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ ! -z "$VCLUSTER_LB" ]; then
    echo -e "${CYAN}vCluster Endpoint:${NC} https://$VCLUSTER_LB"
fi

# Get ClusterGateway endpoint
CG_ENDPOINT=$(kubectl get clustergateway $TARGET_VCLUSTER -o jsonpath='{.spec.access.endpoint.const.address}' 2>/dev/null)
if [ ! -z "$CG_ENDPOINT" ]; then
    echo -e "${CYAN}ClusterGateway Endpoint:${NC} $CG_ENDPOINT"
fi

# Check ArgoCD application (if exists)
if kubectl get application -n argocd $SERVICE_NAME >/dev/null 2>&1; then
    echo -e "${CYAN}ArgoCD Application:${NC} $SERVICE_NAME"
    ARGOCD_URL="https://${INGRESS_HOST}/argocd/applications/$SERVICE_NAME"
    echo -e "${CYAN}ArgoCD UI:${NC} $ARGOCD_URL"
fi

echo ""

# Step 6: Verify database and Redis configuration
echo -e "${YELLOW}Step 6: Verifying database and Redis configuration...${NC}"

if [ ! -z "$GITOPS_URL" ]; then
    git clone $GITOPS_URL /tmp/${SERVICE_NAME}-gitops 2>/dev/null
    
    # Check OAM application for database and cache configuration
    if [ -f "/tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml" ]; then
        echo "Checking OAM application configuration..."
        
        # Check for database configuration
        if grep -q "database: postgres" /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml; then
            echo -e "${GREEN}✅ PostgreSQL database configured${NC}"
            DB_CONFIGURED=true
        else
            echo -e "${RED}❌ Database not found in configuration${NC}"
            DB_CONFIGURED=false
        fi
        
        # Check for Redis configuration
        if grep -q "cache: redis" /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml; then
            echo -e "${GREEN}✅ Redis cache configured${NC}"
            REDIS_CONFIGURED=true
        else
            echo -e "${RED}❌ Redis not found in configuration${NC}"
            REDIS_CONFIGURED=false
        fi
        
        # Display the component configuration
        echo ""
        echo -e "${CYAN}Component Configuration:${NC}"
        grep -A 10 "components:" /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml | head -20
    fi
fi

# Step 7: Check topology policy
echo ""
echo -e "${YELLOW}Step 7: Checking topology policy configuration...${NC}"

if [ -f "/tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml" ]; then
    TOPOLOGY_CLUSTER=$(grep -A 3 "policies:" /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml | grep "clusters:" | sed 's/.*\["\(.*\)"\].*/\1/')
    EXPECTED_CLUSTER="$SERVICE_NAME"
    
    echo "Expected vCluster: $EXPECTED_CLUSTER"
    echo "Actual vCluster in topology: $TOPOLOGY_CLUSTER"
    
    if [ "$TOPOLOGY_CLUSTER" == "$EXPECTED_CLUSTER" ]; then
        echo -e "${GREEN}✅ Topology policy has correct vCluster name${NC}"
        TOPOLOGY_CORRECT=true
    else
        echo -e "${RED}❌ Topology policy has wrong vCluster name${NC}"
        TOPOLOGY_CORRECT=false
    fi
    
    # Show full topology policy
    echo ""
    echo -e "${CYAN}Topology Policy:${NC}"
    grep -A 5 "policies:" /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml
fi

# Step 8: Deploy OAM application and check deployment
echo ""
echo -e "${YELLOW}Step 8: Deploying OAM application to test multi-cluster...${NC}"

if [ -f "/tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml" ]; then
    kubectl apply -f /tmp/${SERVICE_NAME}-gitops/oam/applications/application.yaml
    echo "Waiting for OAM application to deploy..."
    sleep 20
    
    # Check OAM application status
    OAM_STATUS=$(kubectl get application.core.oam.dev $SERVICE_NAME -n $SERVICE_NAME -o jsonpath='{.status.status}' 2>/dev/null)
    if [ "$OAM_STATUS" == "running" ]; then
        echo -e "${GREEN}✅ OAM Application deployed successfully${NC}"
        
        # Check if deployed to vCluster
        APPLIED_CLUSTERS=$(kubectl get application.core.oam.dev $SERVICE_NAME -n $SERVICE_NAME -o jsonpath='{.status.appliedResources[*].cluster}' 2>/dev/null)
        if echo "$APPLIED_CLUSTERS" | grep -q "$TARGET_VCLUSTER"; then
            echo -e "${GREEN}✅ Service deployed to vCluster: $TARGET_VCLUSTER${NC}"
            VCLUSTER_DEPLOYED=true
        else
            echo -e "${YELLOW}⚠️ Service not showing in vCluster yet${NC}"
            VCLUSTER_DEPLOYED=false
        fi
    else
        echo -e "${YELLOW}OAM Application status: $OAM_STATUS${NC}"
        VCLUSTER_DEPLOYED=false
    fi
fi

# Cleanup temp directory
rm -rf /tmp/${SERVICE_NAME}-gitops

# Step 9: Final summary with scoring
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      Test Results Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

SUCCESS_COUNT=0
TOTAL_CHECKS=6

echo "Checklist:"

# Check 1: ApplicationClaim created
if kubectl get applicationclaim $SERVICE_NAME -n default >/dev/null 2>&1; then
    echo "  ✅ ApplicationClaim created"
    ((SUCCESS_COUNT++))
else
    echo "  ❌ ApplicationClaim not created"
fi

# Check 2: GitOps repository created
if [ ! -z "$GITOPS_URL" ]; then
    echo "  ✅ GitOps repository created"
    ((SUCCESS_COUNT++))
else
    echo "  ❌ GitOps repository not created"
fi

# Check 3: Database configured
if [ "$DB_CONFIGURED" == "true" ]; then
    echo "  ✅ PostgreSQL database configured"
    ((SUCCESS_COUNT++))
else
    echo "  ❌ Database not configured"
fi

# Check 4: Redis configured
if [ "$REDIS_CONFIGURED" == "true" ]; then
    echo "  ✅ Redis cache configured"
    ((SUCCESS_COUNT++))
else
    echo "  ❌ Redis not configured"
fi

# Check 5: Topology policy correct
if [ "$TOPOLOGY_CORRECT" == "true" ]; then
    echo "  ✅ Topology policy correct"
    ((SUCCESS_COUNT++))
else
    echo "  ❌ Topology policy incorrect"
fi

# Check 6: ClusterGateway synchronized
if [ ! -z "$CG_ENDPOINT" ] && [ ! -z "$VCLUSTER_LB" ]; then
    CG_HOST=$(echo $CG_ENDPOINT | sed 's|https://||' | sed 's|:443||')
    if [ "$CG_HOST" == "$VCLUSTER_LB" ]; then
        echo "  ✅ ClusterGateway endpoint synchronized"
        ((SUCCESS_COUNT++))
    else
        echo "  ❌ ClusterGateway endpoint mismatch"
    fi
else
    echo "  ❌ ClusterGateway not verified"
fi

echo ""
echo -e "${CYAN}Score: $SUCCESS_COUNT / $TOTAL_CHECKS${NC}"

if [ $SUCCESS_COUNT -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}✅✅✅ PERFECT! All checks passed! ✅✅✅${NC}"
    EXIT_CODE=0
elif [ $SUCCESS_COUNT -ge 4 ]; then
    echo -e "${YELLOW}⚠️ Good - Most features working correctly${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}❌ Test failed - Multiple issues detected${NC}"
    EXIT_CODE=1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Test artifacts created:"
echo "  - Service: $SERVICE_NAME"
echo "  - Namespace: $SERVICE_NAME"
echo "  - vCluster: $TARGET_VCLUSTER"
echo "  - ApplicationClaim: kubectl get applicationclaim $SERVICE_NAME -n default"
echo "  - OAM Application: kubectl get application.core.oam.dev $SERVICE_NAME -n $SERVICE_NAME"
echo "  - Workflow: kubectl get workflow $WORKFLOW -n argo"
echo ""
echo "To clean up all resources:"
echo "  kubectl delete applicationclaim $SERVICE_NAME -n default"
echo "  kubectl delete namespace $SERVICE_NAME $TARGET_VCLUSTER"
echo "  kubectl delete application.core.oam.dev $SERVICE_NAME -n $SERVICE_NAME"
echo ""

exit $EXIT_CODE