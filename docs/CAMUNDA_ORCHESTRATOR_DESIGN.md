# 🎼 Camunda Orchestrator OAM Component Design

## Overview

The **Camunda Orchestrator** OAM ComponentDefinition provides enterprise-grade workflow orchestration for microservices using Camunda 8. It implements modern orchestration patterns including SAGA, choreography, and event-driven architectures while integrating seamlessly with the existing OAM-based platform.

## Architecture Patterns

### 🔄 Orchestration vs Choreography

**Orchestration (Command-driven)**
- Central workflow engine (Camunda 8) coordinates microservices
- BPMN workflows define business processes
- Explicit control flow and error handling
- Centralized monitoring and analytics

**Choreography (Event-driven)**  
- Services communicate through events via realtime-platform
- Decentralized decision making
- Event sourcing and eventual consistency
- Integration with Kafka/Redis streams

**Hybrid Approach**
- Use orchestration for critical business processes
- Use choreography for loose coupling and scalability
- Event-driven triggers can start orchestrated workflows

### 🎯 SAGA Pattern Implementation

**Compensation-based SAGAs**
```
Service A → Service B → Service C
    ↓         ↓         ↓
Compensate A ← Compensate B ← Compensate C (if failure)
```

**Timeout-based SAGAs**
- Automatic timeouts for long-running transactions
- Configurable retry policies with exponential backoff
- Dead letter queues for failed compensations

### 🔍 Service Discovery Integration

The orchestrator automatically discovers microservices using Kubernetes service selectors:
```yaml
orchestration.platform/managed: "true"
```

Services that want to participate in orchestrated workflows should include this label.

## Component Configuration

### Basic Usage

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: payment-orchestrator
spec:
  components:
  - name: payment-workflow-engine
    type: camunda-orchestrator
    properties:
      realtimePlatform: "payment-events-platform"
      camundaMode: "embedded"
      enableEventStreaming: true
      sagaPatterns: ["compensation", "timeout", "retry"]
```

### Advanced Configuration

```yaml
- name: complex-orchestrator
  type: camunda-orchestrator
  properties:
    realtimePlatform: "enterprise-events-platform"
    camundaMode: "remote"  # Use Camunda SaaS
    enableEventStreaming: true
    topicsPrefix: "enterprise-workflows"
    language: "java"       # Triggers repository creation
    framework: "camunda-orchestrator"
    repository: "enterprise-workflows"
    enableIstioGateway: true
    gatewayHost: "workflows.enterprise.local"
    resources:
      cpu: "2000m"
      memory: "2Gi"
    environment:
      CAMUNDA_CLIENT_ID: "enterprise-client"
      LOGGING_LEVEL: "INFO"
```

## Integration Patterns

### 🔗 Realtime Platform Integration

The orchestrator integrates with `realtime-platform` services for:

**Event Publishing**
- Workflow state changes → events
- Service call results → events  
- Compensation triggers → events

**Event Consumption**
- External events → workflow triggers
- Microservice responses → workflow continuation
- Error events → compensation workflows

### 📊 Microservice Coordination

**Service Task Patterns**
```java
// Auto-discovered service calls
zbc.createWorker()
  .taskType("call-microservice-a")
  .handler((client, job) -> {
    // Discover service endpoint
    String serviceUrl = discoveryService.findService("service-a");
    
    // Call microservice
    ResponseEntity result = restTemplate.postForEntity(
      serviceUrl + "/api/process", 
      job.getVariables(), 
      ResponseEntity.class
    );
    
    // Complete workflow task
    return job.complete(result.getBody());
  })
  .open();
```

**Event-Driven Task Patterns**
```java
// Publish event and wait for response
zbc.createWorker()
  .taskType("publish-and-wait")
  .handler((client, job) -> {
    // Publish event via realtime platform
    eventPublisher.publish("service-a-requested", job.getVariables());
    
    // Workflow will continue when response event is received
    return job.complete();
  })
  .open();
```

## Infrastructure Components

### 🗄️ Database Layer
- **PostgreSQL**: Workflow state persistence
- **Redis**: Caching and session management
- **Event Store**: Integration with realtime-platform

### 🔐 Security & RBAC
- Service accounts for Kubernetes API access
- RBAC for service discovery
- Secret management for external integrations

### 📈 Observability
- **Health Checks**: `/actuator/health`, `/actuator/ready`
- **Metrics**: Prometheus integration
- **Tracing**: Integration with existing observability stack
- **Process Analytics**: Camunda Operate integration

## Workflow Templates

### 🏭 Microservice Orchestration Template
```xml
<!-- Basic parallel microservice coordination -->
<bpmn:parallelGateway id="split" />
<bpmn:serviceTask id="serviceA" name="Call Service A">
  <zeebe:taskDefinition type="call-microservice-a" />
</bpmn:serviceTask>
<bpmn:serviceTask id="serviceB" name="Call Service B">  
  <zeebe:taskDefinition type="call-microservice-b" />
</bpmn:serviceTask>
<bpmn:parallelGateway id="join" />
```

### 🔄 SAGA Compensation Template
```xml
<!-- Compensation-enabled workflow steps -->
<bpmn:serviceTask id="step1" name="Execute Step 1">
  <zeebe:taskDefinition type="saga-step-1" />
</bpmn:serviceTask>
<bpmn:serviceTask id="compensate1" name="Compensate Step 1" 
                 isForCompensation="true">
  <zeebe:taskDefinition type="compensate-step-1" />
</bpmn:serviceTask>
```

## Development Workflow

### 🛠️ Repository Creation
When `language` and `framework` are specified, the system creates:

1. **Source Repository**: 
   - Spring Boot + Camunda 8 application
   - BPMN workflow definitions
   - Service task implementations
   - Integration tests

2. **GitOps Repository**:
   - Knative service definitions
   - ConfigMaps for workflows
   - Service discovery configurations

### 🧪 Testing Strategies
- **Unit Tests**: Individual workflow step testing
- **Integration Tests**: End-to-end workflow execution
- **Contract Tests**: Microservice interaction validation
- **Chaos Engineering**: Failure scenario testing

## Operational Considerations

### 🔧 Configuration Management
- **Workflow Models**: Stored in ConfigMaps, versioned
- **Connection Secrets**: Managed via Kubernetes secrets
- **Environment-specific**: Different configs per deployment

### 📊 Monitoring & Alerting
- Workflow execution metrics
- Service discovery health
- Event streaming connectivity
- Compensation pattern success rates

### 🔄 Upgrade Strategies
- Blue/green deployment support
- Workflow version migration
- Backward compatibility for running instances

## Integration Examples

### E-commerce Order Processing
```yaml
- name: order-orchestrator
  type: camunda-orchestrator
  properties:
    realtimePlatform: "order-events"
    sagaPatterns: ["compensation", "timeout"]
    # Coordinates: payment, inventory, shipping, notification services
```

### Healthcare Patient Journey
```yaml  
- name: patient-care-orchestrator
  type: camunda-orchestrator
  properties:
    realtimePlatform: "patient-events"
    enableEventStreaming: true
    # Coordinates: scheduling, clinical, billing, compliance services
```

### Financial Transaction Processing
```yaml
- name: transaction-orchestrator  
  type: camunda-orchestrator
  properties:
    realtimePlatform: "transaction-events"
    camundaMode: "remote"  # Use Camunda SaaS for compliance
    sagaPatterns: ["compensation", "timeout", "retry"]
    # Coordinates: fraud-detection, authorization, settlement services
```

This design provides a comprehensive, production-ready orchestration solution that integrates seamlessly with the existing OAM platform while leveraging Camunda 8's enterprise-grade workflow capabilities.