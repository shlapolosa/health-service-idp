# health-service-idp

CLAUDE.md-compliant microservice application container with GitOps-enabled multi-cluster OAM platform.

## Architecture Overview

This platform provides two primary use cases for microservice development:
1. **Slack-driven microservice creation** - Create complete microservice infrastructure via Slack commands
2. **OAM-driven GitOps development** - Trigger microservice creation through OAM application changes in GitOps repositories

## Complete Flow Diagram

```mermaid
graph TB
    subgraph "Use Case 1: Slack Command Flow"
        A[User Slack Command] -->|/microservice create| B[Istio Ingress Gateway]
        B --> C[Slack API Server]
        C -->|Trigger| D[Argo Workflow]
        D --> E1[Create vCluster]
        D --> E2[Create GitHub Repos]
        D --> E3[Create Secrets]
        E2 --> F1[Source Repository]
        E2 --> F2[GitOps Repository]
        F1 --> G1[Microservice Code]
        F2 --> G2[OAM Application]
        G2 --> H[ArgoCD Sync]
        H --> I[Deploy to Cluster]
    end

    subgraph "Use Case 2: OAM GitOps Flow"
        J[Developer Push to GitOps] --> K[GitHub Actions]
        K -->|Repository Dispatch| L[Update Manifests]
        L --> M[ArgoCD Sync]
        M --> N[Apply OAM to Cluster]
        N --> O[KubeVela Controller]
        O --> P[OAM Application Updated]
        P --> Q[Argo Events EventSource]
        Q -->|Detect Changes| R[Argo Events Sensor]
        R -->|HTTP Trigger| S[Slack API Webhook]
        S --> T[Process OAM Components]
        T -->|For Each Component| U[Argo Workflow]
        U --> V1[Create Microservice]
        U --> V2[Create Knative Service]
        U --> V3[Update Repository]
        V2 --> W[Deploy to vCluster]
        V3 --> X[Push to GitHub]
    end

    subgraph "Infrastructure Components"
        Y1[EKS Cluster]
        Y2[Istio Service Mesh]
        Y3[Argo Workflows]
        Y4[Argo Events]
        Y5[ArgoCD]
        Y6[KubeVela/OAM]
        Y7[Crossplane]
        Y8[vCluster]
        Y9[Knative]
    end

    style A fill:#e1f5fe
    style J fill:#e1f5fe
    style C fill:#fff3e0
    style S fill:#fff3e0
    style D fill:#f3e5f5
    style U fill:#f3e5f5
    style Y1 fill:#e8f5e9
    style Y2 fill:#e8f5e9
    style Y3 fill:#e8f5e9
```

## System Components

### Core Platform
- **EKS/AKS Cluster**: Managed Kubernetes control plane with auto-scaling
- **Istio Service Mesh**: Traffic management and observability
- **Argo Workflows**: Workflow orchestration for microservice creation
- **Argo Events**: Event-driven automation for OAM changes
- **ArgoCD**: GitOps continuous delivery
- **KubeVela**: OAM application controller
- **Crossplane**: Infrastructure as Code compositions
- **vCluster**: Virtual Kubernetes clusters for workload isolation
- **Knative**: Serverless workload management
- **Multi-Registry Support**: Dynamic switching between Docker Hub and Azure Container Registry

### Key Services
- **Slack API Server**: Central API for processing Slack commands and OAM webhooks
- **GitHub Integration**: Automated repository creation and management
- **OAM Components**: Declarative application definitions with automatic resource provisioning

## Workflow Details

### Use Case 1: Slack-Driven Development
1. User sends Slack command: `/microservice create service-name python with database with redis`
2. Istio ingress routes to Slack API server
3. Slack API triggers Argo Workflow with parameters
4. Workflow executes parallel jobs:
   - Creates vCluster for isolation
   - Creates GitHub source and GitOps repositories
   - Sets up secrets and credentials
5. Generates microservice code structure following CLAUDE.md principles
6. Creates OAM application definition in GitOps repo
7. ArgoCD syncs and deploys to cluster

### Use Case 2: OAM-Driven GitOps Development
1. Developer modifies OAM application in GitOps repository
2. Push triggers GitHub Actions workflow
3. Actions dispatch updates deployment manifests
4. ArgoCD syncs changes to cluster
5. KubeVela processes OAM application updates
6. Argo Events EventSource detects OAM changes
7. Sensor triggers HTTP request to Slack API webhook
8. Slack API processes each new component:
   - Creates Argo Workflow for microservice generation
   - Generates service code and Knative deployment
   - Updates source repository with new microservice
9. Services deployed to target vCluster

## Testing

### Functional Test Script
```bash
./scripts/test-functional-multicluster.sh
```

### Infrastructure Health Check
```bash
./scripts/infrastructure-health-check-enhanced.sh
```

## Key Features

- **Multi-cluster isolation** via vCluster
- **GitOps-driven deployments** with ArgoCD
- **Event-driven automation** with Argo Events
- **OAM application model** for declarative infrastructure
- **Automatic code generation** following CLAUDE.md principles
- **Crossplane compositions** for infrastructure provisioning
- **Knative serverless** deployments
- **Comprehensive observability** with Prometheus, Grafana, Jaeger
- **Multi-registry support** for Docker Hub and Azure Container Registry

## Multi-Registry Support

The platform supports seamless switching between container registries based on deployment region:

### Supported Registries
- **Docker Hub** (default): `docker.io/socrates12345/*`
- **Azure Container Registry**: `healthidpuaeacr.azurecr.io/*`
- **Custom Registry**: Any custom registry URL

### Configuration Methods

#### 1. OAM Application Level
```yaml
spec:
  components:
    - name: my-service
      type: webservice
      properties:
        # Option A: Specify registry explicitly
        imageName: my-service
        imageTag: v1.0.0
        registry: acr  # or "dockerhub" or "custom"
        
        # Option B: Use full image path (backward compatible)
        image: docker.io/socrates12345/my-service:v1.0.0
```

#### 2. Global Registry Switch
```bash
# Switch all services to ACR
./scripts/switch-registry.sh switch acr

# Switch back to Docker Hub
./scripts/switch-registry.sh switch dockerhub

# Show current configuration
./scripts/switch-registry.sh show
```

#### 3. Registry Configuration
Registry settings are stored in ConfigMaps in `default` and `crossplane-system` namespaces:
- `DEFAULT_REGISTRY`: Primary registry URL
- `ACR_REGISTRY`: Azure Container Registry URL
- `ACTIVE_REGISTRY`: Currently active registry

### Setup ACR Credentials
For Azure Container Registry, create credentials:
```bash
# Automatically created by setup-secrets.sh if ACR_NAME is set in .env
# Or manually:
kubectl create secret docker-registry acr-credentials \
  --docker-server=healthidpuaeacr.azurecr.io \
  --docker-username=<acr-name> \
  --docker-password=<password> \
  -n default
```
