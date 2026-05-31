# Operator-v1 — Processes, Methodologies, Prompts, Empirical Failure-Modes

Companion to [2026-05-30-tools-needed.md](2026-05-30-tools-needed.md). That doc enumerates the *capabilities* the operator needs; this one enumerates the *reasoning patterns* — when to use which tool, what to ask, what gotchas to recognize.

Structure:
1. **Methodologies** — meta-rules that govern how the operator reasons
2. **Processes** — concrete iteration loops the operator runs
3. **Prompts** — operator system-prompt skeleton + diagnostic prompt templates + subagent-spawn templates
4. **Empirical failure modes** — platform-specific gotchas catalogued from incidents

---

## 1. Methodologies

These are the durable rules. They're already in memory under `feedback-*` files; the operator's system prompt must internalize them.

### M1 — Empirical RCA, no masking
Source: [feedback-empirical-no-masking-brief.md](../../.. /.claude/projects/-Users-socrateshlapolosa-Development-health-service-idp/memory/feedback-empirical-no-masking-brief.md)

- Always read actual logs / specs / cluster state. Never speculate.
- If a step fails, diagnose THAT step before doing anything that bypasses it.
- "Looks Ready" ≠ "works". Don't claim success on cosmetic state.
- When multiple things go wrong, fix one at a time; report each empirically.

**Today's example:** when wearables submission failed, the operator must NOT assume "no code" → push placeholder images. The correct chain is read failing workflow → identify the actual step that crashed → diagnose that script empirically.

### M2 — Local smoke before containerise
Source: [feedback-local-smoke-before-containerise.md](../../.. /.claude/projects/-Users-socrateshlapolosa-Development-health-service-idp/memory/feedback-local-smoke-before-containerise.md)

- Mock-based unit tests miss CLI flag/format bugs.
- Before rebuilding a container that shells out to vela/kubectl/helm: run the code path locally against the real binary (or `k8s.exec` into an existing pod that has it).
- Saves a 3-5 minute build/push/deploy cycle when the bug is in the integration with the CLI.

**Today's example:** the `vela_client --format markdown` regex mismatch would have been caught by a local `vela show webservice` invocation; instead it shipped to a pod, was deployed, and only surfaced via post-deploy verification.

### M3 — Consumer-impact gate before fixing
Source: [feedback-consumer-impact-gate.md](../../.. /.claude/projects/-Users-socrateshlapolosa-Development-health-service-idp/memory/feedback-consumer-impact-gate.md)

- Before raising a PR for a failure surfaced through testing (not user-facing): verify a real consumer reads the output of the failing thing.
- If no consumer depends on it, it's dead code — don't fix.
- Stop when the user's workflow succeeds, not when the script is squeaky-clean.

**Today's example:** S-CP-002 (curl missing) + S-CP-004 (PEP 668) addressed a `PERSONAL_ACCESS_TOKEN` secret that no generated workflow reads. PR #10 was strictly noise reduction (Failed Job in the dashboard); S-CP-004 was correctly discarded after the consumer-impact check.

### M4 — Non-breaking additive changes
Source: [feedback-non-breaking-changes.md](../../.. /.claude/projects/-Users-socrateshlapolosa-Development-health-service-idp/memory/feedback-non-breaking-changes.md)

- Consumers are integrated; every change to architect-v1 prompt / MCP tool surfaces / CDs / OAM wire / APIM policies MUST be additive.
- Fork-first refactors are the right shape (Stage 1 of the oam-apply consolidation): copy verbatim, mutate the copy, route gradually, audit, cut over, delete.

**Today's example:** the 7-stage consolidation deliberately avoided in-place edits of `microservice-standard-contract` (the working Slack chain). Risk-reducing pattern.

### M5 — Reuse → repurpose → create
Source: [feedback-reuse-repurpose-then-create.md](../../.. /.claude/projects/-Users-socrateshlapolosa-Development-health-service-idp/memory/feedback-reuse-repurpose-then-create.md)

- Before proposing new infrastructure: exhaust existing capabilities + check whether an existing thing can be adapted.
- ADR for any new component must justify "why not reuse/repurpose".

**Today's example:** when we needed traits/policies metadata, instead of building a custom parser, we first tested whether `vela show` worked on TraitDefinitions (it did) and only added a lightweight CUE parser for the two kinds vela CLI doesn't support.

### M6 — Brief, structured, empirical responses
Source: same as M1 (last paragraph) — user pushed back hard on long structured tables, multi-paragraph "honest assessments".

- Default response shape: 1-3 short sentences + one specific next step.
- Tables only when data demands it.
- Don't narrate internal deliberation.

---

## 2. Processes (iteration loops)

These are concrete sequences the operator runs. Each is named so it can be invoked from the system prompt or higher-level orchestrator.

### P1 — Empirical RCA loop
For: any reported failure.

```
1. OBSERVE
   - List the resources involved (kubectl get; argo workflow get; argocd app get)
   - Capture: phase, status, conditions, recent events, last log lines
2. CLASSIFY
   - Match against signals catalog (signals/README.md). Existing signal? Apply known fix.
   - Novel? Continue.
3. DIAGNOSE (read-only)
   - For workflows: which step Failed? Read its logs + the script body
   - For pods: events + describe + container logs (current + previous)
   - For ArgoCD apps: status.sync.status + status.conditions + spec.source
   - For Crossplane Objects: status.conditions + the underlying Job's logs
4. ROOT-CAUSE HYPOTHESIS (one sentence)
   - Cite the line/file/event that proves it
   - If can't cite, go back to step 3
5. FIX-SHAPE PROPOSAL
   - Smallest possible change that closes the root cause
   - Bounded blast radius (single file / single CD / single workflow template)
6. EMPIRICAL VALIDATION (local-smoke per M2)
   - Run the changed code path against real cluster before building/pushing
   - For YAML/CUE: vela dry-run, kubectl apply --dry-run=server
   - For scripts in pods: k8s.exec to mimic
7. APPLY
   - PR (don't push to main)
   - Wait for CI
8. MONITOR
   - Verify fix landed + no regression in the parent workflow
9. DOCUMENT
   - New signal entry in catalog if novel
```

### P2 — CI fix loop
For: red CI on an in-flight PR.

```
1. Pull failing job log via gh.actions.log(job_id)
2. Classify the error:
   - Flaky-shaped (timeout, network, runner died) → re-enqueue
   - Real (assertion, missing dep, syntax) → fix
3. Smallest possible fix; push to same branch
4. Wait for CI re-run
5. If new failure → goto 1
6. If green → mark PR ready; report to user
```

**Stopping conditions:** if the same fix shape appears 3 times in a row OR if the failure requires a code design decision → STOP and surface to the user with a focused question.

### P3 — Cleanup of test artifacts (atomic-delete)
For: removing test-class resources without triggering recreation loops.

```
1. ENUMERATE — list every resource matching the test pattern
   (OAM Apps, Claims, XR composites, Crossplane Objects, Jobs,
    ksvcs, ArgoCD apps, workflows, vCluster namespaces, GitHub repos)
2. CLASSIFY EACH — platform-system vs test-only
   - Platform (preserve): slack-api-server, capability-*, govern-opa,
     lifecycle-orchestrator, observe-audit-sink, approve-pr,
     classify-router, compose-canonical, ui-cli, the foundation
     argo + argocd + crossplane + vela + knative components
   - Test (delete): everything else
3. SURFACE — show the list to user; for irreversible items
   (GitHub repos, namespace deletion) get explicit confirmation
4. STOP IN-FLIGHT — terminate any active workflows for the resource set
5. DISABLE SELF-HEAL — patch ArgoCD apps' syncPolicy: null + finalizers: null
   (otherwise ArgoCD recreates everything you delete)
6. ATOMIC DELETE — in this order, fast (no waits between):
   a. ArgoCD apps
   b. OAM Applications
   c. Claims + XR composites (after patching finalizers to null)
   d. ksvcs
   e. Crossplane Objects (after patching finalizers)
   f. Default-ns Jobs leftover
7. CLEAN GITOPS — remove stale OAM files from health-service-idp-gitops
   (otherwise argo-events sensor re-applies them next sync)
8. DELETE GITHUB REPOS — only after step 7; only with delete_repo scope
9. WAIT + VERIFY — 3 minutes; 0 in all buckets; if recreated, identify the source
   (cached ArgoCD state, in-flight workflow, sensor)
```

### P4 — Build/deploy a service (capability-mcp-server pattern)
For: shipping a Python service change.

```
1. Make source edits
2. Run pytest locally (catches syntax + unit-test regressions)
3. Build + push image: docker buildx build --platform linux/amd64
   -f <svc>/Dockerfile -t healthidpuaeacr.azurecr.io/<svc>:<tag> --push <context>
4. Decide deployment strategy:
   - Update kustomization.yaml + push to ArgoCD-watched repo
     (if service is ArgoCD-managed — e.g. slack-api-server)
   - kubectl patch ksvc directly with JSON patch (only image field)
     (if service is directly managed — e.g. capability-mcp-server)
5. Watch knative revision rollout: ready_revision != current ← 8 ticks * 8s
6. EMPIRICAL verify the new code path works (M2 local-smoke fallback)
```

### P5 — Refactor with stage-cascading (the 7-stage pattern)
For: consolidating two implementations into one.

```
Stage 1 — FORK: copy verbatim with rename. No behavior change.
Stage 2 — EXTEND ADDITIVELY: add new capability behind a flag/parameter.
   Both old and new paths continue to work.
Stage 3 — ROUTE: change the caller (single call site) to use the new fork.
   Test empirically end-to-end on the new path.
Stage 4 — REFINEMENTS: handle edge cases discovered post-route.
   Defer if scope grows.
Stage 5 — AUDIT: grep every caller of the old name across repo + cluster.
   Distinguish runtime vs test vs comment.
Stage 6 — CUTOVER: switch the remaining callers to the new fork.
   Verify identical behavior on the legacy paths.
Stage 7 — DELETE: only when audit shows no live cluster reference.
   Refresh cluster cache (kubectl apply) for any templates that
   templateRef the old name from other templates.
```

Each stage is its own PR, independently mergeable, easily rolled back.

### P6 — Architectural-quality audit (catalog richness)
For: ongoing meta-task. Operator could run this as cron.

```
For every ComponentDefinition / TraitDefinition / PolicyDefinition / WorkflowStepDefinition:
1. Read its CUE template
2. Count parameters
3. Count parameters with `// +usage=` annotation
4. Run `vela show <name>` and check DESCRIPTION column populated count
5. Surface gap: "<name> has N parameters, M descriptions" — flag if M < N
```

Output: a quality scorecard the operator (or human) reviews, fixes incrementally per the gradual rollout in [the user's CD enrichment plan](../system-prompt.md#cd-enrichment).

---

## 3. Prompts

### 3.1 Operator-v1 system prompt — skeleton

```markdown
You are operator-v1, an autonomous Kubernetes platform operator for the
health-service-idp platform.

Your single goal: every compliant request that enters the platform succeeds
its run (workflow Succeeded + Claims Ready + ksvc Ready=True).

You have these tools available: [see 2026-05-30-tools-needed.md composite
inventory]

You internalize these methodologies as inviolable rules:
M1 — Empirical RCA, no masking
M2 — Local smoke before containerise
M3 — Consumer-impact gate before fixing
M4 — Non-breaking additive changes
M5 — Reuse → repurpose → create
M6 — Brief, structured, empirical responses

You can run these processes:
P1 — Empirical RCA loop (default for any failure)
P2 — CI fix loop (for in-flight PRs with red CI)
P3 — Cleanup of test artifacts (atomic-delete with user confirmation
     for irreversible steps)
P4 — Build/deploy a service
P5 — Refactor with stage-cascading
P6 — Architectural-quality audit (cron candidate)

Scope guardrails:
- You can FIX any definition (CD CUE, composition Job script, RBAC binding,
  kustomize transformer, workflow template) by raising a PR.
- You CANNOT extend a feature, create new ComponentDefinitions, change
  consumer-intent OAM semantics, or take destructive action (delete repo,
  delete namespace, push to main, force-push) without explicit user
  authorization.
- Before any destructive action, surface the action list and the
  irreversibility risk; wait for confirmation.

When invoked autonomously (timer/cron):
- Run P6 if no in-flight incidents
- Run P2 on any PR you've opened that's not yet merged + has red CI
- Stop and report if you find nothing actionable for 3 consecutive ticks

When invoked by user with a question:
- Default to M6: brief, structured, empirical
- Don't narrate deliberation; state results
```

### 3.2 Diagnostic prompt templates

These are the per-symptom diagnostic skills the operator should have. Each
is a few-shot prompt the operator constructs and runs against itself or
sub-tools.

#### D1 — "Why is X recreating after I delete it?"

```
A resource of kind {kind} named {name} in {namespace} keeps being recreated
within {timing} after I `kubectl delete` it.

Trace which controllers may be touching it:
1. Get the resource's labels + annotations — look for:
   - argocd.argoproj.io/tracking-id (ArgoCD applied it)
   - app.oam.dev/* (KubeVela rendered it from an OAM Application)
   - crossplane.io/composite (Crossplane composition produced it)
   - argoproj.io/workflow-* (Argo Workflow step created it)
2. For each suspected controller, identify its source-of-truth:
   - ArgoCD: spec.source.repoURL + path. If git refresh fails (404 etc),
     the controller may still apply from its cache.
   - KubeVela: the parent OAM Application name from spec.applicationRef
   - Crossplane: the parent XR via metadata.ownerReferences
3. Disable the source before deleting the resource. Specifically:
   - ArgoCD: patch syncPolicy: null + finalizers: null + delete the app first
   - KubeVela: delete the parent OAM Application
   - Crossplane: delete the parent Claim → which deletes the XR → which cascades
4. Atomic delete in P3's documented order to avoid race re-creation
```

#### D2 — "Why is workflow {name} Failed?"

```
For Argo workflow {name}:
1. argo.workflow.get({name}) — read status.phase + status.message
2. List nodes (status.nodes) — which type=Pod nodes have phase != Succeeded?
3. For each failed node:
   - argo.workflow.logs({name}, step={node})
   - If the node is a step calling templateRef, recursively diagnose that
     subroutine's logs
4. Cross-reference the step's `when:` clause. Common failure shapes:
   - "Invalid 'when' expression" — the substituted parameter contains
     characters govaluate can't parse (e.g. base64 string with = or +)
   - "step group deemed errored due to child" — recurse into that child
   - Permission errors — RBAC missing (see D5)
5. For the root failing node, identify whether its script (container.args[0])
   has known anti-patterns (HEREDOC indent, set -e + git commit on
   nothing-to-commit, etc.)
```

#### D3 — "Why is the OAM Application's deploy step Failed?"

```
For OAM Application {name} with workflowFailed status:
1. Read status.workflow.steps[].message — full error from KubeVela
2. Common shapes:
   - "failed to get cluster <X>: virtualclusters... not found" →
     KubeVela's cluster registry has no entry for X. Either the OAM's
     topology policy points at a vCluster that's never been registered
     via `vela cluster join`, OR target should be host.
   - "evaluate base template" → CUE template error in the CD. Read
     the CD's spec.schematic.cue.template and find the field the error
     references.
   - "cannot reference optional field" → CUE optional field is being
     dereferenced without default. Add `*<default> | <type>` to the
     parameter declaration OR wrap reference in `if x != _|_ { ... }`.
3. If topology mismatch (the vCluster issue): fix in oam-updater Job's
   script (sets clusters: [<vcluster>] based on ApplicationClaim.spec.
   targetVCluster) — or in the OAM file in gitops.
```

#### D4 — "Why is ksvc Ready=False / RevisionMissing?"

```
For Knative Service {name} with Ready=False:
1. kubectl get ksvc -o jsonpath='{.status.conditions}' — read reasons
2. Common reasons:
   - RevisionMissing — no Ready revision. Inspect revisions:
     kubectl get revision -l serving.knative.dev/service={name}
   - Unschedulable — pods can't be placed. Run D6 (CPU pressure)
   - ImagePullBackOff — image doesn't exist. Verify with
     `docker manifest inspect <image>` or `crane ls <repo>`
   - ContainerCreating-stuck — usually secrets/configmaps missing
3. For RevisionMissing specifically: check if source repo's CI has built
   + pushed the image referenced. For auto-scaffold path (language: set),
   the microservice-creation workflow's microservice-creator Job + the
   subsequent source-repo CI must have completed.
```

#### D5 — "Why is this Pod/Job failing with permission denied?"

```
For pod/{name} or job/{name} with permission errors:
1. Find the service account: kubectl get pod {name} -o jsonpath='{.spec.serviceAccountName}'
2. List all CRBs / RBs binding to that SA:
   kubectl get clusterrolebinding,rolebinding -A -o json | jq with that SA
3. For the specific verb+resource the error mentions, simulate:
   kubectl auth can-i {verb} {resource} --as=system:serviceaccount:{ns}:{sa}
4. Fix shape: extend the existing ClusterRole that binds to this SA
   (not a new role) — find via crb.roleRef.name
```

#### D6 — "Why is the cluster Insufficient cpu?"

```
1. Per-node CPU allocations: for each node:
   kubectl describe node {n} | grep -A2 "Allocated resources" | grep cpu
   → shows reservations vs available (e.g. 1810m (95%))
2. If reservations > usage significantly, identify reservation hogs:
   kubectl get pods -A -o json | sort by sum of container.resources.requests.cpu
3. Categorize: which pods can be scaled down?
   - Per-vCluster pods (activator + kourier + workload, ~1.1 cores each):
     often the test-vCluster artifacts (see P3 cleanup)
   - Knative active services that are scaled-to-N but idle: bump down
     to min=0 if appropriate
   - Stuck terminating pods: force-delete (--grace-period=0)
```

### 3.3 Subagent prompt template (when operator needs to delegate)

```
[ROLE]
You are a {role}. {one-sentence task summary}.

[CONTEXT]
{What has already happened — recent PRs, recent failures, what state cluster is in}

[NEEDED]
{Specific bounded task — what they should produce}

[SOURCES]
{Exact file paths + cluster resources they should read; "Don't invent"}

[OUTPUT]
{Format spec — file location, structure, length cap}

[CONSTRAINTS]
- {Time/scope cap — "20 min", "under 500 words"}
- {Tool restriction — "read-only", or "you may build but not deploy"}
- Don't invent components or signal patterns — if you can't find empirical evidence, omit
```

Reusing this template gets consistent subagent quality. Today's visualization spawn used this exact shape — produced grounded output in 110 seconds.

### 3.4 User-confirmation prompt template (for destructive/irreversible actions)

```
{Action description — one sentence}

{Why this is needed — one sentence}

Specific items affected:
- {item 1} — {recoverability note}
- {item 2} — {recoverability note}
- ...

Risk: {single sentence on what's hard/impossible to undo}

Proceed? [y/n], or specify "skip <items>" to exclude.
```

Today's pattern: bulk namespace delete was blocked by the classifier exactly because this confirmation wasn't surfaced explicitly. Operator should ALWAYS surface this before destructive ops, not after the classifier denies.

---

## 4. Empirical failure modes (the gotchas catalog)

Specific platform-environment quirks the operator must recognize. Most cost real time today.

| # | Failure shape | Recognition pattern | Fix |
|---|---|---|---|
| F1 | ArgoCD apps recreate after delete | Resource recreated <5min after `kubectl delete`; has `argocd.argoproj.io/tracking-id` annotation | Patch syncPolicy: null + finalizers: null FIRST, then delete (D1, P3) |
| F2 | Cluster cache vs file drift on WorkflowTemplate | Source file shows X, `kubectl get workflowtemplate -o yaml` shows Y | `kubectl apply -f <file>` to refresh the cluster cache |
| F3 | Argo when-clause won't evaluate base64 strings | Workflow Failed: "Invalid 'when' expression 'YXBp...'" | Move conditional INSIDE the script (always run + early-exit), don't use when: |
| F4 | CUE optional field with default → default never materialises | Render error: "cannot reference optional field: X" | Remove `?` from parameter declaration; required field with default = `name: *<default> \| <type>` |
| F5 | `vela show <name> --format markdown` outputs different format | Parser regex matches 0 rows | Drop the flag; default table format has `\| col \|` separators |
| F6 | `vela show` doesn't work on PolicyDefinition/WorkflowStepDefinition | Error "could not find <name> in namespace" | Read CUE template via k8s API; parse `parameter:` block with custom parser |
| F7 | Image build in Crossplane composition Jobs lacks curl/jq | Job log: "curl: not found" / "jq: not found" | `apk add --no-cache curl jq` at top of script |
| F8 | Alpine 3.19+ PEP 668 blocks pip install | "error: externally-managed-environment" | `pip3 install --break-system-packages <pkg>` |
| F9 | Job script with `set -e` + `git commit` on no changes → exits non-zero | BackoffLimitExceeded after first-run success | `git diff --cached --quiet \|\| git commit ...` |
| F10 | Crossplane Object re-fires on Job.spec.template immutability | Event: "CannotUpdateExternalResource: Job.spec.template: Invalid value" | Set `managementPolicies: ["Create", "Observe", "Delete"]` on the Object |
| F11 | Knative ksvc patch strategy drops volumes | Webhook: "volume with name 'X' not mounted" | Use `kubectl patch --type=json` with `[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"..."}]` only |
| F12 | ArgoCD app source.path = file → ComparisonError | "<path>.yaml: app path is not a directory" | source.path = dirname; add `directory.include: <basename>` |
| F13 | argo-workflow-executor SA missing | Pod event: "serviceaccount X not found" | `kubectl create sa <name> -n argo`; verify existing CRB bindings still apply |
| F14 | argoproj.io/applications missing from RBAC | Step Failed: "applications.argoproj.io is forbidden" | Extend existing ClusterRole; don't create a new one |
| F15 | 3-tier auto_create_vcluster default change broke pre-existing tests | Tests assert `True` but code says `False` | Update tests to match (the code is the authority since 3-tier was the intentional design) |
| F16 | spaCy model download produces empty-version URL | Install failed: 404 on `/-en_core_web_sm/-en_core_web_sm.tar.gz` | Pin the wheel URL directly in CI workflow |
| F17 | pytest.ini addopts reference plugin not in requirements.txt | "unrecognized arguments: --cov=src" | Install plugin in CI step (don't add to runtime requirements) |
| F18 | per-vCluster pods reserve 1.1+ cores each → cluster CPU saturated | Pods Pending: Insufficient cpu; actual node usage low | Delete test-vCluster namespaces (D6 + P3) |
| F19 | Webservice CD's `parameter.framework` referenced without default | Render error on `language:` set, `framework:` unset | `framework: *"auto" \| string` (no `?`) |
| F20 | Knative ksvc gitops update via direct kubectl patch reverted by ArgoCD | New image set, then immediately rolled back | Update via the gitops-watched kustomization.yaml file; let ArgoCD sync |

---

## 5. The operator's mental model

Distilled from the patterns above, the operator's mental model has 4 layers:

1. **Schema layer** (what's allowed) — CD CUE templates, parameter types, enum constraints. Govern at CUE/policy-engine level.
2. **Catalog layer** (what's discoverable) — MCP tools returning rich metadata. The agent's source of truth.
3. **Workflow layer** (what happens) — Argo WorkflowTemplates, Crossplane Compositions, ArgoCD Applications. Sequence of state transitions.
4. **Runtime layer** (what's running) — Pods, ksvcs, OAM Applications. The actual cluster state.

Failures cascade DOWN: a schema gap (F19) becomes a workflow failure (cascade), becomes a runtime symptom (RevisionMissing). Fixes go UP: the operator finds the runtime symptom, traces UP to the lowest layer where the gap can be closed cleanly.

Today's incidents always followed this pattern:
- Runtime: ksvc Ready=False
- Workflow: workflow Failed at step X
- Catalog: parameters empty / not what agent saw
- Schema: CUE allowed something policy should have rejected

Operator: trace down, fix at lowest layer possible (cheapest reproduction surface), validate up.

---

## 7. Classification of issues

The operator needs to classify every incident along multiple orthogonal dimensions so the right *process* runs. The matrix below names the dimensions, then catalogs today's incidents against them — empirical training data.

### 7.1 Classification dimensions

| Dimension | Values | Why it matters |
|---|---|---|
| **Class** (signal taxonomy) | S-CP (Crossplane), S-WF (Workflow), S-OAM, S-CD (ComponentDefinition), S-RBAC, S-K8S, S-CFG, S-CI (CI/CD), S-CLN (Cleanup), S-CAT (Catalog quality) | Routes to the right diagnostic prompt |
| **Layer** | Schema, Catalog, Workflow, Runtime | Determines where to look + where to fix (fix at lowest layer possible) |
| **Consumer-impact** | HIGH (blocks user outcome), MEDIUM (degraded UX or drift), LOW (operator-noise only), NONE (dead code) | Per M3 (consumer-impact gate) — gates whether to fix at all |
| **Reversibility** | Reversible (edit/test), Irreversible (delete, push to main, send notification, delete repo) | Per scope-guardrails — irreversible needs explicit user confirmation |
| **Detection channel** | workflow-log, pod-event, dry-run, argocd-status, CI-log, k8s-events, cluster-cron, gh-api | Tells operator which tool to invoke first |
| **Fix venue** | CD CUE, Crossplane composition, WorkflowTemplate, gitops repo, RBAC, image rebuild, CI workflow file, agent prompt, MCP server code | Determines which subagent / tool / PR-target to use |
| **Urgency** | blocker (user can't proceed), degraded (works but slow/messy), cosmetic (operator-noise), latent (no immediate impact) | Prioritization within an autonomous tick |
| **Recurrence** | one-shot (single incident), recurring (every request), pattern (will hit every CD/workflow of this kind) | Pattern → fix in template, not per-incident |

### 7.2 Today's incidents classified

Each row is an actual incident from today's session. The matrix below lets the operator pattern-match future incidents against known classes + run the right process.

| Incident | Class | Layer | Impact | Reversibility | Detection channel | Fix venue | Urgency | Recurrence | Process | PR |
|---|---|---|---|---|---|---|---|---|---|---|
| gitops-setup not idempotent | S-CP-001 | Workflow | HIGH | Reversible | workflow-log | Crossplane composition | blocker | every-request | P1 | #9 |
| gitops-setup missing curl | S-CP-002 | Workflow | LOW | Reversible | pod-event | Crossplane composition | cosmetic | every-request | P1 | #10 |
| gitops-setup PEP 668 pip | S-CP-004 | Workflow | NONE | n/a | pod-event | Crossplane composition | cosmetic | every-request | M3 gate→discard | (none — gated out) |
| gitops-setup clobbers OAM | S-CP-005 | Workflow | HIGH | Reversible | gh-api (commit diff) | Crossplane composition | blocker | every-request | P1 | #11 |
| wait-for-microservice opaque | S-WF-001 | Workflow | MEDIUM | Reversible | workflow-log | WorkflowTemplate | degraded | every-failure | P1 | (deferred) |
| webservice CD allows nginx:* | S-CD-* | Schema | HIGH | Reversible | dry-run | CD CUE | blocker | every-AI-submit | P1 + M4 | #13 |
| catalog.describe returns 0 params | S-CAT-* | Catalog | HIGH | Reversible | mcp-tool-test | MCP server code | blocker | every-AI-submit | P1 | #13 |
| catalog missing traits/policies/recipes | S-CAT-* | Catalog | MEDIUM | Reversible | mcp-server inventory | MCP server code | degraded | every-AI-submit | M5 reuse-vela + P5 | #13 |
| `oam-apply` source.path = file | S-WF-* | Workflow | HIGH | Reversible | argocd-status | WorkflowTemplate | blocker | every-app.submit | P1 | #14 |
| argo-workflow-executor SA missing | S-RBAC-* | Runtime | HIGH | Reversible | pod-event | RBAC | blocker | recurring | P1 + D5 | #14 |
| argoproj.io/applications RBAC missing | S-RBAC-* | Runtime | HIGH | Reversible | workflow-log | RBAC | blocker | every-app.submit | P1 + D5 | #14 |
| 5 test-class workloads reserving CPU | S-K8S-* / S-CLN-* | Runtime | MEDIUM | Irreversible (ns delete) | k8s-top-pods | cleanup | degraded | recurring after tests | P3 + D6 + user-confirm | (no PR — cluster op) |
| recreation loop on delete | S-CLN-001 | Runtime | MEDIUM | Reversible (atomic delete) | k8s-watch | n/a (process) | blocker for cleanup | recurring | P3 + D1 | (no PR — process) |
| pattern2 cluster cache stale | S-WF-* / F2 | Workflow | MEDIUM | Reversible | argo.template.diff | WorkflowTemplate (apply) | degraded | rare | M2 + kubectl apply | #18 |
| 2 Stage-6 sed misses | S-CFG-* | Code | LOW | Reversible | repo-grep classify | source files | degraded | refactor-time | E.4 + ast-inspect | #18 |
| notify-failure when-clause gap | S-WF-* | Workflow | MEDIUM | Reversible | workflow.coverage | WorkflowTemplate | degraded (silent failures) | every-new-step-added | E.6 | #18 |
| spaCy 404 in CI | S-CI-* | CI | HIGH (blocks PR merge) | Reversible | CI-log | CI workflow file | blocker | every-CI-run | P2 | #16 fix-chain |
| pytest-cov missing in CI | S-CI-* | CI | HIGH | Reversible | CI-log | CI workflow file | blocker | every-CI-run | P2 | #16 fix-chain |
| Pre-existing 3-tier broken tests | S-CI-* / F15 | CI | HIGH | Reversible | CI-log | source tests | blocker | latent until refactored | P2 + git-log-blame | #16 fix-chain |
| GitHub test repos still exist | S-CLN-* | gitops | LOW | **Irreversible** | gh-api | gh.repo.delete | cosmetic | recurring after tests | P3 step 8 + user-confirm | (gh API) |
| ksvc Knative patch strategy drops volumes | S-K8S-* / F11 | Runtime | HIGH | Reversible | k8s-webhook | rebuild via kustomize | blocker | every direct patch | F11 + kustomize route | (no PR) |
| ArgoCD auto-revert on direct patch | S-CFG-* / F20 | Runtime | HIGH | Reversible | k8s-watch | gitops repo | blocker | every direct patch | F20 + gitops route | (no PR) |
| pattern1_foundational.py runtime ref | S-CFG-* | Code | LOW | Reversible | grep-classify | source file | degraded | refactor-time | E.4 | #18 |

### 7.3 Decision rules (the operator uses these to route)

```
class + impact + reversibility → action

HIGH consumer-impact + Reversible      → fix immediately (default to P1; PR-based)
HIGH consumer-impact + Irreversible    → surface to user + wait for confirmation
MEDIUM consumer-impact + Reversible    → fix when other work allows (P1)
MEDIUM consumer-impact + Irreversible  → surface; wait
LOW consumer-impact + Reversible       → fix only if other work demands
LOW consumer-impact + Irreversible     → DON'T fix; document as known noise
NONE consumer-impact (per M3 gate)     → don't fix; remove from signals catalog
```

```
detection_channel → first tool to invoke

workflow-log     → argo.workflow.get + argo.workflow.logs
pod-event        → k8s.describe + k8s.events
dry-run          → vela.dry_run + cue.lint
argocd-status    → argocd.app.get + argocd.app.cache_state
CI-log           → gh.actions.log + gh.pr.checks
k8s-events       → k8s.events + k8s.describe
cluster-cron     → P6 audit (catalog quality, drift detection)
gh-api           → gh.repo.* (commits, exists, scopes)
```

```
recurrence → fix-shape

one-shot     → fix the specific resource (e.g. kubectl patch this one Job)
recurring    → fix the template (e.g. Crossplane composition, WorkflowTemplate)
pattern      → fix the schema OR add policy gate (CD CUE constraint, Govern invariant)
```

### 7.4 The classification surfaces a key insight

Today's incidents cluster heavily in TWO classes:

1. **Workflow-layer Crossplane composition Jobs** — 7 incidents (S-CP-001/002/004/005/007 + S-WF-* derivatives). These all live in `crossplane/application-claim-composition.yaml` + `crossplane/app-container-claim-composition.yaml`. **One file** generates most of the cluster's autonomous failure surface. Pattern: a single shell script in a Crossplane Object's Job spec, run by a temporary pod, with `set -e` + side-effects. The operator should treat this file as a **high-incidence area** worth proactive audit (P6 against shell-script anti-patterns: idempotency, missing tooling, set -e + git commit, etc.).

2. **CI workflow files** — 3 incidents in a row (spaCy, pytest-cov, 3-tier tests) all in `.github/workflows/slack-api-server-ci.yml` + adjacent tests. Pattern: rarely-touched config that bit-rots silently. Operator should add P2 to its cron schedule for any open PR.

Other classes had 1-2 incidents each — much lower density.

### 7.5 What the operator does NOT classify (and must not)

- **Architectural decisions** — e.g. "should we have two workflows or one?" — operator escalates to human + architect-v1 agent.
- **Feature scope** — operator can fix definitions/configs/templates; it cannot extend a feature or create a new ComponentDefinition. That's architect-v1's surface.
- **Business logic** — operator doesn't touch consumer OAMs except via the platform-supplied chain.

If an incident falls outside the classification matrix above, operator's correct action is: **document the gap, surface to user, do not act**.

---

## 8. Architectural layer awareness (captured 2026-05-30 reflection)

The operator must distinguish between LINE-LEVEL fixes (today's bread and butter) and FACTORY-LEVEL structural questions (which it should NOT attempt; surface to architect-v1 + human).

### 8.1 The 4 architectural layers

| Layer | Archetype | Owns | Operator scope |
|---|---|---|---|
| **Boundary** | Ports + adapters (hexagonal) | Contracts between consumer/outside and platform | Operator can fix adapter bugs, RBAC, image rebuilds |
| **Flow** | Pipes + filters / DAG | WorkflowTemplates, Crossplane compositions, Job scripts | Operator can fix step scripts, RBAC, idempotency. CANNOT add new lines. |
| **Manufacturer** | Bounded context (DDD) | Per-manufacturer catalog + govern + execute + lines | Operator CANNOT — architect-v1 + human territory |
| **Substrate** | Shared infrastructure | K8s, ArgoCD, KubeVela, Crossplane, Knative, Istio | Operator can apply RBAC, patch ksvcs, restart components. CANNOT change shape. |

### 8.2 Classifying any incident by layer

Before applying P1 (Empirical RCA), the operator asks: at which layer does the root cause live?

```
Symptom               | Probably at layer
----------------------|------------------
script bug in Job     | Flow (Crossplane composition Job)
RBAC denied           | Boundary (adapter SA / role binding)
CUE template error    | Boundary (CD as a contract)
workflow when-clause  | Flow
ArgoCD source.path    | Flow
ksvc not scheduling   | Substrate
image not found       | Boundary (the build/push adapter)
catalog returns []    | Boundary (the catalog adapter)
recreation loop       | Substrate + Flow interaction
line doesn't exist    | Manufacturer — STOP, escalate
```

### 8.3 Escalation triggers (operator stops + asks human)

The operator MUST stop and surface when:

- Fixing the issue requires changing the BOUNDARY contract (port shape, adapter responsibilities)
- Fixing requires creating a new MANUFACTURER realisation
- Fixing requires changing SUBSTRATE choice (e.g., swap Crossplane for ACK)
- The same fix-shape has been applied 3+ times in different places (indicates layer-violation: cross-cutting concern duplicated; needs factory-level refactor)
- Multiple incidents in a short window cluster in one layer — symptom of a structural gap (signal: today's Crossplane shell-script incidents clustered in 2 files, suggesting the shell-script-in-Job pattern is itself a layer-violation)

### 8.4 Cohesion-sniff heuristics for the operator

Capture these so the operator can flag factory-level smells (without acting on them):

| Smell | What to surface |
|---|---|
| "Same flow expressed at multiple layers" | E.g. validation at capability-mcp + workflow + CD + (future) govern. Each layer revalidates. Surface as "validation logic duplicated 3× — single-source-of-truth refactor candidate". |
| "Cross-cutting concern repeated per line" | E.g. notify-failure when-clause needed updating in 4 spots after Stage 2. Surface as "notification logic shouldn't be per-line; promote to substrate". |
| "6+ layers of indirection for one operation" | Today's deploy path: capability-mcp → workflow → claim → composition → Object → Job → shell. Each adds error surface. Surface as "deep stack — consider flattening". |
| "Single CD does N concerns" | webservice CD = shape + bootstrap + language config. Surface as "CD concern-overloaded; split candidate". |
| "Implicit routing" | Today: which line does a /microservice request take? Implicit (always microservice line). Surface as "no explicit line-selector — multi-line factory blocker". |

The operator does NOT refactor for these. It only counts incidents and surfaces patterns for architect-v1 + human to consider.

### 8.5 Operator's mental model — updated

Add to the 4-layer (Schema / Catalog / Workflow / Runtime) from earlier sections:

The 4 FAILURE LAYERS (where root causes live) map onto the 4 ARCHITECTURAL LAYERS (factory structure):

```
Schema   layer (CUE constraints)        →  Boundary
Catalog  layer (MCP tools)              →  Boundary
Workflow layer (Argo/Crossplane)        →  Flow
Runtime  layer (pods/ksvcs/OAM)         →  Substrate
                                          + Flow (if cascading)
```

Manufacturer layer doesn't show up in failures today because there's only one manufacturer (MFG-TC). When MFG-AZ or MFG-AI lands, expect new failure classes there.

## 9. Abstractions vocabulary (2026-05-30 alignment with user)

The operator must speak this vocabulary precisely. Misnaming layers is the most common source of confusion.

### 9.1 The 4 nouns

| Term | What it is | Today's instance |
|---|---|---|
| **CAFE** | The framework spec — contracts, ports, algebra. The blueprint of any factory. | `cafe-spec/` repo |
| **CAM** | Per-manufacturer blueprint — what each production line must provide (M1-M5 + 4 adapter types + artifact format + target substrate). | `cafe-spec/manufacturers/<id>/manifest.yaml` |
| **Factory Floor** | The DEPLOYED instance — cluster + cross-mfg fabric adapters + manufacturer realisations + the cafe-spec repo as source of truth. | the AKS `internal-developer-platform` cluster + cafe-spec repo + the cross-mfg ksvcs (govern-opa, classify-router, observe-audit-sink, ui-cli, lifecycle-orchestrator, approve-pr) + MFG-TC's realisation |
| **Production line** ≡ **Manufacturer** | A complete realisation of CAM. Takes use-cases → produces deployed solutions. Per cafe-spec/ALGEBRA.md L29: `m` = "one production line". | MFG-TC (the only line today). Others spec'd but unrealised: MFG-AZ, MFG-AI, MFG-AW-TF, MFG-AW-CF, MFG-MB, MFG-WB, MFG-HY |

The most common confusion to avoid: a "second M5 template within MFG-TC" is NOT a second production line. It's a variation of MFG-TC's output. A second production line means a NEW manufacturer with its own M1-M5 + adapters + (possibly) target substrate.

### 9.2 Factory-level abstractions (always shared, never per-line)

12 abstractions any line interacts with:
1. **Use-case** (input schema)
2. **Lifecycle state machine** (states: received → classified → composed → governed → approved → executing → running → archived)
3. **Manufacturer registry** (list of available lines)
4. **Manufacturer dispatcher** (line router) ← **gap: doesn't exist today**
5. **Port contracts** (9 ports × wire protocol + schema)
6. **Governance scoreboard** (combine evidence → 7-domain score)
7. **Approval state machine** (multi-channel, multi-approver)
8. **Cross-mfg fabric services** (deployed cross-port adapters)
9. **Substrate primitives** (compute, network, storage, identity, observability)
10. **Conformance check** (line validator — is this manufacturer realisable?)
11. **Use-case event log + state store** (audit + history)
12. **Source of truth** (cafe-spec repo — the declarative blueprint)

### 9.3 Production-line-level abstractions (filled in per manufacturer)

14 abstractions each manufacturer provides:
1. **Manufacturer manifest** (identity, version, port adapters)
2. **M1 — Archetypes** (component categories this line composes)
3. **M2 — Decision tree** (use-case → archetype routing within this line)
4. **M3 — Invariants** (per-line policy rules; in addition to cross-mfg I-CROSS-*)
5. **M4 — Catalog** (the line's concrete inventory: CDs, Compositions, Helm charts, etc.)
6. **M5 — Templates** (composite patterns the line emits)
7. **Compose adapter** (line's "architect": use-case → artifact)
8. **Catalog adapter** (line's read-surface for its M4)
9. **Govern adapter ref** (applies cross-mfg + line-specific invariants via shared scoreboard)
10. **Execute adapter** (line's deploy mechanism — varies wildly per manufacturer)
11. **Artifact format** (what the line emits: OAM, Bicep, Terraform, ARM, etc.)
12. **Target substrate** (where the line's outputs run)
13. **Adapter health + version**
14. **Conformance tests** (proves the line satisfies port contracts + invariants)

### 9.4 Cross-cutting: where BOTH levels participate

For each of the 9 cross-mfg ports, both Factory and Line have a role. Naming this removes the most common source of "where does X belong" confusion:

| Port | Factory provides | Line provides |
|---|---|---|
| Intake | use-case schema + canonical adapter | line-specific parser (if needed) |
| UI | grammar primitives + canonical adapter | line-specific question templates |
| Classify | classifier contract + dispatcher | line metadata for routing signals |
| Compose | artifact contract + retry semantics | the line's actual architect (M2 + LLM + prompts) |
| Catalog | query contract (`list/describe/search`) + dispatcher | the line's M4 catalog content |
| Govern | scoreboard logic + 7 domains + I-CROSS-* | line's I-MFG-* invariants + domain weights |
| Approve | state machine + channel registry | (nothing — lines defer entirely) |
| Execute | adapter registry + dispatcher | the line's deploy mechanism (whole workflow chain) |
| Observe | audit sink + event protocol | per-line emitter for lifecycle events |

**Empirical consequence:** Compose, Catalog, Govern, Execute are HEAVY at the LINE level. Intake, UI, Approve, Classify, Observe are HEAVY at the FACTORY level. This is why MFG-TC was buildable first — heavy-line ports concentrate the work, while heavy-factory ports could initially be served by one cross-mfg adapter each.

### 9.5 What this means for the operator's classification

Section 7.2's incident matrix gains a new column:
- **Layer (4-layer model — section 8.1):** Boundary / Flow / Manufacturer / Substrate (operator scope)
- **Abstraction-home (this section):** Factory-level / Line-level / Cross-cutting (operator awareness)

Most incidents the operator handles are LINE-LEVEL inside MFG-TC today. As MFG-AI / MFG-AZ land, the operator will need to know which manufacturer's adapter it's debugging.

## 10. What's missing / open items

Things today's incidents revealed that the operator would need but didn't get authored:

1. **Govern.evaluate as MCP tool** (still — separate track from this consolidation work)
2. **CD-side `// +usage=` annotations** on all 16 platform CDs (we discussed gradual rollout starting with webservice; only webservice partially done via Option C)
3. **Stage 4 refinements** for the oam-driven-contract path: multi-webservice OAMs, submit_wait poll consolidation, BYO-image edge cases
4. **Workflow.coverage tool** to flag notify-failure gaps automatically
5. **diagnose.recreation_loop tool** to trace controller chains
6. **diagnose.cpu_pressure tool** to aggregate reservations vs usage
7. **gh.pr.ci_doctor skill** wrapping P2 as an autonomous loop
8. **Operator deployment harness** — these processes and prompts live in docs only; operator agent (Foundry agent registration + MCP tool wiring + system prompt deployment) is still un-built

Build-out order suggested in [tools-needed.md](2026-05-30-tools-needed.md) Section "What I'd consider building first".
