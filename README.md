# Health Service Internal Developer Platform (IDP)

A GitOps-enabled cloud-native platform for intelligent architecture visualization and microservice development, built with minimal cost and maximum stability principles.

## 🚀 Quick Start

The platform supports **two primary use cases** for application development:

### Use Case 1: Crossplane ApplicationClaim Workflow (Guided)
For developers who want a guided experience with automatic infrastructure provisioning:

```yaml
# Create an ApplicationClaim for automatic setup
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  annotations:
    webservice.oam.dev/source: "api-driven"  # Prevents circular dependencies
spec:
  name: my-health-service
  language: python
  framework: fastapi
  database: postgres
  cache: redis
  appContainer: my-custom-repo  # Optional: specify target repository
  realtime: health-streaming    # Optional: adds real-time capabilities

# Flow: ApplicationClaim → Crossplane → GitOps Repository → ArgoCD → KubeVela → Knative + Infrastructure
```

### Use Case 2: Direct OAM Application Management (Expert)
For developers who want direct control over their application definition:

```yaml
# Simple webservice (minimal artifacts) 
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: simple-app
spec:
  components:
  - name: hello-api
    type: webservice
    properties:
      image: nginx:alpine
      port: 80

# Complex application with infrastructure
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: complex-app
spec:
  components:
  # OAM-compliant webservice → Knative Service (minimal artifacts)
  - name: health-api
    type: webservice
    properties:
      image: health-api:latest
      port: 8080
      
  # Complete infrastructure → Crossplane ApplicationClaim  
  - name: app-infrastructure
    type: application-infrastructure
    properties:
      name: health-api
      language: python
      framework: fastapi
      database: postgres
      cache: redis
      repository: custom-repo-name  # Optional: specify target repository
      
  # Real-time platform → Complete streaming infrastructure
  - name: streaming-platform
    type: realtime-platform
    properties:
      name: health-streaming
      database: postgres
      visualization: metabase

# Flow: Manual Edit → ArgoCD → KubeVela → Mixed Resources (Knative Services + Crossplane Claims)
```

## 🏗️ Architecture Overview

### High-Level Architecture
- **EKS Cluster**: Minimal managed control plane with Karpenter-managed workload nodes
- **vCluster**: Virtual Kubernetes environment for workload isolation (`architecture-visualization`)
- **Knative + Istio**: Service mesh for microservices with automatic scaling
- **ArgoCD**: GitOps deployment watching `health-service-idp-gitops` repository
- **KubeVela**: OAM application management and infrastructure orchestration
- **Observability**: Prometheus, Grafana, Jaeger, Kiali accessible via subpath routing

## 📋 OAM Components Reference

### Table 1: OAM ComponentDefinitions

All components that can be added to OAM applications (`oam/applications/application.yaml`):

| Component | Use Case | Crossplane Mapping | Kubernetes Artifact |
|-----------|----------|-------------------|---------------------|
| **Application Components (OAM-Compliant)** | | | |
| `webservice` | Auto-scaling web applications, microservices, APIs | Optional: `ApplicationClaim` for infrastructure | **Knative Service** + Optional Argo Workflow ⭐ |
| `kafka` | Event streaming, message queues | None (direct) | Helm Release (Bitnami Kafka Chart) |
| `redis` | In-memory caching, session storage | None (direct) | Helm Release (Bitnami Redis Chart) |
| `mongodb` | Document database, NoSQL storage | None (direct) | Helm Release (Bitnami MongoDB Chart) |
| **Infrastructure Components (Crossplane-Managed)** | | | |
| `application-infrastructure` | Complete application setup with repos | `ApplicationClaim` | Multiple: Repos + Infrastructure + Secrets |
| `realtime-platform` | Complete streaming infrastructure | `RealtimePlatformClaim` | **Knative Service** + Kafka + MQTT + Lenses + Metabase + PostgreSQL ⭐ |
| `vcluster` | Virtual Kubernetes environments | `VClusterEnvironmentClaim` | vCluster + Istio + Knative + ArgoCD + Observability |
| `neon-postgres` | Managed PostgreSQL database | None (direct) | Secret with connection details |
| `auth0-idp` | Identity provider integration, SSO | None (direct) | ExternalSecret from AWS Secrets Manager |

### Table 2: Crossplane Claims (Beyond OAM)

Additional Crossplane claims available for direct use, not mapped to OAM components:

| Claim | Use Case | Example | Kubernetes Artifact |
|-------|----------|---------|---------------------|
| `ApplicationClaim` | Guided application creation with infrastructure | Creating complete app stack via Slack/API | Multiple: OAM Application + Infrastructure Claims |
| `RealtimePlatformClaim` | Complete streaming infrastructure | Real-time analytics platform | Namespace + Kafka + MQTT + Lenses + Metabase + PostgreSQL + Secrets |
| `VClusterEnvironmentClaim` | Virtual Kubernetes environments | Isolated development environments | vCluster + Istio + Knative + ArgoCD + Observability Stack |

### Component Categories

**Application Components (OAM-Compliant)** - Deploy directly as Kubernetes workloads via KubeVela  
**Infrastructure Components (Crossplane-Managed)** - Create Crossplane claims for infrastructure that OAM/KubeVela cannot natively manage  
**Real-time Components** - Specialized streaming and IoT infrastructure via Crossplane  
**Specialized Components** - Advanced data and processing platforms via Crossplane

> **Key Architecture**: 
> - **Native OAM Components** (`webservice`, `kafka`, `redis`, `mongodb`) - Direct Kubernetes resources via KubeVela
> - **Infrastructure Components** (`application-infrastructure`, `realtime-platform`, `vcluster`) - Crossplane Claims for complex infrastructure
> - **Specialized Components** - External integrations and advanced platforms

## 🔄 Architectural Equivalence: WebService vs Real-time Platform

Both `webservice` and `realtime-platform` follow identical architectural patterns as **composite components** that provision complete application stacks (workload + infrastructure):

| **Aspect** | **webservice** | **realtime-platform** |
|------------|----------------|------------------------|
| **Primary Output** | Knative Service (HTTP/REST endpoints) | Knative Service (WebSocket + Kafka consumers) |
| **Secondary Output** | Optional: Argo Workflow (when `language` specified) | RealtimePlatformClaim → Complete streaming infrastructure |
| **Infrastructure Components** | Optional: PostgreSQL, Redis, MongoDB via ApplicationClaim | Kafka, MQTT, Lenses HQ/Agent, PostgreSQL, Metabase |
| **ComponentDefinition** | `webservice` in consolidated-component-definitions.yaml | `realtime-platform` in consolidated-component-definitions.yaml |
| **Crossplane Integration** | Optional: ApplicationClaim for infrastructure bootstrap | Required: RealtimePlatformClaim for streaming infrastructure |
| **Environment Variables** | `AGENT_TYPE`, `LOG_LEVEL`, custom environment | `REALTIME_PLATFORM_NAME`, `WEBSOCKET_ENABLED`, `AGENT_TYPE` |
| **Secret Management** | Optional: Database/cache connection secrets | Required: Kafka/MQTT/Lenses/Metabase connection secrets |
| **OAM Usage Pattern** | `type: webservice` with optional `language`/`database` | `type: realtime-platform` with `database`/`visualization`/`iot` |
| **Architectural Pattern** | **Composite Component**: Workload + Optional Infrastructure | **Composite Component**: Workload + Required Infrastructure |
| **Service Discovery** | Via optional database/cache service names | Via Kafka/MQTT/Lenses service names in dedicated namespace |
| **Namespace Strategy** | Single namespace (where Application defined) | Dual namespace: Application + `{name}-realtime` namespace |
| **Scaling** | Knative auto-scaling (0-10 replicas) | Knative auto-scaling (1-10 replicas, min=1 for streaming) |

**Key Insight**: Both are **composite components** that provision complete application stacks rather than single-purpose components. The only difference is the type of infrastructure they provision and the application template they use.

## 🔗 Lenses Agent-to-HQ Connection Process

The real-time platform uses **Lenses HQ** for Kafka management with a **Lenses Agent** that connects to provide monitoring and control capabilities. The connection process is **fully automated** through our multi-environment setup:

### Architecture Overview
```
┌─────────────┐    gRPC    ┌──────────────┐    ┌─────────────────┐
│  Lenses HQ  │ ←────────→ │ Lenses Agent │ ←→ │ Kafka Ecosystem │
│  (Port 9991)│  Port 10000│   (Per NS)   │    │ Schema Registry │
│  (Port 10000)│           │              │    │ Kafka Connect   │
└─────────────┘            └──────────────┘    └─────────────────┘
```

### Multi-Environment Agent Key Management

**1. Environment Creation Process:**
```bash
# 1. Access Lenses HQ web interface
http://lenses-hq.streaming-platform-2025-realtime.local/environments

# 2. Create new environment
- Login with admin/admin
- Navigate to Environments → New Environment  
- Name: my-streaming-platform
- Get generated agent key: agent_key_xyz123...

# 3. Add to .env file
echo "my-namespace-realtime-agent-key=agent_key_xyz123..." >> .env

# 4. Update secrets and trigger automation
./setup-secrets.sh
```

**2. Automated Connection Flow:**
```mermaid
graph TD
    A[Create Environment in HQ] --> B[Get Agent Key]
    B --> C[Add to .env file]
    C --> D[Run setup-secrets.sh]
    D --> E[ConfigMap Updated]
    E --> F[CronJob Syncs Secret]
    F --> G[Agent Deployment Restarted]
    G --> H[Agent Connects to HQ]
    H --> I[Environment Shows Connected]
```

**3. Technical Implementation:**

| Component | Purpose | Configuration |
|-----------|---------|---------------|
| **ConfigMap** | `env-agent-keys` stores namespace→key mappings | `streaming-platform-2025-realtime-agent-key: agent_key_xyz` |
| **CronJob** | Syncs secrets every 2 minutes with namespace-specific keys | Reads ConfigMap, creates `lenses-credentials` per namespace |
| **Secret** | `lenses-credentials` contains `AGENT_KEY` for each namespace | Agent reads `AGENT_KEY` from secret in its namespace |
| **Agent Config** | `provisioning.yaml` uses environment variable from secret | `agentKey: value: $AGENT_KEY` |

**4. Connection Requirements:**
- **HQ Service**: Exposes both port 9991 (web UI) and port 10000 (agent registration)
- **Agent Authentication**: Uses HQ-generated agent key (not demo keys)
- **Network**: Agent connects to `lenses-hq:10000` via gRPC within cluster
- **Restart Policy**: Agent automatically restarts when secrets change

**5. Accessing Lenses HQ Web Interface:**

The realtime-platform automatically creates Istio networking resources to expose Lenses HQ:

```bash
# Check if HQ is accessible (requires Istio LoadBalancer)
kubectl get svc istio-ingressgateway -n istio-system

# Get the external IP/hostname
GATEWAY_URL=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Access HQ via browser (replace namespace-name with your actual namespace)
echo "Lenses HQ: http://$GATEWAY_URL/"
echo "Host header required: lenses-hq.<namespace-name>-realtime.local"
```

**Local Development Access:**
```bash
# Port-forward for local access (alternative to LoadBalancer)
kubectl port-forward -n <namespace>-realtime svc/lenses-hq 9991:9991

# Access HQ locally
echo "Lenses HQ Local: http://localhost:9991"
echo "Login: admin/admin"
```

**DNS Configuration:**
If using the hostname approach, add to your `/etc/hosts`:
```bash
# Get LoadBalancer IP
LB_IP=$(kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add to /etc/hosts
echo "$LB_IP lenses-hq.streaming-platform-2025-realtime.local" | sudo tee -a /etc/hosts
```

**6. Troubleshooting:**
```bash
# Check agent key in namespace
kubectl get secret lenses-credentials -n <namespace> -o jsonpath='{.data.AGENT_KEY}' | base64 -d

# Check agent logs for connection status  
kubectl logs -n <namespace> deployment/lenses-agent --tail=20

# Check HQ logs for agent registration attempts
kubectl logs -n <namespace> deployment/lenses-hq --tail=20 | grep agent

# Check HQ web interface accessibility
kubectl get gateway,virtualservice -n <namespace>-realtime

# Manual trigger secret sync
kubectl create job manual-sync --from=cronjob/multi-env-secret-sync -n default
```

## 🔄 System Workflows

### Deployment Flow with Source Detection
```mermaid
graph TD
    A[Developer Input] --> B{Use Case Choice}
    B -->|Use Case 1| C[ApplicationClaim with api-driven annotation]
    B -->|Use Case 2| D[Direct OAM Edit with oam-driven source]
    C --> E[Crossplane Processing]
    D --> F[ArgoCD Sync]
    E --> G{Source Detection}
    G -->|api-driven| H[oam-updater runs]
    G -->|oam-driven| I[Skip oam-updater - prevent circular dependency]
    H --> J[Component Existence Check]
    J -->|New component| K[Update OAM Application]
    J -->|Existing component| L[Skip to prevent duplication]
    I --> F
    K --> F
    L --> F
    F --> M[KubeVela Processing]
    M --> N{Component Type Analysis}
    N -->|webservice| O[Knative Service]
    N -->|infrastructure| P[Crossplane Claims]
    N -->|realtime-platform| Q[Streaming Infrastructure]
    O --> R[Application Ready]
    P --> R
    Q --> R
```

### GitOps Architecture with Source Tracking
```
Source Code Changes → Version Manager → GitOps Repo → ArgoCD → KubeVela → Kubernetes Resources
                                                              ↓
                                                    Source Detection System
                                                              ↓
                                               {api-driven, oam-driven, analyzer-driven}
                                                              ↓
                                               Prevents Circular Dependencies
```

## 📁 Project Structure

```
health-service-idp/
├── microservices/                    # 18 AI-powered microservices
│   ├── shared-libs/agent-common/     # Shared FastAPI library with real-time support
│   ├── streamlit-frontend/           # Web interface
│   ├── orchestration-service/        # Central workflow coordinator
│   └── *-anthropic/ & *-deterministic/  # AI + rule-based agent pairs
├── crossplane/                       # Infrastructure definitions
│   ├── application-claim-composition.yaml  # ApplicationClaim → Infrastructure
│   ├── oam/                          # OAM component definitions
│   └── realtime-platform-manifests/  # Real-time infrastructure
├── slack-api-server/                 # Slack integration for commands
├── .github/workflows/                # CI/CD pipelines
│   └── comprehensive-gitops.yml      # Main deployment pipeline
└── cluster-lifecycle.sh             # Infrastructure management
```

## 🛠️ Essential Commands

### Infrastructure Management
```bash
# Create or resume EKS cluster with vCluster
./cluster-lifecycle.sh up

# Pause all workloads (cost optimization)
./cluster-lifecycle.sh pause

# Complete infrastructure shutdown
./cluster-lifecycle.sh down
```

### Microservice Development
```bash
# Build and test individual microservice
cd microservices/business-analyst-anthropic
poetry install && poetry run pytest
./build.sh && ./test-deployment.sh

# Deploy via docker-compose for local development
docker-compose up
```

### Real-time Platform Features
The platform includes comprehensive real-time streaming capabilities:

- **Kafka Cluster**: Event streaming with Schema Registry
- **MQTT Broker**: IoT device connectivity  
- **Lenses**: Stream processing with SQL-based transformations
- **Metabase**: Analytics dashboards and visualization
- **WebSocket Support**: Real-time client connectivity

Example real-time microservice:
```python
from agent_common import create_realtime_agent_app, RealtimeAgent

class HealthStreamingAgent(RealtimeAgent):
    async def process_health_data(self, device_data):
        # Automatic Kafka, MQTT, Redis connectivity
        await self.publish_to_kafka("health_events", device_data)
        await self.send_mqtt_alert("alerts/health", alert_data)

app = create_realtime_agent_app(HealthStreamingAgent)
```

## 🔧 Development Patterns

### Bootstrap Source Detection System
The platform prevents circular dependencies through comprehensive source tracking:

**Source Types**:
- **`api-driven`**: ApplicationClaims created via Argo workflows (Slack commands, API calls)
- **`oam-driven`**: ApplicationClaims created from user-edited OAM manifests  
- **`analyzer-driven`**: ApplicationClaims created by automated OAM analysis

**Key Features**:
- **Circular Dependency Prevention**: OAM-driven claims skip oam-updater to prevent loops
- **Component Duplication Prevention**: Existence checking before adding components
- **Repository Parameter Support**: Custom repository names via `repository` parameter
- **Audit Trail**: Clear source annotations for troubleshooting and debugging

### Agent Microservice Structure
All agent microservices follow this pattern:
- `src/main.py` - FastAPI app using `agent_common.fastapi_base.create_agent_app()`
- `src/{agent_name}.py` - Agent implementation extending `BaseMicroserviceAgent`
- `pyproject.toml` - Poetry configuration with standardized dependencies
- `knative-service.yaml` - Knative deployment configuration
- `Dockerfile` - Multi-stage build copying from `shared-libs/agent-common`

### Standard API Endpoints
All agents expose:
- `GET /health` - Health check for Kubernetes probes
- `GET /` - Service status and capabilities
- `POST /{agent-endpoints}` - Agent-specific capabilities
- `GET /docs` - Auto-generated OpenAPI documentation

### Real-time Integration
When `realtime` parameter is specified:
- `GET /ws` - WebSocket endpoint for real-time communication
- `GET /stream/events` - Server-Sent Events stream
- `POST /realtime/*` - Real-time specific APIs

## 💰 Cost Optimization

The platform is designed for minimal cost:
- **vCluster pause/resume**: Complete workload shutdown capability
- **Karpenter auto-scaling**: Nodes provisioned only when needed
- **Knative scale-to-zero**: Applications scale down when not in use
- **Single t3.medium node**: Hosts control plane components efficiently

## 🔍 Observability Access

All observability tools are accessible via subpath routing:
- **ArgoCD**: `/argocd` - GitOps deployment management
- **Grafana**: `/grafana` - Metrics and monitoring dashboards  
- **Jaeger**: `/jaeger` - Distributed tracing
- **Kiali**: `/kiali` - Service mesh visualization
- **Prometheus**: `/prometheus` - Metrics collection

## 📚 Documentation

- **[ARCHITECTURAL_DECISIONS.md](ARCHITECTURAL_DECISIONS.md)**: Complete architectural evolution and decisions
- **[CLAUDE.md](CLAUDE.md)**: Developer guidelines and development principles
- **[REALTIME_SYSTEM.md](REALTIME_SYSTEM.md)**: Real-time streaming architecture
- **[crossplane/DEVELOPER-GUIDE.md](crossplane/DEVELOPER-GUIDE.md)**: Infrastructure development guide
- **[microservices/README.md](microservices/README.md)**: Microservices development guide

## 🚦 Getting Started

1. **Set up infrastructure**: `./cluster-lifecycle.sh up`
2. **Choose your development approach**:
   - **Guided**: Create ApplicationClaims for automatic setup
   - **Expert**: Edit OAM applications directly in GitOps repository
3. **Deploy applications**: ArgoCD automatically syncs and deploys
4. **Monitor**: Access observability tools via ingress endpoints

## 🔄 CI/CD Pipeline

The platform includes a comprehensive GitOps pipeline:
- **Semantic versioning**: `MAJOR.MINOR.COMMIT_SHA` format
- **Multi-stage builds**: Optimized container images
- **Automated testing**: Unit, integration, and deployment tests
- **GitOps synchronization**: Automatic deployment via ArgoCD
- **Version management**: Automatic OAM application updates

## 🤝 Contributing

Follow the development guidelines in [CLAUDE.md](CLAUDE.md):
- Use Test-Driven Development (TDD)
- Follow 12-factor app principles
- Implement Onion Architecture pattern
- Use dependency injection
- Create comprehensive tests

---

**Platform Status**: Production-ready with comprehensive real-time streaming capabilities
**Cost Model**: Pay-per-use with aggressive cost optimization
**Support**: Internal Developer Platform Team