# Semantic Versioning GitOps Implementation

This document describes the semantic versioning strategy implemented for the Visual Architecture Tool microservices.

## 🏷️ Versioning Strategy

### Semantic Version Format
```
MAJOR.MINOR.PATCH+COMMIT_SHA
```

**Examples:**
- `1.1.8+90d5b54` - Production release
- `1.2.0-develop+abc1234` - Development branch
- `1.1.9-feature-auth+def5678` - Feature branch

### Version Components

1. **MAJOR**: Incremented for breaking changes
2. **MINOR**: Incremented for new features
3. **PATCH**: Auto-incremented based on commit count
4. **COMMIT_SHA**: Short 7-character commit hash
5. **BRANCH**: Added as pre-release identifier for non-main branches

## 📦 Container Tagging Strategy

Each container build generates multiple tags:

### Release Branches (main, master, release/*)
```bash
# Full semantic version with commit SHA
docker.io/socrates12345/service:1.1.8+90d5b54

# Short commit SHA (primary deployment tag)
docker.io/socrates12345/service:90d5b54

# Branch with commit SHA
docker.io/socrates12345/service:main-90d5b54

# Latest tag
docker.io/socrates12345/service:latest

# Major version tag
docker.io/socrates12345/service:1

# Minor version tag
docker.io/socrates12345/service:1.1
```

### Development Branches
```bash
# Full semantic version with branch prefix
docker.io/socrates12345/service:1.1.8-develop+abc1234

# Short commit SHA
docker.io/socrates12345/service:abc1234

# Branch with commit SHA
docker.io/socrates12345/service:develop-abc1234

# Develop tag (for develop branch only)
docker.io/socrates12345/service:develop
```

### Feature Branches
```bash
# Full semantic version with sanitized branch name
docker.io/socrates12345/service:1.1.8-feature-auth+def5678

# Short commit SHA
docker.io/socrates12345/service:def5678

# Branch with commit SHA
docker.io/socrates12345/service:feature-auth-def5678
```

## 🔄 GitOps Integration

### Automated Workflow

1. **Code Push** → Detects changed services
2. **Version Generation** → Creates semantic version
3. **Container Build** → Builds with rich metadata
4. **Registry Push** → Pushes all semantic tags
5. **Manifest Update** → Updates OAM applications
6. **Deployment** → Deploys to vcluster with version tracking

### Metadata Labels

Each container includes comprehensive metadata:

```yaml
labels:
  # OpenContainers standard labels
  org.opencontainers.image.version: "1.1.8+90d5b54"
  org.opencontainers.image.revision: "90d5b54abc123..."
  org.opencontainers.image.source: "https://github.com/shlapolosa/health-service-idp"
  org.opencontainers.image.created: "2025-07-05T08:40:04Z"
  org.opencontainers.image.title: "streamlit-frontend"
  org.opencontainers.image.description: "Visual Architecture Tool - streamlit-frontend"
  
  # Custom versioning labels
  version: "1.1.8+90d5b54"
  commit: "90d5b54abc123..."
  commit-short: "90d5b54"
  branch: "main"
  service: "streamlit-frontend"
  build-date: "2025-07-05T08:40:04Z"
  build-number: "42"
  workflow-run: "12345"
```

### Kubernetes Metadata

OAM Applications and Knative Services include version tracking:

```yaml
metadata:
  labels:
    version: "1.1.8+90d5b54"
    semantic-version: "1.1.8"
    commit-sha: "90d5b54"
  annotations:
    semantic-version.gitops/enabled: "true"
    semantic-version.gitops/version: "1.1.8+90d5b54"
    semantic-version.gitops/commit: "90d5b54"
    deployment.kubernetes.io/revision: "1625485204"
```

## 🛠️ Version Management Commands

### Using the Version Manager Script

```bash
# Generate semantic version for a service
.github/scripts/version-manager.sh version streamlit-frontend
# Output: 1.1.8+90d5b54

# Generate all container tags
.github/scripts/version-manager.sh tags streamlit-frontend
# Output: comma-separated list of all tags

# Update OAM applications with new version
.github/scripts/version-manager.sh update-oam streamlit-frontend

# Create version summary
.github/scripts/version-manager.sh summary streamlit-frontend

# Increment major version (creates breaking change)
.github/scripts/version-manager.sh increment-major

# Increment minor version (adds new features)
.github/scripts/version-manager.sh increment-minor
```

### Manual Version Management

Update the base version in `.version` file:
```bash
# Current: 1.1
echo "2.0" > .version  # Next major version
echo "1.2" > .version  # Next minor version
```

## 🔍 Version Tracking and Debugging

### Finding Current Versions

```bash
# Check deployed service version
kubectl get ksvc streamlit-frontend -o jsonpath='{.metadata.labels.version}'

# Check pod version
kubectl get pods -l app=streamlit-frontend -o jsonpath='{.items[0].metadata.labels.version}'

# Check container image version
kubectl get pods -l app=streamlit-frontend -o jsonpath='{.items[0].spec.containers[0].image}'

# Get all version metadata
kubectl get ksvc streamlit-frontend -o yaml | grep -E "(version|commit|semantic)"
```

### Version History

```bash
# List all available tags for a service
curl -s https://registry.hub.docker.com/v2/repositories/socrates12345/streamlit-frontend/tags/ | jq '.results[].name'

# Get container metadata
docker inspect socrates12345/streamlit-frontend:90d5b54 | jq '.[0].Config.Labels'
```

## 🚀 Deployment Strategies

### Rolling Deployments

Knative automatically handles rolling deployments with version tracking:

```bash
# Current deployment
kubectl get revisions -l serving.knative.dev/service=streamlit-frontend

# Rollback to previous version
kubectl patch ksvc streamlit-frontend --type='merge' -p='{"spec":{"template":{"metadata":{"name":"streamlit-frontend-rollback"}}}}'
```

### Blue-Green Deployments

Use version tags for blue-green deployments:

```bash
# Deploy new version to staging
kubectl apply -f - <<EOF
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: streamlit-frontend-staging
spec:
  template:
    metadata:
      labels:
        version: "1.2.0+abc1234"
    spec:
      containers:
      - image: socrates12345/streamlit-frontend:abc1234
EOF

# Switch traffic after validation
kubectl patch ksvc streamlit-frontend --type='merge' -p='{"spec":{"template":{"spec":{"containers":[{"image":"socrates12345/streamlit-frontend:abc1234"}]}}}}'
```

## 📊 Monitoring and Observability

### Version Metrics

Track deployment versions with Prometheus labels:

```yaml
# ServiceMonitor for version tracking
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: architecture-tool-versions
spec:
  selector:
    matchLabels:
      app: streamlit-frontend
  endpoints:
  - port: http
    path: /metrics
    metricRelabelings:
    - sourceLabels: [__meta_kubernetes_pod_label_version]
      targetLabel: version
    - sourceLabels: [__meta_kubernetes_pod_label_commit_sha]
      targetLabel: commit_sha
```

### Version Dashboard

Create Grafana dashboard queries:

```promql
# Current deployed versions
up{job="architecture-tool"} * on(instance) group_left(version, commit_sha) 
  kube_pod_labels{label_app="streamlit-frontend"}

# Version deployment frequency
increase(kube_pod_created{pod=~"streamlit-frontend-.*"}[1h])

# Rollback detection
changes(kube_pod_labels{label_version=~".*"}[24h])
```

## 🔒 Security Considerations

### Container Vulnerability Tracking

Each semantic version is scanned for vulnerabilities:

```bash
# Scan specific version
trivy image socrates12345/streamlit-frontend:1.1.8+90d5b54

# Track vulnerabilities by version
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.labels.version}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
```

### Supply Chain Security

- All builds include provenance information
- SLSA compliance through GitHub Actions
- Container signing with cosign (future enhancement)

## 📚 References

- [Semantic Versioning Specification](https://semver.org/)
- [OCI Image Spec](https://github.com/opencontainers/image-spec)
- [Knative Serving](https://knative.dev/docs/serving/)
- [GitOps Toolkit](https://toolkit.fluxcd.io/)

---

_This semantic versioning implementation ensures consistent, traceable, and automated version management across the Visual Architecture Tool microservices ecosystem._