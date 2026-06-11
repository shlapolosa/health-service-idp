# RT-2 — Role-aware realtime components (ingest / processor / gateway)

## Context

RT-1 (#156/#167) proved the realtime **transport**: a message on a Kafka topic the gateway
consumes is delivered through the gateway's consume→broadcast, over websocket, through APIM,
to a client (`WS_RECEIVED_TELEMETRY`). But of the intended pipeline only **one component's one
direction** was actually exercised:

```
rtdemo-ingest      sensor_raw     realtime_data_pipeline    sensor_agg     rtdemo-gateway     /ws
(webservice,   ─▶  (topic)   ─▶   (processor, NOT       ─▶  (topic)   ─▶   (realtime-     ─▶  client
 no producer)                      deployed)                                service) ✅ tested
        ▲────────────────────────── grey = never exercised ──────────────────────────▲
```

Root cause: `rtdemo-ingest`/`rtdemo-worker` were declared `type: webservice` → the scaffold gave
them a **generic onion HTTP shell with zero Kafka logic**. The `realtime_data_pipeline` processor
(meant to live inside the `realtime-platform` component) was never deployed. Only `rtdemo-gateway`
(`type: realtime-service`) got the realtime flavor, which wires `agent_common.realtime_fastapi`
(consume→/ws) automatically — which is exactly why it "just worked" once the lib bugs were fixed.

**What already exists (verified):**
- `realtime-service` CD already accepts `consumes?: [...string]`, `produces?: [...string]`,
  `websocket?: bool`, `realtime?: string` and injects `CONSUME_<t>` / `PRODUCE_<t>` /
  `REALTIME_PLATFORM_NAME` env (catalog/realtime-service.cd.yaml).
- `agent_common.realtime_agent` already has the engine primitives for **every** role:
  `send_kafka_message()` (produce), `register_message_handler(topic, fn)` + `_kafka_consumer_loop()`
  (consume), and `GenericRealtimeAgent` (concrete passthrough).
- The mscv scaffold branches on `SERVICE_FLAVOR=realtime` and emits **one** `main.py` shape — the
  ws gateway (`create_realtime_agent_app(..., websocket_endpoints=[{path:/ws}])`).

**So the contract you want — "declare the component and the topic it pub/subs" — already half-exists.**
The gap is purely: the scaffold + CD only know the **gateway** role; ingest and processor have no
generated wiring, and the platform cannot auto-generate the **business logic** (what to produce from an
HTTP body; how to aggregate `sensor_raw`→`sensor_agg`) — only the transport + a logic slot.

## Goal

Make **ingest**, **processor**, and **gateway** first-class realtime roles, each declaring its
pub/sub topics in OAM, with the platform auto-wiring transport (topics, consume/produce, ws, binding,
deploy, APIM) and giving the developer one clear logic slot. Then prove the **whole**
ingest→processor→gateway chain end-to-end through APIM.

## The role model

| Role | OAM declares | Platform auto-wires (transport) | Developer supplies (1 slot) |
|---|---|---|---|
| **ingest** | `produces:[sensor_raw]`, http, `expose-api` | HTTP endpoint + Kafka producer + binding + APIM | `to_message(req) -> dict` (map HTTP body → event); default = passthrough |
| **processor** | `consumes:[sensor_raw] produces:[sensor_agg]` | consumer loop + producer + binding | `transform(msg) -> dict | None` (aggregate / filter); default = identity |
| **gateway** | `consumes:[sensor_agg] websocket:true`, `expose-api` | consumer + `/ws` broadcast + JWT + binding + APIM | usually nothing (passthrough) — already done in RT-1 |

Invariant: the platform owns **bytes-in/bytes-out**; the developer owns **what the bytes mean**.

## Design decision — surface

Two ways to expose the roles. **Recommended: a `role` parameter on the existing
`realtime-service` CD** (not three full CDs), because:
- KubeVela 1.10.3 templates **cannot `import` shared CUE** ([[binding-contract]] CUE gotchas), so
  three full CDs would **triplicate the ~250-line render** → maintenance smell, against the
  maintainability-first principle.
- OAM authoring is essentially identical: `type: realtime-service` + `role: ingest` vs
  `type: realtime-ingest`.

```yaml
# realtime-service CD: add
role?: *"gateway" | "ingest" | "processor"
```

`role` drives: `websocket` default (gateway→true, else false), the `expose-api` apiType
(gateway→websocket, ingest→http), and the `serviceFlavor` hint passed to the scaffold claim
(`realtime-gateway` / `realtime-ingest` / `realtime-processor`).

**Optional sugar (defer):** three trivial alias ComponentDefinitions that set `role` + defaults and
delegate to the same render. Add only if discoverability demands it; flag the CUE-duplication cost.

> Open decision for the user: role-param (DRY, recommended) vs 3 named types (discoverable, triplicated
> CUE). The engine + scaffold + e2e work below is identical either way.

## Workstreams (additive, one PR each, fork→extend→route→verify)

### W1 — agent_common engine: ingest + processor app factories
`microservices/shared-libs/agent-common/src/agent_common/realtime_fastapi.py` (+ realtime_agent.py).
- Add `create_realtime_ingest_app(service_name, produce_topic, to_message=None, ...)`: a FastAPI app
  with `POST /ingest` (and `/health`) that calls `agent.send_kafka_message(produce_topic,
  to_message(body))`. `to_message` defaults to identity (passthrough). No websocket route.
- Add `create_realtime_processor_app(service_name, consume_topics, produce_topic, transform=None, ...)`:
  registers a per-topic handler via `register_message_handler` that runs `transform(msg)` and, if
  non-None, `send_kafka_message(produce_topic, result)`. No HTTP/ws beyond `/health`.
- Both reuse the existing config/secret/connection machinery (REALTIME_PLATFORM_NAME, CONSUME_*/
  PRODUCE_*, `_resolve_streaming_topics`). Gateway path unchanged.
- Tests in `tests/test_realtime_roles.py`: ingest produces on POST; processor transform→produce;
  passthrough defaults; non-breaking (gateway app still builds).

### W2 — realtime-service CD: `role` param + role-driven wiring
`factory/production-lines/traditional-cloud/adapters/catalog/realtime-service.cd.yaml`.
- Add `role?` param; derive `websocket` default + `serviceFlavor` (`realtime-<role>`) from it.
- `expose-api` apiType by role: gateway→`websocket`, ingest→`http` (processor: no expose-api — internal).
- Keep `consumes`/`produces`→`CONSUME_`/`PRODUCE_` env (already present); processor's `consumes`
  feeds `_resolve_streaming_topics`, gateway's too; ingest uses `produces` only.
- Additive: default `role=gateway` ⇒ today's behavior byte-identical.

### W3 — mscv scaffold: role-branching main.py
`factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml`
(the `SERVICE_FLAVOR=realtime` block).
- Branch on `SERVICE_ROLE` (from the claim's serviceFlavor): emit
  - `gateway` → existing `create_realtime_agent_app(..., websocket_endpoints=[/ws])` [unchanged].
  - `ingest` → `create_realtime_ingest_app(produce_topic=$FIRST_PRODUCE, to_message=to_message)`.
  - `processor` → `create_realtime_processor_app(consume_topics=$CONSUMES, produce_topic=$FIRST_PRODUCE,
    transform=transform)`.
- Each non-gateway main.py imports a **dev hook** from a sibling generated stub
  (`src/handlers.py` with `to_message`/`transform` defaulting to passthrough/identity) — see W4.
- Keep the agent_common vendor + deps steps (cfedc69 mechanism), shared by all roles.

### W4 — dev-logic slot + no-clobber on re-scaffold
- Generate `src/handlers.py` with a clearly-marked editable stub (`to_message` / `transform`).
- mscv must **create it only if absent** (the scaffold already `git pull --rebase`s; add a
  `[ -f src/handlers.py ] || cat > src/handlers.py` guard) so re-submits never overwrite the
  developer's logic. Document the contract in the generated README.

### W5 — true end-to-end proof OAM
- New `rtdemo2` OAM (or evolve rtdemo): `realtime-ingest` (produces sensor_raw, expose-api http) →
  `realtime-processor` (consumes sensor_raw, produces sensor_agg, a real aggregate e.g. rolling avg) →
  `realtime-gateway` (consumes sensor_agg, /ws) + `realtime-platform` + auth0.
- Verify each hop: `POST` telemetry to the ingest API **through APIM** → `sensor_raw` offset advances
  → processor consumes + produces `sensor_agg` → gateway delivers on `/ws` **through APIM**. One
  message in at the HTTP edge, transformed value out at the ws edge.

### W6 — RT-SVC-RESILIENCE (fold in)
- Make `_initialize_realtime_connections` non-fatal: on Kafka-unreachable, log + serve HTTP/ws +
  background-retry with backoff (don't crash). Critical now that ingest/processor/gateway all hard-depend
  on Kafka — a broker blip must not take down the HTTP ingest edge or live ws connections.

## Critical files
| File | Change |
|---|---|
| `agent_common/realtime_fastapi.py` (+ realtime_agent.py) | ingest/processor app factories; non-fatal Kafka init |
| `agent_common/tests/test_realtime_roles.py` | NEW role tests |
| `catalog/realtime-service.cd.yaml` | `role` param + role-driven websocket/expose-api/serviceFlavor |
| `composition/application-claim-composition.yaml` | scaffold role-branch + `src/handlers.py` stub (no-clobber) |
| `factory/docs/examples/rtdemo2-oam.yaml` | NEW full-chain e2e OAM |

## Architectural caveat — gateway broadcast at scale (must address before min-scale>1)
The gateway uses a Kafka consumer **group** (`<svc>-group`). With >1 replica, partitions are **split**
across replicas, so a message is consumed by **one** replica — but ws clients load-balance across
**all** replicas → a client on replica B misses a message consumed by replica A. RT-1 passed because
the gateway ran at **min-scale=1** (single pod). For a scalable gateway, each replica must see **all**
messages: either a **unique consumer group per pod** (broadcast-consume, not work-share — set
`group_id=<svc>-<pod>`), or a shared fan-out bus (Redis pub/sub) between replicas. **Processor and
ingest scale normally** (work-share is correct for them). Bake the per-pod-group choice into the
gateway role; pin gateway min-scale=1 until then.

## Risks / guards
- **CUE no-import** → do NOT triplicate the render; role-param keeps one CD ([[binding-contract]]).
- **Re-scaffold clobber** → `src/handlers.py` generated only-if-absent (W4); dev logic is sacred.
- **Topic existence/Reset** → fast-data-dev loses topics on restart; rely on `KAFKA_AUTO_CREATE=true`
  + the realtime-platform topic-provisioning job; processor/gateway tolerate not-yet-existing topics.
- **Consumer-group collisions** → distinct `group_id` per role/service; gateway per-pod (above).
- **Non-breaking** → `role` defaults to `gateway`; existing rtdemo gateway + all `webservice`
  components untouched; new factories are additive ([[feedback-non-breaking-changes]]).

## Verification
1. **Unit**: W1 tests green (ingest produce, processor transform→produce, passthrough defaults).
2. **E2E-chain**: rtdemo2 — one `POST` through APIM emerges transformed on `/ws` through APIM;
   `kafka-consumer-groups` shows sensor_raw + sensor_agg offsets advancing.
3. **Re-submit**: edit `src/handlers.py`, re-submit OAM → handler preserved (no clobber).
4. **Regression**: existing `realtime-service` (no role) still renders the ws gateway byte-identical;
   `webservice` components unchanged.
5. **Resilience**: kill demo-kafka briefly → ingest HTTP + gateway /ws stay up, reconnect on recovery.

## Effort
W1: 4-6h · W2: 2-3h · W3: 3-4h · W4: 1-2h · W5: 2-3h · W6: 2-3h — ~14-21h, ~5-6 PRs.
Reuses the RT-1 engine + binding contract; no new CD render, no new template repo.
