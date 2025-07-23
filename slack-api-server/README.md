# Slack API Server

A FastAPI-based microservice for handling Slack slash commands and triggering VCluster and AppContainer provisioning through GitOps workflows. This service supports **two primary use cases** for infrastructure and application provisioning:

## 🚀 Use Cases

### Use Case 1: Crossplane ApplicationClaim Workflow (Guided)
Slack commands trigger ApplicationClaim creation for automatic infrastructure and application setup:

```bash
# Create complete application stack
/microservice create health-analyzer with python and postgres
# Flow: Slack → ApplicationClaim → Crossplane → GitOps → ArgoCD → KubeVela → Knative
```

### Use Case 2: Direct OAM Application Management (Expert)
Slack commands can trigger direct OAM application updates for expert users:

```bash
# Trigger OAM updates through GitOps
/vcluster create prod-cluster with observability
# Flow: Slack → GitOps Repository Update → ArgoCD → KubeVela → Infrastructure
```

## Overview

This service implements the Onion Architecture pattern and provides:
- Slack slash command handling (`/vcluster`, `/appcontainer`, and `/microservice`)
- Advanced natural language processing with spaCy
- GitOps workflow integration supporting both use cases
- Repository-focused microservice provisioning
- Comprehensive error handling and logging

## Features

- **Onion Architecture**: Clean separation of concerns with Domain, Application, Infrastructure, and Interface layers
- **Enhanced NLP**: spaCy integration with regex fallback for command parsing
- **GitHub Integration**: Repository dispatch for automated VCluster creation
- **Slack Integration**: Webhook handling with signature verification
- **FastAPI**: Modern async web framework with auto-generated API docs
- **Docker Support**: Containerized deployment with health checks
- **Knative Ready**: Configured for Knative serving with autoscaling

## Architecture

```
┌─────────────────┐
│  Interface      │  FastAPI Controllers, Dependency Injection
├─────────────────┤
│  Application    │  Use Cases, Business Logic Orchestration
├─────────────────┤
│  Infrastructure │  GitHub Client, NLP Parser, Slack Verifier
├─────────────────┤
│  Domain         │  Entities, Value Objects, Domain Services
└─────────────────┘
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /slack/command` - Slack slash command webhook
- `POST /slack/events` - Slack events API webhook (future)
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## Environment Variables

### Required
- `PERSONAL_ACCESS_TOKEN` - GitHub personal access token
- `GITHUB_REPOSITORY` - Target GitHub repository (default: `shlapolosa/health-service-idp`)

### Optional
- `SLACK_SIGNING_SECRET` - Slack app signing secret for request verification
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `ENVIRONMENT` - Environment name (default: `development`)
- `PORT` - Server port (default: `8080`)

## Development

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download spaCy model**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Set environment variables**:
   ```bash
   export PERSONAL_ACCESS_TOKEN=your_github_token
   export GITHUB_REPOSITORY=shlapolosa/health-service-idp
   export SLACK_SIGNING_SECRET=your_slack_signing_secret  # Optional
   ```

4. **Run the server**:
   ```bash
   python main.py
   ```

### Docker Development

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Build Docker image**:
   ```bash
   ./build.sh
   ```

### Testing

1. **Test health endpoint**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **Test API documentation**:
   ```bash
   curl http://localhost:8080/docs
   ```

3. **Test deployment** (Kubernetes):
   ```bash
   ./test-deployment.sh
   ```

## Slack Commands

### `/vcluster create`
Creates a new VCluster with specified configuration.

**Examples**:
```
/vcluster create my-cluster
/vcluster create my-cluster in namespace dev
/vcluster create my-cluster with observability and security
/vcluster create large my-cluster in namespace prod with observability
```

**Parameters**:
- `name` - VCluster name (auto-generated if not provided)
- `namespace` - Kubernetes namespace (default: `default`)
- `size` - VCluster size: `small`, `medium`, `large`, `xlarge` (default: `medium`)
- `capabilities` - Enable/disable features: `observability`, `security`, `gitops`, `logging`, `networking`, `autoscaling`, `backup`

### `/vcluster help`
Shows available commands and usage examples.

### `/microservice create`
Creates a new microservice and adds it to an existing or new repository structure.

**Examples**:
```
/microservice create order-service
/microservice create order-service with python and redis
/microservice create order-service repository myapp
/microservice create payment-service repo ecommerce with java and postgres
/microservice create user-service in repo users with python and redis
```

**Parameters**:
- `name` - Microservice name (required)
- `repository` - Target repository name (auto-derived from microservice name if not provided)
- `language` - Programming language: `python`, `java`, `fastapi`, `springboot` (default: `python`)
- `database` - Database type: `none`, `postgres`, `postgresql` (default: `none`)
- `cache` - Cache type: `none`, `redis` (default: `none`)
- `namespace` - Kubernetes namespace (default: `default`)

**Flow (Use Case 1 - ApplicationClaim)**:
1. Creates or updates AppContainer with repositories (source + GitOps)
2. Adds microservice to `microservices/{name}/` folder
3. Creates ApplicationClaim for Knative deployment
4. Crossplane processes claim and creates infrastructure
5. Updates ArgoCD and OAM definitions
6. ArgoCD syncs to KubeVela for deployment

**Flow (Use Case 2 - Direct OAM)**:
1. Updates OAM application.yaml directly in GitOps repository
2. ArgoCD detects changes and syncs
3. KubeVela processes OAM components
4. Creates Knative services and infrastructure claims

**Important**: VCluster creation is separate. Use `/vcluster create` first if needed.

### `/microservice help`
Shows available microservice commands and usage examples.

## Deployment

### Kubernetes (Knative)

1. **Deploy to cluster**:
   ```bash
   ./deploy.sh
   ```

2. **Manual deployment**:
   ```bash
   kubectl apply -f knative-service.yaml
   ```

### Resource Requirements

- **CPU**: 250m request, 1 CPU limit
- **Memory**: 256Mi request, 512Mi limit
- **Scaling**: 1-5 replicas with scale-to-zero

## 🔄 Integration Workflows

### Use Case 1: ApplicationClaim Integration
The service creates ApplicationClaims that trigger Crossplane compositions:

**ApplicationClaim Payload**:
```yaml
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: slack-triggered-app
spec:
  name: my-microservice
  language: python
  framework: fastapi
  database: postgres
  cache: redis
  realtime: health-streaming
```

### Use Case 2: Direct GitOps Integration
The service triggers GitHub repository dispatch for direct OAM updates:

**Repository Dispatch Payload**:
```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "my-cluster",
    "namespace": "default",
    "user": "user123",
    "slack_channel": "C1234567890",
    "capabilities": { ... },
    "resources": { ... },
    "use_case": "direct_oam"  # or "application_claim"
  }
}
```

### GitOps Repository Structure
Both use cases update the GitOps repository:
```
health-service-idp-gitops/
├── oam/applications/application.yaml    # Single OAM application (Use Case 2)
├── crossplane/application-claims/       # ApplicationClaims (Use Case 1)
└── argocd/applications/                 # ArgoCD app definitions
```

## Security

- **Request Verification**: Optional Slack signature verification
- **Non-root User**: Runs as user ID 1000
- **Minimal Capabilities**: Drops all Linux capabilities
- **Read-only Root**: Configurable read-only root filesystem
- **Network Policies**: Supports Kubernetes network policies

## Monitoring

- **Health Checks**: Kubernetes liveness and readiness probes
- **Logging**: Structured logging with configurable levels
- **Metrics**: Compatible with Prometheus (via FastAPI metrics)
- **Tracing**: Ready for OpenTelemetry integration

## Troubleshooting

### Common Issues

1. **spaCy Model Missing**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **GitHub Token Issues**:
   - Ensure `PERSONAL_ACCESS_TOKEN` is set
   - Verify token has `repo` and `workflow` scopes

3. **Slack Verification Failures**:
   - Check `SLACK_SIGNING_SECRET` configuration
   - Verify webhook URL in Slack app settings

### Logs

View logs in development:
```bash
docker-compose logs -f slack-api-server
```

View logs in Kubernetes:
```bash
kubectl logs -l app=slack-api-server -f
```