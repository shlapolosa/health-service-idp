#!/bin/bash

# Test script for Slack VCluster creation
# Simulates the API call that would be made by the Slack API server

set -e

# Configuration
GITHUB_TOKEN="${PERSONAL_ACCESS_TOKEN}"
REPO_OWNER="shlapolosa"
REPO_NAME="health-service-idp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if [[ -z "$GITHUB_TOKEN" ]]; then
        log_error "PERSONAL_ACCESS_TOKEN environment variable not set"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl not found. Please install curl."
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found. Install jq for better JSON formatting."
    fi
    
    log_success "Prerequisites checked"
}

# Test Case 1: Basic VCluster with default capabilities
test_basic_vcluster() {
    log_info "🧪 Test Case 1: Basic VCluster with defaults"
    
    PAYLOAD='{
        "event_type": "slack_create_vcluster",
        "client_payload": {
            "vcluster_name": "test-basic",
            "namespace": "testing",
            "repository": "test-app",
            "user": "test.user",
            "slack_channel": "C1234567890",
            "slack_user_id": "U1234567890"
        }
    }'
    
    echo "📤 Sending payload:"
    echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "$PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1 | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [[ "$HTTP_CODE" == "204" ]]; then
        log_success "Basic VCluster test dispatched successfully"
    else
        log_error "Basic VCluster test failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Test Case 2: VCluster with custom capabilities
test_custom_capabilities() {
    log_info "🧪 Test Case 2: VCluster with custom capabilities"
    
    PAYLOAD='{
        "event_type": "slack_create_vcluster",
        "client_payload": {
            "vcluster_name": "test-custom",
            "namespace": "testing",
            "repository": "custom-app",
            "user": "test.user",
            "capabilities": {
                "observability": true,
                "security": true,
                "gitops": false,
                "monitoring": true,
                "logging": false,
                "networking": true,
                "autoscaling": true,
                "backup": true
            },
            "resources": {
                "cpu_limit": "4000m",
                "memory_limit": "8Gi",
                "storage_size": "20Gi",
                "node_count": 5
            },
            "slack_channel": "C1234567890",
            "slack_user_id": "U1234567890"
        }
    }'
    
    echo "📤 Sending payload:"
    echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "$PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1 | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [[ "$HTTP_CODE" == "204" ]]; then
        log_success "Custom capabilities test dispatched successfully"
    else
        log_error "Custom capabilities test failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Test Case 3: VCluster without repository
test_no_repository() {
    log_info "🧪 Test Case 3: VCluster without repository"
    
    PAYLOAD='{
        "event_type": "slack_create_vcluster",
        "client_payload": {
            "vcluster_name": "test-no-repo",
            "namespace": "testing",
            "user": "test.user",
            "capabilities": {
                "observability": false,
                "security": true,
                "gitops": true,
                "monitoring": false,
                "logging": true,
                "networking": false,
                "autoscaling": false,
                "backup": false
            },
            "slack_channel": "C1234567890"
        }
    }'
    
    echo "📤 Sending payload:"
    echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "$PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1 | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [[ "$HTTP_CODE" == "204" ]]; then
        log_success "No repository test dispatched successfully"
    else
        log_error "No repository test failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Test Case 4: Invalid parameters (should fail validation)
test_invalid_parameters() {
    log_info "🧪 Test Case 4: Invalid parameters (should fail validation)"
    
    PAYLOAD='{
        "event_type": "slack_create_vcluster",
        "client_payload": {
            "vcluster_name": "Invalid_Name_With_Underscores",
            "namespace": "INVALID-NAMESPACE-CAPS",
            "repository": "invalid repo name",
            "user": "test.user",
            "capabilities": {
                "observability": "invalid_boolean",
                "security": true
            }
        }
    }'
    
    echo "📤 Sending payload (should trigger validation errors):"
    echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "$PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1 | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [[ "$HTTP_CODE" == "204" ]]; then
        log_success "Invalid parameters test dispatched (validation will happen in workflow)"
    else
        log_error "Invalid parameters test failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Test Case 5: Production-like configuration
test_production_config() {
    log_info "🧪 Test Case 5: Production-like configuration"
    
    PAYLOAD='{
        "event_type": "slack_create_vcluster",
        "client_payload": {
            "vcluster_name": "prod-demo",
            "namespace": "production",
            "repository": "microservices-suite",
            "user": "devops.engineer",
            "capabilities": {
                "observability": true,
                "security": true,
                "gitops": true,
                "monitoring": true,
                "logging": true,
                "networking": true,
                "autoscaling": true,
                "backup": true
            },
            "resources": {
                "cpu_limit": "8000m",
                "memory_limit": "16Gi",
                "storage_size": "100Gi",
                "node_count": 10
            },
            "slack_channel": "C9876543210",
            "slack_user_id": "U9876543210"
        }
    }'
    
    echo "📤 Sending payload:"
    echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        -d "$PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1 | cut -d: -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [[ "$HTTP_CODE" == "204" ]]; then
        log_success "Production config test dispatched successfully"
    else
        log_error "Production config test failed with HTTP $HTTP_CODE"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Show GitHub Actions runs
show_github_actions() {
    log_info "📊 Recent GitHub Actions runs:"
    
    RUNS_RESPONSE=$(curl -s \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/runs?per_page=5")
    
    if command -v jq &> /dev/null; then
        echo "$RUNS_RESPONSE" | jq -r '.workflow_runs[] | select(.name == "Create VCluster from Slack") | "🔗 \(.html_url) | Status: \(.status) | Conclusion: \(.conclusion // "running")"'
    else
        echo "Install jq to see formatted GitHub Actions runs"
        echo "Or visit: https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    fi
}

# Main execution
main() {
    echo "🚀 Testing Slack VCluster Creation GitHub Action"
    echo "=============================================="
    
    check_prerequisites
    
    echo ""
    echo "💡 This script will trigger GitHub Actions workflows."
    echo "   You can monitor them at: https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    echo ""
    
    # Run test cases
    test_basic_vcluster
    sleep 2
    
    test_custom_capabilities
    sleep 2
    
    test_no_repository
    sleep 2
    
    test_invalid_parameters
    sleep 2
    
    test_production_config
    sleep 2
    
    echo ""
    show_github_actions
    
    echo ""
    log_success "🎉 All test cases dispatched successfully!"
    echo ""
    echo "📈 Next steps:"
    echo "  1. Monitor GitHub Actions: https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    echo "  2. Check Slack notifications (if configured)"
    echo "  3. Verify VCluster creation in your Kubernetes cluster"
    echo ""
    echo "⏱️  Expected workflow duration: 5-30 minutes depending on cluster provisioning"
}

# Handle command line arguments
case "${1:-run}" in
    "test1"|"basic")
        check_prerequisites
        test_basic_vcluster
        ;;
    "test2"|"custom")
        check_prerequisites
        test_custom_capabilities
        ;;
    "test3"|"no-repo")
        check_prerequisites
        test_no_repository
        ;;
    "test4"|"invalid")
        check_prerequisites
        test_invalid_parameters
        ;;
    "test5"|"production")
        check_prerequisites
        test_production_config
        ;;
    "status"|"runs")
        check_prerequisites
        show_github_actions
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  run          Run all test cases (default)"
        echo "  basic        Test basic VCluster creation"
        echo "  custom       Test custom capabilities"
        echo "  no-repo      Test without repository"
        echo "  invalid      Test invalid parameters"
        echo "  production   Test production configuration"
        echo "  status       Show recent GitHub Actions runs"
        echo "  help         Show this help"
        ;;
    "run"|*)
        main
        ;;
esac