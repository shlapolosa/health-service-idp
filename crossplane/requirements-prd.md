<context>
# Overview
This project delivers a fully Kubernetes-native Internal Developer Platform (IDP) using GitOps and Crossplane to provision:
1. Entire vCluster environments with modular infrastructure (ArgoCD, observability stack, ingress, etc.) running on cost-optimized Karpenter-managed nodes.
2. Complete applications that include GitHub-backed repositories, CI/CD pipelines, container registries, Knative deployments, Redis/Postgres/other dependencies, and automatic AWS API Gateway exposure.
3. Consistent auth (Auth0), database (Neon Postgres), and optional domain configuration per environment.

All infrastructure provisioning is done through Kubernetes-native CRDs, using Crossplane Compositions, with complete observability, operational readiness, and GitOps automation. No UI is required. This platform is ideal for platform engineers and developers who prefer declarative, automated control over cloud-native development environments.

# Core Features

### 1. **Modular vCluster Provisioning**

* **What it does**: Creates a namespaced vCluster running on Karpenter-managed compute with only Istio ingress and optional stack: ArgoCD, Grafana, Prometheus, Jaeger, Kiali.
* **Why it's important**: Developers need isolated, cost-optimized, observability-ready Kubernetes environments.
* **How it works**: Users submit a `VClusterEnvironmentClaim` that Crossplane uses to create the vCluster, Istio Gateway, and component stack via Helm. Compute is isolated via taints/tolerations set by Karpenter. Optionally accepts domain.

### 2. **Declarative Application Bootstrapping**

* **What it does**: Spins up an app in GitHub with codebase, Dockerfile, pyproject.toml (or pom.xml), Knative service, ArgoCD Application, OAM components, and GitOps flow.
* **Why it's important**: Reduces friction, ensures consistency, leverages existing stack (Knative, ArgoCD, GitHub, Docker Hub).
* **How it works**: `ApplicationClaim` provisions GitHub repo, GitHub Actions pipeline, deploys Knative Service via OAM, adds ArgoCD app, auto-wires to shared Auth0 and Neon Postgres secrets.

### 3. **API Gateway Exposure**

* **What it does**: Deploys AWS API Gateway REST API and routes for every backend API app.
* **Why it's important**: Enables external consumption of services with secure access.
* **How it works**: Detects `exposeApi: true` in `ApplicationClaim`, provisions API Gateway via Crossplane AWS provider, and maps to Knative ingress using a VPC Link (for internal-only services) or public route.

### 4. **Shared Secrets and Authentication**

* **What it does**: Injects Auth0 tenant config and Neon Postgres connection secrets into each app.
* **Why it's important**: Enables centralized auth and data while maintaining isolation.
* **How it works**: Secrets are synced into each vCluster using External Secrets Operator. Applications mount credentials via Knative env vars.

### 5. **Knative Cold Start Protection**

* **What it does**: Ensures that no request is lost due to scale-from-zero latency.
* **Why it's important**: Guarantees reliability and user experience.
* **How it works**: Activator is configured with `concurrency-state-endpoint`, Karpenter provisioners have low scale-up delay. Pre-warming logic can be added for latency-sensitive apps.

</context>

<PRD>
# Technical Architecture

## System Components and Technologies

* **Crossplane**: For provisioning infrastructure and app stacks via CRDs and compositions.
* **Karpenter**: For dynamic provisioning of vCluster workloads using taints/tolerations.
* **vCluster**: For multi-tenant Kubernetes namespaces with separate control planes.
* **ArgoCD**: For GitOps sync of application manifests.
* **Knative**: For service autoscaling, revisioning, and serving.
* **Istio**: As the only ingress per vCluster, supports routing, observability, and mTLS.
* **Prometheus + Grafana + Jaeger + Kiali**: For full observability stack.
* **Auth0**: For authentication using preconfigured client ID and secret.
* **Neon Postgres**: Shared Postgres DB with per-app schema isolation.
* **AWS API Gateway**: For exposing internal Knative services via REST APIs.
* **External Secrets Operator**: To inject shared Auth0 and Neon secrets.
* **GitHub Actions**: For CI/CD to Docker Hub and updating GitOps repo.
* **Docker Hub**: As default container registry (e.g., `socrates12345/*`).

## Data Models

### VClusterEnvironmentClaim

```yaml
spec:
  name: string
  domain: optional string
  include:
    - argoCD
    - grafana
    - prometheus
    - jaeger
    - kiali
    - apiGatewaySupport
```

### ApplicationClaim

```yaml
spec:
  name: string
  language: python | java
  framework: fastapi | springboot
  hasFrontend: true | false
  database: postgres | none
  cache: redis | none
  exposeApi: true
```

## APIs and Integrations

* GitHub API for repo creation
* AWS API Gateway for routing setup
* Neon API for DB provisioning (if needed)
* Kubernetes API for Knative, Secrets, OAM
* External Secrets to sync shared secrets

## Infrastructure Requirements

* Management cluster with Crossplane and ArgoCD
* Karpenter setup with taints for vCluster workloads
* External Secrets Operator installed
* IAM roles for API Gateway provisioning
* DockerHub/GHCR credentials

# Development Roadmap

## Phase 1: MVP

* Crossplane setup with Helm, AWS, GitHub, Kubernetes providers
* `VClusterEnvironmentClaim` CRD and composition
* Helm deployments for vCluster, Istio, ArgoCD
* `ApplicationClaim` CRD with GitHub repo, ArgoCD App, OAM + Knative service
* Auth0 + Neon credentials managed via External Secrets
* CI/CD via GitHub Actions
* Basic API Gateway provisioning

## Phase 2: Extension

* Add Redis, Postgres, Kafka Helm apps
* Add Streamlit/React frontend options
* Add custom domain and TLS support via Istio + Cert Manager
* Add workload annotations for prewarming or concurrency tuning
* Add Prometheus-based scaling via KEDA

## Phase 3: Enterprise Readiness

* Policy-as-Code enforcement (OPA)
* Canary deployment via Argo Rollouts
* Slack notifications + GitHub status integrations
* Cost analysis + resource metrics to Grafana dashboards

# Logical Dependency Chain

1. **Foundational Setup**

   * Crossplane installed and configured with Helm, AWS, GitHub, Kubernetes providers
   * Karpenter + taints set up
   * Istio and observability stack Helm charts

2. **Shared Infrastructure**

   * External Secrets for Auth0 + Neon secrets
   * GitHub Actions base CI templates
   * OAM Component + Application definitions for Python/Java apps

3. **CRD Development**

   * `VClusterEnvironmentClaim` composition and controller
   * `ApplicationClaim` composition

4. **Knative + API Gateway**

   * Knative configuration for concurrency and autoscaling
   * AWS API Gateway setup logic with public/private support

5. **Prewarm + Reliability**

   * Activator tuning
   * Karpenter provisioner latency optimization

# Risks and Mitigations

| Risk                                | Mitigation                                              |
| ----------------------------------- | ------------------------------------------------------- |
| Cold starts in Knative              | Use `initialScale`, concurrency state endpoint, warmers |
| Taint/compute misconfig             | Use static labels + validation in `ApplicationClaim`    |
| AWS API Gateway provisioning errors | Build dry-run simulator, CI tests                       |
| Secret distribution failure         | External Secrets retries + ArgoCD sync waves            |
| GitHub API throttling               | Use GitHub App tokens with proper scopes                |

# Appendix

## Secrets Format

* `auth0-credentials`

```yaml
clientId: ...
clientSecret: ...
domain: my-tenant.auth0.com
```

* `neon-db`

```yaml
PGHOST=...
PGUSER=...
PGPASSWORD=...
PGDATABASE=...
```

## Example ArgoCD App

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app-fastapi
spec:
  source:
    repoURL: https://github.com/socrates12345/app-fastapi
    path: manifests/
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  project: default
  syncPolicy:
    automated: {}
```

</PRD>
