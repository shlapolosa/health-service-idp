# WEBHOOK-PLATFORM (#WH-1): Externally-exposed outbound webhook delivery

## 1. Goal

External third parties self-register an HTTPS endpoint + signing key and reliably
receive platform events (today: Kafka `sensor_agg`, lifecycle events) as **signed**
payloads with **retries/backoff** and **delivery logs**. A **self-service UI must be
exposed externally** so consumers manage their own endpoints/keys without
platform-team involvement.

## 2. Reuse decision (one line)

**Reuse Svix `svix/svix-server:v1.69.0` (MIT) as the engine + its magic-link App
Portal as the external self-service UI; repurpose the realtime-platform CD shape and
the realtime-transport wheel for the Kafka→engine bridge — build only thin glue.**
Full justification + comparison table: `factory/docs/adr/ADR-webhook-platform.md`.

| | Svix (chosen) | Convoy | Build |
|---|---|---|---|
| License | **MIT** | Elastic v2 (gated) | n/a |
| External self-service UI | **App Portal, magic-link, no account** | dashboard iframe | none |
| Image | `svix/svix-server:v1.69.0` | `getconvoy/convoy` | ours |
| Signing / retries / logs | yes / yes / yes | yes / yes / yes | reimplement |
| Fit | = realtime-platform shape | = shape | reuses wheel, no UI |

Sources: svix.com/open-source-webhook-service, github.com/svix/svix-webhooks (MIT),
hub.docker.com/r/svix/svix-server (v1.69.0 tag), svix.com/application-portal (magic
links); github.com/frain-dev/convoy + LICENSE (Elastic v2); docs.getconvoy.io.

## 3. Architecture

```
                     EXTERNAL                                      INTERNAL (vCluster, <name>-webhook ns)
  third-party dev ──HTTPS──> Istio ingressgateway ──VS/GW──> svix-server :8071 ── App Portal (magic link)
       │  (manages endpoints in portal)         host:                    │           REST /api/v1
       │                              <name>-webhook-portal.<lbHost>     ├── Postgres (metadata + delivery logs)
       │                                                                 └── Redis (queue + retry backoff)
       ▼ receives SIGNED POST
  registered HTTPS endpoint  <─────── svix delivery (HMAC, exp-backoff retries) ◄── svix /app/<consumer>/msg
                                                                                          ▲
  Kafka topic sensor_agg ──> realtime-service role:webhook (BRIDGE) ──forward msg────────┘
       (rtdemo2 platform)        envFrom <name>-conn (engine URL+admin token secret)
```

Components rendered by the `webhook-platform` CD + its composition:
- **svix-server** Deployment+Service (engine; pinned image; SVIX_DB_DSN/SVIX_REDIS_DSN/SVIX_JWT_SECRET).
- **Postgres** + **Redis** (svix deps).
- **App-Portal Gateway + VirtualService** — EXTERNALLY EXPOSED on `<name>-webhook-portal.<lbHost>`.
- **`<name>-svix-credentials`** Secret (SVIX_JWT_SECRET + minted SVIX_ADMIN_TOKEN) — runtime, never committed.
- **`<name>-conn`** Secret (pure-CUE) — WEBHOOK_ENGINE_API URL + WEBHOOK_ADMIN_TOKEN_SECRET name + event-type env.
- **event-type reconcile Job** — registers `spec.eventTypes[]` in Svix (idempotent, mirrors realtime topic-provisioning).

The **bridge** is a `realtime-service` in `role: webhook`: consumes declared
`consumes:` topics, maps each to a Svix event type, POSTs to the engine `/api/v1/app/<app>/msg`.

## 4. How external users register (self-service flow)

1. Platform/bridge creates a Svix **application** per consumer (or one shared app with
   per-endpoint filtering) via the admin REST API.
2. Operator (or an automated onboarding step) mints a **magic link** to the App Portal
   for that consumer: `POST /api/v1/app/<app>/dashboard/access` → short-lived session URL.
3. The consumer opens `https://<name>-webhook-portal.<lbHost>/...` (the external host),
   no Svix account needed, and: **adds their HTTPS endpoint URL**, **picks which event
   types to subscribe** (e.g. `sensor.agg`), and **copies their per-endpoint signing
   secret**. They can also view delivery logs + retry failed deliveries — all self-serve.
4. Programmatic alternative: the same REST API is publishable via **APIM** (expose-api)
   so a consumer registers endpoints by API call instead of the UI.

## 5. Event flow

`Kafka sensor_agg` → bridge (realtime-service role:webhook) consumes → maps topic→event
type `sensor.agg` → `POST <engine>/api/v1/app/<app>/msg` (bearer admin token) → Svix
fans out to every subscribed endpoint with an **HMAC signature header**, retrying with
exponential backoff and recording each attempt in the delivery log.

## 6. Security

- **Per-consumer signing secret**: Svix issues a unique HMAC secret per endpoint;
  consumers verify the `svix-signature` header. Secret is shown only in the portal.
- **Portal auth = magic link / short-lived session** (Svix App Portal model) — no
  long-lived consumer credential, no Svix account, no platform-team involvement.
- **Admin token** (`SVIX_ADMIN_TOKEN`) is minted by an init Job (`svix-server jwt
  generate`) into the runtime `<name>-svix-credentials` Secret — NEVER committed. The
  `<name>-conn` secret references it BY NAME; the bridge `envFrom`s it.
- **NetworkPolicy** (follow-up): restrict Postgres/Redis to the `<name>-webhook` ns;
  allow ingressgateway → svix only on :8071; egress from svix to the internet
  (delivery) is required and open.
- **`<name>-conn`**: the binding-contract aggregate — engine API URL, admin-token
  secret name, event-type env — so consumers bind ONE secret (mirrors realtime
  `<name>-conn`).
- Optionally publish the ingest/registration API through APIM with `validate-jwt`
  (expose-api trait already does this) for the programmatic path.

## 7. Rollout order

1. Merge CD + composition + XRD (this PR; additive, nothing references them yet).
2. **DONE (WH-1 complete):** composition renders Postgres (PVC+Secret+Deploy+Svc),
   Redis (Deploy+Svc), `<name>-svix-credentials` creds-init Job (mints
   `SVIX_JWT_SECRET` + `SVIX_MAIN_SECRET` + admin token via `svix-server jwt generate`,
   idempotent, SA/Role/RoleBinding scoped to the one Secret), Svix engine Deploy+Svc,
   App-Portal Gateway+VirtualService, and an event-type reconcile Job. XRD split to
   `webhook-platform-claim-xrd.yaml` (LegacyCluster, mirrors RealtimePlatformClaim).
3. Add the **webhook sink** to `microservices/shared-libs/realtime-transport` + a
   `role: webhook` scaffold variant (follow-up §9). Do NOT bump/release the wheel here.
4. Operator applies to the cluster (definitions-sync auto-applies the composition+XRD
   under `factory/substrate/crossplane/*.yaml`):
   - pre-pull images: `svix/svix-server:v1.69.0`, `postgres:16`, `redis:7-alpine`,
     `alpine/k8s:1.28.4`, `curlimages/curl:8.5.0`.
   - `vela def apply factory/production-lines/.../catalog/webhook-platform.cd.yaml`
   - `kubectl apply -f factory/substrate/crossplane/webhook-platform-claim-xrd.yaml`
   - composition is GitOps-synced (or `kubectl apply -f ...-composition.yaml`).
   - Runtime secret minted by the creds-init Job: `<name>-svix-credentials`
     (`SVIX_JWT_SECRET`, `SVIX_MAIN_SECRET`, `SVIX_ADMIN_TOKEN`). Nothing in git.
   - deploy `webhookdemo` OAM.
5. Mint a magic link, register a test endpoint, verify a signed `sensor.agg` delivery.
6. (Optional) publish the registration REST API through APIM.

### Contract-test / data-plane proof (follow-up)
The Svix engine Deployment carries `contract-test.cafe.io/enabled: "true"`. A
`check_webhook` was intentionally **not** added to `factory/substrate/contract-tests/
runner.py` yet (it needs live-cluster wiring + a `Deps.svix_*` client and a
`role: webhook` dispatch; half-adding it would fail the 38-green suite). The proof to
implement: via the engine REST API create an application + an endpoint pointing at a
test sink, POST a message of a declared event type, then assert the sink received the
HMAC-signed delivery within the retry window. Add alongside the bridge sink in §9.

## 8. OAM a consumer writes

See `factory/docs/examples/webhookdemo-oam.yaml`: a `webhook-platform` component
(declares `portalHost`, pinned `engineImage`, `eventTypes`) + a `realtime-service`
`role: webhook` bridge that `consumes: [sensor_agg]`, binds `webhookdemo-conn`, and
maps the topic to the `sensor.agg` event type.

## 9. Follow-up: transport-wheel webhook sink (DO NOT release the wheel here)

Add to `microservices/shared-libs/realtime-transport` a sink mirroring the processor
forward path. Exact factory function signature to add:

```python
# realtime_transport/sinks/webhook.py
def make_webhook_sink(
    engine_api: str,            # WEBHOOK_ENGINE_API from <name>-conn
    admin_token: str,           # from <name>-svix-credentials (envFrom)
    app_id: str,                # Svix application id for this platform/consumer
    topic_to_event_type: dict[str, str],  # {"sensor_agg": "sensor.agg"}
    *,
    timeout_s: float = 5.0,
) -> Callable[[str, bytes], Awaitable[None]]:
    """Returns an async sink(topic, payload) that POSTs
    {engine_api}/app/{app_id}/msg with {eventType, payload} using the admin
    bearer token. Idempotent via Svix idempotency-key = message hash."""
```

Wire `role == "webhook"` in the realtime-service role dispatch to consume `CONSUME_*`
and call this sink (no produce-back). Then bump+release the wheel in a SEPARATE PR.

---

## 9. BRIDGE — DELIVERED (Kafka→Svix), 2026-06-13 (RT-BRIDGE)

The webhook role + bridge wiring is now built. The full repeatable pipeline:

```
POST /ingest (rtdemo2 ingest) -> produce sensor_raw
  -> processor (sensor_raw -> sensor_agg)
  -> BRIDGE realtime-service role:webhook (consume sensor_agg)
       -> to_event(message) [default identity]
       -> POST {WEBHOOK_ENGINE_API}/app/{WEBHOOK_APP_ID}/msg
            { "eventType": WEBHOOK_EVENTTYPE_sensor_agg ("sensor.agg"),
              "payload": <message> }
            Authorization: Bearer {WEBHOOK_ADMIN_TOKEN}
  -> Svix fans out HMAC-signed POST to every registered endpoint subscribed
     to sensor.agg (exp-backoff retries, delivery logs).
```

### Bridge runtime contract (env it consumes)

The bridge envFroms ONE secret — `<webhook>-conn` — which carries everything:

| Env var                     | Source                              | Used for |
|-----------------------------|-------------------------------------|----------|
| `WEBHOOK_ENGINE_API`        | `<webhook>-conn` (CD, static URL)   | Svix REST base `http://<name>-svix.<ns>.svc:8071/api/v1` |
| `WEBHOOK_APP_ID`            | `<webhook>-conn` (bootstrap Job patches; CD default `platform-events`) | the shared app to POST to |
| `WEBHOOK_ADMIN_TOKEN`       | `<webhook>-conn` (bootstrap Job patches) | bearer for `/app/<app>/msg` |
| `WEBHOOK_EVENTTYPE_<topic>` | OAM `environment` (CD passes through) | topic→Svix event-type map (default = dotted topic) |
| `CONSUME_<topic>`           | realtime-service CD (`consumes:`)   | which Kafka topic(s) to bridge |
| `KAFKA_BOOTSTRAP_SERVERS` + `<realtime>-conn` | rtdemo2 `<realtime>-conn` | the source Kafka |

`role: webhook` is INTERNAL — `submit_use_case._auto_expose_external_components`
skips it (like processor): no HTTP surface to publish to APIM.

### Shared-app model (#5)

The platform provisions ONE shared Svix application `uid=platform-events` at
bootstrap. The bridge posts ALL events to it; external consumers register their
endpoints on it via the App Portal and subscribe to a subset of event types
(event-type-filtered fan-out). One app, many endpoints, server-side filtering.

The bootstrap reconcile Job writes the app id + admin token + engine URL into
BOTH `<name>-svix-credentials` and `<name>-conn`, so the bridge needs only the
single `envFrom: [{secretRef: {name: <webhook>-conn}}]` the OAM already declares.

### Two composition bug fixes (now correct)

**BUG-A (401 "Invalid token"):** the old creds-init minted the admin token with
`svix-server jwt generate`, which signs with the CLI's *default* secret — NOT the
random `SVIX_JWT_SECRET` injected into the server Deployment. The server verified
against a different key ⇒ 401. **Fix:** the admin JWT is now minted
DETERMINISTICALLY in-shell — HS256 (openssl) over the EXACT minted
`SVIX_JWT_SECRET` (raw utf-8 bytes, matching svix-server `HS256Key::from_bytes`),
claims `sub=org_23rb8YdGqMT0qIzpgGwdXfHirMu` (Svix default org ⇒ org-admin),
`iss=svix-server`, `exp=+10y`. Token and the server's verifying secret are now the
same key by construction.

**BUG-B (event types never created):** the old reconcile did `PUT /event-type/<n>/`
then `|| POST`, but the PUT-by-name 404s pre-create on this Svix and the `|| POST`
fallback was swallowed under `set -e` — so types like `sensor.agg` were never
registered (had to be hand-created via API). **Fix:** the bootstrap Job now
`POST /api/v1/event-type/` per declared type and treats `409 already-exists` as
success; it ALSO create-or-gets the shared app and patches the conn secret. Always
runs (even with no `eventTypes`) because the shared-app + conn-patch are required.
