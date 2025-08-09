# OAM vCluster Architecture Test Plan

## Test Objectives
Incrementally verify and fix the OAM-driven vCluster infrastructure architecture, ensuring each component works before proceeding to the next.

## Prerequisites Checklist
```bash
# Run these checks before starting tests
kubectl get crd releases.helm.crossplane.io  # Crossplane Helm provider
kubectl get crd applications.core.oam.dev    # OAM CRDs
kubectl get deployment -n vela-system        # KubeVela
kubectl get deployment -n argocd             # ArgoCD
kubectl get deployment -n argo               # Argo Workflows
```

---

## Phase 1: Foundation Components (Host Cluster)

### Test 1.1: Verify Crossplane Helm Provider
**Objective**: Ensure Crossplane can create Helm releases

```bash
# Check if provider-helm is installed
kubectl get provider.pkg.crossplane.io

# Check if ProviderConfig exists
kubectl get providerconfig.helm.crossplane.io

# Test creating a simple Helm release
cat <<EOF | kubectl apply -f -
apiVersion: helm.crossplane.io/v1beta1
kind: Release
metadata:
  name: test-nginx
  namespace: default
spec:
  forProvider:
    chart:
      name: nginx
      repository: https://charts.bitnami.com/bitnami
      version: "13.2.34"
    namespace: test-helm
    values:
      service:
        type: ClusterIP
  providerConfigRef:
    name: default
EOF

# Verify release created
kubectl get release.helm.crossplane.io test-nginx
kubectl get pods -n test-helm

# Cleanup
kubectl delete release.helm.crossplane.io test-nginx
```

**Expected**: Helm release created successfully
**Fix if fails**: 
- Install/configure provider-helm
- Check ProviderConfig named "default" exists

### Test 1.2: Verify OAM ComponentDefinitions
**Objective**: Ensure PostgreSQL and Redis ComponentDefinitions work

```bash
# Apply ComponentDefinitions
kubectl apply -f crossplane/oam/postgresql-componentdefinition.yaml
kubectl get componentdefinition postgresql

# Check existing Redis ComponentDefinition
kubectl get componentdefinition redis

# List all ComponentDefinitions
kubectl get componentdefinition -A
```

**Expected**: Both ComponentDefinitions exist
**Fix if fails**:
- Check KubeVela is running
- Verify CRDs are installed

---

## Phase 2: vCluster Creation and Configuration

### Test 2.1: Create Test vCluster
**Objective**: Create a vCluster with proper syncer configuration

```bash
# Create a test vCluster claim
cat <<EOF | kubectl apply -f -
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: test-infra
  namespace: default
spec:
  name: test-infra
  components:
    argoCD: false  # Start simple
    istio: false
    knativeServing: false
    prometheus: false
    grafana: false
EOF

# Monitor creation
kubectl get vclusterenvironmentclaim test-infra -w

# Wait for vCluster to be ready (this may take 5-10 minutes)
kubectl wait --for=condition=ready vclusterenvironmentclaim test-infra --timeout=600s

# Check if vCluster pod is running
kubectl get pods -n test-infra | grep vcluster

# Check if kubeconfig secret exists
kubectl get secret vc-test-infra-vcluster -n test-infra
```

**Expected**: vCluster created and ready
**Fix if fails**:
- Check Crossplane compositions
- Review vCluster logs: `kubectl logs -n test-infra -l app=vcluster`

### Test 2.2: Verify vCluster Syncer Configuration
**Objective**: Ensure HelmRelease sync is configured

```bash
# Connect to vCluster
vcluster connect test-infra-vcluster -n test-infra

# In another terminal, check syncer config
kubectl get cm vcluster-config -n test-infra -o yaml | grep -A 10 "helm.crossplane.io"

# Check if CRDs are synced to vCluster
kubectl get crd | grep "helm.crossplane.io"
```

**Expected**: HelmRelease CRD visible in vCluster
**Fix if fails**:
- Update vCluster values in composition
- Recreate vCluster with new config

---

## Phase 3: OAM Application with Infrastructure

### Test 3.1: Deploy Simple OAM Application with PostgreSQL
**Objective**: Test infrastructure provisioning via OAM

```bash
# Create test OAM application
cat <<EOF | kubectl apply -f -
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: test-postgres-only
  namespace: default
spec:
  components:
  - name: test-db
    type: postgresql
    properties:
      name: test-db
      database: testdb
      auth:
        username: testuser
        password: testpass123
        postgresPassword: adminpass123
      storage: 1Gi
      storageClass: gp2
      resources:
        cpu: 100m
        memory: 128Mi
        cpuLimit: 200m
        memoryLimit: 256Mi
      metrics: false
EOF

# Check if Helm release is created
kubectl get release.helm.crossplane.io -A | grep test-db

# Check if PostgreSQL pods are running
kubectl get pods -n default | grep test-db

# Connect to vCluster and check if resources are visible
vcluster connect test-infra-vcluster -n test-infra -- kubectl get pods -n default
```

**Expected**: PostgreSQL deployed and accessible
**Fix if fails**:
- Check ComponentDefinition CUE template
- Verify Crossplane provider-helm is working
- Check vCluster syncer logs

### Test 3.2: Test Database Connectivity
**Objective**: Verify database is accessible

```bash
# Test from host cluster
kubectl run pg-test --image=postgres:14 --rm -it --restart=Never -- \
  psql "postgresql://testuser:testpass123@test-db-postgresql.default.svc.cluster.local:5432/testdb" -c "SELECT 1"

# Test from vCluster
vcluster connect test-infra-vcluster -n test-infra -- \
  kubectl run pg-test --image=postgres:14 --rm -it --restart=Never -- \
  psql "postgresql://testuser:testpass123@test-db-postgresql.default.svc.cluster.local:5432/testdb" -c "SELECT 1"
```

**Expected**: Both connections succeed
**Fix if fails**:
- Check service DNS resolution
- Verify network policies
- Check vCluster service sync

---

## Phase 4: ArgoCD Integration

### Test 4.1: Register vCluster with ArgoCD
**Objective**: Ensure ArgoCD can target vCluster

```bash
# Run registration script
./scripts/register-vcluster-argocd.sh test-infra test-infra test-app

# Verify cluster secret created
kubectl get secret test-infra-cluster -n argocd

# Check ArgoCD knows about the cluster
argocd cluster list

# Or via kubectl
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=cluster
```

**Expected**: vCluster registered as ArgoCD cluster
**Fix if fails**:
- Check script permissions
- Verify ArgoCD is running
- Check service account creation in vCluster

### Test 4.2: Deploy via ArgoCD to vCluster
**Objective**: Test ArgoCD deployment to vCluster

```bash
# Create simple ArgoCD app targeting vCluster
cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: test-vcluster-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps
    targetRevision: HEAD
    path: guestbook
  destination:
    name: test-infra  # The registered vCluster
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF

# Check sync status
kubectl get application test-vcluster-app -n argocd

# Verify deployment in vCluster
vcluster connect test-infra-vcluster -n test-infra -- kubectl get all -n default
```

**Expected**: Application deployed to vCluster
**Fix if fails**:
- Check ArgoCD cluster secret config
- Verify network connectivity
- Check RBAC permissions

---

## Phase 5: Full Integration Test

### Test 5.1: Complete Slack Workflow Simulation
**Objective**: Test the entire flow from Slack command

```bash
# Simulate Slack command by triggering Argo Workflow
cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: test-full-integration
  namespace: argo
spec:
  serviceAccountName: argo-workflow-executor
  entrypoint: test-flow
  templates:
  - name: test-flow
    steps:
    - - name: create-app
        templateRef:
          name: appcontainer-standard-contract
          template: create-appcontainer
        arguments:
          parameters:
          - name: resource-name
            value: "integration-test"
          - name: resource-type
            value: "appcontainer"
          - name: namespace
            value: "default"
          - name: user
            value: "test-user"
          - name: github-org
            value: "shlapolosa"
          - name: docker-registry
            value: "docker.io/socrates12345"
EOF

# Monitor workflow
kubectl get workflow -n argo -w
argo logs -n argo test-full-integration
```

**Expected**: Complete workflow executes successfully
**Fix if fails**:
- Check each workflow step
- Verify GitHub permissions
- Check Crossplane claim processing

### Test 5.2: Verify End-to-End Infrastructure
**Objective**: Confirm all components working together

```bash
# Check all resources created
echo "=== Host Cluster ==="
kubectl get applicationclaim
kubectl get vclusterenvironmentclaim
kubectl get release.helm.crossplane.io
kubectl get application.core.oam.dev

echo "=== vCluster ==="
vcluster list
vcluster connect test-infra-vcluster -n test-infra -- kubectl get all -A

echo "=== ArgoCD ==="
kubectl get application -n argocd
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=cluster

echo "=== Verify Connectivity ==="
# Test app can reach database
vcluster connect test-infra-vcluster -n test-infra -- \
  kubectl run test-connectivity --image=busybox --rm -it --restart=Never -- \
  nc -zv test-db-postgresql.default.svc.cluster.local 5432
```

**Expected**: All components present and connected
**Fix if fails**:
- Review each component's logs
- Check network policies
- Verify DNS resolution

---

## Phase 6: Cleanup

```bash
# Delete test resources in reverse order
kubectl delete workflow -n argo test-full-integration
kubectl delete application -n argocd test-vcluster-app
kubectl delete application.core.oam.dev test-postgres-only
kubectl delete vclusterenvironmentclaim test-infra

# Wait for cleanup
sleep 30

# Verify cleanup
kubectl get all -n test-infra
kubectl get release.helm.crossplane.io | grep test
```

---

## Troubleshooting Guide

### Common Issues and Fixes

1. **vCluster won't start**
   - Check node resources: `kubectl top nodes`
   - Review composition logs: `kubectl logs -n crossplane-system deploy/crossplane`

2. **Helm releases not syncing**
   - Verify syncer config includes helm.crossplane.io
   - Check RBAC in vCluster namespace
   - Review syncer logs: `kubectl logs -n test-infra -l app=vcluster -c syncer`

3. **ArgoCD can't reach vCluster**
   - Verify service DNS resolution
   - Check bearer token validity
   - Test with insecure TLS first

4. **OAM not processing**
   - Check KubeVela controller: `kubectl logs -n vela-system deploy/kubevela-vela-core`
   - Verify ComponentDefinitions loaded
   - Check application controller logs

5. **Database connection fails**
   - Verify service exists: `kubectl get svc | grep postgresql`
   - Check credentials in secrets
   - Test DNS from pod: `nslookup test-db-postgresql.default.svc.cluster.local`

---

## Success Criteria

✅ All tests pass in sequence
✅ Infrastructure accessible from vCluster apps
✅ ArgoCD deploys to correct cluster
✅ OAM processes in correct context
✅ Resources properly isolated
✅ Cleanup removes all resources

## Next Steps After Testing

1. Document any fixes needed
2. Update architecture if changes required
3. Create runbook for operations
4. Set up monitoring and alerts
5. Plan production rollout