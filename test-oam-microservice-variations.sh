#!/bin/bash

# Comprehensive OAM Microservice Test Suite
# Tests various microservice configurations including secret management and realtime integration

set -e

# Configuration
NAMESPACE="test-microservices"
VCLUSTER_CONTEXT="platform_user@socrateshlapolosa-karpenter-demo.us-west-2.eksctl.io"
TEST_PREFIX="test-ms"
CLEANUP_ON_EXIT=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Cleanup function
cleanup() {
    if [ "$CLEANUP_ON_EXIT" = true ]; then
        log_info "Cleaning up test resources..."
        kubectl delete namespace $NAMESPACE --ignore-not-found=true --context=$VCLUSTER_CONTEXT || true
        log_info "Cleanup completed"
    fi
}

# Set cleanup trap
trap cleanup EXIT

# Test configuration arrays
declare -A test_configs=(
    ["basic-python"]="python fastapi none none false"
    ["python-with-db"]="python fastapi postgresql none false"
    ["python-with-cache"]="python fastapi none redis false"
    ["python-full-stack"]="python fastapi postgresql redis false"
    ["realtime-basic"]="python fastapi none none true realtime-platform-1"
    ["realtime-full"]="python fastapi postgresql redis true realtime-platform-2"
    ["nodejs-basic"]="nodejs express none none false"
    ["nodejs-realtime"]="nodejs express mongodb none true realtime-platform-3"
)

# Function to create test namespace
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Ensure we're in the correct context
    kubectl config use-context $VCLUSTER_CONTEXT
    
    # Create test namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Create mock realtime platform secrets for testing
    create_mock_realtime_secrets
    
    log_success "Test environment ready"
}

# Function to create mock realtime platform secrets
create_mock_realtime_secrets() {
    log_info "Creating mock realtime platform secrets..."
    
    for platform in realtime-platform-1 realtime-platform-2 realtime-platform-3; do
        # Kafka secret
        kubectl create secret generic "${platform}-kafka-secret" \
            --from-literal=KAFKA_BROKERS="kafka.${platform}.svc.cluster.local:9092" \
            --from-literal=KAFKA_USERNAME="test-user" \
            --from-literal=KAFKA_PASSWORD="test-password" \
            -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
        
        # MQTT secret
        kubectl create secret generic "${platform}-mqtt-secret" \
            --from-literal=MQTT_HOST="mqtt.${platform}.svc.cluster.local" \
            --from-literal=MQTT_PORT="1883" \
            --from-literal=MQTT_USERNAME="test-user" \
            --from-literal=MQTT_PASSWORD="test-password" \
            -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
        
        # Database secret
        kubectl create secret generic "${platform}-db-secret" \
            --from-literal=DB_HOST="postgres.${platform}.svc.cluster.local" \
            --from-literal=DB_PORT="5432" \
            --from-literal=DB_NAME="realtime_db" \
            --from-literal=DB_USERNAME="realtime_user" \
            --from-literal=DB_PASSWORD="realtime_password" \
            -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
        
        # Metabase secret
        kubectl create secret generic "${platform}-metabase-secret" \
            --from-literal=METABASE_URL="http://metabase.${platform}.svc.cluster.local:3000" \
            --from-literal=METABASE_USERNAME="admin" \
            --from-literal=METABASE_PASSWORD="admin123" \
            -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
        
        # Lenses secret
        kubectl create secret generic "${platform}-lenses-secret" \
            --from-literal=LENSES_URL="http://lenses.${platform}.svc.cluster.local:3030" \
            --from-literal=LENSES_USERNAME="admin" \
            --from-literal=LENSES_PASSWORD="admin123" \
            -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    done
    
    log_success "Mock realtime platform secrets created"
}

# Function to create OAM Application for testing
create_test_application() {
    local test_name=$1
    local language=$2
    local framework=$3
    local database=$4
    local cache=$5
    local realtime=$6
    local realtime_platform=$7
    
    local app_name="${TEST_PREFIX}-${test_name}"
    
    log_info "Creating test application: $app_name"
    
    # Build the OAM Application YAML
    cat > "/tmp/${app_name}-app.yaml" <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: $app_name
  namespace: $NAMESPACE
spec:
  components:
  - name: $app_name
    type: webservice
    properties:
      image: nginx:alpine
      port: 8080
      language: $language
      framework: $framework$([ "$database" != "none" ] && echo "
      database: $database")$([ "$cache" != "none" ] && echo "
      cache: $cache")$([ "$realtime" = "true" ] && echo "
      realtime: $realtime_platform")
    traits:
    - type: knative-service
      properties:
        minScale: 0
        maxScale: 5
        containerConcurrency: 10
EOF
    
    # Apply the application
    kubectl apply -f "/tmp/${app_name}-app.yaml" -n $NAMESPACE
    
    log_success "Application $app_name created"
    return 0
}

# Function to wait for application readiness
wait_for_application() {
    local app_name=$1
    local timeout=300
    local interval=10
    local elapsed=0
    
    log_info "Waiting for application $app_name to be ready..."
    
    while [ $elapsed -lt $timeout ]; do
        local status=$(kubectl get application $app_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        
        if [ "$status" = "running" ]; then
            log_success "Application $app_name is ready"
            return 0
        elif [ "$status" = "unhealthy" ]; then
            log_error "Application $app_name is unhealthy"
            kubectl describe application $app_name -n $NAMESPACE
            return 1
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        log_info "Still waiting for $app_name... (${elapsed}s/${timeout}s)"
    done
    
    log_error "Timeout waiting for application $app_name"
    return 1
}

# Function to test artifact creation
test_artifact_creation() {
    local app_name=$1
    local expected_realtime=$2
    
    log_info "Testing artifact creation for $app_name..."
    
    # Test Knative Service creation
    local ksvc_count=$(kubectl get ksvc -n $NAMESPACE -l app.oam.dev/name=$app_name --no-headers 2>/dev/null | wc -l)
    if [ "$ksvc_count" -eq 1 ]; then
        log_success "✓ Knative Service created"
    else
        log_error "✗ Expected 1 Knative Service, found $ksvc_count"
        return 1
    fi
    
    # Test OAM Application
    local app_count=$(kubectl get application $app_name -n $NAMESPACE --no-headers 2>/dev/null | wc -l)
    if [ "$app_count" -eq 1 ]; then
        log_success "✓ OAM Application exists"
    else
        log_error "✗ OAM Application not found"
        return 1
    fi
    
    # Test secret injection if realtime is enabled
    if [ "$expected_realtime" = "true" ]; then
        local deployment=$(kubectl get deployment -n $NAMESPACE -l app.oam.dev/name=$app_name -o name 2>/dev/null | head -1)
        if [ -n "$deployment" ]; then
            local secret_refs=$(kubectl get $deployment -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].envFrom[*].secretRef.name}' 2>/dev/null | wc -w)
            if [ "$secret_refs" -gt 0 ]; then
                log_success "✓ Secret references found in deployment"
            else
                log_warning "⚠ No secret references found (may be expected for some configurations)"
            fi
        fi
    fi
    
    return 0
}

# Function to test endpoint discovery
test_endpoint_discovery() {
    local app_name=$1
    
    log_info "Testing endpoint discovery for $app_name..."
    
    # Get Knative Service URL
    local ksvc_url=$(kubectl get ksvc $app_name -n $NAMESPACE -o jsonpath='{.status.url}' 2>/dev/null || echo "")
    if [ -n "$ksvc_url" ]; then
        log_success "✓ Knative Service URL: $ksvc_url"
    else
        log_warning "⚠ Knative Service URL not available yet"
    fi
    
    # Check for Istio Gateway (external access)
    local gateway_count=$(kubectl get gateway -n $NAMESPACE -l app.oam.dev/name=$app_name --no-headers 2>/dev/null | wc -l)
    if [ "$gateway_count" -gt 0 ]; then
        log_success "✓ Istio Gateway found for external access"
    else
        log_info "ℹ No Istio Gateway (internal access only)"
    fi
    
    return 0
}

# Function to run comprehensive test for a single configuration
run_single_test() {
    local test_name=$1
    local config=$2
    
    log_info "===================="
    log_info "Testing: $test_name"
    log_info "Config: $config"
    log_info "===================="
    
    # Parse configuration
    read -r language framework database cache realtime realtime_platform <<< "$config"
    
    # Create application
    if ! create_test_application "$test_name" "$language" "$framework" "$database" "$cache" "$realtime" "$realtime_platform"; then
        log_error "Failed to create application for $test_name"
        return 1
    fi
    
    # Wait for readiness
    local app_name="${TEST_PREFIX}-${test_name}"
    if ! wait_for_application "$app_name"; then
        log_error "Application $app_name failed to become ready"
        return 1
    fi
    
    # Test artifact creation
    if ! test_artifact_creation "$app_name" "$realtime"; then
        log_error "Artifact creation test failed for $test_name"
        return 1
    fi
    
    # Test endpoint discovery
    if ! test_endpoint_discovery "$app_name"; then
        log_error "Endpoint discovery test failed for $test_name"
        return 1
    fi
    
    log_success "Test completed successfully: $test_name"
    return 0
}

# Function to generate test report
generate_test_report() {
    log_info "===================="
    log_info "GENERATING TEST REPORT"
    log_info "===================="
    
    echo ""
    echo "Test Summary:"
    echo "============="
    
    local total_tests=${#test_configs[@]}
    local passed_tests=0
    local failed_tests=0
    
    for test_name in "${!test_configs[@]}"; do
        local config="${test_configs[$test_name]}"
        local app_name="${TEST_PREFIX}-${test_name}"
        
        # Check if application exists and is healthy
        local status=$(kubectl get application $app_name -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
        
        if [ "$status" = "running" ]; then
            echo "✓ $test_name: PASSED"
            ((passed_tests++))
        else
            echo "✗ $test_name: FAILED ($status)"
            ((failed_tests++))
        fi
    done
    
    echo ""
    echo "Results: $passed_tests passed, $failed_tests failed, $total_tests total"
    echo ""
    
    # Detailed artifact inventory
    echo "Artifact Inventory:"
    echo "=================="
    
    echo ""
    echo "Applications:"
    kubectl get applications -n $NAMESPACE -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,AGE:.metadata.creationTimestamp
    
    echo ""
    echo "Knative Services:"
    kubectl get ksvc -n $NAMESPACE -o custom-columns=NAME:.metadata.name,URL:.status.url,READY:.status.conditions[0].status,AGE:.metadata.creationTimestamp
    
    echo ""
    echo "Secrets:"
    kubectl get secrets -n $NAMESPACE -o custom-columns=NAME:.metadata.name,TYPE:.type,AGE:.metadata.creationTimestamp
    
    echo ""
    echo "Endpoints Summary:"
    echo "=================="
    
    for test_name in "${!test_configs[@]}"; do
        local app_name="${TEST_PREFIX}-${test_name}"
        local ksvc_url=$(kubectl get ksvc $app_name -n $NAMESPACE -o jsonpath='{.status.url}' 2>/dev/null || echo "N/A")
        echo "$app_name: $ksvc_url"
    done
}

# Main execution function
main() {
    log_info "Starting Comprehensive OAM Microservice Test Suite"
    log_info "Namespace: $NAMESPACE"
    log_info "Context: $VCLUSTER_CONTEXT"
    
    # Setup test environment
    setup_test_environment
    
    # Run tests for each configuration
    local test_results=()
    
    for test_name in "${!test_configs[@]}"; do
        local config="${test_configs[$test_name]}"
        
        if run_single_test "$test_name" "$config"; then
            test_results["$test_name"]="PASSED"
        else
            test_results["$test_name"]="FAILED"
            log_warning "Continuing with next test despite failure..."
        fi
        
        # Small delay between tests
        sleep 5
    done
    
    # Generate final report
    generate_test_report
    
    log_success "Test suite completed!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --context)
            VCLUSTER_CONTEXT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-cleanup      Keep test resources after completion"
            echo "  --namespace NS    Use specific namespace (default: test-microservices)"
            echo "  --context CTX     Use specific kubectl context (default: architecture-visualization)"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main