# Technology Layer (Phase 5) — Architecture Building Blocks (ABB), then Solution (SBB)

> **EA discipline (TOGAF):** the *architecture* defines the technology **capabilities required**
> (Architecture Building Blocks — product-agnostic). The concrete products / OAM component types are
> **Solution Building Blocks (SBB)** that *realize* the ABBs and belong in a separate solution view.
> The earlier draft incorrectly stated SBBs (Knative, Kafka, OAM types) *as* the architecture — fixed.
>
> **Deliverable:** `technology-layer.archimate.xml` — 2 views, engine-generated.

## View 1 — Technology Architecture (ABB)  *product-agnostic*
`Application Component  ← realized / served by ←  Architecture Building Block`

| Application component | Realising ABB (capability required) |
|---|---|
| Gamification Platform (13 µsvcs) | **Container Workload Runtime** |
| Event Hub | **Event Streaming Platform** |
| Analytics & Reporting | **Analytical Data Store (OLAP)** (+ Stream Processing & Feature Computation) |
| Member Gateway (/ws) | **Real-time Push Channel** |
| Consent & Identity | **Identity & Access Management** |
| Sahatna BFFs | **API Federation & Aggregation** |
| Platform Data Stores | **Relational Persistence (OLTP)** |

Cross-cutting ABBs (serve the platform, not one component): **Service Mesh & API Gateway**,
**Secrets Management**, **Declarative Provisioning (GitOps)**, **Observability**.

This view names *no product* — it is the technology architecture proper. It would hold for any
realisation (this platform, a different cloud, on-prem).

## View 2 — Solution Realization (SBB realizes ABB)  *the concrete choice*
`Architecture Building Block  ← realized by ←  Solution Building Block`

| ABB | SBB (product · OAM component type) |
|---|---|
| Container Workload Runtime | Knative Serving · **webservice** |
| Service Mesh & API Gateway | Istio + Azure APIM |
| Event Streaming Platform | Kafka + Lenses · **realtime-platform** |
| Stream Processing & Feature Computation | Lenses SQL processors · **analytics-platform** |
| Relational Persistence (OLTP) | Neon PostgreSQL · **postgresql** |
| Analytical Data Store (OLAP) | Snowflake + Kafka Connect · **analytics-platform** |
| Real-time Push Channel | WebSocket Gateway · **realtime-service** |
| Identity & Access Management | Auth0 · **auth0-idp** |
| API Federation & Aggregation | Hive Gateway · **graphql-gateway** |
| Secrets Management | Azure Key Vault + External Secrets |
| Declarative Provisioning (GitOps) | KubeVela + Crossplane + ArgoCD (OAM control plane) |
| Observability | Prometheus + Grafana + Jaeger |

The OAM component types are **SBBs** — the platform's solution catalogue — not the architecture.
Swapping a product (e.g. Neon → another managed Postgres, Snowflake → ClickHouse) changes only this
view; View 1 is unaffected. That separation is the whole point of ABB vs SBB.

## Notes
- **analytics-platform rides realtime-platform** (leaderboard → wellness-stream) — a solution-level
  wiring (SBB↔SBB), captured in the SBB view's labels, not in the ABB architecture.
- The live `wellness-gamification-example.yaml` is a 4-component demo (postgresql, realtime-platform,
  analytics-platform, realtime-service); the full SBB set above implies ~9 OAM components.
- View 1 has one minor connector-lane overlap where several cross-cutting ABBs serve the platform
  component (a centre-anchored-renderer artifact, target is unambiguous).
