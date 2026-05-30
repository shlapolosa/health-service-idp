#!/bin/bash

# Test Resources Cleanup Script
# Deletes all test-related claims, applications, and resources in the correct order

set -e

echo "==========================================="
echo "   Test Resources Cleanup Script"
echo "==========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Function to delete resources safely
delete_resources() {
    local resource_type=$1
    local namespace=$2
    local pattern=$3
    
    if [ -z "$pattern" ]; then
        # Delete all resources of this type
        if [ "$namespace" = "ALL" ]; then
            kubectl delete $resource_type --all -A 2>/dev/null || true
        else
            kubectl delete $resource_type --all -n $namespace 2>/dev/null || true
        fi
    else
        # Delete resources matching pattern
        if [ "$namespace" = "ALL" ]; then
            kubectl get $resource_type -A -o name | grep "$pattern" | xargs -I {} kubectl delete {} 2>/dev/null || true
        else
            kubectl get $resource_type -n $namespace -o name | grep "$pattern" | xargs -I {} kubectl delete {} -n $namespace 2>/dev/null || true
        fi
    fi
}

# Main cleanup function
cleanup_test_resources() {
    echo "Starting cleanup of test resources..."
    echo ""
    
    # Step 1: Delete OAM Applications from vClusters
    echo "Step 1: Deleting OAM Applications from vClusters..."
    for vcluster in $(kubectl get vcluster -A -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | grep -E 'test-svc|test-' || true); do
        if [ -n "$vcluster" ]; then
            echo "  Cleaning vCluster: $vcluster"
            vcluster connect $vcluster --namespace $vcluster -- kubectl delete application --all -A 2>/dev/null || true
        fi
    done
    print_status "OAM Applications deleted from vClusters"
    echo ""
    
    # Step 2: Delete Argo Workflows
    echo "Step 2: Deleting Argo Workflows..."
    delete_resources "workflow" "argo" "test-"
    print_status "Argo Workflows deleted"
    echo ""
    
    # Step 3: Delete ArgoCD Applications
    echo "Step 3: Deleting ArgoCD Applications..."
    delete_resources "application" "argocd" "test-"
    print_status "ArgoCD Applications deleted"
    echo ""
    
    # Step 4: Delete ApplicationClaims (OAM/Crossplane)
    echo "Step 4: Deleting ApplicationClaims..."
    kubectl get applicationclaim -A -o name | grep -E 'test-svc|test-' | xargs -I {} kubectl delete {} 2>/dev/null || true
    print_status "ApplicationClaims deleted"
    echo ""
    
    # Step 5: Delete VClusterEnvironmentClaims
    echo "Step 5: Deleting VClusterEnvironmentClaims..."
    kubectl get vclusterenvironmentclaim -A -o name | grep -E 'test-svc|test-' | xargs -I {} kubectl delete {} 2>/dev/null || true
    print_status "VClusterEnvironmentClaims deleted"
    echo ""
    
    # Step 6: Delete XAppContainerClaims (Crossplane Composites)
    echo "Step 6: Deleting XAppContainerClaims..."
    kubectl get xappcontainerclaim -A -o name | grep -E 'test-svc|test-' | xargs -I {} kubectl delete {} 2>/dev/null || true
    print_status "XAppContainerClaims deleted"
    echo ""
    
    # Step 7: Delete all other Crossplane Claims
    echo "Step 7: Deleting other Crossplane Claims..."
    for xrd in $(kubectl get xrd -o name | grep claim); do
        resource=$(echo $xrd | sed 's/compositeresourcedefinition.apiextensions.crossplane.io\///' | sed 's/x//' | sed 's/s.platform.*//')
        echo "  Checking $resource claims..."
        kubectl get $resource -A 2>/dev/null | grep -E 'test-svc|test-' | awk '{print "kubectl delete " $1 " " $2 " -n " $3}' | bash 2>/dev/null || true
    done
    print_status "All Crossplane Claims deleted"
    echo ""
    
    # Step 8: Delete Crossplane Managed Resources
    echo "Step 8: Deleting Crossplane Managed Resources..."
    kubectl get managed -A | grep -E 'test-svc|test-' | awk '{print "kubectl delete " $1 " " $2}' | bash 2>/dev/null || true
    print_status "Crossplane Managed Resources deleted"
    echo ""
    
    # Step 9: Delete Jobs
    echo "Step 9: Deleting Jobs..."
    kubectl get jobs -A | grep -E 'test-svc|test-' | awk '{print "kubectl delete job " $2 " -n " $1}' | bash 2>/dev/null || true
    print_status "Jobs deleted"
    echo ""
    
    # Step 10: Delete vClusters
    echo "Step 10: Deleting vClusters..."
    for vcluster in $(kubectl get vcluster -A -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | grep -E 'test-svc|test-' || true); do
        if [ -n "$vcluster" ]; then
            ns=$(kubectl get vcluster -A | grep $vcluster | awk '{print $1}')
            echo "  Deleting vCluster: $vcluster in namespace: $ns"
            vcluster delete $vcluster --namespace $ns 2>/dev/null || true
        fi
    done
    print_status "vClusters deleted"
    echo ""
    
    # Step 11: Force delete StatefulSets and Pods in test namespaces
    echo "Step 11: Force deleting StatefulSets and Pods..."
    for ns in $(kubectl get ns -o name | grep -E 'test-svc|test-' | sed 's/namespace\///'); do
        echo "  Cleaning namespace: $ns"
        kubectl delete statefulset --all -n $ns --force --grace-period=0 2>/dev/null || true
        kubectl delete pod --all -n $ns --force --grace-period=0 2>/dev/null || true
    done
    print_status "StatefulSets and Pods deleted"
    echo ""
    
    # Step 12: Delete test namespaces
    echo "Step 12: Deleting test namespaces..."
    for ns in $(kubectl get ns -o name | grep -E 'test-svc|test-' | sed 's/namespace\///'); do
        echo "  Deleting namespace: $ns"
        kubectl delete namespace $ns --force --grace-period=0 2>/dev/null || true
    done
    print_status "Test namespaces deleted"
    echo ""
    
    # Step 13: Clean up test pods in default namespace
    echo "Step 13: Cleaning test pods in default namespace..."
    kubectl get pods -n default | grep -E 'test-svc|test-' | awk '{print $1}' | xargs -I {} kubectl delete pod {} -n default --force --grace-period=0 2>/dev/null || true
    print_status "Test pods in default namespace deleted"
    echo ""
    
    # Step 14: Clean up any GitHub repositories (if using GitHub provider)
    echo "Step 14: Checking for test GitHub repositories..."
    kubectl get repository.repo.github.upbound.io -A 2>/dev/null | grep -E 'test-svc|test-' | awk '{print "kubectl delete repository.repo.github.upbound.io " $2 " -n " $1}' | bash 2>/dev/null || true
    print_status "GitHub repositories cleaned"
    echo ""
}

# Verification function
verify_cleanup() {
    echo "==========================================="
    echo "   Verification"
    echo "==========================================="
    echo ""
    
    local issues_found=0
    
    # Check for remaining ApplicationClaims
    echo "Checking ApplicationClaims..."
    count=$(kubectl get applicationclaim -A 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining ApplicationClaims"
        kubectl get applicationclaim -A | grep -E 'test-svc|test-'
        issues_found=1
    else
        print_status "No test ApplicationClaims found"
    fi
    
    # Check for remaining VClusterEnvironmentClaims
    echo "Checking VClusterEnvironmentClaims..."
    count=$(kubectl get vclusterenvironmentclaim -A 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining VClusterEnvironmentClaims"
        kubectl get vclusterenvironmentclaim -A | grep -E 'test-svc|test-'
        issues_found=1
    else
        print_status "No test VClusterEnvironmentClaims found"
    fi
    
    # Check for remaining ArgoCD Applications
    echo "Checking ArgoCD Applications..."
    count=$(kubectl get application -n argocd 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining ArgoCD Applications"
        kubectl get application -n argocd | grep -E 'test-svc|test-'
        issues_found=1
    else
        print_status "No test ArgoCD Applications found"
    fi
    
    # Check for remaining test namespaces
    echo "Checking test namespaces..."
    count=$(kubectl get ns 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining test namespaces"
        kubectl get ns | grep -E 'test-svc|test-'
        issues_found=1
    else
        print_status "No test namespaces found"
    fi
    
    # Check for remaining test pods in default namespace
    echo "Checking test pods in default namespace..."
    count=$(kubectl get pods -n default 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining test pods in default namespace"
        kubectl get pods -n default | grep -E 'test-svc|test-'
        issues_found=1
    else
        print_status "No test pods in default namespace"
    fi
    
    # Check for remaining Crossplane managed resources
    echo "Checking Crossplane managed resources..."
    count=$(kubectl get managed -A 2>/dev/null | grep -cE 'test-svc|test-' || echo "0")
    if [ "$count" -gt 0 ]; then
        print_warning "Found $count remaining Crossplane managed resources"
        kubectl get managed -A | grep -E 'test-svc|test-' | head -5
        issues_found=1
    else
        print_status "No test Crossplane managed resources found"
    fi
    
    echo ""
    if [ $issues_found -eq 0 ]; then
        print_status "✨ All test resources successfully cleaned!"
    else
        print_warning "⚠️  Some test resources may still exist. Run the script again or manually clean remaining resources."
    fi
}

# Main execution
main() {
    echo "This script will delete all test-related resources including:"
    echo "  - OAM Applications"
    echo "  - Argo Workflows"
    echo "  - ArgoCD Applications"
    echo "  - ApplicationClaims"
    echo "  - VClusterEnvironmentClaims"
    echo "  - XAppContainerClaims"
    echo "  - All other Crossplane Claims"
    echo "  - Crossplane Managed Resources"
    echo "  - Jobs"
    echo "  - vClusters"
    echo "  - Test namespaces"
    echo "  - Test pods"
    echo ""
    
    read -p "Do you want to proceed with cleanup? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled."
        exit 1
    fi
    
    echo ""
    cleanup_test_resources
    
    echo ""
    verify_cleanup
    
    echo ""
    echo "==========================================="
    echo "   Cleanup Complete"
    echo "==========================================="
    echo ""
    echo "You can run this script again if any resources were missed."
    echo "To force a more aggressive cleanup, you can also run:"
    echo "  kubectl delete ns --force --grace-period=0 \$(kubectl get ns | grep test- | awk '{print \$1}')"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if vcluster CLI is available
if ! command -v vcluster &> /dev/null; then
    print_warning "vcluster CLI is not installed. Some vCluster operations may fail."
fi

# Run main function
main