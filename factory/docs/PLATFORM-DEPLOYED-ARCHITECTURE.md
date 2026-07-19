# Full-Capability Deployed Architecture (C4 Container view)

What the **runtime** looks like when one instance of every catalog capability is deployed at
once. This is the *workload plane* (the apps a consumer's OAM produces) sitting on the shared
*platform plane* (substrate). Contrast with `PLATFORM-CAPABILITIES.md`, which is the factory/meta view.

```mermaid
flowchart TB
    %% ---------------- External actors ----------------
    DEV(["👤 Developer / API consumer"])
    IOT(["📟 IoT / telemetry source"])
    RCVR(["🌐 External webhook receiver"])
    EU(["👤 End user (chat / GraphQL)"])

    %% ---------------- Edge / shared ingress ----------------
    subgraph EDGE["🛡️ Edge & Identity (shared)"]
        ISTIO["Istio Ingress Gateway<br/>LB 20.233.105.82.nip.io"]
        APIM["Azure APIM<br/>dual-auth: JWT OR sub-key"]
        AUTH0["Auth0<br/>identity provider"]
    end

    DEV --> APIM
    EU --> ISTIO
    IOT --> ISTIO

    %% ---------------- Capability: webservice stack ----------------
    subgraph C_WS["📦 webservice app (onion, python)"]
        WSVC["ksvc: api<br/>(domain/app/infra/interface)"]
        WSPG[("postgresql<br/>-conn")]
        WSRD[("redis<br/>-conn")]
        WSVC --> WSPG & WSRD
        WSVC -. envFrom auth0-conn .-> AUTH0
    end
    APIM -- expose-api --> WSVC

    %% ---------------- Capability: realtime platform ----------------
    subgraph C_RT["📦 realtime platform (rtdemo2) + bundled deps"]
        KAFKA[["Kafka broker"]]
        LENSES["Lenses HQ + Agent"]
        META["Metabase<br/>(analytics UI)"]
        MQTT["MQTT broker"]
        RTPG[("Postgres<br/>(lenses/metabase meta)")]
        RING["ksvc: ingest"]
        RPROC["ksvc: processor"]
        RGATE["ksvc: gateway /ws"]
        MQTT --> KAFKA
        RING -- sensor_raw --> KAFKA
        KAFKA -- sensor_raw --> RPROC
        RPROC -- sensor_agg --> KAFKA
        KAFKA -- sensor_agg --> RGATE
        LENSES --> KAFKA
        LENSES --> RTPG
        META --> RTPG
    end
    ISTIO --> RING
    RGATE -- websocket --> EU

    %% ---------------- Capability: webhook platform ----------------
    subgraph C_WH["📦 webhook platform (webhookdemo)"]
        SVIX["Svix engine<br/>+ postgres + redis"]
        PORTAL["App Portal<br/>(self-service endpoints)"]
        BRIDGE["ksvc: bridge<br/>role:webhook"]
        BRIDGE -- POST /msg --> SVIX
        SVIX --> PORTAL
    end
    KAFKA -- sensor_agg --> BRIDGE
    SVIX == HMAC-signed POST ==> RCVR
    RCVR -. registers endpoint .-> PORTAL

    %% ---------------- Capability: graphql gateway ----------------
    subgraph C_GQL["📦 graphql-gateway (Hive)"]
        HIVE["ksvc: hive-gateway<br/>(federation)"]
        SUB1["ksvc: subgraph-a"]
        SUB2["ksvc: subgraph-b"]
        HIVE --> SUB1 & SUB2
    end
    APIM --> HIVE
    HIVE -. federates .-> WSVC

    %% ---------------- Capability: camunda orchestrator ----------------
    subgraph C_CAM["📦 camunda-orchestrator (Zeebe 8) + bundled deps"]
        ZEEBE["Zeebe broker"]
        OPER["Operate + Tasklist + Optimize"]
        CAMES[("Elasticsearch<br/>(Operate/Tasklist store)")]
        WORKER["ksvc: zeebe-worker<br/>(handlers.py)"]
        WORKER --> ZEEBE
        ZEEBE --> CAMES
        OPER --> CAMES
    end
    ISTIO --> OPER

    %% ---------------- Capability: rasa chatbot ----------------
    subgraph C_BOT["📦 rasa-chatbot"]
        RASA["ksvc: rasa<br/>(prebaked model)"]
    end
    ISTIO --> RASA
    EU --> RASA

    %% ---------------- Platform plane (substrate) ----------------
    subgraph PLANE["⚙️ Platform plane — every box above is reconciled onto this"]
        direction LR
        KNATIVE["Knative v1.22<br/>(scale-to-zero ksvc)"]
        XPLANE["Crossplane v2.3<br/>(backing infra claims)"]
        ARGOCD["ArgoCD v3.4<br/>(per-app gitops repos)"]
        VELA["KubeVela<br/>(OAM render)"]
    end

    classDef ext fill:#fff3cd,stroke:#d39e00
    classDef edge fill:#e2e3ff,stroke:#5a4fcf
    classDef plane fill:#eee,stroke:#888
    class DEV,IOT,RCVR,EU ext
    class ISTIO,APIM,AUTH0 edge
    class KNATIVE,XPLANE,ARGOCD,VELA plane
```

## Reading it
- **Boxes (`📦`) = one OAM Application each** — independently scaffolded (own source+gitops repos), independently scalable, can live in its own vcluster/cluster.
- **Solid arrows = live data flow**; **`==>` = the proven signed-webhook hop**; **dotted = config/discovery wiring** (`envFrom <comp>-conn`, endpoint self-registration, federation).
- **Cross-capability flow** (the interesting bit): realtime's `sensor_agg` topic fans out to **both** the websocket gateway *and* the webhook bridge → Svix → external receiver. GraphQL federates the webservice subgraph. Everything fronts through Istio/APIM with Auth0-minted JWTs.
- **Platform plane** is shared singleton infra — not per-app. Each `📦` is rendered by KubeVela → Crossplane provisions its backing infra → ArgoCD syncs → Knative runs it.

## Footprint when ALL deployed at once (why it needs scale)
| App | Pods (approx) |
|---|---|
| webservice + pg + redis | 3 |
| realtime platform (kafka/lenses/mqtt + 3 ksvc) | 8 |
| webhook platform (svix/pg/redis + bridge) | 5 |
| graphql gateway + 2 subgraphs | 3 |
| camunda (zeebe/operate/tasklist + worker) | 5 |
| rasa | 1–2 |
| **workload total** | **~25–26** |

Plus ~85 platform-plane pods already running → **~110–115 pods**, needing **~7–8 B2ms nodes**
(max-pods=30/node). **Current cap: uaenorth vCPU quota ≈ 5 nodes** → full simultaneous deploy is
quota-blocked today; deploy in waves or request a quota increase.
```
