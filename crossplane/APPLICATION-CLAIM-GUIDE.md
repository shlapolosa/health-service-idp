# ApplicationClaim Complete Usage Guide

This guide covers the complete ApplicationClaim functionality including database and cache provisioning.

## Overview

ApplicationClaim creates CLAUDE.md-compliant microservices with optional database and cache infrastructure, following the two-tier architecture:

1. **AppContainerClaim** - Creates application container infrastructure (source + GitOps repos)
2. **ApplicationClaim** - Adds individual microservices to existing containers

## Basic Usage

### Minimal Microservice (No Database/Cache)

```yaml
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: simple-service
spec:
  name: simple-service
  language: python
  framework: fastapi
  # Uses default appContainer: health-service-idp
  # database: none (default)
  # cache: none (default)
```

### Microservice with Database and Cache

```yaml
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: user-service
spec:
  name: user-service
  language: python
  framework: fastapi
  database: postgres  # Provisions PostgreSQL
  cache: redis       # Provisions Redis
  exposeApi: true    # Creates AWS API Gateway integration
```

## Infrastructure Provisioning

### PostgreSQL Database (`database: postgres`)

When `database: postgres` is specified, ApplicationClaim provisions:

- **PostgreSQL Helm Release**: Bitnami PostgreSQL chart with:
  - 10GB persistent storage (GP2)
  - Memory: 256Mi request, 512Mi limit
  - CPU: 250m request, 500m limit
  - Health checks and readiness probes
  - Metrics collection enabled

- **Database Secret**: Contains connection credentials:
  ```
  DATABASE_URL: postgresql://username:password@host:5432/dbname
  DB_HOST: service-postgresql.namespace.svc.cluster.local
  DB_PORT: 5432
  DB_NAME: service-name
  DB_USER: service-name
  DB_PASSWORD: generated-password
  ```

- **Connection String**: Available in microservice environment:
  ```bash
  DATABASE_URL="postgresql://user:pass@host:5432/dbname"
  ```

### Redis Cache (`cache: redis`)

When `cache: redis` is specified, ApplicationClaim provisions:

- **Redis Helm Release**: Bitnami Redis chart with:
  - 5GB persistent storage (GP2) for master and replica
  - Memory: 128Mi request, 256Mi limit
  - CPU: 100m request, 200m limit
  - High availability with 1 replica
  - Metrics collection enabled

- **Cache Secret**: Contains connection credentials:
  ```
  REDIS_URL: redis://:password@host:6379/0
  REDIS_HOST: service-redis-master.namespace.svc.cluster.local
  REDIS_PORT: 6379
  REDIS_PASSWORD: generated-password
  ```

## Generated Microservice Structure

All microservices follow CLAUDE.md compliance with Onion Architecture:

```
microservices/service-name/
├── src/
│   ├── domain/          # Business rules and entities
│   │   └── models.py
│   ├── application/     # Use cases and business logic
│   │   └── use_cases.py
│   ├── infrastructure/ # External services, repositories
│   │   └── repositories.py
│   ├── interface/      # API endpoints, controllers
│   │   └── api.py
│   └── main.py         # Application entry point
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── test_main.py    # Main test file
├── manifest/           # Kubernetes manifests
├── pyproject.toml      # Poetry dependencies
├── Dockerfile          # Multi-stage container build
└── README.md           # Service documentation
```

### FastAPI Service Features

- **Health Endpoints**: `/health`, `/ready` for Kubernetes probes
- **Environment Configuration**: 12-Factor App compliance
- **Dependency Injection**: Ready for DI patterns
- **Auto-documentation**: OpenAPI/Swagger at `/docs`
- **Security**: Non-root user, minimal container surface
- **Observability**: Structured logging, metrics ready

### Database Integration (Python/FastAPI)

Generated code includes database connection setup:

```python
# src/infrastructure/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency injection ready
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Cache Integration (Python/FastAPI)

Generated code includes Redis connection setup:

```python
# src/infrastructure/cache.py
import os
import redis

REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL)

# Dependency injection ready
def get_cache():
    return redis_client
```

## GitOps Integration

ApplicationClaim automatically creates GitOps manifests:

### Knative Service
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: service-name
  namespace: app-container
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containers:
      - image: docker.io/socrates12345/service-name:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: service-name-postgres-secret
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: service-name-redis-secret  
              key: REDIS_URL
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
```

### OAM Component
```yaml
apiVersion: core.oam.dev/v1beta1
kind: Component
metadata:
  name: service-name
spec:
  workload:
    apiVersion: serving.knative.dev/v1
    kind: Service
  parameters:
  - name: image
    fieldPaths: ["spec.template.spec.containers[0].image"]
  - name: replicas  
    fieldPaths: ["metadata.annotations[autoscaling.knative.dev/minScale]"]
```

## CI/CD Integration

ApplicationClaim integrates with existing CI/CD pipeline:

1. **Automatic Detection**: Pipeline detects changes in `microservices/service-name/`
2. **Security Scanning**: Trivy vulnerability scanning, dependency checks
3. **Semantic Versioning**: Automatic version generation and tagging
4. **Container Building**: Multi-stage Docker builds with metadata
5. **GitOps Update**: Automatic manifest updates via repository dispatch

### Build Labels
Each container includes rich metadata:
```dockerfile
LABEL org.opencontainers.image.version="1.2.34"
LABEL org.opencontainers.image.revision="abc1234"
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL service="service-name"
LABEL commit="abc1234"
LABEL build-date="2023-07-07T15:30:00Z"
```

## Architecture Patterns

### Two-Tier Crossplane Architecture

```
Host Cluster (EKS)
├── Crossplane Control Plane
├── AppContainerClaim Compositions
└── VClusterEnvironmentClaim Compositions

vCluster (Application Environment)
├── Crossplane (Application Management)
├── AppContainerClaim (Create new containers)
├── ApplicationClaim (Add microservices)
├── Knative Serving
├── ArgoCD (GitOps)
└── Observability Stack
```

### AppContainer Pattern

1. **AppContainerClaim** creates:
   - Source repository with microservices structure
   - GitOps repository with ArgoCD App-of-Apps
   - CI/CD pipeline for automatic deployments

2. **ApplicationClaim** adds:
   - Individual microservices to existing containers
   - Database and cache infrastructure
   - GitOps manifests and OAM components

## Production Considerations

### Security
- **Secrets Management**: Use External Secrets Operator for production
- **Network Policies**: Implement pod-to-pod communication restrictions
- **RBAC**: Service-specific service accounts with minimal permissions
- **Image Security**: Regular vulnerability scanning and updates

### Scaling
- **Database**: Consider RDS or CloudSQL for production workloads
- **Cache**: Consider ElastiCache or Cloud Memorystore
- **Storage**: Use appropriate storage classes for persistence
- **Monitoring**: Enable ServiceMonitor for Prometheus metrics

### Backup and Recovery
- **Database Backup**: Configure automated backups
- **Persistent Volume Snapshots**: Regular storage snapshots
- **GitOps Recovery**: Infrastructure as Code enables full recovery

## Examples

See `test-application-claim-full.yaml` for complete examples including:
- Minimal microservice (no dependencies)
- Full-featured service (database + cache + API Gateway)
- Custom container integration
- Java SpringBoot service example

## Troubleshooting

### Database Connection Issues
1. Check secret creation: `kubectl get secret service-name-postgres-secret`
2. Verify database pod status: `kubectl get pods -l app.kubernetes.io/name=postgresql`
3. Test connection: `kubectl exec -it pod -- psql -h localhost -U username -d dbname`

### Cache Connection Issues
1. Check Redis secret: `kubectl get secret service-name-redis-secret`
2. Verify Redis pods: `kubectl get pods -l app.kubernetes.io/name=redis`
3. Test connection: `kubectl exec -it pod -- redis-cli -a password ping`

### CI/CD Pipeline Issues
1. Check workflow detection: Verify changes are in `microservices/service-name/`
2. Review build logs in GitHub Actions
3. Confirm GitOps repository dispatch events
4. Verify ArgoCD application sync status