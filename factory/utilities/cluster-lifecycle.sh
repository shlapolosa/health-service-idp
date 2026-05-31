#!/bin/bash

# Cluster Lifecycle Management Script
# Handles scale-up and scale-down with vcluster automation

CLUSTER_NAME="socrateshlapolosa-karpenter-demo"
NODEGROUP_NAME="socrateshlapolosa-karpenter-demo-ng-medium"
VCLUSTER_NAME="architecture-vizualisation"
VCLUSTER_NAMESPACE="vcluster-platform"

# AWS SSO Authentication Function
refresh_aws_credentials() {
    echo "🔑 Refreshing AWS SSO credentials..."
    
    # 1. Pick your profile
    profile="${AWS_PROFILE:-default}"
    
    # 2. Where is your SSO directory?
    sso_region=$(aws configure get sso_region --profile "$profile")
    
    # 3. Where do your AWS services live?
    aws_region=$(aws configure get region --profile "$profile")
    # Fallback if you haven't set it:
    aws_region=${aws_region:-us-west-2}
    
    account=$(aws configure get sso_account_id --profile "$profile")
    role=$(aws configure get sso_role_name --profile "$profile")
    
    # 4. Grab the most recent SSO cache file
    cache=$(ls -1t ~/.aws/sso/cache/*.json 2>/dev/null | head -n1)
    if [[ -z "$cache" ]]; then
        echo "❌ No SSO cache found. Please run 'aws sso login' first."
        exit 1
    fi
    
    token=$(jq -r .accessToken "$cache")
    
    # 5. Exchange for AWS creds in the SSO realm
    creds_json=$(
        aws sso get-role-credentials \
            --account-id   "$account" \
            --role-name    "$role" \
            --access-token "$token" \
            --region       "$sso_region"
    )
    
    # 6. Export them
    export AWS_ACCESS_KEY_ID=$(jq -r .roleCredentials.accessKeyId <<<"$creds_json")
    export AWS_SECRET_ACCESS_KEY=$(jq -r .roleCredentials.secretAccessKey <<<"$creds_json")
    export AWS_SESSION_TOKEN=$(jq -r .roleCredentials.sessionToken <<<"$creds_json")
    
    # 7. And set the AWS region for STS/EKS calls
    export AWS_REGION="$aws_region"
    export AWS_DEFAULT_REGION="$aws_region"
    
    echo "✅ AWS credentials refreshed successfully"
}

scale_up() {
    echo "🚀 Starting cluster scale-up..."
    
    # Refresh AWS credentials first
    refresh_aws_credentials
    
    echo "⬆️  Scaling managed nodegroup to 1 node..."
    aws eks update-nodegroup-config --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP_NAME --scaling-config minSize=1,maxSize=5,desiredSize=1
    
    echo "⏰ Waiting for managed nodegroup node to be ready..."
    kubectl wait --for=condition=Ready node -l alpha.eksctl.io/nodegroup-name=$NODEGROUP_NAME --timeout=300s
    
    echo "🎛️  Verifying Karpenter is running (should auto-start with node)..."
    kubectl wait --for=condition=Ready pod -l app=karpenter -n kube-system --timeout=300s
    
    echo "▶️  Resuming vcluster (restores workloads and triggers Karpenter scaling)..."
    vcluster resume $VCLUSTER_NAME --namespace $VCLUSTER_NAMESPACE
    
    echo "⏰ Waiting for vcluster connection to be ready..."
    sleep 30
    
    echo "📊 Monitoring Karpenter auto-scaling..."
    timeout=300  # 5 minutes timeout
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        karpenter_nodes=$(kubectl get nodes -l karpenter.sh/nodepool --no-headers 2>/dev/null | wc -l)
        managed_nodes=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=$NODEGROUP_NAME --no-headers 2>/dev/null | wc -l)
        vcluster_pods=$(kubectl get pods -n $VCLUSTER_NAMESPACE | grep $VCLUSTER_NAME | grep Running | wc -l)
        
        echo "📊 Nodes: $karpenter_nodes Karpenter + $managed_nodes Managed | vcluster pods: $vcluster_pods"
        
        if [ "$vcluster_pods" -gt 0 ] && [ $((karpenter_nodes + managed_nodes)) -gt 1 ]; then
            echo "✅ vcluster resumed and Karpenter scaling detected!"
            break
        fi
        
        sleep 15
        elapsed=$((elapsed + 15))
    done
    
    echo "✅ Cluster scale-up complete!"
    echo "📊 Final status:"
    kubectl get nodes
    echo ""
    echo "🏗️  vcluster status:"
    kubectl get pods -n $VCLUSTER_NAMESPACE | grep $VCLUSTER_NAME
    echo ""
    echo "💡 vcluster resumed - workloads will trigger automatic Karpenter node provisioning"
}

scale_down() {
    echo "⬇️  Starting cluster scale-down using vcluster pause..."
    
    # Refresh AWS credentials first
    refresh_aws_credentials
    
    echo "⏸️  Pausing vcluster (disconnects and removes all workloads)..."
    vcluster pause $VCLUSTER_NAME --namespace $VCLUSTER_NAMESPACE
    
    echo "⏰ Waiting for vcluster workloads to be removed..."
    sleep 30
    
    echo "🔄 Waiting for Karpenter to detect workload removal and auto-scale down nodes..."
    echo "📊 Monitoring node count..."
    
    # Monitor until only managed nodegroup nodes remain
    timeout=300  # 5 minutes timeout
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        karpenter_nodes=$(kubectl get nodes -l karpenter.sh/nodepool --no-headers 2>/dev/null | wc -l)
        managed_nodes=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=$NODEGROUP_NAME --no-headers 2>/dev/null | wc -l)
        
        echo "📊 Current nodes: $karpenter_nodes Karpenter + $managed_nodes Managed"
        
        if [ "$karpenter_nodes" -eq 0 ]; then
            echo "✅ All Karpenter nodes have auto-terminated!"
            break
        fi
        
        sleep 15
        elapsed=$((elapsed + 15))
    done
    
    if [ $elapsed -ge $timeout ]; then
        echo "⚠️  Timeout waiting for Karpenter auto-scale down, some nodes may remain"
        echo "🔍 Remaining Karpenter nodes:"
        kubectl get nodes -l karpenter.sh/nodepool --no-headers 2>/dev/null || echo "None"
    fi
    
    echo "⬇️  Scaling managed nodegroup to 0..."
    aws eks update-nodegroup-config --cluster-name $CLUSTER_NAME --nodegroup-name $NODEGROUP_NAME --scaling-config minSize=0,maxSize=5,desiredSize=0
    
    echo "⏰ Waiting for managed nodes to terminate..."
    kubectl wait --for=delete node -l alpha.eksctl.io/nodegroup-name=$NODEGROUP_NAME --timeout=300s || true
    
    echo "✅ Scale-down complete!"
    echo "💰 All infrastructure has been scaled to zero"
    echo "🔄 Use './cluster-lifecycle.sh up' to scale back up"
    echo ""
    echo "💡 vcluster is paused, not just scaled down - this cleanly removes all workloads"
}

status() {
    echo "📊 Cluster Status:"
    echo "==================="
    echo "🏗️  Nodes:"
    kubectl get nodes 2>/dev/null || echo "❌ Cannot connect to cluster"
    echo ""
    echo "🏗️  vcluster:"
    kubectl get pods -n $VCLUSTER_NAMESPACE 2>/dev/null | grep $VCLUSTER_NAME || echo "❌ vcluster not running"
    echo ""
    echo "🎛️  Karpenter:"
    kubectl get pods -n kube-system 2>/dev/null | grep karpenter || echo "❌ Karpenter not running"
    echo "🔧 Karpenter replicas: $(kubectl get deployment karpenter -n kube-system -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "unknown")"
}

upgrade_nodegroup() {
    echo "🔄 Starting nodegroup vertical scaling upgrade..."
    
    # Refresh AWS credentials first
    refresh_aws_credentials
    
    echo "📊 Creating new t3.medium nodegroup..."
    eksctl create nodegroup --cluster=$CLUSTER_NAME --name=$NODEGROUP_NAME --instance-types=t3.medium --nodes=3 --nodes-min=0 --nodes-max=5 --node-private-networking=false
    
    echo "⏰ Waiting for new nodes to be ready..."
    kubectl wait --for=condition=Ready node -l eks.amazonaws.com/nodegroup=$NODEGROUP_NAME --timeout=600s
    
    echo "✅ t3.medium nodegroup created successfully!"
    
    echo "✅ Vertical scaling complete!"
    echo "📊 New cluster status:"
    kubectl get nodes -l eks.amazonaws.com/nodegroup=$NODEGROUP_NAME -o custom-columns=NAME:.metadata.name,INSTANCE:.metadata.labels.node\.kubernetes\.io/instance-type,STATUS:.status.conditions[-1].type
}

usage() {
    echo "Usage: $0 {up|down|status|upgrade|configure-argocd}"
    echo "  up             - Scale cluster up (1 MNG node + vcluster resume + auto Karpenter scaling)"
    echo "  down           - Scale cluster down (vcluster pause + auto node cleanup)"
    echo "  status         - Show current cluster status"
    echo "  upgrade        - Upgrade nodegroup from t3.small to t3.medium"
    echo "  configure-argocd - Set up ArgoCD with GitHub access using GITHUB_TOKEN"
    echo ""
    echo "Improved cost-optimized approach:"
    echo "  - Uses vcluster pause/resume for clean workload management"
    echo "  - 1 x t3.medium MNG node (hosts Karpenter controller)"
    echo "  - Karpenter auto-scales based on workload demand"
    echo "  - vcluster pause cleanly removes ALL workloads"
    echo "  - Karpenter detects workload removal and auto-terminates nodes"
    echo "  - Eliminates orphaned node scenarios"
    echo "  - No manual node draining required"
}

configure_argocd_github() {
    echo "🔧 Configuring ArgoCD with GitHub access..."
    
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "❌ GITHUB_TOKEN environment variable not set"
        echo "💡 Export your GitHub personal access token:"
        echo "   export GITHUB_TOKEN='github_pat_...'"
        return 1
    fi
    
    echo "🔑 Creating GitHub secret in ArgoCD..."
    kubectl create secret generic repo-github \
        --from-literal=type=git \
        --from-literal=url=https://github.com \
        --from-literal=password="$GITHUB_TOKEN" \
        --from-literal=username=token \
        -n argocd \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo "🏷️  Labeling secret for ArgoCD repository access..."
    kubectl label secret repo-github argocd.argoproj.io/secret-type=repository -n argocd
    
    echo "✅ ArgoCD GitHub access configured!"
    echo "📋 You can now create ArgoCD applications that access private GitHub repos"
}

case "$1" in
    up)
        scale_up
        ;;
    down)
        scale_down
        ;;
    status)
        status
        ;;
    upgrade)
        upgrade_nodegroup
        ;;
    configure-argocd)
        configure_argocd_github
        ;;
    *)
        usage
        exit 1
        ;;
esac