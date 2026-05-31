# Deployment Landscape Documentation

## Overview
This document provides a comprehensive overview of the current deployment environment, including all services, external endpoints, configuration requirements, and connectivity setup.

**Last Updated**: August 18, 2025  
**Environment**: Azure Kubernetes Service (AKS)  
**External LoadBalancer IP**: `20.233.105.82`

---

## Table of Contents
1. [External Access Configuration](#external-access-configuration)
2. [Namespace Organization](#namespace-organization)
3. [Deployed Services](#deployed-services)
4. [Persistent Storage](#persistent-storage)
5. [Istio Service Mesh Configuration](#istio-service-mesh-configuration)
6. [Lenses Platform Configuration](#lenses-platform-configuration)
7. [MQTT Configuration](#mqtt-configuration)
8. [Monitoring and Observability](#monitoring-and-observability)

---

## External Access Configuration

### Hosts File Configuration
Add the following entries to your `/etc/hosts` file (Mac/Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows):

```bash
# Azure Kubernetes Service - Platform Services
20.233.105.82   lenses.local       # Lenses HQ Dashboard
20.233.105.82   metabase.local     # Metabase Analytics
20.233.105.82   kafka.local        # Kafka Manager UI
20.233.105.82   mqtt.local         # MQTT WebSocket Interface
```

### External API Endpoints

| Service | External URL | Protocol | Authentication |
|---------|-------------|----------|----------------|
| **Slack API Server** | `http://20.233.105.82/slack/command` | HTTP/REST | Bearer Token |
| **Identity Service** | `http://20.233.105.82/identity/` | HTTP/REST | None |
| **Realtime Service** | `http://20.233.105.82/realtime/` | HTTP/REST | None |
| **Lenses HQ** | `http://lenses.local` | HTTP | admin/admin |
| **Metabase** | `http://metabase.local` | HTTP | admin/admin |
| **MQTT Broker** | `tcp://20.233.105.82:1883` | TCP/MQTT | Anonymous allowed |
| **MQTT WebSocket** | `ws://mqtt.local:9001` | WebSocket | Anonymous allowed |
| **ArgoCD** | `http://20.233.105.82/argocd` | HTTP | admin/[retrieve from secret] |
| **Grafana** | `http://20.233.105.82/grafana` | HTTP | admin/admin |

---

## Namespace Organization

### Active Namespaces

| Namespace | Purpose | Status |
|-----------|---------|--------|
| `default` | Main application deployments, OAM components | Active |
| `realtime-service-realtime` | Realtime platform services (Kafka, MQTT, Lenses) | Active |
| `iot-streaming-platform` | IoT data streaming infrastructure | Active |
| `knative-serving` | Serverless workloads and autoscaling | Active |
| `istio-system` | Service mesh control plane | Active |
| `crossplane-system` | Infrastructure as Code provisioning | Active |
| `argocd` | GitOps continuous deployment | Active |
| `argo` | Workflow orchestration | Active |
| `argo-events` | Event-driven automation | Active |
| `vela-system` | OAM runtime and controllers | Active |

---

## Deployed Services

### Knative Services (Serverless)

| Service | Namespace | URL Path | Status |
|---------|-----------|----------|--------|
| `slack-api-server` | default | `/slack/command` | Ready |
| `identity-service-test` | default | `/identity/` | Ready |
| `realtime-pipeline-test` | default | `/realtime/` | Ready |
| `rasa-chat-test` | default | `/rasa/` | Pending Image |
| `rasa-webchat-test` | default | `/webchat/` | Pending Image |

### Realtime Platform Services

| Service | Namespace | Type | Ports | Purpose |
|---------|-----------|------|-------|---------|
| `postgres` | realtime-service-realtime | Deployment | 5432 | Database for Lenses/Metabase |
| `demo-kafka` | realtime-service-realtime | Deployment | 9092, 2181, 3030 | Kafka broker and Zookeeper |
| `lenses-hq` | realtime-service-realtime | Deployment | 9991 | Lenses HQ Dashboard |
| `lenses-agent` | realtime-service-realtime | Deployment | 9991 | Lenses Agent (connects to HQ) |
| `metabase` | realtime-service-realtime | Deployment | 3000 | Analytics and BI |
| `mqtt-broker` | realtime-service-realtime | Deployment | 1883, 9001 | MQTT messaging |

---

## Persistent Storage

### Persistent Volume Claims

| PVC Name | Namespace | Size | Storage Class | Mount Path | Used By |
|----------|-----------|------|---------------|------------|---------|
| `postgres-storage` | realtime-service-realtime | 10Gi | default | `/var/lib/postgresql/data` | PostgreSQL |
| `data-iot-streaming-platform-0` | iot-streaming-platform | 5Gi | default | `/data` | IoT Platform |
| `data-test-crazy-0` | test-crazy | 5Gi | default | `/data` | Test Service |

---

## Istio Service Mesh Configuration

### Gateways

| Gateway | Namespace | Ports | Purpose |
|---------|-----------|-------|---------|
| `iot-platform-gateway` | default | 80, 1883, 9001 | Main ingress for IoT platform |
| `subdomain-gateway` | default | 80 | Subdomain-based routing |
| `knative-ingress-gateway` | knative-serving | 80, 443 | Knative service routing |
| `slack-api-gateway` | default | 80, 443 | Slack API routing |

### VirtualServices (Key Routes)

| VirtualService | Gateway | Host Match | Destination |
|----------------|---------|------------|-------------|
| `mqtt-tcp-routing` | iot-platform-gateway | * (port 1883) | mqtt-broker.realtime-service-realtime:1883 |
| `lenses-subdomain-vs` | subdomain-gateway | lenses.local | lenses-hq.realtime-service-realtime:9991 |
| `metabase-subdomain-vs` | subdomain-gateway | metabase.local | metabase.realtime-service-realtime:3000 |
| `slack-api-vs` | slack-api-gateway | * | slack-api-server.default:80 |

---

## Lenses Platform Configuration

### Lenses HQ Setup
1. **Access URL**: http://lenses.local
2. **Default Credentials**: admin/admin
3. **Agent Key**: Retrieved from HQ after first login

### Lenses Agent Connection

#### Prerequisites
- Lenses HQ must be running and accessible
- Agent key must be generated from Lenses HQ UI

#### Configuration Steps

1. **Generate Agent Key in Lenses HQ**:
   ```bash
   # Access Lenses HQ
   open http://lenses.local
   # Login with admin/admin
   # Navigate to Admin → Agents → Generate New Key
   ```

2. **Update Agent Configuration**:
   ```bash
   # Set the agent key in ConfigMap
   kubectl create configmap lenses-agent-key \
     --from-literal=agent-key="<YOUR_AGENT_KEY>" \
     -n realtime-service-realtime \
     --dry-run=client -o yaml | kubectl apply -f -
   
   # Update the secret
   kubectl create secret generic lenses-credentials \
     --from-literal=agent-key="<YOUR_AGENT_KEY>" \
     -n realtime-service-realtime \
     --dry-run=client -o yaml | kubectl apply -f -
   
   # Restart the agent
   kubectl rollout restart deployment/lenses-agent -n realtime-service-realtime
   ```

3. **Verify Connection**:
   ```bash
   # Check agent logs
   kubectl logs -n realtime-service-realtime deployment/lenses-agent --tail=50
   
   # Look for: "Connection [lenses-hq] of type LensesHQServer initialized"
   ```

### Current Agent Configuration
- **Agent Key ConfigMap**: `lenses-agent-key`
- **Agent Config ConfigMap**: `lenses-agent-config`
- **Credentials Secret**: `lenses-credentials`
- **Connection Endpoint**: `lenses-hq.realtime-service-realtime:9991`

---

## MQTT Configuration

### MQTT Broker Access

#### External TCP Connection
```bash
# Publish a message
mosquitto_pub -h 20.233.105.82 -p 1883 -t "test/topic" -m "Hello MQTT"

# Subscribe to a topic
mosquitto_sub -h 20.233.105.82 -p 1883 -t "health/device_data" -v
```

#### WebSocket Connection
```javascript
// JavaScript WebSocket example
const client = new Paho.MQTT.Client("mqtt.local", 9001, "clientId");
client.connect({
    onSuccess: () => console.log("Connected to MQTT via WebSocket")
});
```

### MQTT Configuration Details
- **Protocol**: MQTT v3.1.1 / v5.0
- **Anonymous Access**: Enabled
- **Persistence**: Disabled (for testing)
- **Logging**: All events logged to stdout
- **ConfigMap**: Uses mounted config at `/mosquitto/config/mosquitto.conf`

---

## Monitoring and Observability

### Access Points (via Subpath Routing)

| Tool | URL | Purpose | Credentials |
|------|-----|---------|-------------|
| **ArgoCD** | http://20.233.105.82/argocd | GitOps deployment dashboard | admin/[from secret] |
| **Grafana** | http://20.233.105.82/grafana | Metrics visualization | admin/admin |
| **Jaeger** | http://20.233.105.82/jaeger | Distributed tracing | None |
| **Kiali** | http://20.233.105.82/kiali | Service mesh observability | admin/admin |
| **Prometheus** | http://20.233.105.82/prometheus | Metrics collection | None |

### Retrieving ArgoCD Password
```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

---

## Quick Troubleshooting

### Check Service Health
```bash
# Check all pods in realtime namespace
kubectl get pods -n realtime-service-realtime

# Check Knative services
kubectl get ksvc -A

# Check Istio configuration issues
istioctl analyze -A
```

### Common Issues and Solutions

1. **MQTT Connection Refused**
   - Check if mqtt-broker pod is running
   - Verify Istio gateway configuration
   - Ensure port 1883 is exposed on LoadBalancer

2. **Lenses Agent Not Connecting**
   - Verify agent key is correct
   - Check Lenses HQ is accessible
   - Review agent logs for connection errors

3. **Web UI Shows Blank Page**
   - Services expect root path access
   - Use subdomain URLs (lenses.local, metabase.local)
   - Check browser console for asset loading errors

4. **Service Not Accessible Externally**
   - Verify VirtualService configuration
   - Check Gateway is correctly configured
   - Ensure Istio ingress gateway is running

---

## Development Workflow

### Deploying New Services

1. **Create OAM Component Definition**:
   ```yaml
   apiVersion: core.oam.dev/v1beta1
   kind: ComponentDefinition
   metadata:
     name: my-service
   spec:
     workload:
       definition:
         apiVersion: serving.knative.dev/v1
         kind: Service
   ```

2. **Apply OAM Application**:
   ```bash
   kubectl apply -f my-app.yaml
   ```

3. **Expose via Istio**:
   ```yaml
   apiVersion: networking.istio.io/v1beta1
   kind: VirtualService
   metadata:
     name: my-service-vs
   spec:
     gateways:
     - iot-platform-gateway
     hosts:
     - "*"
     http:
     - match:
       - uri:
           prefix: /my-service
       route:
       - destination:
           host: my-service.default.svc.cluster.local
   ```

### Testing Endpoints
```bash
# Test internal connectivity
kubectl run test-curl --image=curlimages/curl --rm -it --restart=Never -- \
  curl http://service-name.namespace.svc.cluster.local

# Test external connectivity
curl http://20.233.105.82/path/to/service
```

---

## Security Considerations

1. **Network Policies**: Currently not enforced - consider implementing for production
2. **TLS/SSL**: Configure certificates for production deployments
3. **Authentication**: Implement proper authentication for production services
4. **Secrets Management**: Use external-secrets operator for production secrets

---

## Useful Commands Reference

```bash
# Get all resources in a namespace
kubectl get all -n realtime-service-realtime

# Check Istio proxy configuration
istioctl proxy-config listeners deployment/istio-ingressgateway -n istio-system

# Debug Knative service
kubectl describe ksvc slack-api-server

# View OAM applications
kubectl get applications -A

# Check Crossplane claims
kubectl get applicationclaims -A

# Monitor pod logs
kubectl logs -f deployment/lenses-agent -n realtime-service-realtime

# Port forward for local debugging
kubectl port-forward -n realtime-service-realtime svc/lenses-hq 9991:9991
```

---

## Contact & Support

For issues or questions about this deployment:
1. Check the infrastructure health: `./scripts/infrastructure-health-check.sh`
2. Review logs in Grafana/Loki
3. Check ArgoCD for deployment status
4. Consult the CLAUDE.md for development guidelines

---

*This document reflects the current state of the deployment as of August 18, 2025.*