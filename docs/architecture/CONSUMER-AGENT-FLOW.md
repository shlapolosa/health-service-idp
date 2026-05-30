# Consumer agent — how to use the catalog + factory MCPs

This document covers the **consumer side** of the producer-consumer model. The consumer is whoever owns an architecture intent and wants to deploy it: another Foundry agent, n8n workflow, CI pipeline, or a human at a terminal.

The **producer** is `architect-v1` (Foundry agent) — the consumer never talks to the producer directly. They communicate through the MCPs + git.

---

## Tool surface (what the consumer can call)

| MCP | Tool | Verb | What it does | Cost |
|---|---|---|---|---|
| catalog | `catalog.list` | read | List every published ComponentDefinition in the cluster | free |
| catalog | `catalog.describe(name)` | read | Get the parameter schema for a component (`vela show` live) | free |
| catalog | `catalog.search(category, qualityAttributes)` | read | Deterministic rank of KB candidates against a request profile | free |
| catalog | `catalog.scaffold(component, app_name, namespace)` | read | Generate a minimal valid OAM Application snippet | free |
| catalog | `catalog.validate(oam_yaml)` or `oam.dry_run(oam_yaml)` | read | `vela dry-run` over the OAM. Returns `{ok, diagnostics}` | free |
| catalog | `kb.read / kb.list / kb.diff` | read | Browse the platform's capability ledger (which techs are KB-only vs deployed) | free |
| catalog | `examples.patterns / examples.read` | read | Reference exemplar artifacts | free |
| catalog | **`app.submit(oam_yaml)`** | **write** | Validate + commit OAM to gitops + trigger the standard `oam-apply` workflow. Dry-run must pass | sync |
| catalog | **`app.submit_wait(oam_yaml)`** | **write** | Commit OAM + trigger the `oam-apply-wait` workflow which polls `vela dry-run` until prereqs land (≤ 72h), then deploys | async |
| factory | **`factory.propose(repo, title, body, files)`** | **write** | Open a PR. For consumers: file a `capability-factory/requests/REQ-NNN-<slug>.yaml` describing what they need | sync (returns PR URL) |
| factory | `factory.list_open_prs(repo, head_prefix)` | read | Inspect open architect-originated proposals | free |

Auth: the consumer holds an APIM subscription key and sends it as `Ocp-Apim-Subscription-Key` header. Same key works against all three MCPs (catalog, web, factory).

---

## The producer-consumer protocol

```
┌────────┐                ┌────────────┐                ┌────────────┐
│Consumer│                │MCPs / Argo │                │  GitHub +  │
│ agent  │                │  + Vela    │                │  ArgoCD    │
└────┬───┘                └─────┬──────┘                └─────┬──────┘
     │                          │                              │
     │ 1. compose OAM from intent                              │
     │                          │                              │
     │ 2. oam.dry_run(oam)                                     │
     ├─────────────────────────►│                              │
     │  ◄── {ok: true|false, diagnostics}                      │
     │                          │                              │
     │  IF ok=true:                                            │
     │ 3a. app.submit(oam) ────►│                              │
     │  ◄── {workflow_name}     │── oam-apply ────────────────►│
     │                          │   creates ArgoCD App         │
     │                          │   → ArgoCD syncs & deploys   │
     │                                                          │
     │  IF ok=false because "component X not found":           │
     │ 3b. catalog.search(qa)   ── look for near-fit existing  │
     │      → if found alternative: revise OAM, goto step 2    │
     │      → else: continue                                   │
     │                                                          │
     │ 3c. factory.propose(repo, title, body, files={          │
     │       "capability-factory/requests/REQ-NNN-X.yaml":     │
     │           "<CapabilityRequest YAML>"                    │
     │     })  ────────────────►│                              │
     │  ◄── {pr_url, branch}    │── PR opened, architect       │
     │                          │   eventually processes       │
     │                                                          │
     │ 3d. app.submit_wait(oam) ►│                             │
     │  ◄── {workflow_name}     │── oam-apply-wait ───────────►│
     │                          │   polls vela dry-run         │
     │                          │   then create ArgoCD App     │
     │                          │   when prereqs land          │
     └──────────────────────────┴──────────────────────────────┘
                       Consumer is NEVER blocked.
```

---

## Phased flow (the recipe)

### Phase 1 — Compose

Build an OAM Application YAML from the architecture intent. Use `catalog.list()` to discover available component types. Use `catalog.describe(name)` to get the parameter schema for any component you reference. Use `catalog.scaffold(component, app_name)` to get a starter snippet.

### Phase 2 — Verify

```yaml
oam.dry_run(oam_yaml: <your OAM>)
→ {ok: true | false, diagnostics: "..."}
```

If `ok=true`, skip to Phase 5. Submit your OAM.

If `ok=false`, read the diagnostics. Two common shapes:

| Diagnostic | What it means | Next phase |
|---|---|---|
| `ComponentDefinition "foo" not found` | Component you depend on isn't published | Phase 3 |
| `field "x" is required` / `value "y" is not valid` | Your OAM has structural issues | Fix your OAM, retry Phase 2 |

### Phase 3 — Diagnose (only if dry_run fails on missing component)

You have three options in priority order — **always try in this order, per the design principle of reuse → repurpose → create**:

**Option A: Find an existing alternative.**

```yaml
catalog.search(
  category: "<the category your missing tech serves>",
  qualityAttributes: {<the requirements you actually need>}
)
→ ranked list with score per candidate
```

Read the top 3 results' descriptions (via `catalog.describe`). If one is a near-fit (score ≤ 2.0, fails only on attributes that aren't actually hard requirements for you), revise your OAM to use it and return to Phase 2.

**Option B: File a capability request.**

If no existing component is acceptable, ask the producer (architect) to add what you need. **Do not block** — file the request as a PR via `factory.propose`:

```python
factory.propose(
  repo: "health-service-idp",
  title: "request: new capability for <tech> (REQ-NNN)",
  body: """
    Consumer agent: <my-name>
    Why I need this: <one paragraph>
    Why no existing capability works: <list what I considered + why each was rejected>
  """,
  files: {
    "capability-factory/requests/REQ-NNN-<slug>.yaml":
      "id: REQ-NNN\n" +
      "date: 2026-05-28\n" +
      "category: <enum>\n" +
      "qualityAttributes:\n" +
      "  durability: {level: strong, required: true}\n" +
      "  ...\n" +
      "needs_human_input: true\n" +
      "status: pending\n"
  }
)
→ {pr_url, branch}
```

Tell the user the PR URL. They (or the architect agent on its next run) will review.

**Option C: Submit anyway with `app.submit_wait`.**

Don't wait for Option B's PR to merge before queuing your OAM. Commit your intent now, let the deployment fire automatically when the new ComponentDefinition becomes available:

```yaml
app.submit_wait(oam_yaml: <your OAM>)
→ {ok: true, workflow_name: "oam-apply-wait-xyz",
   message: "queued; will poll vela dry-run until ready"}
```

This commits your OAM to gitops + starts a workflow that polls `vela dry-run` every 60 seconds for up to 72 hours. The instant the producer's PR is merged + ArgoCD applies the new CD, your workflow's next dry-run iteration succeeds and the standard deployment chain fires. **You are never blocked.**

### Phase 4 — (only if Option A in Phase 3 picked an alternative)

Revise your OAM to reference the existing alternative. Return to Phase 2. Submit via `app.submit`.

### Phase 5 — Submit

Choose based on Phase 3:

| Situation | Tool |
|---|---|
| Phase 2 dry-run passed | `app.submit(oam)` |
| Phase 2 dry-run failed because of missing CD AND you filed a `factory.propose` request | `app.submit_wait(oam)` — Option C |
| Phase 2 dry-run failed AND you picked a near-fit existing alternative in Option A | revise OAM, `app.submit(revised_oam)` |

### Phase 6 — Monitor

For `app.submit` — the workflow is usually done in 30-90 seconds. Check ArgoCD's Application object (named after your `app-name`).

For `app.submit_wait` — could be minutes to 72h. Currently no MCP tool wraps Argo Workflows status (`app.status` is on the backlog). Poll via:
- `kubectl -n argo get workflow <workflow_name>` (if you have cluster access)
- The committed file in gitops at `oam/applications/<app-name>.yaml`
- ArgoCD's Application object eventually appears with sync status

---

## Decision rules baked in

The consumer agent's system prompt should encode these as **hard rules**:

1. **Never call `app.submit` without first running `oam.dry_run`.** Even if you're confident. The MCP rejects with the same diagnostic anyway; the round trip is wasted.

2. **Always try Option A (existing alternative) before Option B (new request).** Run `catalog.search` with the QA you actually need, not the QA you assumed. Be willing to relax soft requirements.

3. **Never call `factory.propose` to push code-files into the implementation.** Consumers file `request` YAMLs only. Implementation files (`crossplane/oam/`, `capability-factory/kb/`, `docs/adr/`) are the producer's surface. Crossing the lane creates a review nightmare.

4. **If you call `app.submit_wait`, the deployment will eventually fire, OR the workflow will time out after 72h.** Don't poll more often than every 5 minutes; the workflow runs on a 60-second cycle internally.

5. **`factory.propose` requires explicit human confirmation in your conversation before invocation.** Same gate the producer has. Surface the proposed body + files to your user. Wait for "yes" before calling.

6. **Never edit committed OAM files in `oam/applications/` directly.** That bypasses the gitops gate. Always go through `app.submit` or `app.submit_wait`.

---

## Worked example

Consumer's intent: *"deploy a stateless web API on Knative, backed by a Postgres database with HA."*

```python
# 1. Compose
oam = """
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata: { name: my-api, namespace: default }
spec:
  components:
  - name: api
    type: webservice
    properties: { image: myregistry/myapi:v1, port: 8080 }
  - name: db
    type: postgres-ha       # ← speculative; let's see
    properties: { storage: 50Gi, replicas: 3 }
"""

# 2. Verify
r = oam.dry_run(oam_yaml=oam)
# → {ok: false, diagnostics: 'ComponentDefinition "postgres-ha" not found'}

# 3. Diagnose
search = catalog.search(
  category="datastore",
  qualityAttributes={
    "queryModel": "relational",
    "availabilityClass": {"level": "ha-multizone", "required": True},
    "durability": {"level": "strong", "required": True},
  }
)
# → [{technology: "postgres", score: 1.0, passed_hard: false,
#      detail: {availabilityClass: {offer: "replicated", penalty: 1.0}}}]

# Read the near-fit
postgres_kb = kb.read(tech="postgres")
# postgres exists but its KB profile says availabilityClass=replicated, not ha-multizone.

# Option A: is "replicated" close enough to "ha-multizone" for my actual need?
# → probably yes; revise OAM to use type: postgres instead.
revised_oam = oam.replace("postgres-ha", "postgres").replace("replicas: 3", "")

# 2 (again)
r = oam.dry_run(oam_yaml=revised_oam)
# → {ok: true}

# 5. Submit
app.submit(oam_yaml=revised_oam)
# → {ok: true, workflow_name: "oam-apply-abc", commit_sha: "..."}
```

If `postgres` had genuinely failed to meet a hard requirement, the consumer would:

```python
# Option B: file a request
factory.propose(
  repo="health-service-idp",
  title="request: postgres-ha capability for multi-zone deployments",
  body=("Consumer agent: my-api-deployer\n"
        "Why I need this: app SLA requires multi-zone failover, not just replication.\n"
        "Why no existing capability works: postgres KB profile shows availabilityClass=replicated, "
        "not ha-multizone. I considered relaxing my requirement but the SLA is contractual."),
  files={
    "capability-factory/requests/REQ-007-postgres-ha.yaml":
      "id: REQ-007\ndate: 2026-05-28\ncategory: datastore\n"
      "qualityAttributes:\n  availabilityClass: {level: ha-multizone, required: true}\n"
      "  queryModel: relational\n  durability: {level: strong, required: true}\n"
      "status: pending\n"
  }
)
# → {pr_url, branch}

# Option C: queue the deployment in parallel
app.submit_wait(oam_yaml=oam)   # original OAM with type: postgres-ha
# → {ok: true, workflow_name: "oam-apply-wait-xyz",
#    message: "queued; will poll vela dry-run until ready"}
```

The PR is now open for human review. The workflow is parked, polling. When the architect agent / human merges the producer's response PR (which adds `postgres-ha` ComponentDefinition), the workflow's next dry-run iteration passes and the OAM deploys. Consumer never blocked.

---

## What this document is NOT

- Not a system prompt — it's an architecture spec. The consumer agent's actual prompt would distil this into instructions + refusal rules.
- Not exhaustive on auth — consumer needs the APIM sub key (issued via Foundry Project Connection on the consumer's project, same pattern as `architect-v1`'s connection).
- Not the producer's prompt — see `agents/architect-v1/system-prompt.md` for that side.
