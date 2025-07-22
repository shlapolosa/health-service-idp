#!/bin/bash
# Test OAM → Crossplane Workflow Orchestration
# This script creates a test OAM Application to validate the workflow orchestration

set -e

echo "🧪 Testing OAM → Crossplane Workflow Orchestration"
echo "================================================="

# Check prerequisites
if ! kubectl get workflowstepdefinition create-crossplane-claims -n vela-system &>/dev/null; then
    echo "❌ Custom WorkflowStepDefinitions not found. Run ./install-workflow-orchestration.sh first"
    exit 1
fi

# Create test namespace
TEST_NAMESPACE="workflow-orchestration-test"
echo "📋 Creating test namespace: $TEST_NAMESPACE"
kubectl create namespace "$TEST_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Create test OAM Application with full workflow orchestration
echo ""
echo "🚀 Creating test OAM Application with workflow orchestration..."

cat <<EOF | kubectl apply -f -
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: workflow-test-app
  namespace: $TEST_NAMESPACE
spec:
  components:
  - name: test-app-container
    type: app-container
    properties:
      name: workflow-test
      description: "Test application container for workflow orchestration"
      gitHubOrg: "shlapolosa"
  
  - name: test-microservice
    type: microservice-with-db
    properties:
      name: test-service
      language: python
      framework: fastapi
      database: postgres
      cache: redis
      appContainer: workflow-test
  
  # Workflow configuration with custom steps
  workflow:
    steps:
    - name: provision-infrastructure
      type: create-crossplane-claims
      timeout: 15m
    - name: wait-for-infrastructure
      type: wait-for-claims
      timeout: 10m
      dependsOn: ["provision-infrastructure"]
    - name: deploy-applications
      type: create-crossplane-claims
      timeout: 10m
      dependsOn: ["wait-for-infrastructure"]
    - name: validate-deployment
      type: wait-for-claims
      timeout: 5m
      dependsOn: ["deploy-applications"]
    
    # Failure handling
    onFailure:
      steps:
      - name: cleanup-resources
        type: cleanup-failed-claims
        timeout: 5m
  
  # Policies for execution order
  policies:
  - name: execution-order
    type: crossplane-execution-order
    properties:
      phases: ["infrastructure", "application"]
      phaseDelay: "30s"
      parallelWithinPhase: true
  
  - name: health-monitoring
    type: health
    properties:
      probeTimeout: 10
      probeInterval: 30
      unhealthyAction: "wait"
      failedAction: "cleanup"
      enableAlerting: false
      cleanupOnFailure: true
  
  # Traits for automatic workflow execution
  traits:
  - type: crossplane-workflow
    properties:
      enabled: true
      timeout: "30m"
      retries: 3
      cleanupOnFailure: true
      mode: "sequential"
      enableMonitoring: true
      enableNotifications: false
EOF

echo "✅ Test OAM Application created"

# Monitor the application
echo ""
echo "📊 Monitoring application status..."
echo "   Use Ctrl+C to stop monitoring"
echo ""

# Function to check application status
check_status() {
    local app_status
    app_status=$(kubectl get application workflow-test-app -n "$TEST_NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "unknown")
    echo "Application Status: $app_status"
    
    # Show workflow status if available
    if kubectl get application workflow-test-app -n "$TEST_NAMESPACE" -o jsonpath='{.status.workflow}' &>/dev/null; then
        local workflow_status
        workflow_status=$(kubectl get application workflow-test-app -n "$TEST_NAMESPACE" -o jsonpath='{.status.workflow.status}' 2>/dev/null || echo "unknown")
        echo "Workflow Status: $workflow_status"
    fi
    
    # Show any created Claims
    local claims
    claims=$(kubectl get applicationclaims,vclusterenvironmentclaims,appcontainerclaims -n "$TEST_NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$claims" -gt 0 ]; then
        echo "Created Claims: $claims"
        kubectl get applicationclaims,vclusterenvironmentclaims,appcontainerclaims -n "$TEST_NAMESPACE" --no-headers 2>/dev/null || true
    fi
    
    echo "---"
}

# Monitor for up to 5 minutes
TIMEOUT=300  # 5 minutes
ELAPSED=0
INTERVAL=15

while [ $ELAPSED -lt $TIMEOUT ]; do
    check_status
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "🔍 Final Status Check:"
check_status

# Show detailed application information
echo ""
echo "📋 Application Details:"
kubectl describe application workflow-test-app -n "$TEST_NAMESPACE" || true

echo ""
echo "🧪 Test completed!"
echo ""
echo "🧹 Cleanup Commands:"
echo "   # Delete test application:"
echo "   kubectl delete application workflow-test-app -n $TEST_NAMESPACE"
echo ""
echo "   # Delete test namespace (and all resources):"
echo "   kubectl delete namespace $TEST_NAMESPACE"
echo ""
echo "📊 Next Steps:"
echo "   1. Review the workflow execution in KubeVela"
echo "   2. Check if Crossplane Claims were created properly"
echo "   3. Validate the orchestration worked as expected"