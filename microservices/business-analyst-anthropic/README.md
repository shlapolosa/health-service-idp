# Business Analyst Anthropic Microservice

A serverless business analyst microservice using Knative, FastAPI, and spaCy for natural language processing of business requirements. This service processes unstructured requirements and converts them into structured Subject-Action-Object format with entity extraction and user story generation.

## Features

- **Requirements Analysis**: Converts natural language requirements into structured format
- **Entity Extraction**: Identifies and extracts key entities from requirement text
- **User Story Generation**: Creates user stories from structured requirements
- **Complexity Assessment**: Evaluates requirement complexity based on multiple factors
- **Validation**: Checks requirements for completeness and consistency
- **Health Monitoring**: Built-in health checks and observability

## API Endpoints

### Health Check
- `GET /health`: Service health status

### Core Functionality
- `POST /analyze-requirements`: Analyze natural language requirements
- `POST /extract-entities`: Extract entities from text
- `POST /generate-user-stories`: Generate user stories from requirements
- `POST /assess-complexity`: Assess complexity of requirements  
- `POST /validate-requirements`: Validate requirements completeness

## Prerequisites

- Docker
- Kubernetes cluster with Knative installed
- kubectl configured to access your cluster
- Poetry (for local development)
- Python 3.10+ (for local development)

## Local Development

### Setup

1. Install dependencies:
```bash
poetry install
```

2. Download spaCy model:
```bash
poetry run python -m spacy download en_core_web_sm
```

3. Run the application locally:
```bash
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing

Run tests:
```bash
poetry run pytest tests/ -v
```

Run with coverage:
```bash
poetry run pytest tests/ --cov=src --cov-report=html
```

### Code Quality

Format code:
```bash
poetry run black src/ tests/
poetry run isort src/ tests/
```

Type checking:
```bash
poetry run mypy src/
```

## Docker Build and Run

### Local Docker Development

1. Build the Docker image:
```bash
./build.sh
```

2. Run the container locally:
```bash
./run.sh
```

3. Test with docker-compose:
```bash
docker-compose up
```

## Deployment to Knative

### Prerequisites

Ensure your cluster has:
- Knative Serving installed
- Istio or other supported networking layer
- Container registry access

### Deploy

1. Set your Docker registry:
```bash
export DOCKER_REGISTRY="ghcr.io/your-org"
```

2. (Optional) Set Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

3. Deploy to Knative:
```bash
./deploy.sh
```

4. Test the deployment:
```bash
./test-deployment.sh
```

### Environment Variables

- `LOG_LEVEL`: Logging level (default: INFO)
- `AGENT_TYPE`: Agent type identifier (business-analyst)
- `IMPLEMENTATION_TYPE`: Implementation type (anthropic)
- `ANTHROPIC_API_KEY`: API key for Anthropic services (optional)

## API Usage Examples

### Analyze Requirements

```bash
curl -X POST https://your-service-url/analyze-requirements \
  -H "Content-Type: application/json" \
  -d '{
    "query": "User should be able to create and manage their profile and update billing information",
    "parameters": {
      "domain": "ecommerce"
    }
  }'
```

### Extract Entities

```bash
curl -X POST https://your-service-url/extract-entities \
  -H "Content-Type: application/json" \
  -d '{
    "query": "The customer wants to update their billing address and payment method"
  }'
```

### Generate User Stories

```bash
curl -X POST https://your-service-url/generate-user-stories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "parameters": {
      "requirements": [{
        "subject": "user",
        "action": "create",
        "object": "profile",
        "priority": "high",
        "category": "functional",
        "rationale": "to manage personal information",
        "acceptance_criteria": ["Profile form is accessible", "Data is validated"],
        "stakeholders": ["user", "admin"],
        "business_value": "improves user experience",
        "complexity": "medium",
        "entities": [],
        "confidence_score": 0.8
      }]
    }
  }'
```

## Architecture

### Components

- **FastAPI Application**: REST API framework with automatic documentation
- **spaCy NLP Processor**: Natural language processing for entity extraction
- **Business Knowledge Base**: Domain-specific stakeholder and pattern mappings
- **Template Engine**: User story and requirement template generation
- **Pydantic Models**: Data validation and serialization

### Design Patterns

- **Dependency Injection**: Loose coupling between components
- **Repository Pattern**: Abstracted data access
- **Strategy Pattern**: Pluggable NLP processing strategies
- **Template Method**: Standardized processing workflows

## Configuration

### Knative Service Configuration

The service is configured for:
- **Auto-scaling**: 1-10 replicas based on traffic
- **Resource limits**: 2 CPU, 1Gi memory max
- **Health checks**: Readiness and liveness probes
- **Security**: Non-root user, dropped capabilities

### Customization

Modify `knative-service.yaml` to adjust:
- Resource requirements
- Scaling parameters
- Environment variables
- Security policies

## Monitoring and Observability

### Health Checks

- **Readiness probe**: `/health` endpoint (10s initial delay)
- **Liveness probe**: `/health` endpoint (30s initial delay)

### Logging

Structured logging with configurable levels:
- ERROR: Critical issues
- INFO: General operational messages
- DEBUG: Detailed processing information

### Metrics

Built-in FastAPI metrics for:
- Request count and duration
- Response status codes
- Endpoint performance

## Security

### Container Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem (where possible)
- Dropped capabilities
- No privilege escalation

### API Security

- Input validation with Pydantic
- Error handling without information leakage
- Optional API key authentication

## Troubleshooting

### Common Issues

1. **spaCy model not found**:
   ```bash
   docker exec -it container python -m spacy download en_core_web_sm
   ```

2. **Memory issues**:
   - Increase resource limits in `knative-service.yaml`
   - Optimize spaCy model size

3. **Slow startup**:
   - Pre-download spaCy models in Docker image
   - Use readiness probe with appropriate delays

### Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

Check service logs:
```bash
kubectl logs -l app=business-analyst-anthropic -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks (black, isort, mypy, pytest)
5. Submit a pull request

## License

MIT License - see LICENSE file for details