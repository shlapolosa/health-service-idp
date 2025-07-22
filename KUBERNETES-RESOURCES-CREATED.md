# Kubernetes Resources Created by OAM Real-time Health Pipeline

When the OAM Application `health-realtime-pipeline` is applied, the following Kubernetes resources are automatically created through the Crossplane → KubeVela → vCluster workflow:

## 1. Host Cluster Resources (EKS Management Cluster)

### vCluster Environment
```yaml
# Created via VClusterEnvironmentClaim
apiVersion: infrastructure.cluster.x-k8s.io/v1beta1
kind: Cluster
metadata:
  name: health-streaming
  namespace: default
```

### External Secrets for Snowflake
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: snowflake-credentials
  namespace: health-streaming
spec:
  secretStoreRef:
    name: aws-secretsmanager
  target:
    name: snowflake-kafka-credentials
```

### Crossplane Claims Triggered
```yaml
# 1. vCluster Environment
apiVersion: platform.example.org/v1alpha1
kind: VClusterEnvironmentClaim
metadata:
  name: health-streaming-env
spec:
  name: health-streaming
  components:
    istio: true
    knativeServing: true
    observability: true

# 2. Real-time System (new custom claim)
apiVersion: platform.example.org/v1alpha1  
kind: RealtimeSystemClaim
metadata:
  name: health-lenses
spec:
  namespace: health-streaming
  lensesConfig: {...}
  kafkaConfig: {...}
  snowflakeConfig: {...}

# 3. IoT Broker (new custom claim)
apiVersion: platform.example.org/v1alpha1
kind: IotBrokerClaim  
metadata:
  name: health-mqtt
spec:
  namespace: health-streaming
  mqttConfig: {...}
  connectorConfig: {...}
```

## 2. vCluster Resources (health-streaming namespace)

### Core Infrastructure Components

#### PostgreSQL Database (Lenses Backend)
```yaml
apiVersion: helm.crossplane.io/v1beta1
kind: Release
metadata:
  name: lenses-backend-postgres
  namespace: health-streaming
spec:
  chart:
    name: postgresql
    repository: https://charts.bitnami.com/bitnami
  values:
    auth:
      database: lenses_system
      # Creates databases: hq, agent1, agent2, metabaseappdb
```

#### Configuration Generator Job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: lenses-config-generator
  namespace: health-streaming
spec:
  template:
    spec:
      containers:
      - name: config-creator
        image: busybox
        command: ["sh", "-c", "generate configs..."]
      volumes:
      - name: lenses-hq-config
      - name: lenses-agent-config
```

### Lenses Platform Components

#### Lenses HQ (Control Plane)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lenses-hq
  namespace: health-streaming
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lenses-hq
  template:
    spec:
      containers:
      - name: lenses-hq
        image: lensting/lenses-hq:6-preview
        ports:
        - containerPort: 9991
        env:
        - name: CONFIG_PATH
          value: "/app/config.yaml"
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
        livenessProbe:
          httpGet:
            path: /api/health
            port: 9991
        readinessProbe:
          httpGet:
            path: /api/ready
            port: 9991

---
apiVersion: v1
kind: Service
metadata:
  name: lenses-hq-service
  namespace: health-streaming
spec:
  selector:
    app: lenses-hq
  ports:
  - name: http
    port: 9991
    targetPort: 9991
```

#### Lenses Agent (Data Plane)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lenses-agent
  namespace: health-streaming
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: lenses-agent
        image: lensting/lenses-agent:6-preview
        env:
        - name: DEMO_HQ_URL
          value: "http://lenses-hq-service.health-streaming.svc.cluster.local:9991"
        - name: LENSES_HEAP_OPTS
          value: "-Xmx1536m -Xms512m"
        volumeMounts:
        - name: agent-settings
          mountPath: /mnt/settings
```

#### Kafka Platform (Fast Data Dev)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka-platform
  namespace: health-streaming
spec:
  template:
    spec:
      containers:
      - name: kafka
        image: lensesio/fast-data-dev:3.9.0
        ports:
        - containerPort: 9092  # Kafka
        - containerPort: 8081  # Schema Registry
        - containerPort: 8083  # Kafka Connect
        env:
        - name: ADV_HOST
          value: "kafka-platform"
        - name: RUNNING_SAMPLEDATA
          value: "1"
        volumeMounts:
        - name: connector-jars
          mountPath: /connectors

---
apiVersion: v1
kind: Service
metadata:
  name: kafka-service
  namespace: health-streaming
spec:
  ports:
  - name: kafka
    port: 9092
  - name: schema-registry
    port: 8081
  - name: connect
    port: 8083
```

### MQTT Broker Components

#### Eclipse Mosquitto MQTT Broker
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: health-mqtt-broker
  namespace: health-streaming
spec:
  template:
    spec:
      containers:
      - name: mosquitto
        image: eclipse-mosquitto:latest
        ports:
        - containerPort: 1883  # MQTT
        - containerPort: 9001  # WebSockets
        volumeMounts:
        - name: mosquitto-config
          mountPath: /mosquitto/config
        - name: mosquitto-data
          mountPath: /mosquitto/data
        - name: mosquitto-logs
          mountPath: /mosquitto/log

---
apiVersion: v1
kind: Service
metadata:
  name: health-mqtt-service
  namespace: health-streaming
spec:
  ports:
  - name: mqtt
    port: 1883
    targetPort: 1883
  - name: websockets
    port: 9001
    targetPort: 9001
```

#### MQTT Configuration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mosquitto-config
  namespace: health-streaming
data:
  mosquitto.conf: |
    listener 1883
    protocol mqtt
    listener 9001
    protocol websockets
    allow_anonymous false
    password_file /mosquitto/config/passwd
    persistence true
    persistence_location /mosquitto/data/
    log_dest file /mosquitto/log/mosquitto.log
```

### Analytics Components

#### Metabase Dashboard
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metabase-dashboard
  namespace: health-streaming
spec:
  template:
    spec:
      containers:
      - name: metabase
        image: metabase/metabase:latest
        ports:
        - containerPort: 3000
        env:
        - name: MB_DB_TYPE
          value: postgres
        - name: MB_DB_HOST
          value: lenses-backend-postgres-service

---
apiVersion: v1
kind: Service
metadata:
  name: metabase-service
  namespace: health-streaming
spec:
  ports:
  - name: http
    port: 3000
```

## 3. Knative Services (Auto-scaling Applications)

### Health Data Generator
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: health-data-sim
  namespace: health-streaming
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "2"
    spec:
      containers:
      - image: socrates12345/health-data-generator:latest
        ports:
        - containerPort: 8080
        env:
        - name: MQTT_HOST
          value: "health-mqtt-service.health-streaming.svc.cluster.local"
        - name: MQTT_TOPIC
          value: "health/device_data"
```

### Analytics Proxy Service  
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: health-analytics
  namespace: health-streaming
spec:
  template:
    spec:
      containers:
      - image: nginx:alpine
        ports:
        - containerPort: 8080
```

## 4. Istio/Ingress Resources (External Access)

### Virtual Services
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: lenses-ui
  namespace: health-streaming
spec:
  hosts:
  - "lenses.health-streaming.local"
  http:
  - route:
    - destination:
        host: lenses-hq-service
        port:
          number: 9991

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: mqtt-websockets
  namespace: health-streaming  
spec:
  hosts:
  - "mqtt.health-streaming.local"
  http:
  - route:
    - destination:
        host: health-mqtt-service
        port:
          number: 9001

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: analytics-dashboard
  namespace: health-streaming
spec:
  hosts:
  - "analytics.health-streaming.local"
  http:
  - route:
    - destination:
        host: metabase-service
        port:
          number: 3000
```

### Gateway Configuration
```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: health-streaming-gateway
  namespace: health-streaming
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "lenses.health-streaming.local"
    - "mqtt.health-streaming.local" 
    - "analytics.health-streaming.local"
    - "generator.health-streaming.local"
```

## 5. Persistent Volumes and Storage

### Storage for MQTT Data
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mosquitto-data-pvc
  namespace: health-streaming
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
  storageClassName: gp2
```

### Storage for Kafka Data
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: kafka-data-pvc
  namespace: health-streaming
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 10Gi
```

### Storage for PostgreSQL
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data-pvc
  namespace: health-streaming
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 8Gi
```

## 6. Network Policies and Security

### MQTT → Kafka Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mqtt-kafka-policy
  namespace: health-streaming
spec:
  podSelector:
    matchLabels:
      app: kafka-platform
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: lenses-agent
    ports:
    - protocol: TCP
      port: 9092
```

### Lenses → PostgreSQL Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: lenses-postgres-policy
  namespace: health-streaming
spec:
  podSelector:
    matchLabels:
      app: postgresql
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: lenses-hq
    - podSelector:
        matchLabels:
          app: lenses-agent
    ports:
    - protocol: TCP
      port: 5432
```

## 7. Monitoring and Observability

### ServiceMonitor for Prometheus
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: lenses-metrics
  namespace: health-streaming
spec:
  selector:
    matchLabels:
      app: lenses-hq
  endpoints:
  - port: http
    path: /metrics
```

### Grafana Dashboard ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: health-streaming-dashboard
  namespace: health-streaming
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "Health Streaming Pipeline",
        "panels": [...] 
      }
    }
```

## 8. External Endpoints Created

After successful deployment, the following endpoints are accessible:

### Web Interfaces
- **Lenses Platform**: `https://lenses.health-streaming.local/` (Port 9991)
  - Stream processing UI, connector management, topic monitoring
- **Metabase Analytics**: `https://analytics.health-streaming.local/` (Port 3000)  
  - Real-time health data dashboards and visualizations
- **Data Generator API**: `https://generator.health-streaming.local/api/` (Port 8080)
  - Control interface for synthetic health data generation

### MQTT Endpoints  
- **MQTT TCP**: `mqtt://health-mqtt-service.health-streaming.svc.cluster.local:1883`
  - Direct MQTT client connections (internal cluster access)
- **MQTT WebSockets**: `wss://mqtt.health-streaming.local/` (Port 9001)
  - Browser-based MQTT connections via WebSocket

### API Endpoints
- **Kafka REST Proxy**: `http://kafka-service.health-streaming.svc.cluster.local:8083`
  - Kafka Connect REST API for connector management
- **Schema Registry**: `http://kafka-service.health-streaming.svc.cluster.local:8081`  
  - Avro schema management and evolution
- **Lenses API**: `https://lenses.health-streaming.local/api/`
  - Programmatic access to Lenses functionality

### Internal Service Discovery
All services are accessible within the vCluster via DNS:
```bash
# MQTT Broker
health-mqtt-service.health-streaming.svc.cluster.local:1883

# Kafka Cluster  
kafka-service.health-streaming.svc.cluster.local:9092

# Lenses HQ
lenses-hq-service.health-streaming.svc.cluster.local:9991

# PostgreSQL Database
lenses-backend-postgres-service.health-streaming.svc.cluster.local:5432

# Metabase Dashboard
metabase-service.health-streaming.svc.cluster.local:3000
```

## 9. Data Flow Verification

### Test the Complete Pipeline
```bash
# 1. Publish test message to MQTT
mosquitto_pub -h mqtt.health-streaming.local -p 9001 \
  -t "health/device_data" \
  -m '{"deviceId":"test001","timestamp":1640995200,"heartRate":75,"systolic":120,"diastolic":80,"oxygenSaturation":98,"bodyTemperature":98.6,"latitude":40.7128,"longitude":-74.0060}' \
  -u health-user -P secure-health-pass

# 2. Verify message in Kafka topic
kubectl exec -it kafka-platform-0 -n health-streaming -- kafka-console-consumer --topic device_data --bootstrap-server localhost:9092

# 3. Check processed topics in Lenses UI
# Visit: https://lenses.health-streaming.local/topics

# 4. Verify data in Snowflake via Metabase
# Visit: https://analytics.health-streaming.local/

# 5. Monitor pipeline health
kubectl get pods -n health-streaming
kubectl get services -n health-streaming  
kubectl get virtualservices -n health-streaming
```

This comprehensive infrastructure provides a complete real-time health data streaming platform with external access points, internal service communication, monitoring, and data persistence - all provisioned from a single OAM Application specification! 🚀