# Enhanced Secret Management for WebService Integration

This guide demonstrates the enhanced secret management system that enables automatic discovery and injection of realtime platform secrets into webservice components.

## Overview

The enhanced secret management system provides:

1. **Standardized Secret Naming**: `{platform-name}-{service}-secret` pattern
2. **Cross-Component Discovery**: Webservices can automatically find realtime platform secrets
3. **Automatic Injection**: Secrets are injected when `realtime: platform-name` is specified
4. **Validation**: Integration validation before deployment

## Quick Start

### 1. Basic WebService with Realtime Integration

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: integrated-health-app
spec:
  components:
  # Realtime platform provides infrastructure
  - name: health-streaming
    type: realtime-platform
    properties:
      database: postgres
      visualization: metabase
      iot: true
      
  # Webservice automatically discovers and uses the platform's secrets
  - name: health-api
    type: webservice
    properties:
      image: health-api:latest
      port: 8080
      realtime: health-streaming  # 🆕 Auto-discovers Kafka, MQTT, DB secrets
```

### 2. What Gets Created Automatically

When you specify `realtime: health-streaming`, the webservice automatically:

- **Discovers secrets** following the pattern: `health-streaming-{service}-secret`
- **Injects secret references** into the container's `envFrom`
- **Adds environment variables**:
  - `REALTIME_PLATFORM_NAME=health-streaming`
  - `REALTIME_INTEGRATION_ENABLED=true`
  - `WEBSERVICE_NAME=health-api`
- **Validates secrets** using an init container
- **Creates integration annotations** for monitoring

### 3. Available Secrets by Service Type

The system discovers these standardized secret types:

| Service Type | Secret Name Pattern | Environment Variables |
|--------------|--------------------|--------------------|
| Kafka | `{platform}-kafka-secret` | `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SCHEMA_REGISTRY_URL` |
| MQTT | `{platform}-mqtt-secret` | `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD` |
| Database | `{platform}-db-secret` | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| Metabase | `{platform}-metabase-secret` | `METABASE_URL`, `METABASE_USER`, `METABASE_PASSWORD` |
| Lenses | `{platform}-lenses-secret` | `LENSES_URL`, `LENSES_USER`, `LENSES_PASSWORD` |

## Advanced Usage

### 1. Manual Secret Injection

If you need more control, use the SecretInjectorClaim directly:

```yaml
apiVersion: platform.example.org/v1alpha1
kind: SecretInjectorClaim
metadata:
  name: custom-integration
  namespace: my-namespace
spec:
  webserviceName: "my-api"
  realtimePlatformName: "my-streaming-platform"
  namespace: "my-namespace"
  validationMode: "strict"
  requiredServices: ["kafka", "db", "mqtt"]
  injectionStrategy: "immediate"
```

### 2. Using Secrets in Your Application Code

With the enhanced secret loader in the `agent-common` library:

```python
from agent_common.secret_loader import (
    load_and_inject_realtime_secrets,
    validate_webservice_realtime_integration,
    PlatformSecretLoader
)

# Automatic discovery and configuration
async def configure_app_with_realtime():
    # Environment variables are automatically available
    platform_name = os.getenv("REALTIME_PLATFORM_NAME")
    webservice_name = os.getenv("WEBSERVICE_NAME")
    
    if platform_name:
        # Load all platform secrets
        loader = PlatformSecretLoader(platform_name)
        secrets = await loader.load_platform_secrets()
        
        # Validate integration
        validation = await validate_webservice_realtime_integration(
            webservice_name, platform_name
        )
        
        if validation['status'] == 'ready':
            logger.info(f"Integration ready: {validation['available_services']}")
        else:
            logger.warning(f"Integration issues: {validation['recommendations']}")
        
        return secrets
    
    return {}

# Use in FastAPI application
from agent_common import create_agent_app, BaseMicroserviceAgent

class HealthStreamingAgent(BaseMicroserviceAgent):
    async def initialize(self):
        # Secrets are automatically loaded from environment
        self.platform_secrets = await configure_app_with_realtime()
        
        if self.platform_secrets.get('kafka_bootstrap_servers'):
            await self.setup_kafka_client()
        
        if self.platform_secrets.get('mqtt_host'):
            await self.setup_mqtt_client()

app = create_agent_app(HealthStreamingAgent)
```

### 3. Environment Variables Available

When `realtime: platform-name` is specified, these environment variables are automatically injected:

#### Core Integration Variables
```bash
REALTIME_PLATFORM_NAME="health-streaming"
REALTIME_INTEGRATION_ENABLED="true"
WEBSERVICE_NAME="health-api"
```

#### Service-Specific Variables (from secrets)
```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS="health-streaming-kafka:9092"
KAFKA_SCHEMA_REGISTRY_URL="http://health-streaming-schema-registry:8081"

# MQTT  
MQTT_HOST="health-streaming-mqtt"
MQTT_PORT="1883"
MQTT_USER="iot_user"
MQTT_PASSWORD="secure_password"

# Database
DB_HOST="health-streaming-postgres"
DB_PORT="5432"
DB_NAME="health_streaming_db"
DB_USER="api_user"
DB_PASSWORD="secure_password"

# Metabase
METABASE_URL="http://health-streaming-metabase:3000"
METABASE_USER="dashboard_user"
METABASE_PASSWORD="secure_password"

# Lenses
LENSES_URL="http://health-streaming-lenses-hq:9991"
LENSES_USER="stream_user"
LENSES_PASSWORD="secure_password"
```

## Validation and Troubleshooting

### 1. Check Integration Status

```bash
# Check webservice annotations
kubectl get ksvc health-api -o yaml | grep realtime.platform.example.org

# Check integration secret
kubectl get secret health-api-health-streaming-integration -o yaml

# Check secret injection job logs
kubectl logs job/health-api-secret-injector
```

### 2. Validate Secret Discovery

```bash
# List all discoverable secrets for a platform
kubectl get secrets -l "realtime.platform.example.org/name=health-streaming"

# Check secret contents (be careful with sensitive data)
kubectl get secret health-streaming-kafka-secret -o jsonpath='{.data}' | base64 -d
```

### 3. Common Integration Patterns

#### Pattern 1: REST API with Kafka Publishing
```yaml
- name: order-api
  type: webservice
  properties:
    image: order-api:latest
    realtime: order-streaming  # Gets Kafka + DB secrets
    environment:
      SERVICE_TYPE: "rest-api"
      ENABLE_KAFKA_PUBLISHING: "true"
```

#### Pattern 2: IoT Data Processor
```yaml
- name: sensor-processor
  type: webservice
  properties:
    image: sensor-processor:latest
    realtime: iot-platform  # Gets MQTT + Kafka + DB secrets
    environment:
      SERVICE_TYPE: "iot-processor"
      MQTT_TOPICS: "sensors/+/data"
```

#### Pattern 3: Analytics Dashboard Backend
```yaml
- name: analytics-api
  type: webservice
  properties:
    image: analytics-api:latest
    realtime: analytics-platform  # Gets Metabase + DB secrets
    environment:
      SERVICE_TYPE: "analytics"
      DASHBOARD_INTEGRATION: "enabled"
```

## Security Considerations

### 1. Secret Lifecycle Management

- **Automatic Rotation**: Secrets are mounted as volumes and update automatically
- **Least Privilege**: Only necessary secrets are injected based on service type
- **Audit Trail**: All injection activities are logged and annotated

### 2. Network Security

- **Service Mesh**: All communication goes through Istio for encryption
- **Namespace Isolation**: Secrets are scoped to their respective namespaces
- **RBAC**: SecretInjector uses minimal required permissions

### 3. Monitoring and Alerting

```bash
# Monitor secret injection status
kubectl get secretinjectors -o wide

# Check for failed injections
kubectl get events --field-selector reason=SecretInjectionFailed

# Monitor secret access patterns
kubectl logs -l app.kubernetes.io/component=secret-integration
```

## Migration Guide

### From Manual Secret Management

**Before** (Manual approach):
```yaml
- name: my-api
  type: webservice
  properties:
    image: my-api:latest
    envFrom:
    - secretRef:
        name: manually-created-kafka-secret
    - secretRef:
        name: manually-created-db-secret
    environment:
      KAFKA_BROKERS: "localhost:9092"  # Hardcoded
```

**After** (Automatic discovery):
```yaml
- name: my-api
  type: webservice
  properties:
    image: my-api:latest
    realtime: my-platform  # Automatically discovers and injects secrets
```

### Migration Steps

1. **Deploy realtime platform** with standardized naming
2. **Update webservice definition** to use `realtime` parameter
3. **Update application code** to use environment variables
4. **Remove manual secret references**
5. **Test integration** using validation tools

## Best Practices

### 1. Naming Conventions

- **Platform names**: Use kebab-case (`health-streaming`, `iot-platform`)
- **Webservice names**: Use kebab-case (`health-api`, `sensor-processor`)
- **Namespaces**: Group related components (`health-production`, `iot-staging`)

### 2. Development Workflow

1. **Create realtime platform** first
2. **Verify secrets are created** using standardized naming
3. **Deploy webservice** with `realtime` parameter
4. **Validate integration** using SecretInjectorClaim if needed
5. **Monitor and debug** using provided tools

### 3. Testing

```python
# Unit test for secret integration
async def test_realtime_integration():
    validation = await validate_webservice_realtime_integration(
        "test-api", "test-platform"
    )
    assert validation['status'] == 'ready'
    assert 'kafka' in validation['available_services']

# Integration test
async def test_secret_loading():
    secrets = await load_realtime_platform_secrets("test-platform")
    assert secrets['kafka_bootstrap_servers'] is not None
    assert secrets['db_host'] is not None
```

## Troubleshooting Guide

### Common Issues

#### 1. No secrets discovered
```
Error: No secrets discovered for realtime platform: my-platform
```
**Solution**: Verify the realtime platform is deployed and secrets follow naming convention

#### 2. Webservice not found
```
Warning: Webservice not found: my-api
```
**Solution**: Deploy webservice first, or create SecretInjectorClaim after deployment

#### 3. Permission denied
```
Error: Failed to label secret my-platform-kafka-secret
```
**Solution**: Ensure SecretInjector ServiceAccount has proper RBAC permissions

### Debug Commands

```bash
# Check secret naming patterns
kubectl get secrets | grep -E ".*-(kafka|mqtt|db|metabase|lenses)-secret"

# Validate SecretInjector deployment
kubectl get secretinjectors -o yaml

# Check job logs for detailed output
kubectl logs -l app.kubernetes.io/component=secret-management

# Validate RBAC permissions
kubectl auth can-i create secrets --as=system:serviceaccount:default:secret-injector-sa
```

## Performance Considerations

- **Secret Discovery**: O(n) where n is number of expected secret types (5 max)
- **Injection Time**: Typically completes within 30-60 seconds
- **Memory Overhead**: Minimal - only metadata is stored in integration secrets
- **Network Impact**: Secrets are mounted as volumes, no continuous polling

## Future Enhancements

1. **Automatic Secret Rotation**: Integration with external secret managers
2. **Advanced Validation**: Health checks for secret connectivity
3. **Multi-Platform Support**: Discovery across multiple realtime platforms
4. **Backup and Recovery**: Secret backup and restoration capabilities
5. **Metrics and Monitoring**: Prometheus metrics for secret usage patterns

---

For more information, see:
- [REALTIME_SYSTEM.md](../REALTIME_SYSTEM.md) - Realtime platform architecture
- [ARCHITECTURAL_DECISIONS.md](../ARCHITECTURAL_DECISIONS.md) - Design decisions
- [crossplane/DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md) - Infrastructure development