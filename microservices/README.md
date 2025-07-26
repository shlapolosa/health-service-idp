# Health Service Microservices

This directory contains the microservices that power the Health Service Internal Developer Platform (IDP). The platform supports **two primary use cases** for microservice development:

## Current Microservices
- fix-test-1753087435 (python/fastapi)
- workflow-verification (python/fastapi)
- detect-changes-test (python/fastapi)
- health-processor (python/fastapi)

## 🚀 Use Cases

### Use Case 1: Crossplane ApplicationClaim Workflow (Guided)
For developers who want automatic microservice scaffolding with infrastructure provisioning:

```yaml
# Create an ApplicationClaim for automatic setup
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
spec:
  name: my-health-service
  language: python
  framework: fastapi
  database: postgres
  cache: redis
  realtime: health-streaming  # Optional: adds real-time capabilities

# Flow: ApplicationClaim → Crossplane → Microservice Scaffold → GitOps → ArgoCD → Knative
```

### Use Case 2: Direct OAM Application Management (Expert)
For developers who want direct control over their microservice definition in the OAM application:

```yaml
# Edit oam/applications/application.yaml directly
spec:
  components:
  # Microservice component → Creates Knative Service
  - name: health-analyzer
    type: webservice
    properties:
      image: health-analyzer:latest
      port: 8080
      realtime: "health-streaming"  # Connect to real-time platform
      websocket: true
      streaming:
        enabled: true
        topics: ["health_events"]

# Flow: Manual Edit → ArgoCD → KubeVela → Knative Service
```

## 🏗️ Architecture Overview

### Microservice Types

**AI-Powered Agents:**
- `business-analyst-anthropic` - Requirements processing with Claude
- `business-architect-anthropic` - Business strategy with AI insights
- `application-architect-anthropic` - API design with intelligent recommendations
- `infrastructure-architect-anthropic` - Infrastructure design with AI optimization
- `solution-architect-anthropic` - Solution consolidation with AI analysis
- `project-manager-anthropic` - Project planning with intelligent scheduling
- `developer-anthropic` - Code generation with AI assistance
- `accountant-anthropic` - Financial analysis with AI insights
- `orchestration-service` - Central workflow coordinator

**Deterministic Variants:**
- Each agent has a `-deterministic` counterpart for rule-based processing
- Provides fallback capabilities and cost optimization
- Ensures system reliability when AI services are unavailable

**Frontend Services:**
- `streamlit-frontend` - Web interface for architecture design

### Shared Infrastructure
- `shared-libs/agent-common` - Shared FastAPI library with real-time support
- Standardized APIs, health checks, and WebSocket capabilities
- Real-time streaming integration (Kafka, MQTT, Redis)

## 🔄 Development Workflows

### Standard Microservice Structure
All microservices follow this pattern:
```
microservices/{service-name}/
├── src/
│   ├── main.py              # FastAPI app using agent_common
│   ├── {service_name}.py    # Service implementation
│   └── models.py            # Pydantic models
├── tests/
├── pyproject.toml           # Poetry configuration
├── Dockerfile               # Multi-stage build
├── knative-service.yaml     # Knative deployment
├── build.sh                 # Build script
├── run.sh                   # Local development
└── test-deployment.sh       # Integration tests
```

### Standard API Endpoints
All microservices expose:
- `GET /health` - Health check for Kubernetes probes
- `GET /` - Service status and capabilities
- `POST /{service-endpoints}` - Service-specific capabilities
- `GET /docs` - Auto-generated OpenAPI documentation

### Real-time Integration
When connected to a real-time platform:
- `GET /ws` - WebSocket endpoint for real-time communication
- `GET /stream/events` - Server-Sent Events stream
- `POST /realtime/*` - Real-time specific APIs

## 🛠️ Development Commands

### Build Individual Microservice
```bash
cd microservices/business-analyst-anthropic
./build.sh
```

### Local Development
```bash
# Using Poetry
poetry install && poetry run pytest
poetry run python src/main.py

# Using Docker Compose
docker-compose up

# Using run script
./run.sh
```

### Testing
```bash
# Unit tests
poetry run pytest tests/

# Integration tests
./test-deployment.sh

# Test specific namespace
NAMESPACE=my-namespace ./test-deployment.sh
```

## 🔧 Integration Patterns

### Use Case 1 Integration
ApplicationClaims automatically:
1. Generate microservice scaffolding in `microservices/{name}/`
2. Create Knative service definitions
3. Set up GitOps workflows
4. Configure OAM applications
5. Deploy via ArgoCD

### Use Case 2 Integration
Direct OAM editing allows:
1. Manual component definition in `oam/applications/application.yaml`
2. ArgoCD automatic sync detection
3. KubeVela processing of OAM components
4. Knative service creation
5. Real-time platform connectivity

## 🎯 Real-time Capabilities

Microservices can connect to real-time platforms for:
- **Kafka Integration**: Event streaming and processing
- **MQTT Connectivity**: IoT device communication
- **WebSocket Support**: Real-time client updates
- **Redis Caching**: High-performance data access
- **Stream Processing**: Real-time analytics with Lenses

Example real-time microservice:
```python
from agent_common import create_realtime_agent_app, RealtimeAgent

class HealthAnalyzer(RealtimeAgent):
    async def process_health_data(self, device_data):
        # Automatic Kafka, MQTT, Redis connectivity
        analysis = await self.analyze_data(device_data)
        await self.publish_to_kafka("health_analysis", analysis)
        await self.send_websocket_update(analysis)

app = create_realtime_agent_app(HealthAnalyzer)
```

## 📊 Monitoring and Observability

### Health Checks
- Kubernetes readiness and liveness probes
- Dependency health validation
- Real-time platform connectivity checks

### Metrics
- Request/response metrics via FastAPI
- Real-time streaming metrics
- Business logic specific metrics

### Logging
- Structured logging with correlation IDs
- Integration with platform observability stack
- Real-time log streaming capabilities

## 🚦 Getting Started

### Option 1: Use ApplicationClaim (Guided)
1. Create an ApplicationClaim YAML
2. Apply to cluster: `kubectl apply -f application-claim.yaml`
3. Monitor creation in ArgoCD
4. Access service via Knative ingress

### Option 2: Direct OAM Editing (Expert)
1. Edit `oam/applications/application.yaml`
2. Add your microservice component
3. Commit to GitOps repository
4. ArgoCD automatically syncs changes
5. Monitor deployment in KubeVela

## 🤝 Contributing

Follow the development guidelines in [../CLAUDE.md](../CLAUDE.md):
- Use Test-Driven Development (TDD)
- Follow 12-factor app principles
- Implement Onion Architecture pattern
- Use dependency injection
- Create comprehensive tests

---

**Microservices Status**: Production-ready with comprehensive real-time capabilities  
**Development Model**: Dual use case support (Guided + Expert)  
**Integration**: Full GitOps and OAM compatibility
- trading-engine (java/springboot)
- user-analytics-service (python/fastapi)
- system-monitoring (python/fastapi)
- notification-service (python/fastapi)
- test-service-default (python/fastapi)
- simple-web (python/fastapi)
- user-service (python/fastapi)
- notification-service (python/fastapi)
- notification-service-df3s3 (python/fastapi)
- email-service-x9k2m (python/fastapi)
- retail-realtime-test (python/fastapi)
- fintech-realtime-manual (python/fastapi)
