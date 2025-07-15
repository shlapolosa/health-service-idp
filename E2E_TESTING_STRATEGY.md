# End-to-End Testing Strategy: Microservice Slash Command

## Overview

This document outlines the comprehensive end-to-end testing strategy for the microservice slash command functionality in the health-service-idp platform. The E2E test validates the complete flow from Slack command input to fully provisioned microservice environment with repositories, VCluster, and GitOps infrastructure.

## Test Objective

**Primary Goal**: Verify that a Slack slash command `/microservice create <name> <language> with <database>` successfully creates:
1. A running Argo workflow
2. A VCluster environment
3. An AppContainer with repositories
4. Source code repository with CLAUDE.md-compliant structure
5. GitOps repository with ArgoCD and OAM applications
6. Hello-world microservice in the microservices folder
7. Slack notifications throughout the process

## Architecture Overview

```mermaid
graph TD
    A[Slack /microservice command] --> B[Slack API Server]
    B --> C[CreateMicroserviceUseCase]
    C --> D[Argo Workflows API]
    D --> E[microservice-standard-contract]
    E --> F[appcontainer-standard-contract]
    F --> G[vcluster-standard-contract]
    G --> H[Crossplane VClusterEnvironmentClaim]
    F --> I[Crossplane AppContainerClaim]
    I --> J[GitHub Repositories]
    I --> K[GitOps Structure]
    E --> L[Slack Notifications]
    
    H --> M[VCluster Instance]
    J --> N[Source Repo with microservices/]
    K --> O[GitOps Repo with argocd/ and oam/]
```

## Components Under Test

### 1. Slack API Server
**Location**: `/slack-api-server/`
**Deployment**: `default` namespace
**Service**: `slack-api-server` (LoadBalancer via Istio)

**Key Components:**
- **Controllers**: `src/interface/controllers.py` - FastAPI endpoints
- **Use Cases**: `src/application/use_cases.py` - CreateMicroserviceUseCase
- **Dependencies**: `src/interface/dependencies.py` - Dependency injection
- **Argo Client**: `src/infrastructure/argo_client.py` - Workflow submission
- **Domain Models**: `src/domain/models.py` - MicroserviceRequest with to_argo_payload()

**Cluster Resources:**
```bash
kubectl get deployment slack-api-server -n default
kubectl get service slack-api-server -n default
kubectl get pods -l app=slack-api-server -n default
```

### 2. Argo Workflows Templates
**Location**: `/argo-workflows/`
**Namespace**: `argo`

**Template Chain:**
1. **microservice-standard-contract.yaml** - Entry point template
2. **appcontainer-standard-contract.yaml** - AppContainer orchestration
3. **vcluster-standard-contract.yaml** - VCluster provisioning
4. **simple-slack-notifications.yaml** - Notification system

**Cluster Resources:**
```bash
kubectl get workflowtemplate microservice-standard-contract -n argo
kubectl get workflowtemplate appcontainer-standard-contract -n argo
kubectl get workflowtemplate vcluster-standard-contract -n argo
kubectl get workflowtemplate simple-slack-notifications -n argo
```

### 3. Crossplane Resources
**Location**: `/crossplane/`
**Namespace**: `default` (claims), `crossplane-system` (compositions)

**Resource Types:**
- **VClusterEnvironmentClaim** - VCluster provisioning
- **AppContainerClaim** - Repository and GitOps setup
- **ApplicationClaim** - Microservice deployment

**Cluster Resources:**
```bash
kubectl get vclusterenvironmentclaim -n default
kubectl get appcontainerclaim -n default
kubectl get applicationclaim -n default
```

### 4. GitHub Repositories
**Organization**: `socrates12345`
**Repositories Created**:
- Source: `https://github.com/socrates12345/{service-name}`
- GitOps: `https://github.com/socrates12345/{service-name}-gitops`

**Expected Structure:**
```
source-repo/
├── CLAUDE.md
├── README.md
├── microservices/
│   ├── hello-world/
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── shared-libs/
├── .github/
│   └── workflows/
└── tests/

gitops-repo/
├── argocd/
│   └── applications/
├── oam/
│   └── components/
└── manifests/
```

## Test Scripts

### 1. Comprehensive E2E Test Script

**Location**: `/tmp/comprehensive-e2e-test.sh`

```bash
#!/bin/bash
# Comprehensive End-to-End Test for Microservice Slash Command

set -e

SLACK_API_URL="http://af433f091b55640038c23af3a641d716-112208284.us-west-2.elb.amazonaws.com"
GITHUB_ORG="socrates12345"
EXPECTED_SERVICE_NAME="test-e2e-service"
EXPECTED_VCLUSTER="test-e2e-vcluster"

# Test execution phases:
# 1. Cleanup previous test artifacts
# 2. Send Slack slash command
# 3. Monitor workflow execution
# 4. Verify VCluster creation
# 5. Verify AppContainer creation
# 6. Verify repository structure
# 7. Verify Slack notifications
```

### 2. Unit Test Scripts

**Location**: `/slack-api-server/tests/`

**Test Categories:**
- **Domain Models**: `test_domain_models.py` - MicroserviceRequest validation
- **Use Cases**: `test_application_use_cases.py` - CreateMicroserviceUseCase logic
- **Infrastructure**: `test_infrastructure_argo_client.py` - Argo API integration
- **Integration**: `test_api_endpoints.py` - FastAPI endpoint testing

**Run Tests:**
```bash
cd slack-api-server
poetry run pytest tests/ -v
```

## Message Flow & Data Transformation

### 1. Slack Command Input
```
/microservice create payment-service python with postgresql
```

### 2. Parsed Command Structure
```python
# In EnhancedNLPParser
{
    "action": "create",
    "microservice_name": "payment-service",
    "microservice_language": "python",
    "microservice_database": "postgresql",
    "microservice_cache": "none",
    "namespace": "default",
    "github_org": "socrates12345"
}
```

### 3. Domain Model Creation
```python
# In CreateMicroserviceUseCase
MicroserviceRequest(
    name="payment-service",
    namespace="default", 
    user="john.doe",
    slack_channel="C12345",
    language=MicroserviceLanguage.PYTHON,
    database=MicroserviceDatabase.POSTGRESQL,  # Note: "postgresql"
    cache=MicroserviceCache.NONE,
    # ... other fields
)
```

### 4. Argo Payload Generation
```python
# In MicroserviceRequest.to_argo_payload()
{
    "microservice-name": "payment-service",
    "namespace": "default",
    "language": "python",
    "database": "postgres",  # Mapped from "postgresql"
    "cache": "none",
    # ... other parameters
}
```

### 5. Standardized Contract Parameters
```yaml
# Passed to microservice-standard-contract template
parameters:
  # TIER 1: Universal
  - name: resource-name
    value: payment-service
  - name: resource-type
    value: microservice
  - name: namespace
    value: default
  - name: user
    value: john.doe
  
  # TIER 2: Platform  
  - name: security-enabled
    value: "true"
  - name: observability-enabled
    value: "true"
  - name: auto-create-dependencies
    value: "true"
  
  # TIER 3: Microservice-Specific
  - name: microservice-language
    value: python
  - name: microservice-database
    value: postgres
  - name: microservice-framework
    value: auto
```

### 6. Workflow Execution Flow
```
microservice-standard-contract
├── validate-parameters (validates all tiers)
├── notify-starting (Slack notification)
├── ensure-appcontainer
│   ├── determine-appcontainer-name
│   ├── create-appcontainer-if-needed
│   │   ├── validate-parameters
│   │   ├── notify-starting
│   │   ├── ensure-vcluster
│   │   │   ├── determine-vcluster-name
│   │   │   ├── create-vcluster-if-needed
│   │   │   │   ├── validate-parameters
│   │   │   │   ├── notify-starting
│   │   │   │   ├── create-vcluster-claim
│   │   │   │   ├── wait-for-vcluster-ready
│   │   │   │   └── notify-success
│   │   │   └── check-existing-vcluster
│   │   ├── create-appcontainer-claim
│   │   ├── wait-for-repositories
│   │   └── notify-success
│   └── check-existing-appcontainer
├── create-microservice-claim
├── wait-for-microservice-ready
├── extract-microservice-info
└── notify-success
```

### 7. Crossplane Resource Creation
```yaml
# VClusterEnvironmentClaim
apiVersion: vcluster.platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: payment-vcluster
spec:
  environmentType: development
  capabilities:
    observability: true
    security: true
    gitops: true

# AppContainerClaim  
apiVersion: platform.example.org/v1alpha1
kind: AppContainerClaim
metadata:
  name: payment-app
spec:
  description: "AppContainer for microservice payment-service"
  gitHubOrg: socrates12345
  vclusterName: payment-vcluster

# ApplicationClaim
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: payment-service
spec:
  language: python
  framework: fastapi
  database: postgres
```

## Monitoring & Verification

### 1. Workflow Monitoring
```bash
# List recent workflows
kubectl get workflows -n argo --sort-by=.metadata.creationTimestamp

# Monitor specific workflow
kubectl get workflow <workflow-name> -n argo -w

# Check workflow logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name>
```

### 2. Resource Status Checks
```bash
# Check VCluster status
kubectl get vclusterenvironmentclaim -n default
kubectl describe vclusterenvironmentclaim <vcluster-name>

# Check AppContainer status  
kubectl get appcontainerclaim -n default -o yaml

# Check Application status
kubectl get applicationclaim -n default
```

### 3. Repository Verification
```bash
# Check repository existence
curl -s "https://api.github.com/repos/socrates12345/<repo-name>"

# Check repository structure
curl -s "https://api.github.com/repos/socrates12345/<repo-name>/contents/microservices"
curl -s "https://api.github.com/repos/socrates12345/<repo-name>/contents/CLAUDE.md"
```

### 4. Slack Notification Testing
```bash
# Test webhook directly
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test notification"}' \
  "https://hooks.slack.com/services/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"
```

## Expected Outcomes

### ✅ Success Criteria

1. **Slack Response**: HTTP 200 with JSON response containing creation started message
2. **Workflow Creation**: Workflow created in `argo` namespace with correct labels
3. **Workflow Completion**: Workflow reaches `Succeeded` phase within 15 minutes
4. **VCluster Ready**: VClusterEnvironmentClaim shows `Ready: True` status
5. **AppContainer Ready**: AppContainerClaim shows `ready: true` status
6. **Repository Structure**: 
   - Source repo exists with CLAUDE.md, microservices/, .github/
   - Hello-world microservice in microservices/hello-world/
   - GitOps repo exists with argocd/ and oam/ directories
7. **Slack Notifications**: At least 3 notifications sent (starting, progress, success)

### ❌ Failure Scenarios

1. **Slack API Error**: Non-200 response or error message
2. **Workflow Failure**: Workflow enters `Failed` phase
3. **Template Not Found**: Cannot find workflow template
4. **Parameter Validation**: Invalid parameter values cause validation failure
5. **Crossplane Timeout**: Resources not provisioned within timeout
6. **Repository Creation**: Repositories not created or missing structure
7. **Notification Failure**: Slack webhook returns non-200 response

## Test Environment Requirements

### Prerequisites
- EKS cluster with Argo Workflows installed
- Crossplane with VCluster and AppContainer compositions
- Slack API server deployed and configured
- GitHub access for repository creation
- Slack webhook configured and tested

### Environment Variables
```bash
export SLACK_API_URL="http://af433f091b55640038c23af3a641d716-112208284.us-west-2.elb.amazonaws.com"
export GITHUB_ORG="socrates12345"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"
```

### Cluster Access
```bash
# Verify cluster access
kubectl cluster-info

# Verify namespace access
kubectl get ns argo default crossplane-system

# Verify Argo Workflows
kubectl get workflowtemplates -n argo

# Verify Crossplane
kubectl get compositions
```

## Debugging & Troubleshooting

### Common Issues

1. **Template Resolution Errors**
   - Check template exists: `kubectl get workflowtemplate <name> -n argo`
   - Verify template references in other templates

2. **Parameter Validation Failures**
   - Check parameter names match template definitions
   - Verify tier-specific parameter validation

3. **Crossplane Resource Issues**
   - Check compositions: `kubectl get compositions`
   - Verify CRDs: `kubectl get crds | grep platform`

4. **Secret/Authentication Issues**
   - Check Slack signing secret: `kubectl get secret slack-credentials -n default`
   - Verify GitHub token: `kubectl get secret github-credentials -n default`

### Debug Commands
```bash
# Get workflow details
kubectl describe workflow <workflow-name> -n argo

# Check workflow logs
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> --tail=50

# Check Slack API server logs
kubectl logs -l app=slack-api-server -n default --tail=50

# Check Crossplane logs
kubectl logs -n crossplane-system -l app=crossplane --tail=50
```

## Test Execution

### Manual Execution
```bash
# Make script executable
chmod +x /tmp/comprehensive-e2e-test.sh

# Run test
./tmp/comprehensive-e2e-test.sh
```

### Automated Execution
```bash
# Run as part of CI/CD
# Add to .github/workflows/e2e-test.yml
```

### Test Data Cleanup
```bash
# Clean up test resources
kubectl delete workflows -l test=e2e -n argo
kubectl delete vclusterenvironmentclaim -l test=e2e -n default
kubectl delete appcontainerclaim -l test=e2e -n default
```

## Success Metrics

### Quantitative Metrics
- **Response Time**: Slack API response < 2 seconds
- **Workflow Duration**: Complete workflow < 15 minutes
- **Repository Creation**: < 5 minutes after workflow start
- **VCluster Ready**: < 10 minutes after claim creation
- **Success Rate**: > 95% test pass rate

### Qualitative Metrics
- **Structure Compliance**: CLAUDE.md present and correct
- **GitOps Structure**: ArgoCD and OAM applications properly structured
- **Notification Quality**: Clear, informative Slack messages
- **Error Handling**: Meaningful error messages for failures

This comprehensive testing strategy ensures all components of the microservice slash command functionality work together correctly in an end-to-end scenario.