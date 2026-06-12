# DEV-AGENT — Autonomous software factory: use case → architecture → OAM → infra → implemented logic

## Context

The platform now provisions everything declaratively (GQL-1, RT-1: OAM in → repos, CI, images,
ksvcs, Kafka, auth, APIM products out), but the **logic slot stays empty**: scaffolded services
ship as shells (rtdemo-ingest produced nothing; the `transform()`/`to_message()` slots from RT-2
are placeholders). Goal: a **developer-agent** that closes that loop — listens for platform
events, and when an OAM app's services are all up, checks out the monorepo and implements the
logic until the contract tests pass.

### n8n audit findings (2026-06-11)

The "logic we had in n8n" lives in `local-ai-packaged/n8n-workflows-refactor/` (NOT deployed
in-cluster; nothing to migrate live — this is absorption of design, not porting of runtime).
It is a 7-stage **document pipeline**: webhook router (intent classify + slugify) →

1. **Business Analysis** → BRD (generate-or-reuse, validate, commit `BRD.md`)
2. **Architecture** → FOUR views: Business / Application / Data / Infrastructure architecture
   (ArchiMate-schema JSON, generate+validate+store each)
3. **Solution Architecture** → extract sequence diagrams → **search existing landscape → map
   sequences to components → assess change** (reuse-vs-create assessment)
4. **Risk Assessment** → risk artifact
5. **Test Strategy** → QA package
6. **Project Management** → **PRD** (generate+validate, commit)
7. **Software Delivery** → write PRD into repo → **run Taskmaster** (PRD → task decomposition)
   on a per-project branch of `shlapolosa/software-delivery`

Mechanics: Ollama (`ollama.socrates-hlapolosa.org`) for generation, Postgres for project/job/
artifact state, SSH+git for committing artifacts. **Critically: the n8n pipeline never spun
infrastructure and never implemented code — it stopped at PRD + task list.** The current
platform supersedes most of its mechanics:

| n8n piece | Superseded by |
|---|---|
| webhook intake + classify + slugify | slack-api-server → `app.submit` + architect-v1 |
| "search existing landscape" (reuse) | catalog MCP `kb.*`/`examples.*` + reuse→repurpose→create prompts |
| Ollama generation | Foundry architect-v1 (and Claude for the dev-agent) |
| Postgres job/artifact state | intake ledger + claims/ArgoCD conditions + `lifecycle.state` |
| SSH+git artifact commits | mscv / Socrates-FactoryBot GitHub App |

**The residue worth absorbing** (the actual gaps):
1. **The artifact chain** — architect-v1 today jumps use-case → OAM directly. The intermediate
   spec (BRD→PRD compressed) is exactly what the dev-agent needs to know *what* to implement.
2. **Taskmaster decomposition** — PRD → tasks = the dev-agent's work queue (and the repo's
   CLAUDE.md already mandates task-master).
3. **Validate-after-generate** at every stage (architect-v1 has `validate.*` — keep the pattern).
4. (Prior art: `n8n-workflows-start-here/` has a separate repo-analyzer → code-transformer →
   validator → test-generator pipeline — same analyze→transform→validate loop the dev-agent uses.)

**Decision (lean v1):** do NOT reproduce the 7-stage waterfall. Compress to: architect emits
`REQUIREMENTS.md` (BRD/PRD-essential + per-component acceptance criteria) alongside the OAM.
The 4-view architecture / risk / test-strategy documents become an optional "analysis pack"
later (W5 ports the prompts, doesn't wire them into the critical path).

## Target pipeline

```
use case (Slack / MCP / chat)
  └─▶ architect-v1: catalog reuse-check → OAM + REQUIREMENTS.md ──▶ app.submit
        └─▶ claims → repos + CI + infra + ksvcs   (EXISTS, proven)
              └─▶ Argo Events: "all components Ready" aggregate    (extend EVENT-2/W5)
                    └─▶ DEV-AGENT Job (Claude Code headless, ephemeral):
                          clone monorepo → read REQUIREMENTS.md + handler slots
                          → task-master decompose → implement → unit-test → push
                              └─▶ CI builds → redeploys → HARD-4 contract tests
                                    ├─ green → Slack "service live" + ledger mark ✅
                                    └─ red  → dev-agent iterates (bounded) ↺
```

The **interface contract** that makes this tractable (not "agent, write me an app"):
- RT-2 W4 dev slots (`src/handlers.py`: `to_message`/`transform`) = bounded edit surface
- `REQUIREMENTS.md` = what to implement (per-component acceptance criteria)
- HARD-4 contract tests = the done-signal the agent iterates against

## Workstreams

### W0 — n8n absorption + retirement (audit follow-through)
- Port the 4 high-value prompt sets (architecture views, solution-reuse assessment, risk, test
  strategy) from the n8n JSONs into `factory/production-lines/.../compose/prompts/analysis/`
  as **dormant** analysis-pack assets (documented, not wired).
- Mark `local-ai-packaged` n8n pipeline as absorbed/retired in its README; close #121
  (E2E-RUN-6 n8n path) as superseded — the platform-native path replaces it.

### W1 — SPEC-1: the spec travels into the repo
- Extend architect-v1 (compose adapter): after composing the OAM, also emit `REQUIREMENTS.md` —
  use-case summary, per-component responsibility, **acceptance criteria phrased as the contract
  tests** ("POST /ingest with X → sensor_raw carries Y"), non-goals. Validate-after-generate.
- `app.submit` carries it; mscv materializes it at monorepo root + per-service
  `microservices/<svc>/REQUIREMENTS.md` section. OAM annotation links the ledger entry.
- Schema kept minimal: the dev-agent and the human read the same file.

### W2 — dev-agent container image
- **Runtime placement: in-cluster ephemeral K8s Job on AKS**, namespace `dev-agent-system`,
  spawned by the Argo Events sensor (native trigger pattern, same as oam-apply/APIM Jobs).
  Rationale: trigger origin is in-cluster; cleanest creds (Workload Identity → Key Vault for
  FactoryBot key + ANTHROPIC_API_KEY via ExternalSecret); direct scoped-SA reads of platform
  state; $0 compute when idle (~1 CPU/2-4Gi per pass); cluster-stopped ⇒ no events ⇒ no runs.
  The container is the sandbox: NetworkPolicy restricts egress to github.com + api.anthropic.com,
  making headless `--dangerously-skip-permissions` safe. Rejected: GitHub Actions runner (cluster
  is the trigger origin anyway; key in org secrets), ACI/Container Apps (second substrate),
  Anthropic-hosted agents (not wired to the event fabric).
- `factory/production-lines/traditional-cloud/adapters/dev-agent/`: image with Claude Code
  (headless `claude -p`) + git + gh + task-master + python/poetry + node.
- Entrypoint contract: env in (`APP_NAME`, `REPO_URL`, `SPEC_PATH`, `ATTEMPT`), then:
  clone → read REQUIREMENTS.md + slots → `task-master` decompose (tasks.json committed for
  audit) → implement slots/service code → run unit tests → rebase-push (mscv retry pattern).
- Guardrails: edits confined to its monorepo checkout; token/turn budget caps; no cluster creds
  beyond what the Job mounts; bounded attempts (default 3) then Slack escalation.
- Creds: Socrates-FactoryBot GitHub App via Workload Identity + Key Vault (reuse P8.2 wiring);
  `ANTHROPIC_API_KEY` from Key Vault → ExternalSecret.

### W3 — trigger plumbing: "all services up" → dev-agent Job
- Extend the W5 lifecycle sensor: aggregate condition "every component of OAM app X Ready"
  (ArgoCD app Healthy + all ksvcs Ready) → spawn dev-agent Job (Argo Events trigger template).
- Idempotency: ledger/annotation marker `dev-agent.platform/status: {pending|running|done|failed}`
  — fire once per spec-generation; re-fire when `REQUIREMENTS.md` hash changes (spec update ⇒
  re-implementation pass).
- Frugality: ephemeral Job, runs only on Ready events, exits when done.

### W4 — the verification loop (depends on HARD-4)
- v1 inner loop: dev-agent runs unit tests locally before push (fast feedback).
- Outer loop: push → CI → redeploy → HARD-4 contract tests fire on ksvc-Ready → result lands in
  `lifecycle.state` → sensor re-invokes dev-agent with the failure report if red (ATTEMPT+1).
- Done: contract tests green → ledger marked, Slack "use case X is live: <APIM product URL>".

### W5 — analysis pack (optional depth, from W0 assets)
- `architect-v1` gains an opt-in "deep analysis" mode generating the 4-view architecture +
  risk + test-strategy docs into `docs/analysis/` of the monorepo. Not on the critical path;
  exists because the prompts are already written and enterprise consumers will ask for them.

### W6 — E2E: the full factory proof
- One command/Slack message: *"Build me a service that ingests wearable heart-rate telemetry
  and streams anomalies to a dashboard"* → architect composes (realtime ingest/processor/gateway
  + topics per RT-2) + REQUIREMENTS.md → infra up → dev-agent implements `to_message` +
  anomaly `transform` → contract tests green → demonstrate live data through APIM (HTTP in,
  ws out). Zero human commits.

## Dependency graph (why hardening lands first)

```
#169 HARD-2 (transport lib)  ─┐
#168 HARD-1 (scaffold image) ─┼─▶ RT-2 W1–W4 (roles + dev slots) ─┐
#170 HARD-3 (:latest ban)    ─┘                                    ├─▶ DEV-AGENT W2–W4 ─▶ W6 E2E
#171 HARD-4 (contract tests) ──────────────────────────────────────┤
SPEC-1 (W1, independent — can start immediately) ──────────────────┘
W0 n8n absorption (independent, small) — anytime
```

## Critical files
| File | Change |
|---|---|
| `compose adapter (architect-v1 prompt + capability-mcp-core submit path)` | REQUIREMENTS.md emission + validation |
| `application-claim-composition.yaml` (or mscv image post-HARD-1) | materialize REQUIREMENTS.md in monorepo |
| `factory/.../adapters/dev-agent/` | NEW: image, entrypoint, prompts, budget guards |
| `factory/substrate/argo-events/` | all-Ready aggregate sensor + dev-agent Job trigger + retry wiring |
| `factory/.../compose/prompts/analysis/` | NEW (dormant): ported n8n analysis prompts |
| `local-ai-packaged` README + task #121 | retirement notes |

## Risks / guards
- **Agent push hygiene**: direct-push to monorepo main with contract-test gate + Slack notify
  (autonomous-by-default); `DEV_AGENT_PR_MODE=true` flag for PR-review mode. Repos are PUBLIC —
  the agent must never write secrets (guard: pre-push secret scan in entrypoint).
- **Cost control**: per-Job token budget + 3-attempt cap + per-day app cap; Slack escalation
  instead of infinite loops. Cluster frugality unchanged (ephemeral Jobs).
- **Spec drift**: REQUIREMENTS.md hash marker prevents re-implementation storms; spec edits are
  deliberate re-triggers.
- **mscv push-race (#162)**: dev-agent uses the same rebase-retry; it lands AFTER scaffold Jobs
  (all-Ready gate) so contention is low.
- **Non-breaking**: everything additive; apps without REQUIREMENTS.md simply never trigger the
  dev-agent ([[feedback-non-breaking-changes]]).

## Verification
1. W1: submit OAM via architect → REQUIREMENTS.md lands in monorepo + ledger linked.
2. W2: dev-agent Job against rtdemo2 fixture implements `transform` correctly in ≤3 attempts.
3. W3: sensor fires exactly once per app-Ready; spec-hash change re-fires; no storms.
4. W4: forced-red contract test → agent receives failure report → fixes → green.
5. W6: full factory proof, zero human commits, live demo through APIM.
6. Regression: legacy submissions (no spec) behave exactly as today.

## Effort
W0: 2-3h · W1: 4-6h · W2: 6-8h · W3: 3-4h · W4: 4-5h · W5: 2-3h · W6: 3-4h — ~24-33h.
Sequenced after #169/#168/#171 + RT-2 W1-W4 (the interfaces it builds on).

## W2-W4 implementation notes (2026-06-12)

Shipped (all additive; sensor inert until a ksvc carries `dev-agent.cafe.io/enabled=true`):
- `factory/production-lines/traditional-cloud/adapters/dev-agent/` — image (node22-slim +
  git + python3 + pinned kubectl v1.31.4 + pinned `@anthropic-ai/claude-code`),
  `scripts/entrypoint.sh`, `scripts/verify-loop.sh`, `prompts/implement.md`,
  `tests/dry-run.sh` (PATH-shim harness, 16 assertions, macOS-safe — scripts use
  python3 for all parsing, no sed/jq).
- `factory/substrate/dev-agent/` — namespace, SA + least-privilege RBAC (read-only
  ksvc/jobs/pods/logs in `default`; creates nothing outside `dev-agent-system`),
  NetworkPolicy (egress 443 + DNS only; FQDN-tightening needs Cilium),
  ExternalSecret SKELETON (no values), `all-ready-sensor.yaml` (W3).

Decisions taken:
1. **All-Ready gate lives in the entrypoint**, not the sensor — Argo Events can't join
   across resources. Sensor fires per ksvc-Ready (mirrors HARD-4 contract-test-sensor
   exactly: resource EventSource UPDATE + gjson Ready filter + parameterised Job create);
   the entrypoint lists `app.oam.dev/name=<app>` ksvcs and exits 0 quietly if any is
   unready (the laggard's own Ready event re-fires).
2. **Two-layer idempotency.** Job name `dev-agent-<app>-<spec-hash-8>` (annotation
   `dev-agent.cafe.io/spec-hash` via sprig dataTemplate, fallback `g<generation>`) stops
   Ready-flap stacking; the repo marker `.dev-agent/spec-hash` (committed with the
   implementation) is what actually breaks the self-trigger loop, because the agent's own
   push bumps the generation. Changed REQUIREMENTS => new hash => re-fire.
3. **REQUIREMENTS.md 3-location fallback**: source-repo root → `<app>-gitops` root →
   ledger `health-service-idp-gitops/oam/applications/<app>-REQUIREMENTS.md` (matches
   where SPEC-1 lands it today; survives the planned move to the monorepo root).
4. **W4 verdict plumbing**: after push, verify-loop waits per CHANGED service for a NEW
   `latestCreatedRevisionName`, then for Job `ct-<revision>` completion, parses the
   one-line `{"component","type","check","pass","detail"}` verdict from its logs;
   `pass:false` details are injected verbatim into the next iteration's prompt.
   Timeouts produce synthetic fail verdicts so feedback is never empty.
5. **Cost/safety bounds**: MAX_ITERATIONS=3, CLAUDE_MAX_TURNS=50,
   `--permission-mode acceptEdits` (not skip-permissions) + NetworkPolicy sandbox +
   forbidden-path revert + pre-push secret scan (public repos). task-master decomposition
   deferred — the prompt drives implementation directly in v1.

Rollout order (operator):
1. Key Vault: create `dev-agent-github-token` + `dev-agent-anthropic-key` in
   kv-socrates-6706; wire the ExternalSecret (or `kubectl create secret` interim).
2. `az acr build --registry healthidpuaeacr --image dev-agent:v0.1.0 factory/production-lines/traditional-cloud/adapters/dev-agent/`
3. `kubectl apply -f factory/substrate/dev-agent/namespace.yaml -f rbac.yaml -f networkpolicy.yaml -f externalsecret.yaml` then `all-ready-sensor.yaml`.
4. Opt in one app: CD/annotation change stamps `dev-agent.cafe.io/enabled="true"`
   (+ optional `dev-agent.cafe.io/spec-hash`) on its ksvcs — owned by the CD workstream.

Open questions: (a) ksvc namespace is assumed `default` (NAMESPACE env exists but the
sensor hardcodes the watch ns); (b) generation-fallback Job names re-fire on every CI
deploy until the spec-hash annotation is stamped — harmless (marker exits 0) but noisy,
so stamping the annotation should land with the CD opt-in; (c) Slack escalation on
exhausted iterations is a log line today — wire to the existing notification path.
