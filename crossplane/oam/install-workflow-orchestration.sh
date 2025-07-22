#!/bin/bash
# Install Custom OAM → Crossplane Workflow Orchestration
# This script installs the custom WorkflowStepDefinitions, PolicyDefinitions, and TraitDefinitions

set -e

echo "🚀 Installing OAM → Crossplane Workflow Orchestration Components"
echo "================================================================"

# Check if we can access the cluster
if ! kubectl cluster-info &>/dev/null; then
    echo "❌ Unable to access Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

# Check if KubeVela is installed
if ! kubectl get namespace vela-system &>/dev/null; then
    echo "❌ KubeVela (vela-system namespace) not found. Please install KubeVela first."
    echo "   Installation: kubectl apply -f https://github.com/kubevela/kubevela/releases/download/v1.9.0/vela-core.yaml"
    exit 1
fi

# Check if KubeVela controller is running
if ! kubectl get pods -n vela-system -l app.kubernetes.io/name=kubevela-vela-core &>/dev/null; then
    echo "❌ KubeVela controller not found. Please ensure KubeVela is properly installed."
    exit 1
fi

echo "✅ KubeVela detected and running"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install WorkflowStepDefinitions
echo ""
echo "📋 Installing Custom WorkflowStepDefinitions..."
echo "   - create-crossplane-claims"
echo "   - wait-for-claims" 
echo "   - cleanup-failed-claims"

if kubectl apply -f "$SCRIPT_DIR/workflow-step-definitions.yaml"; then
    echo "✅ WorkflowStepDefinitions installed successfully"
else
    echo "❌ Failed to install WorkflowStepDefinitions"
    exit 1
fi

# Install PolicyDefinitions and TraitDefinitions
echo ""
echo "🔧 Installing PolicyDefinitions and TraitDefinitions..."
echo "   - crossplane-execution-order (Policy)"
echo "   - health (Policy)"
echo "   - crossplane-workflow (Trait)"

if kubectl apply -f "$SCRIPT_DIR/policy-trait-definitions.yaml"; then
    echo "✅ PolicyDefinitions and TraitDefinitions installed successfully"
else
    echo "❌ Failed to install PolicyDefinitions and TraitDefinitions"
    exit 1
fi

# Wait for resources to be ready
echo ""
echo "⏳ Waiting for custom definitions to be ready..."
sleep 10

# Verify installation
echo ""
echo "🔍 Verifying installation..."

# Check WorkflowStepDefinitions
WORKFLOW_STEPS=("create-crossplane-claims" "wait-for-claims" "cleanup-failed-claims")
for step in "${WORKFLOW_STEPS[@]}"; do
    if kubectl get workflowstepdefinition "$step" -n vela-system &>/dev/null; then
        echo "✅ WorkflowStepDefinition '$step' is ready"
    else
        echo "❌ WorkflowStepDefinition '$step' not found"
        exit 1
    fi
done

# Check PolicyDefinitions  
POLICIES=("crossplane-execution-order" "health")
for policy in "${POLICIES[@]}"; do
    if kubectl get policydefinition "$policy" -n vela-system &>/dev/null; then
        echo "✅ PolicyDefinition '$policy' is ready"
    else
        echo "❌ PolicyDefinition '$policy' not found"
        exit 1
    fi
done

# Check TraitDefinitions
TRAITS=("crossplane-workflow")
for trait in "${TRAITS[@]}"; do
    if kubectl get traitdefinition "$trait" -n vela-system &>/dev/null; then
        echo "✅ TraitDefinition '$trait' is ready"
    else
        echo "❌ TraitDefinition '$trait' not found"
        exit 1
    fi
done

echo ""
echo "🎉 OAM → Crossplane Workflow Orchestration Installation Complete!"
echo ""
echo "📖 Next Steps:"
echo "   1. Apply the updated AppContainerClaim composition with workflow support"
echo "   2. Create OAM Applications using the new workflow orchestration"
echo "   3. Monitor workflow execution in KubeVela"
echo ""
echo "💡 Example OAM Application with workflow orchestration:"
echo "   See: $SCRIPT_DIR/../oam/example-oam-applications.yaml"
echo ""
echo "🔧 To test the workflow orchestration:"
echo "   ./test-workflow-orchestration.sh"