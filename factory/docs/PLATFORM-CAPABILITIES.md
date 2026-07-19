# Platform Capabilities — Internal Developer Platform (2026-06-13)

A GitOps, OAM-driven IDP on AKS. A consumer declares an **OAM Application**; the platform
scaffolds source + gitops repos, builds images, provisions backing infra via Crossplane, and
reconciles everything through ArgoCD onto Knative/Istio — with per-component data-plane
contract tests as the acceptance gate.

## End-to-end flow

```mermaid
flowchart TB
    subgraph INTAKE["🚪 Intake (converged on app.submit)"]
        SLACK["slack-api-server<br/>/microservice"]
        MCPF["capability-mcp-factory<br/>factory.route / .propose"]
        MCPTC["capability-mcp-mfg-tc<br/>catalog.* / app.submit"]
        WEBMCP["capability-web-mcp<br/>DISCOVER (SearXNG)"]
        ARCH["architect-v1<br/>(Azure Foundry agent)"]
        ARCH --> MCPF & MCPTC & WEBMCP
        SLACK --> MCPTC
    end

    subgraph ORCH["🏭 Factory / Orchestration"]
        SUBMIT["app.submit use-case<br/>vela dry-run → ledger → claim/commit"]
        LIFE["lifecycle-orchestrator<br/>lifecycle.state"]
        MSCV["mscv scaffolder<br/>(role-branched: gateway/ingest/<br/>processor/webhook + webservice)"]
        DEVAGENT["dev-agent<br/>opencode + GPT-5.4 via APIM<br/>(no Anthropic key)"]
        CT["contract-test-runner (HARD-4)<br/>per-type data-plane gate"]
        WHEEL["realtime-transport wheel<br/>+ rasa-base / zeebe-worker-base"]
        MCPTC --> SUBMIT --> MSCV
        MSCV --> DEVAGENT
        SUBMIT --> LIFE
    end

    subgraph SUBSTRATE["⚙️ Substrate (level-triggered)"]
        VELA["KubeVela 1.10.3<br/>(CD/Trait CUE)"]
        XP["Crossplane v2.3<br/>provider-kubernetes v1.2.1<br/>provider-helm / upjet-github / aws"]
        ARGO["ArgoCD v3.4<br/>(per-service gitops repos)"]
        KN["Knative v1.22 + Istio 1.27"]
        AW["Argo Workflows v4 + Argo Events"]
        ESO["External Secrets v2.5"]
        VELA --> XP --> ARGO --> KN
    end

    subgraph CATALOG["📦 Capability Catalog (OAM ComponentDefinitions)"]
        direction LR
        subgraph APPS["Application components"]
            WS["webservice<br/>(python/node/go/java + onion)"]
            RTP["realtime-platform<br/>(Kafka+Lenses CE+MQTT)"]
            RTS["realtime-service<br/>gateway · ingest · processor · webhook"]
            WH["webhook-platform<br/>(Svix engine + portal)"]
            GQL["graphql-gateway<br/>(Hive federation)"]
            RASA["rasa-chatbot"]
            CAM["camunda-orchestrator<br/>(Zeebe 8)"]
        end
        subgraph BACKING["Backing infra (-conn secrets)"]
            PG["postgresql / neon-postgres"]
            REDIS["redis"] 
            KAFKA["kafka"]
            AUTH["auth0-idp / identity-service"]
        end
    end

    subgraph BIND["🔌 Connectivity & Exposure (traits/recipes)"]
        CONN["&lt;comp&gt;-conn normalization secrets<br/>+ envFrom auto-wire"]
        EXPOSE["expose-api → APIM import"]
        APIM["Azure APIM<br/>(dual-auth: JWT OR sub-key)"]
        BOOT["auto-scaffold-bootstrap trait<br/>→ AppContainerClaim"]
        EXPOSE --> APIM
    end

    INTAKE --> ORCH
    ORCH --> SUBSTRATE
    SUBSTRATE --> CATALOG
    CATALOG --> BIND
    KN --> CT
    APPS -.bind.-> BACKING
    APPS -.expose.-> EXPOSE

    classDef proven fill:#d4f4dd,stroke:#28a745
    class WH,RTS,RTP,WS,DEVAGENT,GQL proven
```

## Proven end-to-end (green = data-plane verified this cycle)
- **webservice + db + cache + identity + expose-api** → APIM-authed python endpoint (E2E-FULL #148)
- **realtime** (ingest→Kafka→processor→gateway `/ws`) through APIM (RT-2 W5 #177)
- **webhook** telemetry → bridge → Svix → **HMAC-signed external delivery** (#180, today)
- **graphql federation** through Hive Gateway, JWT-enforced (GQL-1 #160)
- **dev-agent** writes runnable code via GPT-5.4/APIM, no Anthropic key (#179)

## Key invariants
- **Per-service gitops repos** = tenancy unit (can run in own vcluster/cluster); central repo = audit ledger
- **HARD-3**: no `:latest` in CD defaults; CI commits image digest back to gitops
- **HARD-4**: every component type has a post-deploy contract test gating Ready
- **Bindings**: `<comp>-conn` secrets + envFrom; `expose-api` → APIM; reuse→repurpose→create
- **Intake convergence**: Slack / MCP / architect all funnel through `app.submit`
