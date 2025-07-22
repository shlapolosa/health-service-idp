# Realtime Platform ComponentDefinitions Guide

This guide explains how to use the new realtime platform ComponentDefinitions that provide ultra-minimal interfaces for building real-time streaming applications.

## 🎯 Overview

The realtime platform provides four main ComponentDefinitions:

1. **`realtime-platform`** - Complete streaming infrastructure (Kafka + MQTT + Lenses + Metabase)
2. **`iot-broker`** - MQTT broker for IoT device connectivity
3. **`stream-processor`** - Lenses-based stream processing component
4. **`analytics-dashboard`** - Analytics dashboards (Metabase/Grafana)

## 🚀 Quick Start

### Minimal Setup

The simplest way to get started:

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: my-realtime-app
spec:
  components:
  - name: my-platform
    type: realtime-platform
    properties:
      name: simple-streaming
      # Everything else uses defaults
```

This creates a complete streaming platform with:
- ✅ PostgreSQL database
- ✅ Kafka cluster with Schema Registry
- ✅ MQTT broker for IoT devices
- ✅ Lenses HQ/Agent for stream processing
- ✅ Metabase for analytics
- ✅ All connection secrets automatically generated

### Using the Platform

Once you have a realtime platform, you can reference it from other services:

```yaml
- name: my-service
  type: webservice
  properties:
    name: my-realtime-service
    language: python
    framework: fastapi
    realtime: "simple-streaming"  # References the platform above
    websocket: true
    streaming:
      enabled: true
      topics: ["my_topic"]
```

## 📋 ComponentDefinition Reference

### 1. realtime-platform

**Purpose**: Complete streaming infrastructure in a single component

**Required Parameters**:
- `name` - Platform instance name (DNS-compliant, max 63 chars)

**Optional Parameters**:
```yaml
properties:
  name: my-platform
  database: postgres          # postgres | mysql
  visualization: metabase     # metabase | grafana  
  iot: true                   # Enable MQTT broker
  
  # Advanced configuration
  lensesConfig:
    licenseKey: "your-license"
    heapSize: "1536m"
    enableUI: true
  
  mqttConfig:
    users:
      - username: device-001
        password: secure-pass
    persistenceSize: "5Gi"
    enableWebSockets: true
    qosLevel: 1
  
  kafkaConfig:
    topics: ["topic1", "topic2"]
    retention: "24h"
    partitions: 3
    replicationFactor: 1
  
  snowflakeConfig:
    enabled: false
    credentialsSecret: "snowflake-creds"
    database: "ANALYTICS"
    schema: "STREAMING"
  
  resources:
    cpu: "2000m"
    memory: "4Gi"
  
  scaling:
    minReplicas: 1
    maxReplicas: 3
    targetCPU: 70
```

**What it Creates**:
- Kafka cluster with Schema Registry and Connect
- Eclipse Mosquitto MQTT broker
- Lenses HQ and Agent for stream processing
- Metabase analytics dashboard
- PostgreSQL database for metadata
- All connection secrets with standardized naming

**Generated Secrets**:
- `{name}-mqtt-secret` - MQTT connection details
- `{name}-kafka-secret` - Kafka connection details
- `{name}-db-secret` - Database connection details
- `{name}-metabase-secret` - Analytics dashboard access
- `{name}-lenses-secret` - Stream processing UI access

### 2. iot-broker

**Purpose**: Standalone MQTT broker with Kafka integration

**Required Parameters**:
- `name` - Broker instance name

**Optional Parameters**:
```yaml
properties:
  name: my-iot-broker
  mqttPort: 1883
  websocketPort: 9001
  
  authentication:
    enabled: true
    users:
      - username: device-001
        password: secure-pass
  
  topics:
    - "sensors/temperature"
    - "sensors/humidity"
  
  connector:
    enabled: true
    kafkaTopic: "sensor_data"
    mqttTopic: "sensors/+"
    keyField: "deviceId"
    qos: 1
    errorPolicy: "RETRY"
  
  persistence:
    enabled: true
    size: "5Gi"
```

**Use Cases**:
- Dedicated MQTT broker for specific device types
- Custom topic structures
- Specialized authentication requirements
- Integration with existing Kafka clusters

### 3. stream-processor

**Purpose**: Lenses-based stream processing without full platform

**Required Parameters**:
- `name` - Processor instance name

**Optional Parameters**:
```yaml
properties:
  name: my-processor
  
  queries:
    - name: data-transformation
      sql: |
        INSERT INTO output_topic
        SELECT STREAM
            _value.id AS _key,
            STRUCT(
              id := _value.id,
              processed_data := UPPER(_value.data),
              timestamp := UNIX_TIMESTAMP() * 1000
            ) AS _value
        FROM input_topic
    
    - name: filtering
      sql: |
        INSERT INTO filtered_topic
        SELECT STREAM *
        FROM input_topic
        WHERE _value.priority = 'HIGH'
  
  topics:
    input: ["input_topic"]
    output: ["output_topic", "filtered_topic"]
  
  errorHandling:
    policy: "RETRY"
    retries: 3
    deadLetterTopic: "errors"
  
  processing:
    parallelism: 2
    checkpointInterval: "30s"
    stateBackend: "memory"
```

**Use Cases**:
- Custom stream processing logic
- Data transformation pipelines
- Real-time analytics
- Event routing and filtering

### 4. analytics-dashboard

**Purpose**: Analytics dashboard without full platform infrastructure

**Required Parameters**:
- `name` - Dashboard instance name

**Optional Parameters**:
```yaml
properties:
  name: my-dashboard
  dashboardType: metabase  # metabase | grafana
  
  dataSources:
    - name: kafka-data
      type: kafka
      connectionString: "kafka://my-kafka:9092"
    - name: postgres-data
      type: postgres
      secretRef: "my-db-secret"
    - name: snowflake-data
      type: snowflake
      secretRef: "snowflake-secret"
  
  dashboards:
    - name: overview
      template: "standard-overview"
      autoCreate: true
    - name: real-time-metrics
      template: "streaming-metrics"
      autoCreate: true
  
  alerts:
    enabled: true
    channels:
      - type: email
        config:
          recipients: ["team@company.com"]
      - type: slack
        config:
          webhook: "https://hooks.slack.com/..."
  
  authentication:
    enabled: true
    provider: "internal"  # internal | oauth | ldap
```

**Use Cases**:
- Custom analytics requirements
- Integration with existing dashboards
- Specialized visualization needs
- Multi-tenant analytics

## 🏗️ Architecture Patterns

### Pattern 1: All-in-One Platform

**Best for**: New projects, prototyping, simple applications

```yaml
components:
- name: complete-platform
  type: realtime-platform
  properties:
    name: my-app
    # Uses all defaults - simplest possible setup
```

**Benefits**:
- ✅ Minimal configuration
- ✅ Everything works together out-of-the-box
- ✅ Automatic secret management
- ✅ Integrated monitoring

### Pattern 2: Microservices Architecture

**Best for**: Large applications, team separation, specialized requirements

```yaml
components:
# Core infrastructure
- name: kafka-platform
  type: realtime-platform
  properties:
    name: core-streaming
    iot: false  # No MQTT needed
    
# Specialized IoT broker
- name: iot-devices
  type: iot-broker
  properties:
    name: device-network
    connector:
      kafkaTopic: "device_events"
      
# Custom stream processing
- name: analytics-processor
  type: stream-processor
  properties:
    name: analytics-engine
    queries:
      - name: real-time-aggregation
        sql: "SELECT STREAM ..."
```

**Benefits**:
- ✅ Component isolation
- ✅ Independent scaling
- ✅ Specialized configuration
- ✅ Team ownership boundaries

### Pattern 3: Multi-Environment

**Best for**: Organizations with dev/staging/prod environments

```yaml
# Development
- name: dev-platform
  type: realtime-platform
  properties:
    name: dev-streaming
    resources:
      cpu: "500m"
      memory: "1Gi"
    kafkaConfig:
      retention: "1h"

# Production
- name: prod-platform
  type: realtime-platform
  properties:
    name: prod-streaming
    resources:
      cpu: "4000m"
      memory: "8Gi"
    scaling:
      minReplicas: 3
      maxReplicas: 10
    kafkaConfig:
      retention: "30d"
      replicationFactor: 3
```

## 🔧 Integration with Applications

### WebService Integration

Any webservice can connect to a realtime platform:

```yaml
- name: my-app
  type: webservice
  properties:
    name: my-realtime-app
    realtime: "my-platform"  # Platform name
    websocket: true          # Enable WebSocket endpoints
    streaming:
      enabled: true
      topics: ["events", "metrics"]
      consumerGroup: "my-app-group"
    environment:
      CUSTOM_CONFIG: "value"
```

**Automatic Injections**:
When `realtime: "my-platform"` is specified, the service automatically receives:
- Environment variables for all connection details
- Kubernetes secrets mounted as files
- Network policies for secure communication
- Health check configurations

### Secret Management

All platforms automatically generate standardized secrets:

```bash
# MQTT Connection
MQTT_HOST=my-platform-mqtt.namespace.svc.cluster.local
MQTT_PORT=1883
MQTT_USER=realtime-user
MQTT_PASSWORD=generated-password

# Kafka Connection
KAFKA_BOOTSTRAP_SERVERS=my-platform-kafka.namespace.svc.cluster.local:9092
KAFKA_SCHEMA_REGISTRY_URL=http://my-platform-kafka.namespace.svc.cluster.local:8081

# Database Connection
DB_HOST=my-platform-postgres.namespace.svc.cluster.local
DB_PORT=5432
DB_NAME=myplatform
DB_USER=realtime
DB_PASSWORD=generated-password

# Analytics Dashboard
METABASE_URL=http://my-platform-metabase.namespace.svc.cluster.local:3000
METABASE_USER=admin@example.com
METABASE_PASSWORD=generated-password

# Stream Processing UI
LENSES_URL=http://my-platform-lenses-hq.namespace.svc.cluster.local:9991
LENSES_USER=admin
LENSES_PASSWORD=admin
```

## 📊 Monitoring and Observability

### Health Checks

All components automatically include:
- Kubernetes readiness and liveness probes
- Health check endpoints
- Dependency health validation
- Service discovery integration

### Metrics

Each platform exposes metrics for:
- Message throughput and latency
- Connection counts and status
- Resource utilization
- Error rates and types

### Logging

Structured logging includes:
- Correlation IDs for request tracing
- Component-specific log levels
- Integration with log aggregation systems
- Error categorization and alerting

## 🔒 Security Best Practices

### Authentication

```yaml
mqttConfig:
  users:
    - username: production-device
      password: "use-strong-passwords"
    - username: staging-device  
      password: "different-per-environment"
```

### Network Security

- All inter-service communication uses Kubernetes service DNS
- Network policies automatically restrict access
- TLS encryption for external connections
- Secret rotation capabilities

### Access Control

- Role-based access to analytics dashboards
- API key management for external integrations
- Audit logging for administrative actions

## 🚀 Deployment Strategies

### GitOps Deployment

```yaml
# applications/my-app.yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: production-realtime-app
spec:
  components:
  - name: prod-platform
    type: realtime-platform
    properties:
      name: prod-streaming
      # Configuration from git
```

### Blue-Green Deployment

```yaml
# Blue environment
- name: blue-platform
  type: realtime-platform
  properties:
    name: blue-streaming

# Green environment  
- name: green-platform
  type: realtime-platform
  properties:
    name: green-streaming
```

### Canary Deployment

Use traffic splitting traits to gradually roll out changes:

```yaml
traits:
- type: traffic-split
  properties:
    blue: 90
    green: 10
```

## 📚 Examples and Templates

See `realtime-platform-examples.yaml` for complete examples:

1. **Simple Setup** - Minimal configuration
2. **Health Platform** - Healthcare IoT applications
3. **IoT Sensors** - Sensor data collection
4. **Financial Trading** - High-throughput financial data
5. **Shared Platform** - Multiple applications
6. **Development** - Testing and development environments

## 🤝 Contributing

To extend these ComponentDefinitions:

1. **Add New Parameters** - Extend the CUE parameter schema
2. **Custom Templates** - Create specialized templates for your use case
3. **Integration Points** - Add connections to new external systems
4. **Documentation** - Update examples and guides

## 📖 Related Documentation

- [Ping-Pong Template Guide](./PING-PONG-TEMPLATE-GUIDE.md)
- [ApplicationClaim Reference](../APPLICATION-CLAIM-GUIDE.md)
- [Realtime System Architecture](../../REALTIME_SYSTEM.md)
- [OAM Specification](https://oam.dev/)

---

These ComponentDefinitions provide the foundation for building scalable, production-ready real-time streaming applications with minimal complexity and maximum flexibility.