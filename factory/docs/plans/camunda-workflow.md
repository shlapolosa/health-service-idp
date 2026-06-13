# CAMUNDA-WORKFLOW — modernize the Camunda 8 stack into a first-class component

Bring the existing 770-line `camunda-orchestrator` CD up to the conventions
rasa-chatbot (variant repo) and realtime-platform (`<name>-conn` + contract-test
gate) now follow, REUSING the rendered Camunda 8 stack (Zeebe `8.3.3`, Operate,
Tasklist, optional Optimize). Nothing about the engine/UIs is rebuilt — only the
*conventions* around it.

## What was missing (the six gaps closed)

1. **Variant-logic-as-repo.** BPMN lived in inline ConfigMaps. Now a
   camunda-orchestrator scaffolds a variant-only monorepo dir, like rasa's bot.
2. **Scaffold routing.** `camunda-orchestrator` was absent from `_SCAFFOLD_TYPES`
   and fell through to legacy oam-apply. Now it routes through the claim path with
   `language=camunda` / `framework=zeebe-worker`.
3. **`-conn` secret.** No normalized binding. Now emits `<name>-conn` carrying
   `ZEEBE_ADDRESS` (gateway gRPC), `OPERATE_URL`, `TASKLIST_URL`.
4. **Externally-exposed UI.** UIs were on one bespoke `*.orchestration.local` host.
   Now Operate/Tasklist/Optimize each get a distinct `*.20.233.105.82.nip.io` host
   on the shared `istio: ingressgateway`.
5. **Contract-test gate (HARD-4).** Zeebe ksvc now carries
   `contract-test.cafe.io/enabled: "true"`; `check_camunda` deploys a trivial BPMN
   and runs an instance as the data-plane proof.
6. **HARD-3 pins.** All Camunda image tags stay pinned; the new worker base image is
   pinned (`zeebe-worker-base:v1.0.0`, never `:latest`).

## Invariant / variant split

| Concern | Class | Lives in | Changes when |
|---|---|---|---|
| Camunda 8 engine + UIs (Zeebe/Operate/Tasklist/Optimize) | invariant | the CD's rendered ksvcs (pinned tags) | platform bump (new tag) |
| pyzeebe runtime + worker bootstrap (handler registry, deploy step, graceful loop) | invariant | `zeebe-worker-base:v1.0.0` image | platform bump |
| `processes/*.bpmn` (the workflow definitions — the design surface) | **variant** | app repo `microservices/<svc>/processes/` | dev-agent edits |
| `workers/handlers.py` (job-worker logic per Zeebe service-task type) | **variant** | app repo `workers/` | dev-agent edits |
| `deploy/deploy.py` (thin: enumerate + upload BPMN to Zeebe) | **variant** | app repo `deploy/` | dev-agent edits rarely |
| thin Dockerfile (`FROM zeebe-worker-base:v1.0.0` + `COPY . /app/workflow/`) | variant shim | app repo `docker/worker/Dockerfile` | base-tag bumps only |

The scaffold ships a minimal **working** approval process (start → `review-request`
service task → end) wired to a registered passthrough worker that auto-approves, so
the workflow deploys and an instance completes before any real logic lands —
mirroring rasa's `actions.py` and realtime's `handlers.py` passthrough defaults. All
variant files are **create-if-absent**, and `processes/` is a no-clobber guard
artifact in mscv `entrypoint.sh` (closes the #175 recreation-storm hole for camunda
services).

## Event flow

```
consumer OAM (camunda-orchestrator + worker-scaffold + REQUIREMENTS.md)
  -> app.submit: validate -> commit to ledger -> claim path (camunda in _SCAFFOLD_TYPES)
  -> AppContainerClaim fans out: Zeebe/Operate/Tasklist ksvcs + <name>-conn secret
     + one ApplicationClaim -> mscv Job -> scaffolds processes/*.bpmn + workers/
  -> CI builds the worker image (thin FROM zeebe-worker-base) + deploys BPMN to Zeebe
  -> dev-agent implements processes/*.bpmn + workers/handlers.py per REQUIREMENTS.md
  -> a started instance runs on Zeebe; human tasks surface in Tasklist;
     the run is monitored in Operate; sibling webservices start instances via
     ZEEBE_ADDRESS from <name>-conn (envFrom)
  -> HARD-4 sensor fires on the Ready Zeebe ksvc -> check_camunda deploys a trivial
     BPMN + runs an instance -> data-plane verdict
```

## The OAM a consumer writes

See `factory/docs/examples/workflowdemo-oam.yaml`: a `camunda-orchestrator` (UI on,
gateway on, language omitted → camunda flavor), a `realtime-platform` for the Kafka
event-streaming bridge, and a sibling `webservice` that binds to the orchestrator's
`<name>-conn` via `orchestrator:` to start workflow instances.

## Rollout order (operator runbook)

1. **Build + push the worker base image** (follow-up; see worker-lib signature below):
   `docker build --platform linux/amd64 -t healthidpuaeacr.azurecr.io/zeebe-worker-base:v1.0.0 \
     factory/production-lines/traditional-cloud/adapters/zeebe-worker-base-image/`
   then `docker push ...`.
2. **Build + push the mscv image** (now sources `lib/camunda.sh`):
   `docker build --platform linux/amd64 -t healthidpuaeacr.azurecr.io/mscv:<next> \
     factory/production-lines/traditional-cloud/adapters/mscv-image/` then push; bump
   the Job image ref.
3. **Build + push the contract-test-runner image** (now has `check_camunda` + pyzeebe):
   add `pyzeebe` to the runner image deps, rebuild, push.
4. **Apply the modernized CD:** `vela def apply camunda-orchestrator.cd.yaml` (or commit
   to the definitions gitops path that ArgoCD reconciles).
5. **Seed the worker template repo:** create `shlapolosa/camunda-workflow-template`
   (any minimal repo — the variant scaffold ignores its contents, like chat-template).
6. **Submit the demo:** `app.submit` with `workflowdemo-oam.yaml`; watch the claim,
   Operate/Tasklist hosts, and the HARD-4 verdict.

## What the dev-agent edits later

Exactly the variant rows: `processes/*.bpmn` and `workers/handlers.py` (and rarely
`deploy/deploy.py`). It never touches the Dockerfile, the engine, or the conn wiring.
Re-scaffolds can never clobber its work (create-if-absent + the `processes/`
entrypoint guard, proven by dry-run scenarios 8–9).

## Worker runtime helper (follow-up — specify, do not build this run)

A `zeebe-worker-base` image + a tiny `zeebe_worker_base` python package (the camunda
analogue of `realtime-transport`):

```
zeebe_worker_base.run_worker(handlers: dict[str, Callable]) -> None
    # reads ZEEBE_ADDRESS (+ ZEEBE_INSECURE) from env (<name>-conn, envFrom),
    # opens an insecure pyzeebe channel, registers one job-worker per handler key
    # (the Zeebe service-task job type), runs the poll loop with graceful shutdown.
zeebe_worker_base.deploy_processes(paths: list[str]) -> None
    # deploy each BPMN file to the gateway (used by deploy/deploy.py + boot).
```
The thin Dockerfile's `CMD ["worker"]` invokes a base entrypoint that imports the
variant's `workers.handlers.HANDLERS` and calls `run_worker(HANDLERS)`.

## Risks / open questions

- **Zeebe gateway port over the mesh.** `<name>-conn` advertises `:80` (the Knative
  ksvc port); pyzeebe's default Zeebe gateway port is `26500`. The contract-test
  default falls back to `26500` when no port is given — confirm the in-cluster ksvc
  actually fronts the gateway gRPC on the advertised port during live bring-up.
- **Knative + long-lived gRPC streams.** Job-workers hold long-lived streams to the
  gateway; verify Knative scale-to-zero / activator behaviour doesn't drop them
  (may need `minScale: 1` on the worker, already the orchestrator default).
- **realtimePlatform is required.** The CD mandates a `realtime-platform` ref for the
  event-streaming bridge even when a consumer only wants the engine; a future option
  could make it optional.
