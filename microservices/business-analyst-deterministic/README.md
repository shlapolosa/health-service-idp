# Business Analyst Deterministic Microservice

A FastAPI-based microservice that implements the Business Analyst agent using deterministic algorithms and rule-based NLP processing.

## Overview

This microservice provides business analysis capabilities using deterministic methods instead of AI/LLM approaches. It analyzes natural language requirements and converts them into structured format using:

- Rule-based NLP with spaCy
- Pattern matching for entity extraction
- Deterministic algorithms for complexity assessment
- Template-based user story generation

## Features

- **Requirements Analysis**: Convert natural language to structured Subject-Action-Object format
- **Entity Extraction**: Extract business entities using pattern matching and NLP rules
- **User Story Generation**: Create user stories using deterministic templates
- **Complexity Assessment**: Score complexity using rule-based factors
- **Requirements Validation**: Validate completeness and quality using deterministic rules

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Core Functionality
- `POST /analyze-requirements` - Analyze natural language requirements
- `POST /extract-entities` - Extract entities from text
- `POST /generate-user-stories` - Generate user stories from requirements
- `POST /assess-complexity` - Assess requirement complexity
- `POST /validate-requirements` - Validate requirements quality

## Usage

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Run the service**:
   ```bash
   ./run.sh
   ```
   Service will be available at `http://localhost:8081`

3. **Test the service**:
   ```bash
   ./test-deployment.sh
   ```

### Docker Deployment

1. **Build the image**:
   ```bash
   ./build.sh
   ```

2. **Run with Docker Compose**:
   ```bash
   docker-compose up
   ```

### Knative Deployment

1. **Deploy to Knative**:
   ```bash
   ./deploy.sh
   ```

## Request/Response Format

### Analyze Requirements

**Request**:
```json
{
  "query": "User should be able to create and manage their profile",
  "parameters": {
    "domain": "general"
  }
}
```

**Response**:
```json
{
  "result": {
    "requirements": [
      {
        "subject": "User",
        "action": "create",
        "object": "profile",
        "priority": "medium",
        "category": "crud",
        "complexity": "low",
        "confidence_score": 0.9,
        "acceptance_criteria": [
          "Given valid profile data, when User creates profile, then profile is successfully created"
        ],
        "stakeholders": ["user"]
      }
    ],
    "entities": [...],
    "confidence": 0.9,
    "method": "deterministic"
  },
  "metadata": {
    "agent_type": "business-analyst",
    "implementation": "deterministic",
    "processing_time": 0.1
  }
}
```

## Architecture

The service follows a layered architecture:

1. **FastAPI Layer**: HTTP endpoints and request handling
2. **Agent Layer**: Business logic and task processing
3. **NLP Layer**: Text processing and entity extraction
4. **Pattern Layer**: Rule-based analysis and categorization

## Key Components

- **BusinessAnalystAgent**: Main agent class handling all analysis tasks
- **Deterministic NLP**: Rule-based text processing using spaCy
- **Pattern Matching**: Regex and linguistic patterns for entity extraction
- **Template Engine**: Deterministic user story and criteria generation
- **Scoring Algorithms**: Rule-based complexity and quality assessment

## Configuration

Environment variables:
- `PORT`: Service port (default: 8080)
- `LOG_LEVEL`: Logging level (default: INFO)

## Testing

Run tests with:
```bash
pytest tests/
```

## Deployment

The service is designed for:
- Local development with hot reload
- Docker containerization
- Knative serverless deployment
- Kubernetes orchestration

## Monitoring

Health checks available at `/health` endpoint for:
- Kubernetes readiness/liveness probes
- Load balancer health checks
- Service mesh monitoring