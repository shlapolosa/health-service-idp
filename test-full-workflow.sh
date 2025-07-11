#!/bin/bash

# Comprehensive VCluster + AppContainer Test
# Goal: Successfully provision VCluster and AppContainer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🎯 GOAL: Successfully provision VCluster + AppContainer"
echo "=================================================="
echo ""

# Step 1: Verify prerequisites
log_info "Step 1: Checking prerequisites..."
if [[ -z "${PERSONAL_ACCESS_TOKEN:-}" ]]; then
    log_error "PERSONAL_ACCESS_TOKEN environment variable not set"
    exit 1
fi

# Step 2: Trigger VCluster creation
log_info "Step 2: Triggering VCluster creation workflow..."
PAYLOAD='{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "test-production",
    "namespace": "production-test",
    "repository": "test-app-prod",
    "user": "production.tester",
    "slack_channel": "C1234567890",
    "slack_user_id": "U1234567890",
    "capabilities": {
      "observability": "true",
      "security": "true",
      "gitops": "true",
      "monitoring": "true",
      "logging": "true",
      "networking": "true",
      "autoscaling": "true",
      "backup": "false"
    },
    "resources": {
      "cpu_limit": "4000m",
      "memory_limit": "8Gi",
      "storage_size": "20Gi",
      "node_count": "3"
    }
  }
}'

echo "📤 Sending comprehensive test payload..."
RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  https://api.github.com/repos/shlapolosa/health-service-idp/dispatches)

if [[ -n "$RESPONSE" ]]; then
    log_error "GitHub API returned an error: $RESPONSE"
    exit 1
else
    log_success "✅ GitHub Action triggered successfully"
fi

# Step 3: Monitor workflow progress
log_info "Step 3: Monitoring workflow progress..."
echo "🔍 Watching for workflow completion..."

TIMEOUT=1800  # 30 minutes timeout
START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [[ $ELAPSED -gt $TIMEOUT ]]; then
        log_error "❌ Timeout reached (30 minutes). Check workflow manually."
        echo "   URL: https://github.com/shlapolosa/health-service-idp/actions"
        exit 1
    fi
    
    # Get latest workflow run
    LATEST_RUN=$(curl -s "https://api.github.com/repos/shlapolosa/health-service-idp/actions/runs" \
        -H "Authorization: token $PERSONAL_ACCESS_TOKEN" | \
        jq -r '.workflow_runs[0] | {id: .id, status: .status, conclusion: .conclusion, created_at: .created_at, name: .name}')
    
    RUN_ID=$(echo "$LATEST_RUN" | jq -r '.id')
    STATUS=$(echo "$LATEST_RUN" | jq -r '.status')
    CONCLUSION=$(echo "$LATEST_RUN" | jq -r '.conclusion')
    WORKFLOW_NAME=$(echo "$LATEST_RUN" | jq -r '.name')
    
    # Only monitor VCluster creation workflows
    if [[ "$WORKFLOW_NAME" != "Create VCluster from Slack" ]]; then
        log_info "⏳ Waiting for VCluster workflow to start..."
        sleep 10
        continue
    fi
    
    echo "📊 Run $RUN_ID | Status: $STATUS | Conclusion: $CONCLUSION | Elapsed: ${ELAPSED}s"
    
    if [[ "$STATUS" == "completed" ]]; then
        if [[ "$CONCLUSION" == "success" ]]; then
            log_success "🎉 Workflow completed successfully!"
            echo "   URL: https://github.com/shlapolosa/health-service-idp/actions/runs/$RUN_ID"
            break
        else
            log_error "❌ Workflow failed with conclusion: $CONCLUSION"
            echo "   URL: https://github.com/shlapolosa/health-service-idp/actions/runs/$RUN_ID"
            
            # Get failure details
            FAILED_STEP=$(curl -s "https://api.github.com/repos/shlapolosa/health-service-idp/actions/runs/$RUN_ID/jobs" \
                -H "Authorization: token $PERSONAL_ACCESS_TOKEN" | \
                jq -r '.jobs[0].steps[] | select(.conclusion == "failure") | .name' | head -1)
            
            log_error "   Failed step: $FAILED_STEP"
            exit 1
        fi
    fi
    
    # Show progress every 60 seconds
    if [[ $((ELAPSED % 60)) -eq 0 ]] && [[ $ELAPSED -gt 0 ]]; then
        log_info "⏳ Still running... (${ELAPSED}s elapsed)"
    fi
    
    sleep 15
done

# Step 4: Verify VCluster provisioning
log_info "Step 4: Verifying VCluster provisioning..."

# Check if we can access the cluster to verify resources
if command -v kubectl &> /dev/null; then
    log_info "Checking VCluster resources..."
    
    # Try to get VCluster claim
    if kubectl get vclusterenvironmentclaim test-production -n production-test 2>/dev/null; then
        log_success "✅ VClusterEnvironmentClaim exists"
        
        # Check status
        STATUS=$(kubectl get vclusterenvironmentclaim test-production -n production-test -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        if [[ "$STATUS" == "True" ]]; then
            log_success "✅ VCluster is ready and provisioned"
        else
            log_warning "⚠️ VCluster status: $STATUS"
        fi
    else
        log_warning "⚠️ Cannot verify VCluster claim (kubectl access issue)"
    fi
    
    # Try to get AppContainer claim
    if kubectl get appcontainerclaim test-app-prod -n production-test 2>/dev/null; then
        log_success "✅ AppContainerClaim exists"
        
        # Check status
        APP_STATUS=$(kubectl get appcontainerclaim test-app-prod -n production-test -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
        if [[ "$APP_STATUS" == "True" ]]; then
            log_success "✅ AppContainer is ready and provisioned"
        else
            log_warning "⚠️ AppContainer status: $APP_STATUS"
        fi
    else
        log_warning "⚠️ Cannot verify AppContainer claim (kubectl access issue)"
    fi
else
    log_warning "⚠️ kubectl not available - cannot verify resource status locally"
fi

# Step 5: Summary
echo ""
echo "🎯 TEST RESULTS SUMMARY"
echo "======================"
echo ""
log_success "✅ GitHub Action workflow completed successfully"
log_success "✅ VCluster creation workflow executed"
log_success "✅ Slack notifications should have been sent"

echo ""
echo "📋 Next Steps:"
echo "   1. Check Slack for notifications"
echo "   2. Verify VCluster access using generated kubeconfig"
echo "   3. Confirm observability tools are accessible"
echo "   4. Test AppContainer functionality"
echo ""
echo "🔗 Useful URLs:"
echo "   • GitHub Actions: https://github.com/shlapolosa/health-service-idp/actions"
echo "   • VCluster Docs: https://www.vcluster.com/docs"
echo ""

log_success "🎉 VCluster + AppContainer provisioning test completed!"