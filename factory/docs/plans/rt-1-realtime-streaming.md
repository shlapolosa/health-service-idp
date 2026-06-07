# RT-1: First-Class Realtime Streaming (Plan)

**Task:** RT-1 (#156) — implementation-ready plan for first-class realtime streaming in the OAM-driven platform.
**Status:** PLANNING (doc only). No code, no kubectl/az.
**Date:** 2026-06-07.

---

## 1. Goal (user's words)

> "for realtime, check template to see if possible to also create topics and a
> realtime-service which can write to the topics and also read from the topics
> and expose websocket — when creating realtime component, also need a webservice
> to consume/produce to it and that service must also define a webservice, we
> might need a new template."

Decomposed into three concrete asks:

1. **Topics as a first-class, declarative property** on the realtime component (today topics are hard-coded health-domain topics in a Job — `device_data`, `blood_pressure_device_topic`, etc.).
2. **A realtime-service** that reads/writes topics AND exposes a WebSocket — a *deployable app with source code*, not just infra. Today `realtime-platform` emits a placeholder Knative Service pointing at an image that does not exist.
3. **Producer + consumer webservices** that bind to the platform — these already work via the `realtime:` property on `webservice`. Mostly done; the gap is the realtime-service itself and topic declaration.

---

## 2. What exists today (empirical findings)

### 2.1 `realtime-platform` ComponentDefinition
`factory/production-lines/traditional-cloud/adapters/catalog/realtime-platform.cd.yaml` (migrated #152).
Renders (mirrors webservice pattern):
- **Primary:** a Knative `Service` named `<name>-realtime-service`, image = `parameter.image`, env includes `WEBSOCKET_ENABLED=true`, `REALTIME_PLATFORM_NAME`, `AGENT_TYPE=realtime-data-processor`. **No default image** → this service is inert unless the user supplies one. This is the "realtime-service" the user wants, but it has no source-code scaffolding and no topic/consumer wiring.
- **Secondary:** an always-created `RealtimePlatformClaim` (`platform.example.org/v1alpha1`) for backing infra.
- **Conditional:** an `AppContainerClaim` for source-repo scaffolding only when `language` is set (RETIRE-WFT-2 #152) — language is mapped onto the ApplicationClaim enum `python→fastapi`, `java→springboot`, `nodejs→graphql-gateway`, default python.

Parameters today: `image`, `port`, `version`, `database` (postgres|mysql|mongodb), `visualization` (metabase|grafana), `iot` (bool), `mqttUsers[]`, `language?`, `framework?`, `repository?`, `targetEnvironment?`, `resources`. **No `topics` property.**

### 2.2 `RealtimePlatformClaim` XRD + Composition
- XRD: `factory/substrate/crossplane/realtime-platform-claim-xrd.yaml`
  - spec: `name`, `appContainer`, `database`, `visualization`, `iot`, `mqttUsers[]`. **No topics field.**
  - status: `ready`, `message`, and `secrets{mqtt,kafka,database,metabase}` + connection URLs incl. `realtimeService`, `mqttWebSocket`, `lensesUI`, `metabaseUI`.
- Composition: `factory/substrate/crossplane/realtime-platform-claim-composition.yaml`
  - Provisions full stack: Postgres, MQTT (Mosquitto, exposes `websocket` port — lines ~296/347), Kafka + Schema Registry, Lenses HQ/Agent, Metabase, plus secret-copier RBAC/Job.
  - **Renders these secrets** (each `<name>-<kind>-secret`): `<name>-kafka-secret` (`KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SCHEMA_REGISTRY_URL`), `<name>-lenses-secret` (`LENSES_URL`, `LENSES_USER`, `LENSES_PASSWORD`, `LENSES_HQ_URL`), `<name>-mqtt-secret`, `<name>-db-secret`/`<name>-realtime-postgres-secret`, `<name>-metabase-secret`. NOTE: secret naming is `<name>-kafka-secret` (NOT the `<comp>-conn` single-secret pattern used by postgres/redis/auth0).

### 2.3 Topic creation today — Lenses-mediated, hard-coded
`factory/substrate/crossplane/realtime-platform/09-stream-processing-setup.yaml`:
- A `batch/v1` Job waits for Lenses HQ, then `POST http://lenses-hq:9991/api/v1/kafka/topics` for a **fixed health-domain topic set** (`device_data`, `blood_pressure_device_topic`, `heart_rate_device_topic`, `oxygen_saturation_device_topic`, `temperature_device_topic`, `health_alerts_topic`) with `partitions:3, replication:1`.
- A `ConfigMap` (`stream-processing-queries`) holds Lenses SQL `INSERT INTO ... SELECT STREAM ...` transforms.
- **Confirms platform decision:** topics ARE created through the Lenses HQ REST API (`/api/v1/kafka/topics`), admin:admin. Lenses is the topic-management contract. This is the lever RT-1 must parametrize.

### 2.4 Binding contract for producer/consumer webservices — ALREADY DONE
`factory/.../catalog/webservice.cd.yaml` has a `realtime?: string` parameter. When set it:
- adds env `REALTIME_PLATFORM_NAME`, `REALTIME_INTEGRATION_ENABLED`,
- `envFrom` (all `optional:true`): `<realtime>-kafka-secret`, `<realtime>-mqtt-secret`, `<realtime>-db-secret`, `<realtime>-metabase-secret`, `<realtime>-lenses-secret`.

Connectivity recipes (`factory/core/knowledge-base/connectivity-recipes/recipes.yaml`) codify this:
- `producer-needs-broker` (compute-service + messaging) → `property:webservice.realtime=<rt>`.
- `consumer-needs-broker` (messaging + analytics) → same. Docs explicitly say "Messaging goes through Lenses, not raw broker bootstrap. Topic management + governance live in Lenses HQ."

### 2.5 Shared library already supports websocket realtime services
`microservices/shared-libs/agent-common/src/agent_common/realtime_fastapi.py`:
- `create_realtime_agent_app(...)` → FastAPI app with `/health`, `/realtime/status`, `/realtime/connections`, `@app.websocket("/ws")`, `@app.websocket("/ws/events")`, lifespan that starts a WebSocket cleanup task, `WebSocketConnectionManager`.
- So a Python/FastAPI realtime-service is a *thin* app over this lib + an aiokafka produce/consume loop. `microservices/fintech-realtime-manual/` is a hand-built example proving the onion-architecture shape works for realtime.

### 2.6 Template selection (mscv / submit)
`factory/shared-libs/capability-mcp-core/src/application/submit_use_case.py`:
- Scaffolds when a component is `type: webservice`/`webservice-shape` with `language:` set and image absent/default.
- `_derive_framework(lang, fw)` is single source of truth; `_webservice_services()` builds `services[]` (UNIFY-1 #153) — ONE `AppContainerClaim` per OAM, one `ApplicationClaim` per service, scaffolding `microservices/<name>/`.
- ApplicationClaim XRD (`application-claim-xrd.yaml`) `framework` enum is **`[fastapi, springboot]` only** (comment: "only python/fastapi + java/springboot scaffold"); `language` enum likewise narrow. `realtime-platform.cd.yaml` only scaffolds when `language` is set, mapping to fastapi.

---

## 3. Gap analysis (what's missing for "first-class")

| Capability | Today | Gap |
|---|---|---|
| Declarative topics | Hard-coded health topics in a Job | No `topics:` property anywhere; not parametrized through XRD→Lenses |
| Realtime-service source | Placeholder Knative Service, no image, no scaffold-by-default | No realtime-service template/scaffold that read/writes topics + serves `/ws` |
| Producer webservice binding | DONE (`realtime:` on webservice) | none |
| Consumer webservice binding | DONE (`realtime:` on webservice) | none |
| Normalized `-conn` keys | Multiple `<name>-*-secret`s, ad-hoc keys | Not normalized to the DB_*/REDIS_* convention; no `<comp>-conn` aggregate |
| WebSocket auth | none (`/ws` open) | No identity story for websocket endpoint |
| Zero-touch test | none for realtime | No e2e fixture |

---

## 4. Target OAM example (the north star)

One OAM, four components: realtime platform (with declared topics) + a realtime-service (websocket gateway) + a producer webservice + a consumer webservice. Single identity component auths all exposed APIs (platform invariant).

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: telemetry-platform
spec:
  components:
    # 1. Realtime platform WITH declarative topics (NEW: topics property)
    - name: telemetry-stream
      type: realtime-platform
      properties:
        name: telemetry-stream
        database: postgres
        visualization: metabase
        iot: true
        topics:                       # <-- NEW first-class field
          - { name: sensor_raw,   partitions: 3, retention: 604800000 }
          - { name: sensor_agg,   partitions: 3, retention: 604800000 }
          - { name: alerts,       partitions: 1, retention: 86400000  }

    # 2. Realtime-service: reads+writes topics, exposes WebSocket (NEW shape)
    - name: telemetry-gateway
      type: realtime-service          # <-- NEW ComponentDefinition (see §6)
      properties:
        name: telemetry-gateway
        language: python              # scaffolds microservices/telemetry-gateway/
        realtime: telemetry-stream    # binds -kafka/-lenses/-mqtt secrets
        websocket: true               # exposes /ws, /ws/events
        consumes: [sensor_agg, alerts]
        produces: [sensor_raw]
        identity: telemetry-auth      # JWT on the WS upgrade (see §8)
      traits:
        - type: expose-api            # publishes /openapi.json; /ws via Istio (see §8)
          properties: { identity: telemetry-auth }

    # 3. Producer webservice (EXISTING binding, no change)
    - name: ingest-api
      type: webservice
      properties:
        name: ingest-api
        language: python
        realtime: telemetry-stream    # envFrom telemetry-stream-kafka-secret ...
        identity: telemetry-auth
      traits:
        - type: expose-api
          properties: { identity: telemetry-auth }

    # 4. Consumer webservice (EXISTING binding, no change)
    - name: alert-worker
      type: webservice
      properties:
        name: alert-worker
        language: python
        realtime: telemetry-stream

    # 5. Single identity component (platform invariant: exactly one)
    - name: telemetry-auth
      type: auth0-idp
      properties: { name: telemetry-auth }
```

---

## 5. The `-conn` normalization key set (proposed)

Today realtime binding spreads keys across `<name>-kafka-secret`, `<name>-lenses-secret`, etc. To match the DB_*/REDIS_*/AUTH0_* binding-contract convention (memory: binding-contract 2026-06-06), **add an aggregate `<name>-conn` secret** rendered by the RealtimePlatformClaim composition (additive — keep the existing `-*-secret`s for backward compat; UNIFY/non-breaking rule). Normalized keys:

```
# Kafka (Lenses-fronted)
KAFKA_BOOTSTRAP_SERVERS      = <name>-kafka.<name>-realtime.svc.cluster.local:9092
KAFKA_SCHEMA_REGISTRY_URL    = http://<name>-kafka.<name>-realtime...:8081
# Lenses (topic mgmt / governance)
LENSES_URL                   = http://<name>-lenses-hq...:9991
LENSES_HQ_URL                = (same)
LENSES_USER / LENSES_PASSWORD
# MQTT / IoT
MQTT_HOST / MQTT_PORT / MQTT_WS_URL
# Backing DB (reuse DB_* convention)
DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD / DATABASE_URL
# Topic catalog (NEW — populated from topics[])
TOPICS                       = comma-separated topic names
TOPIC_<UPPERNAME>            = one var per declared topic (e.g. TOPIC_SENSOR_RAW=sensor_raw)
# Identity for this platform binding
REALTIME_PLATFORM_NAME / REALTIME_INTEGRATION_ENABLED
```

`webservice` and `realtime-service` then `envFrom: <realtime>-conn` (single optional secretRef) instead of five separate refs. Decision: **add `-conn` aggregate, keep legacy refs one release, then deprecate** — preserves consumers already integrated.

---

## 6. Template verdict: NEW template — YES (lightweight)

**Verdict: YES, add a `realtime-service` ComponentDefinition, but reuse the existing fastapi scaffold + `agent_common.realtime_fastapi` — do NOT create a new microservice-creator template repo.**

Rationale (reuse → repurpose → create):
- The websocket runtime already exists (`create_realtime_agent_app`, `/ws`, `WebSocketConnectionManager`). Creating a brand-new template repo would duplicate it.
- The ApplicationClaim framework enum is `fastapi`/`springboot` only. A realtime-service is **fastapi + extra deps (aiokafka, websockets)** — it is a *variant of the fastapi scaffold*, not a new language. So: **no new framework enum value**; instead the scaffolder adds a realtime flavor to the fastapi template.

### 6a. `realtime-service` ComponentDefinition (NEW) — outline
- `definition.oam.dev/shape: knative-service`, `requires-source-code: "true"`.
- Renders: Knative Service (like webservice) + `envFrom: <realtime>-conn` + env `WEBSOCKET_ENABLED`, `CONSUME_TOPICS` (from `consumes[]`), `PRODUCE_TOPICS` (from `produces[]`), `REALTIME_PLATFORM_NAME`.
- Emits an `AppContainerClaim`/`ApplicationClaim` carrying a `serviceType: realtime` (or `flavor: realtime`) hint so the scaffolder seeds the realtime fastapi variant. Reuses `_webservice_services()` plumbing in submit_use_case (extend to recognize `type: realtime-service`).
- Health contract: `/health` + `/openapi.json` retained (Knative probes + APIM publish). `/ws` is the websocket; `expose-api` continues to publish only the HTTP/openapi surface (websocket is exposed via Istio VirtualService, not APIM — see §8).

### 6b. Scaffold contents (fastapi realtime flavor) — what the generated `microservices/<name>/` contains
```
src/main.py                 # create_realtime_agent_app(...) wired from env
src/domain/                 # message models (onion)
src/application/            # produce/consume use-cases
src/infrastructure/
    kafka_repository.py     # aiokafka producer+consumer from KAFKA_BOOTSTRAP_SERVERS,
                            #   topics from CONSUME_TOPICS/PRODUCE_TOPICS env
src/interface/api.py        # /health, /openapi.json, REST trigger endpoints
                            # (/ws provided by create_realtime_agent_app)
pyproject.toml              # adds aiokafka, websockets to fastapi base
Dockerfile, tests/, Makefile
```
This mirrors `microservices/fintech-realtime-manual/` (the proven hand-built example) and reuses `agent-common`.

### 6c. UNIFY-1 / services[] integration
- `submit_use_case._webservice_services()` and `_find_scaffold_component()` extended to treat `realtime-service` like `webservice` for scaffolding (language set → one services[] entry, framework `fastapi`, plus `flavor: realtime`).
- ApplicationClaim XRD: add **optional** `serviceFlavor: [webservice, realtime]` (default webservice) rather than widening the `framework` enum — keeps `framework` clean and non-breaking.

---

## 7. Topics: declaration → Lenses (CD/XRD/composition changes)

1. **OAM property** on both `realtime-platform` and `realtime-service`(consumes/produces): `topics: [{name, partitions, retention}]`.
2. **XRD** `realtime-platform-claim-xrd.yaml`: add `spec.topics` array (name required; partitions default 3; retention default 604800000).
3. **Composition** `realtime-platform-claim-composition.yaml`: replace the hard-coded topic Job (`09-stream-processing-setup.yaml` content) with a **parametrized topic-provisioning Job** that loops over `spec.topics` and `POST`s each to `http://<name>-lenses-hq:9991/api/v1/kafka/topics` (the existing Lenses contract). Keep idempotency (`|| echo "exists"`). The hard-coded health topics + Lenses SQL move to an *example*, not the default.
4. Topic names flow into `<name>-conn` as `TOPICS` / `TOPIC_*` (see §5) so producer/consumer/realtime-service discover them via env.

**Trait changes:** the existing `kafka-producer`/`kafka-consumer` trait *names* appear only in recipes; the actual binding is the `realtime:` property on webservice (no standalone TraitDefinitions inject kafka env today). Verdict: **no new TraitDefinitions needed** — the property-driven `realtime:` binding already covers producer+consumer. Topics are declared on the platform/service, not as traits.

---

## 8. Identity / auth for the WebSocket endpoint

- HTTP surface (`/openapi.json`, REST triggers): unchanged — `identity: <auth0>` + `expose-api` → APIM validate-jwt (existing platform rule, exactly one identity per OAM).
- WebSocket `/ws`: APIM "expose-as-MCP/HTTP" does NOT proxy websockets well, and the platform's APIM has a known POST-body bug on Developer SKU (memory: apim-mcp-post-body-bug). **Decision:** expose `/ws` via the **Istio ingress VirtualService directly** (path `svc/<name>/ws`), not through APIM. Auth on the upgrade request: validate the `Authorization: Bearer <jwt>` (or `?token=` query for browser WS) inside the realtime-service against the same `JWT_ISSUER_URI` from `<auth0>-conn`. `create_realtime_agent_app` gains an optional `verify_token` hook in the `/ws` handler.
- This keeps the "exactly one identity component auths all APIs" invariant: the same Auth0 issuer validates both APIM (HTTP) and the in-service WS check.

---

## 9. Zero-touch test design

End-to-end, no manual kubectl (drive through `app.submit` / OAM apply like existing flows):
1. **Fixture OAM** = §4 example with a tiny known topic (`rt1_smoke`) and a built realtime-service image (or scaffold-and-build).
2. **Assertions (script, pytest/bash):**
   - RealtimePlatformClaim → Ready; `<name>-conn`, `<name>-kafka-secret`, `<name>-lenses-secret` exist with expected keys.
   - Topic `rt1_smoke` exists in Lenses (`GET /api/v1/kafka/topics`).
   - realtime-service Knative ready; `GET /health` 200; `GET /openapi.json` 200.
   - Producer webservice POST → message lands on `rt1_smoke` (consume-back assertion via Lenses or a consumer endpoint).
   - WebSocket: connect to `/ws` with a valid JWT → receive an event; connect without JWT → 401/closed.
3. Reuse the recreation-loop atomic-delete recipe (memory) for teardown to avoid the 7-layer recreation cascade.
4. Add as `factory/.../examples/realtime-streaming-example.yaml` + a smoke script under `factory/utilities/`.

---

## 10. Risks

- **Lenses topic API drift / readiness race:** topic Job depends on Lenses HQ being up (existing init-container wait). Parametrized loop inherits this; keep retries.
- **Secret naming split-brain:** introducing `-conn` while keeping `-*-secret`s risks divergence. Mitigate: render `-conn` from the SAME composite fields; mark legacy refs deprecated, remove in a later release.
- **CUE constraints (memory):** vela 1.10.3 templates can't use `import`/top-level `context` and `&&` short-circuit over optionals breaks. The `topics[]` loop + `consumes/produces` env must be written as plain CUE comprehensions with `if x != _|_` guards.
- **WS through Istio, not APIM:** bypasses the central gateway policy surface for `/ws`; auth must be enforced in-service. Document in ADR.
- **Crossplane v1alpha1 Object + conversion webhook (memory: xplane PK):** the realtime composition still uses `kubernetes.crossplane.io/v1alpha1` Objects — pre-existing tech debt; not in RT-1 scope but note for the topic Job (use v1alpha2 if touching it).
- **Multi-webservice scaffold:** submit currently scaffolds; verify realtime-service + 2 webservices all land in one AppContainerClaim (UNIFY-1) without collision.

## 11. Effort estimate

| Workstream | Effort |
|---|---|
| `topics[]` on XRD + parametrized Lenses topic Job in composition | ~1 day |
| `<name>-conn` aggregate secret + TOPIC_* keys | ~0.5 day |
| `realtime-service` ComponentDefinition (CUE) | ~1 day |
| fastapi realtime scaffold flavor + ApplicationClaim `serviceFlavor` + submit_use_case wiring | ~1.5 days |
| WS JWT verify hook in `realtime_fastapi` + Istio VS for `/ws` | ~1 day |
| Zero-touch e2e example + smoke script | ~1 day |
| Recipes + REALTIME-PLATFORM-GUIDE docs + ADR | ~0.5 day |
| **Total** | **~6.5 engineer-days** |

## 12. Reuse-vs-create accounting

- **REUSE:** `agent_common.realtime_fastapi` (websocket runtime), `WebSocketConnectionManager`, fastapi scaffold, `webservice.cd.yaml realtime:` binding, RealtimePlatformClaim infra, Lenses topic REST contract, `_webservice_services()`/submit plumbing, `fintech-realtime-manual` as reference, DB_*/REDIS_* `-conn` convention.
- **REPURPOSE:** hard-coded topic Job → parametrized loop; `realtime-platform.cd.yaml` placeholder service path → real scaffolded realtime-service; `auth0-idp` identity → extended to WS upgrade.
- **CREATE (justified):** `realtime-service` ComponentDefinition (no existing CD scaffolds a websocket+kafka app); `topics[]` schema; `<name>-conn` aggregate; `serviceFlavor: realtime` enum; WS `verify_token` hook. Each is additive/non-breaking; ADR required for the WS-bypasses-APIM trade-off and the new CD.
