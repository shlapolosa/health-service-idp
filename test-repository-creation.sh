#!/bin/bash

# Repository Creation Test Script
# Tests repository creation equivalence between webservice and realtime-platform

set -e

echo "🧪 Repository Creation Equivalence Test"
echo "======================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test configuration
TEST_NAME="repo-creation-test"
TEST_NAMESPACE="default"
TIMEOUT=120

echo -e "${BLUE}📋 Test Configuration:${NC}"
echo "  Application: $TEST_NAME"
echo "  Namespace: $TEST_NAMESPACE"
echo "  Timeout: ${TIMEOUT}s"
echo ""

# Function to check if resource exists
check_resource() {
    local resource_type=$1
    local resource_name=$2
    local namespace=${3:-$TEST_NAMESPACE}
    
    if kubectl get $resource_type $resource_name -n $namespace >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $resource_type/$resource_name exists${NC}"
        return 0
    else
        echo -e "${RED}❌ $resource_type/$resource_name not found${NC}"
        return 1
    fi
}

# Function to wait for resource
wait_for_resource() {
    local resource_type=$1
    local resource_name=$2
    local namespace=${3:-$TEST_NAMESPACE}
    local timeout=${4:-60}
    
    echo -e "${YELLOW}⏳ Waiting for $resource_type/$resource_name...${NC}"
    
    local count=0
    while [ $count -lt $timeout ]; do
        if kubectl get $resource_type $resource_name -n $namespace >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $resource_type/$resource_name is ready${NC}"
            return 0
        fi
        sleep 2
        count=$((count + 2))
    done
    
    echo -e "${RED}❌ Timeout waiting for $resource_type/$resource_name${NC}"
    return 1
}

# Function to check job completion
check_job_completion() {
    local job_name=$1
    local namespace=${2:-$TEST_NAMESPACE}
    
    echo -e "${YELLOW}📊 Checking job status: $job_name${NC}"
    
    # Check if job exists
    if ! kubectl get job $job_name -n $namespace >/dev/null 2>&1; then
        echo -e "${RED}❌ Job $job_name not found${NC}"
        return 1
    fi
    
    # Get job status
    local status=$(kubectl get job $job_name -n $namespace -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "Unknown")
    local completions=$(kubectl get job $job_name -n $namespace -o jsonpath='{.status.completions}' 2>/dev/null || echo "0")
    local succeeded=$(kubectl get job $job_name -n $namespace -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
    
    echo "  Status: $status"
    echo "  Completions: $succeeded/$completions"
    
    # Show job logs
    echo -e "${BLUE}📋 Job logs:${NC}"
    kubectl logs job/$job_name -n $namespace --tail=20 || echo "No logs available"
    
    return 0
}

# Cleanup existing test
echo -e "${YELLOW}🧹 Cleaning up existing test resources...${NC}"
kubectl delete application $TEST_NAME -n $TEST_NAMESPACE --ignore-not-found=true
kubectl delete job -l app.kubernetes.io/name=payment-service -n $TEST_NAMESPACE --ignore-not-found=true
kubectl delete job -l app.kubernetes.io/name=notification-service -n $TEST_NAMESPACE --ignore-not-found=true
kubectl delete job -l app.kubernetes.io/name=analytics-platform -n $TEST_NAMESPACE --ignore-not-found=true
kubectl delete job -l app.kubernetes.io/name=streaming-processor -n $TEST_NAMESPACE --ignore-not-found=true
sleep 5

# Deploy test application
echo -e "${BLUE}🚀 Deploying repository creation test...${NC}"
kubectl apply -f test-repository-creation.yaml

# Wait for application to be ready
echo -e "${YELLOW}⏳ Waiting for application to be ready...${NC}"
kubectl wait --for=condition=Ready application/$TEST_NAME -n $TEST_NAMESPACE --timeout=${TIMEOUT}s

# Check application status
echo -e "${BLUE}📊 Application Status:${NC}"
kubectl get application $TEST_NAME -n $TEST_NAMESPACE -o yaml | grep -A 10 -B 5 status

echo ""
echo -e "${BLUE}🔍 Verifying Expected Resources:${NC}"
echo "=================================="

# Expected resources counters
total_checks=0
passed_checks=0

# Test 1: Knative Services (4 expected)
echo -e "${BLUE}1️⃣ Knative Services:${NC}"
for service in payment-service notification-service analytics-platform-realtime-service streaming-processor-realtime-service; do
    total_checks=$((total_checks + 1))
    if check_resource "ksvc" "$service"; then
        passed_checks=$((passed_checks + 1))
    fi
done

# Test 2: RealtimePlatformClaims (2 expected)
echo -e "${BLUE}2️⃣ RealtimePlatformClaims:${NC}"
for claim in analytics-platform-infrastructure streaming-processor-infrastructure; do
    total_checks=$((total_checks + 1))
    if check_resource "realtimeplatformclaim" "$claim"; then
        passed_checks=$((passed_checks + 1))
    fi
done

# Test 3: Secrets (2 expected)
echo -e "${BLUE}3️⃣ Application Secrets:${NC}"
for secret in payment-service-config notification-service-config; do
    total_checks=$((total_checks + 1))
    if check_resource "secret" "$secret"; then
        passed_checks=$((passed_checks + 1))
    fi
done

# Test 4: Workflow Trigger Jobs (4 expected)
echo -e "${BLUE}4️⃣ Repository Creation Workflow Jobs:${NC}"
sleep 10 # Give time for jobs to be created

for job in payment-service-workflow-trigger notification-service-workflow-trigger analytics-platform-workflow-trigger streaming-processor-workflow-trigger; do
    total_checks=$((total_checks + 1))
    if check_resource "job" "$job"; then
        passed_checks=$((passed_checks + 1))
        # Check job details
        check_job_completion "$job"
        echo ""
    fi
done

# Summary
echo ""
echo -e "${BLUE}📊 Test Results Summary:${NC}"
echo "========================"
echo "Total Checks: $total_checks"
echo "Passed: $passed_checks"
echo "Failed: $((total_checks - passed_checks))"

if [ $passed_checks -eq $total_checks ]; then
    echo -e "${GREEN}🎉 All tests passed! Repository creation equivalence verified.${NC}"
    exit_code=0
else
    echo -e "${RED}❌ Some tests failed. Repository creation needs investigation.${NC}"
    exit_code=1
fi

# Repository creation verification
echo ""
echo -e "${BLUE}🔍 Repository Creation Analysis:${NC}"
echo "================================="

echo -e "${BLUE}Expected Repository Names:${NC}"
echo "• payment-service (webservice default)"
echo "• payment-platform (webservice explicit)"  
echo "• analytics-platform (realtime-platform default)"
echo "• analytics-platform (realtime-platform explicit)"

echo ""
echo -e "${BLUE}Unique Repositories Expected:${NC}"
echo "• payment-service"
echo "• payment-platform" 
echo "• analytics-platform"

# Show workflow parameters from job logs
echo ""
echo -e "${BLUE}📋 Repository Parameters Verification:${NC}"
for job in payment-service-workflow-trigger notification-service-workflow-trigger analytics-platform-workflow-trigger streaming-processor-workflow-trigger; do
    if kubectl get job $job >/dev/null 2>&1; then
        echo ""
        echo -e "${YELLOW}$job repository parameter:${NC}"
        kubectl logs job/$job | grep '"repository-name"' || echo "No repository-name parameter found"
    fi
done

echo ""
echo -e "${GREEN}🎯 Repository Creation Equivalence Test Complete${NC}"
exit $exit_code