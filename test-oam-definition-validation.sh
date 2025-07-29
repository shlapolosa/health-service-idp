#!/bin/bash

# OAM ComponentDefinition Validation Test
# Validates the webservice ComponentDefinition with realtime parameter support

set -e

# Configuration
VCLUSTER_CONTEXT="platform_user@socrateshlapolosa-karpenter-demo.us-west-2.eksctl.io"
NAMESPACE="test-oam-validation"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test OAM ComponentDefinition validation
test_component_definition() {
    log_info "Testing OAM ComponentDefinition validation..."
    
    # Apply the ComponentDefinition
    if kubectl apply -f crossplane/oam/consolidated-component-definitions.yaml --context=$VCLUSTER_CONTEXT; then
        log_success "✓ ComponentDefinition applied successfully"
    else
        log_error "✗ Failed to apply ComponentDefinition"
        return 1
    fi
    
    # Verify webservice ComponentDefinition exists
    if kubectl get componentdefinition webservice --context=$VCLUSTER_CONTEXT >/dev/null 2>&1; then
        log_success "✓ webservice ComponentDefinition exists"
    else
        log_error "✗ webservice ComponentDefinition not found"
        return 1
    fi
    
    # Check the schema includes realtime parameter
    local schema=$(kubectl get componentdefinition webservice --context=$VCLUSTER_CONTEXT -o jsonpath='{.spec.schematic.cue}')
    if echo "$schema" | grep -q "realtime"; then
        log_success "✓ realtime parameter found in schema"
    else
        log_error "✗ realtime parameter not found in schema"
        return 1
    fi
    
    return 0
}

# Test basic webservice creation (no realtime)
test_basic_webservice() {
    log_info "Testing basic webservice creation (no realtime)..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml --context=$VCLUSTER_CONTEXT | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    # Create test application
    cat > /tmp/test-basic-app.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: test-basic-webservice
  namespace: $NAMESPACE
spec:
  components:
  - name: test-basic-webservice
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: python
      framework: fastapi
    traits:
    - type: knative-service
      properties:
        minScale: 0
        maxScale: 2
EOF
    
    if kubectl apply -f /tmp/test-basic-app.yaml --context=$VCLUSTER_CONTEXT; then
        log_success "✓ Basic webservice application created"
    else
        log_error "✗ Failed to create basic webservice application"
        return 1
    fi
    
    # Wait for application to be processed
    sleep 10
    
    # Check if Knative service was created
    if kubectl get ksvc test-basic-webservice -n $NAMESPACE --context=$VCLUSTER_CONTEXT >/dev/null 2>&1; then
        log_success "✓ Knative service created for basic webservice"
    else
        log_error "✗ Knative service not created for basic webservice"
        kubectl describe application test-basic-webservice -n $NAMESPACE --context=$VCLUSTER_CONTEXT
        return 1
    fi
    
    return 0
}

# Test realtime webservice creation
test_realtime_webservice() {
    log_info "Testing realtime webservice creation..."
    
    # Create mock realtime platform secrets first
    create_mock_secrets
    
    # Create test application with realtime parameter
    cat > /tmp/test-realtime-app.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: test-realtime-webservice
  namespace: $NAMESPACE
spec:
  components:
  - name: test-realtime-webservice
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: python
      framework: fastapi
      realtime: test-platform
    traits:
    - type: knative-service
      properties:
        minScale: 0
        maxScale: 2
EOF
    
    if kubectl apply -f /tmp/test-realtime-app.yaml --context=$VCLUSTER_CONTEXT; then
        log_success "✓ Realtime webservice application created"
    else
        log_error "✗ Failed to create realtime webservice application"
        return 1
    fi
    
    # Wait for application to be processed
    sleep 15
    
    # Check if Knative service was created
    if kubectl get ksvc test-realtime-webservice -n $NAMESPACE --context=$VCLUSTER_CONTEXT >/dev/null 2>&1; then
        log_success "✓ Knative service created for realtime webservice"
    else
        log_error "✗ Knative service not created for realtime webservice"
        kubectl describe application test-realtime-webservice -n $NAMESPACE --context=$VCLUSTER_CONTEXT
        return 1
    fi
    
    # Check if secrets are properly injected
    local deployment=$(kubectl get deployment -n $NAMESPACE -l app.oam.dev/name=test-realtime-webservice --context=$VCLUSTER_CONTEXT -o name 2>/dev/null | head -1)
    if [ -n "$deployment" ]; then
        local env_from=$(kubectl get $deployment -n $NAMESPACE --context=$VCLUSTER_CONTEXT -o jsonpath='{.spec.template.spec.containers[0].envFrom}' 2>/dev/null)
        if [ -n "$env_from" ] && [ "$env_from" != "null" ]; then
            log_success "✓ Environment secrets injected into realtime webservice"
            echo "Environment from: $env_from"
        else
            log_error "✗ Environment secrets not injected into realtime webservice"
            return 1
        fi
    else
        log_error "✗ Deployment not found for realtime webservice"
        return 1
    fi
    
    return 0
}

# Create mock secrets for testing
create_mock_secrets() {
    log_info "Creating mock realtime platform secrets..."
    
    # Create secrets for test-platform
    kubectl create secret generic "test-platform-kafka-secret" \
        --from-literal=KAFKA_BROKERS="kafka.test-platform.svc.cluster.local:9092" \
        --from-literal=KAFKA_USERNAME="test-user" \
        --from-literal=KAFKA_PASSWORD="test-password" \
        -n $NAMESPACE --context=$VCLUSTER_CONTEXT --dry-run=client -o yaml | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    kubectl create secret generic "test-platform-mqtt-secret" \
        --from-literal=MQTT_HOST="mqtt.test-platform.svc.cluster.local" \
        --from-literal=MQTT_PORT="1883" \
        --from-literal=MQTT_USERNAME="test-user" \
        --from-literal=MQTT_PASSWORD="test-password" \
        -n $NAMESPACE --context=$VCLUSTER_CONTEXT --dry-run=client -o yaml | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    kubectl create secret generic "test-platform-db-secret" \
        --from-literal=DB_HOST="postgres.test-platform.svc.cluster.local" \
        --from-literal=DB_PORT="5432" \
        --from-literal=DB_NAME="realtime_db" \
        --from-literal=DB_USERNAME="realtime_user" \
        --from-literal=DB_PASSWORD="realtime_password" \
        -n $NAMESPACE --context=$VCLUSTER_CONTEXT --dry-run=client -o yaml | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    kubectl create secret generic "test-platform-metabase-secret" \
        --from-literal=METABASE_URL="http://metabase.test-platform.svc.cluster.local:3000" \
        --from-literal=METABASE_USERNAME="admin" \
        --from-literal=METABASE_PASSWORD="admin123" \
        -n $NAMESPACE --context=$VCLUSTER_CONTEXT --dry-run=client -o yaml | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    kubectl create secret generic "test-platform-lenses-secret" \
        --from-literal=LENSES_URL="http://lenses.test-platform.svc.cluster.local:3030" \
        --from-literal=LENSES_USERNAME="admin" \
        --from-literal=LENSES_PASSWORD="admin123" \
        -n $NAMESPACE --context=$VCLUSTER_CONTEXT --dry-run=client -o yaml | kubectl apply -f - --context=$VCLUSTER_CONTEXT
    
    log_success "Mock secrets created"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test resources..."
    kubectl delete namespace $NAMESPACE --ignore-not-found=true --context=$VCLUSTER_CONTEXT || true
    rm -f /tmp/test-basic-app.yaml /tmp/test-realtime-app.yaml
}

# Main function
main() {
    log_info "Starting OAM ComponentDefinition Validation Test"
    
    # Ensure we're in the correct context
    kubectl config use-context $VCLUSTER_CONTEXT
    
    # Test ComponentDefinition
    if ! test_component_definition; then
        log_error "ComponentDefinition test failed"
        exit 1
    fi
    
    # Test basic webservice
    if ! test_basic_webservice; then
        log_error "Basic webservice test failed"
        cleanup
        exit 1
    fi
    
    # Test realtime webservice
    if ! test_realtime_webservice; then
        log_error "Realtime webservice test failed"
        cleanup
        exit 1
    fi
    
    log_success "All tests passed!"
    
    # Show final state
    log_info "Final resource state:"
    echo ""
    echo "Applications:"
    kubectl get applications -n $NAMESPACE --context=$VCLUSTER_CONTEXT
    echo ""
    echo "Knative Services:"
    kubectl get ksvc -n $NAMESPACE --context=$VCLUSTER_CONTEXT
    echo ""
    echo "Secrets:"
    kubectl get secrets -n $NAMESPACE --context=$VCLUSTER_CONTEXT | grep -E "(test-platform|default)"
    
    # Cleanup
    cleanup
    
    log_success "OAM ComponentDefinition validation completed successfully!"
}

# Set trap for cleanup
trap cleanup EXIT

# Run main function
main