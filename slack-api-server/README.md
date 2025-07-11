# Slack API Server

A FastAPI-based microservice for handling Slack slash commands and triggering VCluster provisioning through GitHub Actions.

## Overview

This service implements the Onion Architecture pattern and provides:
- Slack slash command handling (`/vcluster`)
- Natural language processing with spaCy
- GitHub repository dispatch integration
- VCluster provisioning automation
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

## Integration with GitHub Actions

The service triggers the `slack_create_vcluster` event via GitHub repository dispatch, which executes the VCluster provisioning workflow.

**Payload Structure**:
```json
{
  "event_type": "slack_create_vcluster",
  "client_payload": {
    "vcluster_name": "my-cluster",
    "namespace": "default",
    "user": "user123",
    "slack_channel": "C1234567890",
    "capabilities": { ... },
    "resources": { ... }
  }
}
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