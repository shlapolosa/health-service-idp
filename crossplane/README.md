# Crossplane Infrastructure Compositions

This directory contains Crossplane compositions and resource definitions that power the Health Service IDP infrastructure provisioning. The system supports **two primary use cases** for infrastructure management:

## 🚀 Use Cases

### Use Case 1: Crossplane ApplicationClaim Workflow (Guided)
For developers who want automatic infrastructure provisioning through ApplicationClaims:

```yaml
# Create an ApplicationClaim
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
spec:
  name: my-health-service
  language: python
  framework: fastapi
  database: postgres
  cache: redis
  realtime: health-streaming  # Creates complete streaming platform

# Flow: ApplicationClaim → Crossplane Composition → Infrastructure Resources → GitOps → ArgoCD
```

### Use Case 2: Direct OAM Application Management (Expert)
For developers who want to define infrastructure components directly in OAM applications:

```yaml
# In oam/applications/application.yaml
spec:
  components:
  # Infrastructure component → Creates Crossplane Claims
  - name: streaming-platform
    type: realtime-platform
    properties:
      name: health-streaming
      database: postgres
      visualization: metabase
      iot: true

# Flow: OAM Component → KubeVela → Crossplane Claim → Infrastructure Resources
```

## 🏗️ Architecture Overview

### Crossplane Compositions
- **`application-claim-composition.yaml`** - Main composition for ApplicationClaims (Use Case 1)
- **`realtime-platform-composition.yaml`** - Real-time streaming infrastructure
- **`app-container-claim-composition.yaml`** - Container and repository management

### OAM Integration
- **`oam/`** - OAM ComponentDefinitions and workload definitions
- **`realtime-xrds.yaml`** - Composite Resource Definitions for real-time components
- **`oam/crossplane-compositions.yaml`** - Additional infrastructure compositions

### Infrastructure Types Supported

**Application Infrastructure:**
- Knative services with auto-scaling
- PostgreSQL/MySQL databases
- Redis caching layers
- Container registries and repositories

**Real-time Platform Infrastructure:**
- Complete Kafka clusters with Schema Registry
- MQTT brokers for IoT connectivity
- Lenses stream processing platforms
- Metabase/Grafana analytics dashboards
- Snowflake data warehouse integration

**Cloud Infrastructure:**
- VCluster virtual Kubernetes environments
- Auth0 identity provider integration
- Network policies and security configurations
- Observability and monitoring stacks

## 🔄 Composition Workflows

### Use Case 1: ApplicationClaim Processing

1. **ApplicationClaim Created**
   ```yaml
   apiVersion: platform.example.org/v1alpha1
   kind: ApplicationClaim
   spec:
     name: health-analyzer
     language: python
     realtime: health-streaming
   ```

2. **Crossplane Composition Triggered**
   - `application-claim-composition.yaml` processes the claim
   - Creates infrastructure resources (databases, caches, real-time platforms)
   - Generates Knative service definitions
   - Updates GitOps repository with OAM application

3. **GitOps Repository Updated**
   ```
   health-service-idp-gitops/
   ├── oam/applications/application.yaml    # Updated with new components
   ├── crossplane/claims/                   # Infrastructure claims
   └── argocd/applications/                 # ArgoCD configurations
   ```

4. **ArgoCD Deployment**
   - Monitors `oam/applications/` directory
   - Syncs OAM application to KubeVela
   - KubeVela creates Knative services and processes infrastructure claims

### Use Case 2: Direct OAM Component Processing

1. **OAM Application Updated**
   ```yaml
   # Manually edit oam/applications/application.yaml
   components:
   - name: new-realtime-platform
     type: realtime-platform
     properties:
       name: analytics-streaming
       database: postgres
       iot: true
   ```

2. **ArgoCD Sync**
   - Detects changes in GitOps repository
   - Syncs to KubeVela in the cluster

3. **KubeVela Processing**
   - Processes OAM components
   - For `realtime-platform` type: creates `RealtimePlatformClaim`
   - For `webservice` type: creates Knative services directly

4. **Crossplane Processing**
   - Processes infrastructure claims (if any)
   - Creates cloud resources (databases, message queues, etc.)
   - Updates status and connection secrets

## 📋 Component Types Reference

### Application Components (→ Knative Services)
- **`webservice`** - Auto-scaling web applications
- **`kafka`** - Apache Kafka event streaming  
- **`redis`** - In-memory data store
- **`mongodb`** - Document database

### Infrastructure Components (→ Crossplane Claims)
- **`realtime-platform`** - Complete streaming infrastructure
- **`vcluster`** - Virtual Kubernetes environments
- **`neon-postgres`** - Managed PostgreSQL database
- **`auth0-idp`** - Identity provider integration

### Real-time Components (→ Specialized Infrastructure)
- **`iot-broker`** - MQTT broker for IoT devices
- **`stream-processor`** - Real-time data processing
- **`analytics-dashboard`** - Analytics and visualization

## 🛠️ Development Commands

### Deploy Crossplane Compositions
```bash
# Install all compositions
kubectl apply -f crossplane/

# Install specific composition
kubectl apply -f crossplane/application-claim-composition.yaml
```

### Create ApplicationClaim (Use Case 1)
```bash
# Create from YAML
kubectl apply -f - <<EOF
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: my-health-app
spec:
  name: health-analyzer
  language: python
  framework: fastapi
  database: postgres
  realtime: health-streaming
EOF
```

### Monitor Infrastructure Creation
```bash
# Check ApplicationClaim status
kubectl get applicationclaims

# Check infrastructure resources
kubectl get realtimeplatformclaims
kubectl get neonpostgresclaims

# Check generated OAM application
kubectl get applications -n argocd
```

### Direct OAM Management (Use Case 2)
```bash
# Edit OAM application directly
kubectl edit application health-service-app -n argocd

# Or update via GitOps repository
git clone https://github.com/socrates12345/health-service-idp-gitops
# Edit oam/applications/application.yaml
# Commit and push - ArgoCD will sync automatically
```

## 🔧 Configuration Examples

### Complete ApplicationClaim Example
```yaml
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: comprehensive-health-app
spec:
  name: health-monitoring-system
  language: python
  framework: fastapi
  database: postgres
  cache: redis
  realtime: health-streaming
  
  # Advanced configuration
  realtimeConfig:
    iot: true
    visualization: metabase
    kafkaConfig:
      topics: ["health_events", "device_telemetry", "alerts"]
      retention: "7d"
      partitions: 6
    mqttConfig:
      users:
        - username: health-device-001
          password: secure-device-password
      enableWebSockets: true
  
  resources:
    cpu: "2000m"
    memory: "4Gi"
  
  scaling:
    minReplicas: 2
    maxReplicas: 10
    targetCPU: 70
```

### Direct OAM Component Example
```yaml
# In oam/applications/application.yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: health-service-app
spec:
  components:
  # Web service component
  - name: health-api
    type: webservice
    properties:
      image: health-api:latest
      port: 8080
      realtime: "health-streaming"
      websocket: true
      
  # Infrastructure component
  - name: streaming-platform
    type: realtime-platform
    properties:
      name: health-streaming
      database: postgres
      visualization: metabase
      iot: true
      kafkaConfig:
        topics: ["health_events"]
        retention: "24h"
        
  # Database component
  - name: app-database
    type: neon-postgres
    properties:
      name: health-db
      size: 20Gi
```

## 📊 Monitoring and Troubleshooting

### Check Composition Status
```bash
# View ApplicationClaim events
kubectl describe applicationclaim my-health-app

# Check Crossplane resources
kubectl get crossplane
kubectl get compositions

# View generated infrastructure
kubectl get realtimeplatformclaims,neonpostgresclaims,vclusters
```

### Common Issues

1. **ApplicationClaim Stuck in Pending**
   ```bash
   # Check composition status
   kubectl describe composition application-claim-composition
   
   # Check provider status
   kubectl get providers
   ```

2. **OAM Component Not Creating Infrastructure**
   ```bash
   # Check KubeVela application status
   kubectl get application -n vela-system
   
   # Check component definitions
   kubectl get componentdefinitions
   ```

3. **GitOps Sync Issues**
   ```bash
   # Check ArgoCD application status
   kubectl get applications -n argocd
   
   # View ArgoCD logs
   kubectl logs -n argocd deployment/argocd-application-controller
   ```

## 🚦 Getting Started

### Option 1: Use ApplicationClaim (Guided)
1. Create an ApplicationClaim YAML file
2. Apply: `kubectl apply -f application-claim.yaml`
3. Monitor: `kubectl get applicationclaims -w`
4. Access services via Knative ingress

### Option 2: Direct OAM Editing (Expert)
1. Clone GitOps repository: `git clone https://github.com/socrates12345/health-service-idp-gitops`
2. Edit `oam/applications/application.yaml`
3. Commit and push changes
4. ArgoCD automatically syncs and deploys

## 📚 Related Documentation

- **[OAM ComponentDefinitions Guide](oam/REALTIME-PLATFORM-GUIDE.md)** - Detailed component reference
- **[ApplicationClaim Reference](APPLICATION-CLAIM-GUIDE.md)** - Complete ApplicationClaim documentation
- **[Real-time System Architecture](../REALTIME_SYSTEM.md)** - Streaming platform details
- **[ARCHITECTURAL_DECISIONS.md](../ARCHITECTURAL_DECISIONS.md)** - Architecture evolution and decisions

---

**Infrastructure Status**: Production-ready with comprehensive real-time capabilities  
**Development Model**: Dual use case support (ApplicationClaim + Direct OAM)  
**Integration**: Full GitOps and KubeVela compatibility