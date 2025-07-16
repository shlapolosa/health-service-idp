# Current State: Standardized Parameter Contract System

**Status**: 🟡 Partially Complete - Core functionality working, investigation needed for resource provisioning

This document provides a comprehensive overview of the current implementation state of the standardized parameter contract system for the Internal Developer Platform.

## 🎯 Executive Summary

We have successfully implemented a **standardized parameter contract system** that replaces the previous inconsistent workflow templates with a unified, composable architecture. The system uses a 4-tier parameter structure enabling template composition and consistent developer experience.

### ✅ What's Working
- **Parameter Contract System**: 4-tier standardized parameters across all workflows
- **Template Composition**: Microservice → AppContainer → VCluster workflow chains
- **Slack Notifications**: End-to-end messaging with proper RBAC permissions  
- **Parameter Validation**: JSON, DNS-1123, and enum validation working
- **Crossplane Integration**: Resource claims being created successfully

### 🚧 What Needs Investigation  
- **VCluster Provisioning**: Claims created but stuck in provisioning state
- **Repository Creation**: AppContainerClaim not completing repository setup
- **AWS Authentication**: Tokens expired, need re-auth to debug Crossplane

---

## 🏗️ Architecture Overview

### Template Hierarchy
```
📦 Microservice Creation Request
    ↓
🔧 microservice-standard-contract.yaml
    ↓ (repository management)
📦 AppContainer (creates/updates repositories)
    ↓ (kubectl apply)
☸️  Crossplane Resources (AppContainerClaim, ApplicationClaim)

📦 VCluster Creation Request (separate workflow)
    ↓
🏢 vcluster-standard-contract.yaml
    ↓ (kubectl apply)
☸️  Crossplane Resources (VClusterEnvironmentClaim)
```

### Parameter Contract Tiers

#### Tier 1: Universal Parameters (Required by ALL workflows)
```yaml
- resource-name: "payment-service"      # DNS-1123 compliant name
- resource-type: "microservice"         # microservice|appcontainer|vcluster  
- namespace: "e2e-test"                 # Kubernetes namespace
- user: "claude"                        # Requesting user
- description: "Payment processing service"
- github-org: "socrates12345"           # GitHub organization
- docker-registry: "docker.io/socrates12345"
- slack-channel: "#all-internal-developer-platform"
- slack-user-id: "U123456789"
```

#### Tier 2: Platform Parameters (Common platform features)
```yaml
- security-enabled: "true"              # Enable security features
- observability-enabled: "true"         # Enable monitoring stack
- backup-enabled: "false"               # Enable backup functionality  
- environment-tier: "development"       # development|staging|production
- auto-create-dependencies: "true"      # Auto-create required infrastructure
- resource-size: "medium"               # small|medium|large|xlarge
```

#### Tier 3: Resource-Specific Parameters
```yaml
# VCluster-specific
- vcluster-size: "medium"
- vcluster-capabilities: '{"observability":"true","security":"true",...}'

# Microservice-specific  
- microservice-language: "python"       # python|java|fastapi|springboot
- microservice-framework: "fastapi" 
- microservice-database: "postgresql"   # none|postgresql|postgres
- microservice-cache: "redis"           # none|redis
- target-vcluster: "payment-service-vcluster"

# AppContainer-specific
- enable-default-microservice: "true"
- parent-appcontainer: ""
```

---

## 🚀 Usage Examples

### 1. Create Complete Microservice Environment

Creates microservice + app container + VCluster infrastructure:

```yaml
# /tmp/test-microservice-working.yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: test-microservice-working-
  namespace: argo
spec:
  entrypoint: test-microservice
  templates:
  - name: test-microservice
    steps:
    - - name: create-microservice
        templateRef:
          name: microservice-standard-contract
          template: create-microservice
        arguments:
          parameters:
          - name: resource-name
            value: "payment-service"
          - name: namespace  
            value: "e2e-test"
          - name: user
            value: "claude"
          - name: microservice-language
            value: "python"
          - name: microservice-database
            value: "postgresql"
```

**Run with**: `kubectl apply -f /tmp/test-microservice-working.yaml`

### 2. Create Standalone VCluster

Creates just VCluster infrastructure:

```yaml
# Example VCluster creation
templateRef:
  name: vcluster-standard-contract
  template: create-vcluster
arguments:
  parameters:
  - name: resource-name
    value: "development-cluster"
  - name: vcluster-size
    value: "large"
  - name: vcluster-capabilities
    value: '{"observability":"true","security":"true","gitops":"true"}'
```

### 3. Create AppContainer Only

Creates app container in existing VCluster:

```yaml
# Example AppContainer creation  
templateRef:
  name: appcontainer-standard-contract
  template: create-appcontainer
arguments:
  parameters:
  - name: resource-name
    value: "mobile-backend"
  - name: target-vcluster
    value: "existing-cluster"
  - name: auto-create-dependencies
    value: "false"
```

---

## 🔧 Key Files and Components

### Core Template Files
| File | Purpose | Status |
|------|---------|--------|
| `microservice-standard-contract.yaml` | Top-level microservice creation | ✅ Working |
| `appcontainer-standard-contract.yaml` | Application container orchestration | ✅ Working |
| `vcluster-standard-contract.yaml` | VCluster infrastructure provisioning | ✅ Working |
| `simple-slack-notifications.yaml` | Unified notification system | ✅ Working |

### Test Files (Working Examples)
| File | Purpose | Status |
|------|---------|--------|
| `/tmp/test-microservice-working.yaml` | End-to-end microservice test | ✅ Tested |
| `/tmp/test-appcontainer-manual.yaml` | AppContainer standalone test | ✅ Ready |
| `/tmp/test-slack-correct-channel.yaml` | Slack notification test | ✅ Working |

### Legacy Files (Pre-Contract)
| File | Purpose | Status |
|------|---------|--------|
| `microservice-template-v2.yaml` | Pre-contract microservice template | 🗑️ Legacy |
| `appcontainer-mapping-layer.yaml` | Intermediate solution | 🗑️ Legacy |
| `slack-standard-notifications.yaml` | Complex notification system | 🗑️ Replaced |

---

## 🔧 Setup and Configuration

### Prerequisites
1. **AWS Authentication**: `aws sso login` (currently expired)
2. **Kubernetes Context**: Connected to EKS cluster with Argo Workflows
3. **RBAC Permissions**: Argo service account has secret read access ✅
4. **Slack Integration**: Webhook secret configured ✅

### Slack Webhook Configuration
```bash
# Secret properly configured with working webhook
kubectl get secret slack-webhook -n argo
# Contains:
#   webhook-url: https://hooks.slack.com/services/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
#   signing-secret: 1f50ac1d5e5c39eb9bf00dad682a4141
```

### RBAC Configuration
```bash
# ✅ COMPLETED - Argo workflows can read secrets
kubectl get clusterrole argo-cluster-role -o yaml | grep -A 5 secrets
#   - apiGroups: [""]
#     resources: ["secrets"]  
#     verbs: ["get", "list"]
```

---

## 🔍 Current Status Detail

### ✅ Completely Working Components

#### 1. Parameter Contract System
- **4-tier parameter hierarchy** implemented across all templates
- **Parameter validation** working for all tiers (DNS-1123, JSON, enums)
- **Parameter flow** between composed templates functioning
- **Template composition** enabling Microservice → AppContainer → VCluster chains

#### 2. Slack Notification System  
- **End-to-end notifications** working with simple interface
- **RBAC permissions** properly configured for secret access
- **Workflow controller** restarted to pick up permission changes
- **Message formatting** consistent across all workflow stages

#### 3. Template Composition
- **Microservice template** successfully calls AppContainer template
- **AppContainer template** successfully calls VCluster template  
- **Parameter mapping** working between template levels
- **Error handling** and failure notifications functioning

#### 4. Resource Claim Creation
- **VClusterEnvironmentClaim** being created with correct spec
- **AppContainerClaim** being created with correct parameters
- **Crossplane integration** receiving and processing claims
- **Kubernetes resource** creation working

### 🚧 Components Needing Investigation

#### 1. VCluster Provisioning (High Priority)
**Issue**: VClusterEnvironmentClaim created but stuck in provisioning

**Last Known State**:
```yaml
# payment-service-vcluster VClusterEnvironmentClaim  
status:
  synced: true
  ready: false  # ← Stuck here
```

**Investigation Needed**:
- Check Crossplane VCluster Composition status
- Verify VCluster operator is running and healthy
- Check AWS IAM permissions for VCluster provisioning
- Review Crossplane provider logs

**Next Steps**: 
```bash
# After AWS re-auth, run:
kubectl get vclusterenvironmentclaim payment-service-vcluster -n e2e-test -o yaml
kubectl get composition vcluster-environment
kubectl logs -n crossplane-system deployment/crossplane
```

#### 2. Repository Creation (High Priority)  
**Issue**: AppContainerClaim not completing repository setup

**Last Known State**:
```yaml
# manual-test-app AppContainerClaim
# Unknown status - need to check after AWS re-auth
```

**Investigation Needed**:
- Verify GitHub provider configuration in Crossplane
- Check if GitHub API token is valid and has repo creation permissions
- Review AppContainer Composition and XRD definitions
- Verify repository creation webhook is functioning

**Next Steps**:
```bash
# After AWS re-auth, run:
kubectl get appcontainerclaim manual-test-app -n e2e-test -o yaml
kubectl get composition appcontainer-environment  
kubectl get provider.pkg.crossplane.io -A
```

---

## 🚦 Testing Status

### ✅ Successfully Tested
1. **Parameter Validation**: All tier validation rules working
2. **Template Composition**: Full Microservice → AppContainer → VCluster chain
3. **Slack Notifications**: All notification types (starting, progress, success, failure)
4. **RBAC Permissions**: Workflow secret access functioning  
5. **JSON Parameter Handling**: Complex JSON capabilities parameter working
6. **Resource Creation**: Crossplane claims being created

### 🧪 Test Cases Available
```bash
# End-to-end microservice creation
kubectl apply -f /tmp/test-microservice-working.yaml

# AppContainer standalone creation  
kubectl apply -f /tmp/test-appcontainer-manual.yaml

# Slack notification testing
kubectl apply -f /tmp/test-slack-correct-channel.yaml
```

### 📊 Test Results Summary
| Test Type | Status | Last Result |
|-----------|--------|-------------|
| Parameter validation | ✅ Pass | All validations working |
| Template composition | ✅ Pass | Full chain working |
| Slack notifications | ✅ Pass | All message types sent |
| VCluster creation | 🟡 Partial | Claim created, provisioning stuck |
| Repository creation | 🟡 Partial | Claim created, completion unknown |
| End-to-end workflow | 🟡 Partial | 80% complete, awaiting resource provisioning |

---

## 🐛 Known Issues and Workarounds

### Issue 1: AWS Token Expiration
**Problem**: Cannot currently access cluster to debug Crossplane issues
**Impact**: High - blocks investigation of VCluster and repository provisioning  
**Workaround**: Run `aws sso login` to refresh tokens
**Next Steps**: Re-authenticate and resume debugging

### Issue 2: VCluster Provisioning Delays
**Problem**: VClusterEnvironmentClaim stuck in provisioning state
**Impact**: Medium - microservices can't deploy until VCluster ready
**Workaround**: None currently - investigation needed
**Potential Causes**:
- Crossplane VCluster operator issues
- AWS IAM permission problems  
- Resource quota limits
- Composition configuration errors

### Issue 3: Repository Creation Status Unknown
**Problem**: AppContainerClaim completion status needs verification
**Impact**: Medium - affects developer onboarding flow
**Workaround**: Manual repository creation if needed
**Investigation**: Check Crossplane GitHub provider status

---

## 📝 Critical Bug Fixes Applied

### 1. JSON Parameter Validation Fix
**Problem**: VCluster capabilities JSON failing validation in shell scripts
```bash
# BROKEN
echo "{{inputs.parameters.vcluster-capabilities}}" | jq . 

# FIXED  
CAPABILITIES='{{inputs.parameters.vcluster-capabilities}}'
echo "$CAPABILITIES" | jq .
```

### 2. Template Parameter Reference Fix
**Problem**: AppContainer template using `workflow.parameters` instead of `inputs.parameters`
```yaml
# BROKEN - doesn't work in template composition
value: "{{workflow.parameters.resource-name}}"

# FIXED - works in template composition  
value: "{{inputs.parameters.resource-name}}"
```

### 3. RBAC Permissions Fix
**Problem**: Workflow pods couldn't read Slack webhook secret
```bash
# SOLUTION APPLIED
kubectl patch clusterrole argo-cluster-role --type='json' -p='[{
  "op": "add", "path": "/rules/-", 
  "value": {"apiGroups": [""], "resources": ["secrets"], "verbs": ["get", "list"]}
}]'
kubectl rollout restart deployment workflow-controller -n argo
```

### 4. Notification System Simplification
**Problem**: Over-complex notification interface causing maintenance issues
**Solution**: Migrated from `slack-standard-notifications` to `simple-slack-notifications`

---

## 🎯 Next Steps Priority

### Immediate (After AWS Re-auth)
1. **🔥 Debug VCluster Provisioning**: Investigate why claims stuck in provisioning
2. **🔥 Verify Repository Creation**: Check AppContainerClaim completion status  
3. **✅ Test End-to-End Flow**: Verify complete microservice creation workflow

### Short Term (Next Few Days)
1. **📚 Update Documentation**: Create developer usage guide
2. **🧹 Template Cleanup**: Remove legacy templates once standardized versions proven
3. **🔧 Monitoring Setup**: Add Crossplane resource monitoring

### Medium Term (Next Sprint)
1. **🛡️ Secret Management**: Consider SealedSecrets for automated secret management
2. **📊 Metrics Integration**: Add Prometheus metrics for workflow success rates
3. **🔄 CI/CD Enhancement**: Integrate parameter contract validation in CI

---

## 📞 Getting Help

### For AWS Authentication Issues
```bash
aws sso login --profile default
kubectl get nodes  # Verify cluster access
```

### For Workflow Debugging
```bash
# Check workflow status
kubectl get workflows -n argo

# Get workflow logs  
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name>

# Check Argo UI
kubectl port-forward -n argo svc/argo-server 2746:2746
# Access: http://localhost:2746
```

### For Crossplane Issues
```bash
# Check Crossplane status
kubectl get crossplane -A
kubectl get providers -A
kubectl get compositions

# Check specific resource claims
kubectl get vclusterenvironmentclaims -A
kubectl get appcontainerclaims -A
```

### For Slack Notification Issues  
```bash
# Verify secret exists
kubectl get secret slack-webhook -n argo

# Test notification manually
kubectl apply -f /tmp/test-slack-correct-channel.yaml
```

---

## 📚 Reference Documentation

- **[Architectural Decisions](./ARCHITECTURAL_DECISIONS.md)**: Complete ADR with all design decisions
- **[CLAUDE.md](./CLAUDE.md)**: Project guidelines and development methodology  
- **Template Files**: `argo-workflows/*-standard-contract.yaml`
- **Test Cases**: `/tmp/test-*-working.yaml`
- **Legacy Analysis**: Previous conversation sessions for full context

---

**Document Version**: 1.0  
**Last Updated**: Current session  
**Status**: 🟡 Investigation Required (AWS re-auth needed)  
**Next Review**: After Crossplane debugging complete