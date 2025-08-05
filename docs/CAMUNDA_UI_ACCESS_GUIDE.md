# 🎯 Camunda UI Stack Access Guide

## Overview

The enhanced Camunda orchestrator ComponentDefinition now includes the full Camunda 8 UI stack:

- **Camunda Operate**: Process monitoring and troubleshooting dashboard
- **Camunda Tasklist**: Human task management interface
- **Camunda Optimize** (optional): Process analytics and optimization

## What Gets Created

When you deploy a Camunda orchestrator with `enableUI: true`:

### 1. Core Services
- **Zeebe Engine**: Core workflow engine (port 9600 for gRPC, 8080 for HTTP)
- **Elasticsearch**: Data storage for UI components
- **PostgreSQL**: Workflow state persistence
- **Redis**: Caching and session management

### 2. UI Services  
- **Camunda Operate**: Process instance monitoring (`{name}-operate`)
- **Camunda Tasklist**: Human task management (`{name}-tasklist`)
- **Camunda Optimize**: Analytics dashboard (`{name}-optimize`, requires `enableOptimize: true`)

### 3. Networking
- **Istio Gateway**: External access point
- **Virtual Service**: Routes to different UI components

## Accessing the UIs

### Local Development (Port Forwarding)

```bash
# Operate UI (Process Monitoring)
kubectl port-forward svc/hr-workflow-orchestrator-operate 8081:80
# Access at: http://localhost:8081

# Tasklist UI (Human Tasks)
kubectl port-forward svc/hr-workflow-orchestrator-tasklist 8082:80
# Access at: http://localhost:8082

# Zeebe Gateway (for debugging)
kubectl port-forward svc/hr-workflow-orchestrator 9600:9600
```

### Production Access (via Istio)

When `enableIstioGateway: true` is set, access via configured routes:

```
http://{gatewayHost}/operate    → Camunda Operate
http://{gatewayHost}/tasklist   → Camunda Tasklist
http://{gatewayHost}/optimize   → Camunda Optimize (if enabled)
http://{gatewayHost}/zeebe      → Zeebe API endpoint
```

Example with our demo:
```
http://hr-workflows.local/operate
http://hr-workflows.local/tasklist
```

### External Load Balancer Access

Find the Istio ingress gateway external IP:
```bash
kubectl get svc istio-ingressgateway -n istio-system
```

Then access:
```
http://{EXTERNAL_IP}/operate
http://{EXTERNAL_IP}/tasklist
```

## UI Features

### Camunda Operate
- **Process Instances**: View running and completed workflows
- **Incidents**: Monitor and resolve workflow errors
- **Heat Map**: Identify bottlenecks in processes
- **Variables**: Inspect workflow data
- **Decision Instances**: View DMN decision results

### Camunda Tasklist
- **Task List**: See assigned human tasks
- **Task Forms**: Complete user tasks with custom forms
- **Task Assignment**: Claim and delegate tasks
- **Filters**: Create custom task views
- **Process Context**: View related process data

### Camunda Optimize (Licensed)
- **Dashboard**: Custom analytics dashboards
- **Reports**: Process performance metrics
- **Heatmaps**: Duration and frequency analysis
- **Alerts**: Configure performance alerts
- **Goals**: Set and track KPIs

## Example Deployment

```yaml
- name: my-orchestrator
  type: camunda-orchestrator
  properties:
    realtimePlatform: "events-platform"
    enableUI: true              # Enable Operate & Tasklist
    enableOptimize: false       # Requires license
    enableIstioGateway: true
    gatewayHost: "workflows.mycompany.com"
    resources:
      cpu: "2000m"
      memory: "2Gi"
```

## Default Credentials

For development environments, the default credentials are:
- **Username**: demo
- **Password**: demo

For production, configure proper authentication via environment variables.

## Troubleshooting

### Check UI Service Status
```bash
kubectl get ksvc | grep -E "(operate|tasklist|optimize)"
```

### View Logs
```bash
# Operate logs
kubectl logs -l serving.knative.dev/service=hr-workflow-orchestrator-operate

# Tasklist logs
kubectl logs -l serving.knative.dev/service=hr-workflow-orchestrator-tasklist
```

### Elasticsearch Health
```bash
kubectl exec -it deployment/hr-workflow-orchestrator-elasticsearch -- curl -s http://localhost:9200/_cluster/health
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Istio Gateway                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ /operate │  │/tasklist │  │/optimize │  │  /zeebe  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
   ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐
   │ Operate  │ │ Tasklist │ │ Optimize │ │  Zeebe   │
   │    UI    │ │    UI    │ │    UI    │ │  Engine  │
   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                             │
                    ┌────────▼────────┐
                    │  Elasticsearch  │
                    │   (UI Data)     │
                    └─────────────────┘
```

## Best Practices

1. **Resource Allocation**: UI components need adequate resources
   - Minimum: 2 CPU, 2Gi memory for orchestrator with UI
   - Elasticsearch needs at least 512Mi memory

2. **Scaling**: UI components should have `minScale: 1` to ensure availability

3. **Security**: 
   - Configure proper authentication for production
   - Use TLS for external access
   - Restrict access via network policies

4. **Monitoring**:
   - Monitor Elasticsearch disk usage
   - Track UI response times
   - Set up alerts for failed workflows