# Developer Guide: VCluster with Explicit Component Selection

This guide shows developers how to create vClusters with explicit component selection using boolean flags.

## Available Components

When creating a vCluster, you can enable/disable these components:

| Component | Description | Default | Use Case |
|-----------|-------------|---------|----------|
| `argoCD` | GitOps deployment tool | `false` | Continuous deployment, application lifecycle |
| `grafana` | Metrics visualization | `false` | Dashboards, monitoring, debugging |
| `prometheus` | Metrics collection | `false` | Application metrics, alerting |
| `jaeger` | Distributed tracing | `false` | Request tracing, performance analysis |
| `kiali` | Service mesh observability | `false` | Service topology, traffic flow |
| `apiGateway` | AWS API Gateway integration | `false` | External API access, public endpoints |

## Basic Usage

### Minimal vCluster (just the cluster)
```yaml
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: basic-cluster
  namespace: default
spec:
  name: basic-env
  # All components default to false
  # This creates just the vCluster with no additional components
```

### vCluster with API Gateway only
```yaml
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: api-cluster
  namespace: default
spec:
  name: api-env
  components:
    apiGateway: true   # Enable external API access
    # All others remain false (default)
```

### Full observability stack
```yaml
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: monitoring-cluster
  namespace: default
spec:
  name: monitoring-env
  components:
    grafana: true      # Dashboards
    prometheus: true   # Metrics collection
    jaeger: true       # Distributed tracing
    kiali: true        # Service mesh visualization
    apiGateway: true   # External access to view dashboards
```

## Component Combinations

### Web Application Development
```yaml
spec:
  name: webapp-env
  components:
    grafana: true      # Monitor application performance
    prometheus: true   # Collect custom metrics
    apiGateway: true   # Expose web application
    argoCD: false      # Use direct deployment for development
    jaeger: false      # Skip tracing for simple apps
    kiali: false       # Skip service mesh for single app
```

### Microservices Development
```yaml
spec:
  name: microservices-env
  components:
    grafana: true      # Monitor multiple services
    prometheus: true   # Collect metrics from all services
    jaeger: true       # Trace requests across services
    kiali: true        # Visualize service communication
    apiGateway: true   # Single entry point for APIs
    argoCD: true       # Manage multiple service deployments
```

### Production Environment
```yaml
spec:
  name: production-env
  domain: api.mycompany.com
  components:
    grafana: true      # Production monitoring
    prometheus: true   # Production metrics
    argoCD: true       # GitOps deployments
    apiGateway: true   # Public API access
    jaeger: false      # Disable for performance (optional)
    kiali: false       # Disable UI for security (optional)
```

### CI/CD Testing
```yaml
spec:
  name: ci-test-env
  components:
    apiGateway: true   # Test API endpoints
    grafana: false     # Skip monitoring for short-lived tests
    prometheus: false  # Skip metrics for CI tests
    jaeger: false      # Skip tracing for CI tests
    kiali: false       # Skip visualization for CI tests
    argoCD: false      # Direct deployment in CI pipeline
```

## Component-Specific Configuration

### API Gateway Access
When you enable `apiGateway: true`, you get:
- AWS API Gateway HTTP API
- VPC Link for secure connectivity
- Public endpoint for external access
- Automatic routing to vCluster services

Access your API at: `https://{api-id}.execute-api.{region}.amazonaws.com/prod/`

### Monitoring Stack
When you enable the monitoring components:
- **Grafana**: Access dashboards via port-forward or ingress
- **Prometheus**: Metrics stored and queryable via PromQL
- **Jaeger**: Tracing UI for request flow analysis
- **Kiali**: Service mesh topology and health

### GitOps with ArgoCD
When you enable `argoCD: true`:
- ArgoCD server deployed in vCluster
- Sync applications from Git repositories
- Declarative application management
- Automated deployments and rollbacks

## Best Practices

### Development Environment
```yaml
# Enable everything for development visibility
components:
  grafana: true      # Debug performance issues
  prometheus: true   # Monitor resource usage
  jaeger: true       # Debug request flows
  kiali: true        # Understand service dependencies
  argoCD: true       # Practice GitOps workflows
  apiGateway: true   # Test external integrations
```

### Staging Environment
```yaml
# Production-like but with full debugging
components:
  grafana: true      # Monitor like production
  prometheus: true   # Same metrics as production
  argoCD: true       # Same deployment as production
  apiGateway: true   # Same external access as production
  jaeger: true       # Debug staging-specific issues
  kiali: false       # Reduce overhead, not needed for staging
```

### Production Environment
```yaml
# Minimal overhead, essential components only
components:
  grafana: true      # Essential monitoring
  prometheus: true   # Essential metrics
  argoCD: true       # Essential deployments
  apiGateway: true   # Essential external access
  jaeger: false      # Optional: reduce overhead
  kiali: false       # Optional: security consideration
```

## Component Dependencies

Some components work better together:

### Observability Stack
- `prometheus` + `grafana` = Complete metrics solution
- `jaeger` + `grafana` = Tracing with visualization
- `kiali` requires service mesh (Istio) which is included

### API Gateway Integration
- `apiGateway` works independently
- Combines well with `grafana` for API monitoring
- Works with `argoCD` for automated API deployments

## Status and Monitoring

After creating a vCluster, check component status:

```bash
# Check overall vCluster status
kubectl get vclusterenvironmentclaim my-cluster -o yaml

# Check component-specific status
kubectl get pods -n my-cluster-namespace
```

The status will show:
```yaml
status:
  ready: true
  components:
    grafana:
      ready: true
      endpoint: "http://grafana.my-cluster.svc.cluster.local:80"
    apiGateway:
      ready: true
      endpoint: "https://abc123.execute-api.us-east-1.amazonaws.com/prod"
```

## Resource Requirements

Estimated resource usage per component:

| Component | CPU Request | Memory Request | Notes |
|-----------|-------------|----------------|-------|
| vCluster (base) | 200m | 512Mi | Always included |
| argoCD | 250m | 512Mi | GitOps controller |
| grafana | 100m | 256Mi | Visualization only |
| prometheus | 500m | 1Gi | Metrics storage |
| jaeger | 200m | 512Mi | Tracing collector |
| kiali | 100m | 256Mi | Service mesh UI |
| apiGateway | 0 | 0 | AWS managed service |

**Total for full stack**: ~1.35 CPU, ~3Gi memory

## Troubleshooting

### Component Not Starting
```bash
# Check specific component status
kubectl describe vclusterenvironmentclaim my-cluster

# Check component pods
kubectl get pods -n my-cluster-namespace -l component=grafana
```

### API Gateway Not Accessible
```bash
# Check VPC Link status
kubectl get vclusterenvironmentclaim my-cluster -o jsonpath='{.status.apiGateway}'

# Verify EnvironmentConfig
kubectl get environmentconfigs
```

### Component Resource Issues
```bash
# Check resource usage
kubectl top pods -n my-cluster-namespace

# Check node capacity
kubectl describe nodes
```

## Migration Guide

### From Include Array (Old)
```yaml
# Old format (deprecated)
spec:
  include:
  - grafana
  - apiGatewaySupport
```

### To Component Flags (New)
```yaml
# New format (current)
spec:
  components:
    grafana: true
    apiGateway: true
    prometheus: false  # Explicitly disabled
```

This explicit approach makes it clear what components are available and what you're choosing to enable or disable.