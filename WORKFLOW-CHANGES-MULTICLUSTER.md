# Workflow Changes for Multi-Cluster End-to-End Deployment

## Overview
This document outlines all required changes to enable Knative on the host cluster to deploy services to vClusters using KubeVela's ClusterGateway mechanism.

## Critical Workflow Changes

### 1. Multi-Cluster Registration & Configuration
**Location**: `argo-workflows/microservice-standard-contract.yaml` (after line 1130)  
**Action**: Add new step after vCluster creation

```yaml
- name: register-vcluster-multicluster
  dependencies: [ensure-target-vcluster]
  template: register-vcluster
  arguments:
    parameters:
    - name: vcluster-name
      value: "{{inputs.parameters.vcluster-name}}"
    - name: namespace
      value: "{{inputs.parameters.namespace}}"
```

**Template to Add**:
```yaml
- name: register-vcluster
  inputs:
    parameters:
    - name: vcluster-name
    - name: namespace
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      set -e
      apk add --no-cache curl kubectl
      
      # Install vela CLI
      curl -fsSl https://kubevela.io/script/install.sh | bash
      
      # Get vCluster kubeconfig
      kubectl get secret vc-{{inputs.parameters.vcluster-name}} \
        -n {{inputs.parameters.namespace}} \
        -o jsonpath='{.data.config}' | base64 -d > /tmp/vcluster.kubeconfig
      
      # Register vCluster with KubeVela
      vela cluster join {{inputs.parameters.vcluster-name}} \
        --kubeconfig /tmp/vcluster.kubeconfig
      
      # Verify registration
      vela cluster list | grep {{inputs.parameters.vcluster-name}}
      
      echo "✅ vCluster registered with KubeVela multi-cluster system"
```

### 2. Remove Knative Installation from vCluster
**Location**: `argo-workflows/microservice-standard-contract.yaml` (lines 937-971)  
**Action**: DELETE the entire `install-knative` step and its template

**Reason**: Knative runs on host cluster and deploys to vCluster via ClusterGateway

### 3. Fix OAM Application Deployment Target
**Location**: `crossplane/application-claim-composition.yaml` (lines 598-605)  
**Action**: Update vCluster target detection and propagation

```yaml
# Determine target vCluster from ApplicationClaim spec
VCLUSTER_TARGET=$(kubectl get applicationclaim $SERVICE_NAME \
  -o jsonpath='{.spec.targetVCluster}' 2>/dev/null || echo "")
if [ -z "$VCLUSTER_TARGET" ]; then
  VCLUSTER_TARGET=$(kubectl get applicationclaim $SERVICE_NAME \
    -o jsonpath='{.metadata.annotations.app\.oam\.dev/cluster}' 2>/dev/null || echo "")
fi
if [ -z "$VCLUSTER_TARGET" ]; then
  VCLUSTER_TARGET="architecture-visualization"  # Updated default
fi
echo "🎯 Target vCluster: $VCLUSTER_TARGET"
```

**Location**: `crossplane/application-claim-composition.yaml` (lines 650-700)  
**Action**: Update OAM component generation to include targetEnvironment

```yaml
cat > oam/applications/application.yaml <<EOF
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: $SERVICE_NAME
  namespace: $SERVICE_NAME
  annotations:
    app.oam.dev/cluster: "$VCLUSTER_TARGET"
spec:
  components:
  - name: $SERVICE_NAME
    type: $COMPONENT_TYPE
    properties:
      name: $SERVICE_NAME
      image: $SERVICE_NAME:latest
      language: $LANGUAGE
      framework: $FRAMEWORK
      port: $COMPONENT_PORT
      healthPath: /health
      database: $DATABASE
      cache: $CACHE
      targetEnvironment: "$VCLUSTER_TARGET"  # Add this line
EOF
```

### 4. Add Service Name Validation
**Location**: `argo-workflows/microservice-standard-contract.yaml` (after line 420)  
**Action**: Add validation step after `validate-parameters`

```yaml
- name: validate-service-name-length
  dependencies: [validate-parameters]
  template: validate-name-length
  arguments:
    parameters:
    - name: resource-name
      value: "{{inputs.parameters.resource-name}}"
```

**Template to Add**:
```yaml
- name: validate-name-length
  inputs:
    parameters:
    - name: resource-name
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      NAME="{{inputs.parameters.resource-name}}"
      NAME_LENGTH=${#NAME}
      
      if [ $NAME_LENGTH -gt 20 ]; then
        echo "❌ Service name '$NAME' is too long ($NAME_LENGTH characters)"
        echo "Service names must be 20 characters or less to prevent label issues"
        echo "This ensures generated resource names stay under Kubernetes' 63 character limit"
        exit 1
      fi
      
      echo "✅ Service name length valid: $NAME_LENGTH characters"
```

### 5. Increase vCluster Resource Allocation
**Location**: `crossplane/vcluster-environment-claim-composition.yaml`  
**Action**: Update resource limits and add pod quota

```yaml
resources:
  limits:
    memory: 16Gi  # Increased from 8Gi
    cpu: 8        # Increased from 4
  requests:
    memory: 8Gi   # Increased from 4Gi
    cpu: 4        # Increased from 2
annotations:
  resourcequota.vcluster.com/pods: "200"  # Add pod limit
```

### 6. Fix ArgoCD Deployment to vCluster
**Location**: `argo-workflows/microservice-standard-contract.yaml` (lines 1000-1050)  
**Action**: Update ArgoCD installation to use core version

```yaml
- name: deploy-argocd-to-vcluster
  template: deploy-argocd-core
  arguments:
    parameters:
    - name: vcluster-name
      value: "{{inputs.parameters.vcluster-name}}"
    - name: namespace
      value: "{{inputs.parameters.namespace}}"
    - name: github-token
      value: "{{workflow.parameters.github-token}}"
```

**Template**:
```yaml
- name: deploy-argocd-core
  inputs:
    parameters:
    - name: vcluster-name
    - name: namespace
    - name: github-token
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      set -e
      apk add --no-cache kubectl helm
      
      # Connect to vCluster
      kubectl config set-context vcluster-{{inputs.parameters.vcluster-name}} \
        --cluster=vcluster-{{inputs.parameters.vcluster-name}} \
        --namespace={{inputs.parameters.namespace}}
      
      # Create GitHub token secret
      kubectl create namespace argocd --context=vcluster-{{inputs.parameters.vcluster-name}} || true
      kubectl create secret generic github-token \
        --from-literal=token={{inputs.parameters.github-token}} \
        -n argocd --context=vcluster-{{inputs.parameters.vcluster-name}} || true
      
      # Install ArgoCD Core (lightweight)
      kubectl apply -n argocd \
        --context=vcluster-{{inputs.parameters.vcluster-name}} \
        -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/core-install.yaml
      
      echo "✅ ArgoCD Core deployed to vCluster"
```

### 7. Add KubeVela Installation Check
**Location**: `argo-workflows/microservice-standard-contract.yaml` (after register-vcluster step)  
**Action**: Add KubeVela installation step

```yaml
- name: ensure-kubevela-in-vcluster
  dependencies: [register-vcluster-multicluster]
  template: install-kubevela-core
  arguments:
    parameters:
    - name: vcluster-name
      value: "{{inputs.parameters.vcluster-name}}"
```

**Template**:
```yaml
- name: install-kubevela-core
  inputs:
    parameters:
    - name: vcluster-name
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      set -e
      apk add --no-cache kubectl helm
      
      # Check if KubeVela is installed
      if kubectl get deployment -n vela-system vela-core \
        --context=vcluster-{{inputs.parameters.vcluster-name}} 2>/dev/null; then
        echo "✅ KubeVela already installed"
      else
        echo "📦 Installing KubeVela core..."
        helm repo add kubevela https://kubevela.github.io/charts
        helm repo update
        helm install --create-namespace -n vela-system \
          --context=vcluster-{{inputs.parameters.vcluster-name}} \
          kubevela kubevela/vela-core --version 1.9.0 \
          --set multicluster.enabled=true
      fi
      
      # Apply ComponentDefinitions from host to vCluster
      kubectl get componentdefinitions -o yaml | \
        kubectl apply --context=vcluster-{{inputs.parameters.vcluster-name}} -f -
      
      echo "✅ KubeVela and ComponentDefinitions ready in vCluster"
```

### 8. Fix GitOps Repository Structure
**Location**: `crossplane/application-claim-composition.yaml` (lines 775-850)  
**Action**: Update directory structure for vCluster-specific deployments

```yaml
# Create vCluster-specific directory structure
mkdir -p vcluster/$VCLUSTER_TARGET/applications/$SERVICE_NAME
mkdir -p vcluster/$VCLUSTER_TARGET/manifests

# Copy OAM application to vCluster directory
cp oam/applications/application.yaml \
   vcluster/$VCLUSTER_TARGET/applications/$SERVICE_NAME/application.yaml

# Update app-of-apps to watch vCluster directory
cat > apps/vcluster-$VCLUSTER_TARGET-apps.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $SERVICE_NAME-vcluster-apps
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/$GITHUB_USER/$APP_CONTAINER-gitops.git
    targetRevision: HEAD
    path: vcluster/$VCLUSTER_TARGET/applications
  destination:
    name: $VCLUSTER_TARGET
    namespace: $SERVICE_NAME
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

### 9. Add Multi-Cluster Deployment Validation
**Location**: `argo-workflows/microservice-standard-contract.yaml` (after wait-for-microservice-ready)  
**Action**: Add validation step

```yaml
- name: validate-multicluster-deployment
  dependencies: [wait-for-microservice-ready]
  template: validate-deployment
  arguments:
    parameters:
    - name: resource-name
      value: "{{inputs.parameters.resource-name}}"
    - name: vcluster-name
      value: "{{inputs.parameters.vcluster-name}}"
```

**Template**:
```yaml
- name: validate-deployment
  inputs:
    parameters:
    - name: resource-name
    - name: vcluster-name
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      set -e
      apk add --no-cache kubectl curl
      
      # Check deployment in vCluster
      echo "🔍 Checking deployment in vCluster..."
      kubectl get ksvc {{inputs.parameters.resource-name}} \
        --context=vcluster-{{inputs.parameters.vcluster-name}} \
        -n {{inputs.parameters.resource-name}} || {
        echo "⚠️ Knative service not found in vCluster"
        exit 1
      }
      
      # Verify ClusterGateway connectivity
      echo "🔍 Verifying ClusterGateway..."
      kubectl get clustergateway {{inputs.parameters.vcluster-name}} || {
        echo "⚠️ ClusterGateway not configured"
        exit 1
      }
      
      # Test service endpoint
      SERVICE_URL=$(kubectl get ksvc {{inputs.parameters.resource-name}} \
        --context=vcluster-{{inputs.parameters.vcluster-name}} \
        -n {{inputs.parameters.resource-name}} \
        -o jsonpath='{.status.url}')
      
      if [ ! -z "$SERVICE_URL" ]; then
        echo "✅ Service deployed successfully: $SERVICE_URL"
      else
        echo "⚠️ Service URL not available"
        exit 1
      fi
```

### 10. Update Notification Steps
**Location**: `argo-workflows/microservice-standard-contract.yaml` (lines 350-380)  
**Action**: Enhance success and failure notifications

```yaml
# Success notification
VCLUSTER_CONTEXT="kubectl config use-context vcluster-$VCLUSTER_NAME"
MESSAGE="✅ Microservice '$SERVICE_NAME' created successfully!
📍 vCluster: $VCLUSTER_NAME
🔧 Switch context: $VCLUSTER_CONTEXT
📦 Repository: https://github.com/$GITHUB_USER/$REPO_NAME
🚀 GitOps: https://github.com/$GITHUB_USER/$REPO_NAME-gitops
📊 Namespace: $SERVICE_NAME"

# Failure notification with specific reason
FAILURE_REASON=$(kubectl get workflow $WORKFLOW_NAME -o jsonpath='{.status.message}')
MESSAGE="❌ Failed to create microservice '$SERVICE_NAME'
📍 vCluster: $VCLUSTER_NAME
❗ Reason: $FAILURE_REASON
🔍 Debug: kubectl logs -n argo workflow/$WORKFLOW_NAME
🧹 Cleanup: kubectl delete applicationclaim $SERVICE_NAME"
```

### 11. Add Cleanup on Failure
**Location**: `argo-workflows/microservice-standard-contract.yaml` (after notify-failure)  
**Action**: Add cleanup step

```yaml
- name: cleanup-on-failure
  when: "'{{workflow.status}}' == 'Failed'"
  template: cleanup-resources
  arguments:
    parameters:
    - name: resource-name
      value: "{{inputs.parameters.resource-name}}"
```

**Template**:
```yaml
- name: cleanup-resources
  inputs:
    parameters:
    - name: resource-name
  script:
    image: alpine:3.18
    command: [sh]
    source: |
      echo "🧹 Cleaning up failed resources..."
      
      # Delete ApplicationClaim
      kubectl delete applicationclaim {{inputs.parameters.resource-name}} || true
      
      # Delete namespace if empty
      if [ -z "$(kubectl get all -n {{inputs.parameters.resource-name}} 2>/dev/null)" ]; then
        kubectl delete namespace {{inputs.parameters.resource-name}} || true
      fi
      
      # Delete GitOps repo if it was created
      if [ -d "/tmp/{{inputs.parameters.resource-name}}-gitops" ]; then
        rm -rf /tmp/{{inputs.parameters.resource-name}}-gitops
      fi
      
      echo "✅ Cleanup completed"
```

### 12. Fix Repository Pattern
**Location**: `crossplane/application-claim-composition.yaml` (lines 1018-1086)  
**Action**: Update to default to unified repository

```yaml
# Extract repository from OAM Application level (not component level)
APP_CONTAINER=$(kubectl get application -l app.oam.dev/name=$SERVICE_NAME \
  -o jsonpath='{.items[0].spec.repository}' 2>/dev/null || echo "")

# Default to unified repository if not specified
if [ -z "$APP_CONTAINER" ]; then
  APP_CONTAINER="health-service-idp"  # Default unified repository
  echo "📦 Using default unified repository: $APP_CONTAINER"
else
  echo "📦 Using specified repository: $APP_CONTAINER"
fi
```

## Implementation Priority

1. **Critical** - Must be done first:
   - Remove Knative installation from vCluster (breaks if present)
   - Add vCluster multi-cluster registration
   - Fix OAM targetEnvironment propagation

2. **Important** - Required for stability:
   - Service name validation
   - Increase vCluster resources
   - KubeVela installation in vCluster

3. **Enhancement** - Improves operations:
   - Enhanced notifications
   - Cleanup on failure
   - Deployment validation

4. **Optimization** - Better developer experience:
   - Fix unified repository pattern
   - GitOps directory structure

## Testing Checklist

- [ ] vCluster creates successfully
- [ ] vCluster registers with KubeVela multi-cluster
- [ ] KubeVela core installs in vCluster
- [ ] ComponentDefinitions replicate to vCluster
- [ ] OAM Application includes targetEnvironment
- [ ] Knative service deploys from host to vCluster
- [ ] Service is accessible via ClusterGateway
- [ ] ArgoCD Core deploys successfully
- [ ] GitOps repository has correct structure
- [ ] Cleanup works on failure

## Known Issues & Workarounds

1. **Label Length Issue**: Service names > 20 chars cause failures
   - **Workaround**: Validation step prevents this

2. **vCluster Resource Limits**: Default limits too low for full stack
   - **Workaround**: Increased to 16Gi/8CPU

3. **ArgoCD Memory Usage**: Full ArgoCD exceeds vCluster capacity
   - **Workaround**: Use ArgoCD Core (lightweight)

4. **ClusterGateway Certificate**: May need manual refresh
   - **Workaround**: Check certificate expiry, regenerate if needed

## Next Steps

1. Implement changes in order of priority
2. Test each change incrementally
3. Update CI/CD pipeline to handle multi-cluster deployments
4. Document multi-cluster architecture in ARCHITECTURAL_DECISIONS.md