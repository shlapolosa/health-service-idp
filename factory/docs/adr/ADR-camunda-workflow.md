# ADR: CAMUNDA-WORKFLOW — Modernize the existing Camunda 8 stack into a first-class component

- Status: Accepted
- Date: 2026-06-13
- Relates to: RASA-CONTAINER (#178, variant-repo pattern), RT-1/RT-2 (realtime-platform
  `<name>-conn` binding), HARD-4 (#171, contract-test gate), HARD-3 (image pins).

## Context

The platform already ships a 770-line `camunda-orchestrator.cd.yaml` that renders a
full Camunda 8 Self-Managed stack: Zeebe (workflow engine, `camunda/zeebe:8.3.3`),
Operate, Tasklist, optional Optimize, with Istio Gateways/VirtualServices, BPMN via
ConfigMap, Kafka/event-streaming env, and bootstrap/scaffold/AppContainerClaim hooks.
It worked, but it predated the conventions rasa-chatbot and realtime-platform now
follow, so it was NOT first-class:

- BPMN models lived in inline ConfigMaps, not a dev-agent-editable variant repo.
- No `<name>-conn` secret — sibling webservices/job-workers had no normalized way to
  discover the Zeebe gateway.
- The scaffold-claim defaulted to a python/fastapi webservice (no worker scaffold).
- UIs were on a single bespoke `*.orchestration.local` host (path-prefixed), not the
  shared `*.20.233.105.82.nip.io` ingress convention.
- It was outside the HARD-4 contract-test gate, so "Ready" never implied "the engine
  can deploy and run a process" (the same false-green class that bit RT-1 for days).

## Decision

**Modernize the EXISTING Camunda stack in place** rather than building a new workflow
component or adopting a different engine. Close the six gaps additively, reusing the
rasa (variant repo), realtime-platform (`<name>-conn`), and contract-test patterns
verbatim. Keep every Camunda image, claim, and UI the CD already renders.

### Why Camunda (reuse) over the alternatives

Per the platform's "reuse → repurpose → create" principle, a new component needs an
explicit justification for not reusing what exists:

- **Argo Workflows** — already present, but ONLY as substrate (the CI/claim plumbing,
  EVENT-1/EVENT-2 sensors). It is a DAG/pipeline runner, not a BPMN/human-task engine;
  it has no Tasklist-equivalent human-task UI, no Operate-equivalent business-process
  monitoring, and no long-running stateful saga/compensation semantics. Repurposing it
  as the consumer-facing orchestration surface would mean rebuilding all of that.
- **Temporal** — a code-first durable-execution engine. Strong, but it is a NEW
  dependency (server + UI + SDK) with no BPMN modeler surface, and the platform already
  has a rendered, working Camunda 8 stack. Adopting it would be "create", not "reuse".
- **n8n** — the platform explicitly **RETIRED n8n** (N8N-ABSORB, 2026-06-11); it is not
  a candidate.
- **Camunda 8** — already rendered end-to-end here, gives BPMN modeling, Zeebe's
  horizontally-scalable engine, Operate (monitoring) and Tasklist (human tasks) out of
  the box. The only thing missing was the *conventions*, which is exactly what this ADR
  modernizes. Lowest-risk, highest-reuse path.

### Trade-offs accepted

1. **A second worker base image** (`zeebe-worker-base`) joins `rasa-base` as a prebaked
   invariant layer. Cost: one more image to build/pin/bump. Benefit: thin CI (no dep
   reinstall per build) and a clean dev-agent edit surface — consistent with rasa.
2. **The contract-test BPMN is start→end (no service task)** so it proves the engine
   independently of whether the variant's job-workers are up. We deliberately do NOT
   assert a worker completes a service task in the gate (that depends on the dev-agent's
   not-yet-written logic); the gate proves the *platform* (deploy + instantiate), and
   the worker logic is proven by the variant repo's own tests.
3. **UIs externally exposed by default** (`enableIstioGateway: *true`). Operate/Tasklist
   ARE the workflow design/run surface, so default-exposed matches rasa/realtime UIs;
   set `enableIstioGateway: false` to keep them internal. The legacy
   `*.orchestration.local` path-prefix routes are retained for backward compatibility.
4. **Worker runtime helper deferred.** The `zeebe_worker_base` bootstrap (the pyzeebe
   client + handler registry + deploy step) is SPECIFIED but not built/released this
   run, mirroring how `realtime-transport` was specified before being shipped.

## Consequences

- A `camunda-orchestrator` OAM component is now zero-touch: it provisions the engine +
  UIs + `<name>-conn` secret + a worker-scaffold variant repo, and is gated by a
  data-plane contract test — identical in shape to realtime-platform and rasa-chatbot.
- All changes are additive/non-breaking: existing consumer OAMs that set `gatewayHost`,
  `language`, or omit `enableIstioGateway` continue to validate and render.
