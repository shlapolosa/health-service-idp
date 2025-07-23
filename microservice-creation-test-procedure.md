# Microservice Creation Test Procedure

This document outlines the comprehensive test procedure for validating microservice creation through the Slack API server, including monitoring steps for Crossplane job completion and infrastructure provisioning.

## Prerequisites

### Environment Setup
- Host Kubernetes cluster context active
- Sufficient node capacity (check with `kubectl top nodes`)
- Istio ingress gateway accessible
- Slack API server deployed and responsive

### Required Tools
```bash
kubectl
curl
```

### CRITICAL: Provider Restart Requirement
**⚠️ Important**: Due to known Crossplane provider idle behavior, both Kubernetes and GitHub providers must be restarted before each test to ensure proper resource processing.

```bash
# Automated restart script (recommended)
./scripts/restart-crossplane-providers.sh

# Or restart specific providers manually:
./scripts/restart-crossplane-providers.sh kubernetes
./scripts/restart-crossplane-providers.sh github

# Manual alternative (if script not available):
kubectl delete pod -n crossplane-system -l pkg.crossplane.io/provider=provider-kubernetes
kubectl delete pod -n crossplane-system -l pkg.crossplane.io/provider=provider-upjet-github

# Wait for providers to restart (30-60 seconds)
kubectl get pods -n crossplane-system | grep provider
```

**Expected Result**: Both providers show `1/1 Running` status before proceeding with test.

**Why This Is Necessary**: Providers exhibit "one-shot" behavior where they process initial resources then go idle. Manual restart ensures they will actively process new AppContainerClaim resources during the test.

## Test Procedure

### Phase 1: Pre-Creation Validation

#### 1.1 Node Capacity Check
```bash
kubectl top nodes
```
**Expected Result**: At least one node with available CPU/memory capacity

#### 1.2 Get Istio Ingress URL
```bash
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```
**Expected Result**: AWS ELB hostname returned

#### 1.3 Verify Slack API Server Health
```bash
curl -X GET "http://<ISTIO_INGRESS_URL>/health"
```
**Expected Result**: HTTP 200 with health status

### Phase 2: Microservice Creation

#### 2.1 Create Microservice via API
```bash
curl -X POST "http://<ISTIO_INGRESS_URL>/slack/command" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "command=/microservice&text=create <SERVICE_NAME>"
```

**Expected Response Structure**:
```json
{
  "response_type": "in_channel",
  "text": "🚀 Microservice `<SERVICE_NAME>` creation started",
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🚀 Microservice Creation Started"}
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Name:*\n`<SERVICE_NAME>`"},
        {"type": "mrkdwn", "text": "*Language:*\nPython"},
        {"type": "mrkdwn", "text": "*GitHub Org:*\nshlapolosa"}
      ]
    }
  ]
}
```

#### 2.2 Verify Argo Workflow Creation
```bash
kubectl get workflows -n argo --sort-by='.metadata.creationTimestamp' | tail -5
```
**Expected Result**: New workflow with `microservice-creation-*` name in Running state

### Phase 3: AppContainerClaim Monitoring

#### 3.1 Monitor AppContainerClaim Creation
```bash
# Check every 30 seconds
kubectl get appcontainerclaims | grep <SERVICE_NAME>
```

**Expected Progression**:
- Initial: Not found
- After 1-2 minutes: `SYNCED: True, READY: False`
- After 5-10 minutes: `SYNCED: True, READY: True`

#### 3.2 Monitor Managed Resources
```bash
kubectl get managed --all-namespaces | grep <SERVICE_NAME>
```

**Expected Resources** (should appear within 2-3 minutes):
- `release.helm.crossplane.io/<SERVICE_NAME>-postgres` - PostgreSQL Helm release
- `release.helm.crossplane.io/<SERVICE_NAME>-redis` - Redis Helm release  
- `repository.repo.github.upbound.io/<SERVICE_NAME>-source-repo` - Source repository
- `repository.repo.github.upbound.io/<SERVICE_NAME>-gitops-repo` - GitOps repository
- Multiple `object.kubernetes.crossplane.io/<SERVICE_NAME>-*` - Job and resource objects

### Phase 4: Job Status Monitoring

#### 4.1 Monitor Individual Job Status

**Core Jobs to Monitor**:

| Job Name | Purpose | Expected Duration | Monitoring Command |
|----------|---------|-------------------|-------------------|
| `<SERVICE_NAME>-source-setup` | Source repository structure creation | 1-2 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-source-setup` |
| `<SERVICE_NAME>-gitops-creator` | GitOps repository population | 1-2 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-gitops-creator` |
| `<SERVICE_NAME>-microservice-creator` | Microservice structure creation | 2-3 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-microservice-creator` |
| `<SERVICE_NAME>-secrets-setup` | Secrets configuration | 1-2 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-secrets-setup` |
| `<SERVICE_NAME>-gitops-setup` | GitOps templates (critical for heredoc fix) | 2-3 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-gitops-setup` |
| `<SERVICE_NAME>-oam-updater` | OAM application creation | 1-2 minutes | `kubectl describe object.kubernetes.crossplane.io/<SERVICE_NAME>-oam-updater` |

#### 4.2 Job Status Check Script
```bash
#!/bin/bash
SERVICE_NAME="$1"

echo "=== Job Status Check for $SERVICE_NAME ==="
for job in source-setup gitops-creator microservice-creator secrets-setup gitops-setup oam-updater; do 
  echo -n "$SERVICE_NAME-$job: "
  kubectl get object.kubernetes.crossplane.io/$SERVICE_NAME-$job -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null && echo " ($(kubectl get object.kubernetes.crossplane.io/$SERVICE_NAME-$job -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' 2>/dev/null))" || echo "Not Ready/Not Found"
done
```

**Usage**: `./check-jobs.sh <SERVICE_NAME>`

#### 4.3 Expected Job Progression

**Minutes 0-2**: Jobs created as managed objects
```bash
kubectl get managed | grep <SERVICE_NAME> | grep Job | wc -l
# Expected: 6-8 jobs
```

**Minutes 2-5**: Jobs start executing
```bash
kubectl get jobs --all-namespaces | grep <SERVICE_NAME>
# Expected: Actual Job resources appear
```

**Minutes 5-10**: Jobs complete successfully
```bash
kubectl get jobs --all-namespaces | grep <SERVICE_NAME> | grep Complete
# Expected: All jobs show "Complete" status
```

### Phase 5: Infrastructure Validation

#### 5.1 Database Infrastructure
```bash
# Check PostgreSQL
kubectl get pods -n <SERVICE_NAME> | grep postgres
# Expected: 1/1 or 2/2 Running

# Check Redis  
kubectl get pods -n <SERVICE_NAME> | grep redis
# Expected: 1/1 or 2/2 Running
```

#### 5.2 Namespace Creation
```bash
kubectl get namespaces | grep <SERVICE_NAME>
```
**Expected Namespaces**:
- `<SERVICE_NAME>` - Main application namespace
- `<SERVICE_NAME>-realtime` - Real-time processing components

#### 5.3 GitHub Repository Validation
```bash
# Check repository managed resources
kubectl get repository.repo.github.upbound.io | grep <SERVICE_NAME>
```
**Expected Output**:
- `<SERVICE_NAME>-source-repo`: READY: True
- `<SERVICE_NAME>-gitops-repo`: READY: True

### Phase 6: Application Deployment Validation

#### 6.1 OAM Application Check
```bash
kubectl get applications.core.oam.dev -n <SERVICE_NAME>
```
**Expected**: OAM Application resource created

#### 6.2 ArgoCD Application Check  
```bash
kubectl get applications.argoproj.io -n argocd | grep <SERVICE_NAME>
```
**Expected**: ArgoCD Application(s) for the service

#### 6.3 Knative Service Validation
```bash
kubectl get ksvc -n <SERVICE_NAME>
```
**Expected**: Knative Service deployed and ready

### Phase 7: End-to-End Validation

#### 7.1 Final Status Check
```bash
kubectl get appcontainerclaims <SERVICE_NAME> -o yaml
```

**Expected Final State**:
```yaml
status:
  conditions:
  - type: Synced
    status: "True"
  - type: Ready  
    status: "True"
  sourceRepository:
    url: "https://github.com/shlapolosa/<SERVICE_NAME>"
    cloneUrl: "https://github.com/shlapolosa/<SERVICE_NAME>.git"
  gitopsRepository:
    url: "https://github.com/shlapolosa/<SERVICE_NAME>-gitops"
    cloneUrl: "https://github.com/shlapolosa/<SERVICE_NAME>-gitops.git"
```

#### 7.2 Service Accessibility Test
```bash
# Get Knative service URL
kubectl get ksvc <SERVICE_NAME> -n <SERVICE_NAME> -o jsonpath='{.status.url}'

# Test health endpoint
curl -X GET "<SERVICE_URL>/health"
```
**Expected**: HTTP 200 with service health status

## Troubleshooting

### Common Issues and Solutions

#### Issue: Jobs Stuck in CrashLoopBackOff
**Symptoms**: 
```bash
kubectl get jobs --all-namespaces | grep <SERVICE_NAME>
# Shows jobs in Failed state
```

**Diagnosis**:
```bash
kubectl logs jobs/<SERVICE_NAME>-gitops-setup --tail=20
```

**Common Errors**:
- `/bin/sh: kind:: not found` - Heredoc syntax error (should be fixed in composition)
- Authentication errors - Check GitHub credentials

#### Issue: AppContainerClaim Stuck in "Waiting"  
**Symptoms**:
```bash
kubectl get appcontainerclaims <SERVICE_NAME>
# Shows READY: False for extended period
```

**Diagnosis**:
```bash
kubectl describe appcontainerclaims <SERVICE_NAME>
# Check events and conditions
```

#### Issue: No Knative Service Created
**Symptoms**:
```bash  
kubectl get ksvc -n <SERVICE_NAME>
# No resources found
```

**Root Cause**: Usually indicates GitOps pipeline failure
**Check**: ArgoCD Application sync status

## Success Criteria

### ✅ Complete Success Indicators

1. **All Jobs Complete**: 6/6 core jobs show "Complete" status
2. **AppContainerClaim Ready**: `SYNCED: True, READY: True`  
3. **Infrastructure Running**: PostgreSQL and Redis pods running
4. **Repositories Created**: Both source and GitOps repos accessible
5. **GitOps Pipeline Active**: ArgoCD applications syncing
6. **Service Deployed**: Knative service responding to health checks
7. **No Failed Resources**: All managed resources in ready state

### ⚠️ Partial Success Indicators

- Jobs completed but Knative service not deployed
- Infrastructure ready but GitOps pipeline incomplete
- Repositories created but application not accessible

### ❌ Failure Indicators

- Jobs stuck in CrashLoopBackOff after 10 minutes
- AppContainerClaim remains in "Waiting" state after 15 minutes  
- Multiple managed resources showing "False" ready status
- GitHub repository creation failures

## Test Automation

### Automated Test Script
```bash
#!/bin/bash
SERVICE_NAME="$1"
TIMEOUT=600  # 10 minutes

if [ -z "$SERVICE_NAME" ]; then
  echo "Usage: $0 <service-name>"
  exit 1
fi

echo "🧪 Starting microservice creation test for: $SERVICE_NAME"

# Phase 1: Create microservice
echo "📤 Creating microservice..."
INGRESS_URL=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl -X POST "http://$INGRESS_URL/slack/command" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "command=/microservice&text=create $SERVICE_NAME"

# Phase 2: Monitor completion
echo "⏳ Monitoring job completion..."
end_time=$((SECONDS + TIMEOUT))

while [ $SECONDS -lt $end_time ]; do
  if kubectl get appcontainerclaims $SERVICE_NAME -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' | grep -q "True"; then
    echo "✅ AppContainerClaim ready!"
    break
  fi
  echo "⏳ Still waiting... ($(( (end_time - SECONDS) / 60 )) minutes remaining)"
  sleep 30
done

# Phase 3: Validate results
echo "🔍 Final validation..."
kubectl get appcontainerclaims $SERVICE_NAME
kubectl get ksvc -n $SERVICE_NAME
echo "🎉 Test completed for $SERVICE_NAME"
```

This comprehensive test procedure ensures thorough validation of the microservice creation process and provides clear monitoring steps for each phase of the deployment.