# AKS Platform Installation Guide

## Overview
This guide documents the complete installation process for the health-service-idp platform on Azure Kubernetes Service (AKS).

## Prerequisites
- AKS cluster with 4 nodes (Standard_B2s or larger)
- kubectl configured to access the cluster
- Helm 3.x installed
- Azure CLI installed and authenticated

## Installation Process

### Step 1: Install Core Platform Components
Run the optimized installation script:
```bash
./install-aks-optimized.sh
```

This installs:
- **Istio 1.20.1** - Service mesh with ingress gateway
- **Knative Serving 1.12.0** - Serverless platform
- **ArgoCD** - GitOps continuous delivery
- **Argo Workflows 3.5.5** - Workflow engine
- **Argo Events** - Event-driven automation
- **Crossplane 1.14.0** - Infrastructure as Code
- **KubeVela 1.9.7** - OAM implementation
- **External Secrets Operator** - Secret management
- **PostgreSQL** - Database for testing

### Step 2: Configure Secrets
Create a `.env` file with your credentials:
```bash
cp .env.example .env
# Edit .env with your values
```

Run the secrets setup:
```bash
./setup-secrets.sh
```

This creates:
- Docker registry credentials
- GitHub personal access token
- Slack API credentials
- Argo workflow tokens

### Step 3: Install Platform Resources
```bash
./install-platform-resources.sh
```

This installs:
- **15 ComponentDefinitions**:
  - auth0-idp, camunda-orchestrator, graphql-gateway, graphql-platform
  - identity-service, kafka, mongodb, neon-postgres, postgresql
  - rasa-chatbot, realtime-platform, redis, vcluster
  - webservice, webservice-k8s
- **4 TraitDefinitions**: autoscaler, ingress, kafka-consumer, kafka-producer
- **7 Crossplane XRDs** with Compositions
- **Istio Gateways and VirtualServices**
- **Argo Workflow Templates**
- **GitHub Provider** with ProviderConfigs
- **Service Accounts**: knative-docker-sa, slack-api-server

### Step 4: Deploy Slack API Server
```bash
kubectl apply -f slack-api-server/deployment.yaml
kubectl apply -f slack-api-server/rbac.yaml
kubectl apply -f slack-api-server/istio-gateway.yaml
kubectl apply -f slack-api-server/argocd-application.yaml
```

### Step 5: Verify Installation
Run the infrastructure health check:
```bash
./scripts/infrastructure-health-check-enhanced.sh
```

Expected results:
- ✅ All core platform components running
- ✅ 15 ComponentDefinitions available
- ✅ Slack API server accessible
- ✅ Argo Workflows operational
- ✅ External Secrets Operator ready

## Testing

### Functional Test
Test the complete system with database and Redis:
```bash
./scripts/test-functional-multicluster.sh
```

This test:
1. Creates a Python microservice with PostgreSQL and Redis
2. Triggers Argo workflow via Slack API
3. Creates ApplicationClaim and GitOps repository
4. Deploys to vCluster with proper topology

## Access Points

### Get Istio Ingress IP
```bash
kubectl get svc istio-ingressgateway -n istio-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Service URLs (replace <INGRESS_IP> with actual IP)
- Slack API: `http://<INGRESS_IP>/slack/command`
- ArgoCD UI: `http://<INGRESS_IP>/argocd`
- Argo Workflows: `http://<INGRESS_IP>/argo`

### Port Forwarding (alternative access)
```bash
# ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Argo Workflows
kubectl port-forward svc/argo-server -n argo 2746:2746
```

## Platform Components Status

### Core Infrastructure
| Component | Namespace | Status | Version |
|-----------|-----------|---------|---------|
| Istio | istio-system | ✅ Running | 1.20.1 |
| Knative | knative-serving | ✅ Running | 1.12.0 |
| ArgoCD | argocd | ✅ Running | Latest |
| Argo Workflows | argo | ✅ Running | 3.5.5 |
| Crossplane | crossplane-system | ✅ Running | 1.14.0 |
| KubeVela | vela-system | ✅ Running | 1.9.7 |
| External Secrets | external-secrets-system | ✅ Running | Latest |

### OAM Resources
| Resource Type | Count | Status |
|---------------|-------|---------|
| ComponentDefinitions | 15 | ✅ Ready |
| TraitDefinitions | 4 | ✅ Ready |
| WorkloadDefinitions | 1 | ✅ Ready |
| Crossplane XRDs | 7 | ✅ Ready |

### Providers
| Provider | Status | Purpose |
|----------|---------|---------|
| AWS Provider | ✅ Healthy | AWS resource management |
| Kubernetes Provider | ✅ Healthy | K8s resource management |
| Helm Provider | ✅ Healthy | Helm chart deployments |
| GitHub Provider | ✅ Healthy | Repository management |

## Troubleshooting

### Check Component Health
```bash
# Check all pods
kubectl get pods -A | grep -v Running

# Check Slack API logs
kubectl logs deployment/slack-api-server

# Check Argo Workflows
kubectl get workflows -n argo
```

### Common Issues

1. **Slack API can't connect to Argo**
   - Restart Slack API: `kubectl rollout restart deployment slack-api-server`
   - Check token: `kubectl get secret slack-api-server-argo-token -n default`

2. **GitHub Provider not healthy**
   - Check secret: `kubectl get secret github-provider-secret -n crossplane-system`
   - Re-run: `./setup-secrets.sh`

3. **ComponentDefinition fails to apply**
   - Check for CRD dependencies
   - Verify External Secrets Operator is installed

## Maintenance

### Scale to Zero (Cost Savings)
```bash
# Scale AKS nodes to 0
az aks nodepool scale --resource-group health-service-idp-rg \
  --cluster-name health-service-idp-aks --name nodepool1 --node-count 0
```

### Scale Back Up
```bash
# Scale back to 4 nodes
az aks nodepool scale --resource-group health-service-idp-rg \
  --cluster-name health-service-idp-aks --name nodepool1 --node-count 4
```

## Architecture Notes

### Multi-Platform Support
The scripts support both AWS EKS and Azure AKS:
- AWS uses `.hostname` for LoadBalancer services
- Azure uses `.ip` for LoadBalancer services
- Scripts automatically detect and use the correct field

### Security Considerations
- All secrets stored in Kubernetes secrets
- Service accounts with minimal required permissions
- Network policies enforced via Istio
- RBAC properly configured for all components

## Next Steps
1. Configure monitoring with Prometheus/Grafana
2. Set up backup strategies
3. Implement CI/CD pipelines
4. Configure auto-scaling policies