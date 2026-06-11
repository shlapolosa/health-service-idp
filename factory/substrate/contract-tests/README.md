# Contract Tests (HARD-4 / #171)

Per-component-type **post-deploy data-plane proof**. A component reporting `Ready`
proves the *transport* (the pod accepts connections) — it does **not** prove the
*pipeline*. RT-1 was green for days while **zero telemetry flowed**. This harness
closes that gap: when a ksvc becomes `Ready` it runs the type-appropriate proof and
emits a pass/fail verdict.

This productises the hand-built RT-1 `rt1-flow` (an in-cluster pod that produced a
marker JSON message to the gateway's consumed Kafka topic and asserted the ws client
received it).

## What runs, per type

| component type (`app.kubernetes.io/component`) | role | check |
|---|---|---|
| `realtime-service` | gateway | produce marker to **consumed** topic → assert it arrives on `/ws` (rt1-flow) |
| `realtime-service` | ingest | POST marker to `/ingest` → assert **produced** topic end-offset advances |
| `realtime-service` | processor | produce marker to consumed topic → assert a transformed message appears on produced topic |
| `webservice` (expose-api) | — | `GET /health` → expect `200` |
| `graphql-gateway` | — | `POST /graphql` introspection → expect `200` + `data` |

Verdict (one line of JSON to stdout, exit `0`/`1`):

```json
{"check":"rt-gateway-ws-roundtrip","component":"rtdemo-gateway","detail":"...","pass":true,"type":"realtime-service"}
```

## How the type / role is detected (the contract)

Stated explicitly so the sensor and runner agree:

- **type** = the ksvc label **`app.kubernetes.io/component`** (every CD stamps it:
  `realtime-service` / `graphql-gateway` / `webservice`) → `CHECK_TYPE`.
- **role** (realtime only), most-specific first:
  1. `CHECK_ROLE` env — sensor maps the **`realtime-service.oam.dev/role`** annotation
     (rt-2 W2) to it; absent →
  2. `runner.py` **infers** from binding env the CD injects:
     `CONSUME_*`+`PRODUCE_*`+`WEBSOCKET=true` → gateway; `PRODUCE_*` only → ingest;
     `CONSUME_*`+`PRODUCE_*` (no ws) → processor.
- **app** = `app.oam.dev/name` (KubeVela-stamped) → `COMPONENT_APP` (Job naming/labels only).

Credentials and topics are read **at runtime** from env that the sensor wires via
`envFrom` the component's **`<comp>-conn`** secret (`KAFKA_BOOTSTRAP_SERVERS`,
`CONSUME_<topic>`, `PRODUCE_<topic>`, optional APIM sub-key). **Nothing is baked into
the image** — public-repo safe.

### APIM mode (env flag)

In-cluster by default (`APIM_MODE=false`): ws/http go to the ksvc cluster URL
`http://<name>.<ns>.svc.cluster.local`. Set `APIM_MODE=true` + `APIM_BASE_URL` +
`APIM_SUBSCRIPTION_KEY` to exercise the external path (the runner switches to
`wss://…/ws?token&subscription-key` and adds `Ocp-Apim-Subscription-Key`).

## Trigger plumbing

`factory/substrate/argo-events/contract-test-sensor.yaml` — modeled exactly on the
EVENT-2 sensor (`ksvc-ready-apim-publish.yaml`):

- **EventSource** watches `serving.knative.dev/services` (`UPDATE`) filtered to the
  opt-in label `contract-test.cafe.io/enabled: "true"`.
- **Sensor** fires on `Ready==True` (same gjson array filter) and `create`s a Job.
- **Idempotency**: the Job is named **`ct-<component>-<configurationGeneration>`**. A
  re-fire for the same revision re-creates the same name and is rejected (no stacking);
  a new revision bumps `configurationGeneration` → new name → re-test.
- **RBAC** (in the same file, independent SA `contract-test-event-sa`):
  ClusterRole to `get/list/watch` ksvcs + emit Events; namespaced Role in `default` to
  `create/get/list/delete` Jobs and `get/list` the `<comp>-conn` secret it envFroms.
  It creates **nothing else**.

> **Inert until opted in.** No CD stamps `contract-test.cafe.io/enabled` yet (that CD
> change is owned by other agents). Until it does, the EventSource matches nothing and
> the sensor fires no Jobs — strictly additive.

## Result surfacing

- **v1 (this PR):** the Job's completion/failure is visible to ArgoCD and `kubectl get
  jobs -l app.kubernetes.io/component=contract-test`. The verdict JSON is the Job's last
  log line (`kubectl logs job/ct-<component>-<gen>`); `backoffLimit: 0` means a failed
  contract test fails the Job (not retried-to-green).
- **W4 follow-up (deferred — do NOT modify existing components in this PR):**
  surface the verdict in **`lifecycle.state`** (the dev-agent's done-signal,
  factory/docs/plans/dev-agent-factory.md W4) and route a pass/fail to **Slack** via the
  same `slack-api-server` path the W5 `argocd-health-to-slack` sensor uses. The
  capability-mcp-core status/lifecycle use case would read the labeled Job's status +
  verdict log line. Not wired here to keep this change additive (no edits to
  capability-mcp-core or existing sensors).

## Image

`healthidpuaeacr.azurecr.io/contract-test-runner:<sha>`, built by
`.github/workflows/contract-test-runner-ci.yml` (azure/login OIDC + `az acr login`).
The sensor Job image is pinned to `:latest` as a **TODO-pin placeholder** — replace
with the immutable `<sha>` tag after the first CI build.

## Tests

```bash
PYTHONPATH=. /tmp/rtvenv/bin/python -m pytest tests/ -q
```

Unit tests mock the IO seam (`Deps`: ws / aiokafka / http) so they need no broker,
cluster, or network. They cover verdict formatting, env→config parsing, role inference,
per-type dispatch, the pass/fail branches of every check, timeout behaviour, and ws-URL
construction (in-cluster vs APIM).
