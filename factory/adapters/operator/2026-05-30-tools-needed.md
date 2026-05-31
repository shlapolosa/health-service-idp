# Operator-v1 — Tools Needed (from 2026-05-30 session)

A retrospective of every change made today, mapped to the tools the operator-v1 agent would need to (a) detect, (b) diagnose, and (c) safely apply each fix without human help. This list extends the [signals catalog README](signals/README.md)'s "Implied tools" section.

The format per change: **What I did** → **How operator would detect it** → **Tools required**.

---

## A. Wearables / `/microservice user-service` failure (early session)

### A.1 — gitops-setup / source-setup Jobs not idempotent (S-CP-001, PR #9)

- **Detect:** Workflow `microservice-creation-*` Failed at `wait-for-microservice-ready` (600s timeout) AND child Jobs show `BackoffLimitExceeded` AND AppContainerClaim Ready=False despite first-pod Complete.
- **Diagnose:** Need to inspect (1) Job spec to read the shell script, (2) gitops repo commits to see whether prior commits exist (which would make next-run's `git commit` fail under `set -e`).
- **Fix:** Wrap commits with `git diff --cached --quiet || git commit`; wrap push with `|| true`.

**Tools needed:**
- `argo.workflow.get(name)` — read failure step
- `k8s.describe(job, ns)` — read script via job spec
- `k8s.events(involvedObject)` — see BackoffLimitExceeded events
- `gh.repo.commits(repo, limit)` — confirm prior content exists
- `crossplane.composition.get(name)` — find the script source to fix
- `gh.pr.create(repo, branch, title, body, files)` — propose the fix

### A.2 — wait-for-microservice-ready opacity (S-WF-001)

- **Detect:** Timeout step exits 1 with only progress logs (`Checking ApplicationClaim status... (600s/600s)`) and no diagnostic.
- **Diagnose:** Need the actual `.status.conditions` on the ApplicationClaim + the failed-Job state.

**Tools needed:**
- `argo.workflow.logs(name, step?)` — see step output
- `k8s.get(applicationclaim, name, ns)` + access to `.status.conditions[].message`
- `k8s.list(job, ns, label_selector="app=<name>")` — find related Jobs

### A.3 — gitops-setup HEREDOC + curl + PEP 668 (S-CP-002, S-CP-004; PR #10)

- **Detect:** Pod logs show `curl: not found` or `error: externally-managed-environment`.
- **Diagnose:** Image `alpine/git:2.43.0` lacks curl/jq; Alpine 3.19+ enforces PEP 668.

**Tools needed:**
- `k8s.logs(pod, container, tailLines)` — read pod stderr
- `k8s.exec(pod, container, cmd)` — empirically test `vela`/`curl` availability in-pod (LIVE smoke per `feedback-local-smoke-before-containerise`)

### A.4 — gitops-setup clobbers oam-updater (S-CP-005, PR #11)

- **Detect:** OAM Application in gitops repo has stale `clusters: ["$APP_NAME"]` topology policy even though `targetVCluster=host`.
- **Diagnose:** Crossplane Object retried gitops-setup; second run overwrote oam-updater's correct OAM with the blank template.

**Tools needed:**
- `gh.repo.commit_history(repo, path, limit)` — see timestamps of conflicting writes
- `k8s.events(involvedObject)` — see Crossplane retry events

---

## B. need-a-service-093653 (catalog-quality + workflow bugs)

### B.1 — Catalog returns empty parameter schemas (PR #13, webservice CD constraint)

- **Detect:** `catalog.describe(webservice)` returns `parameters: []` even though CUE template has 29 parameters.
- **Diagnose:** vela_client used `--format markdown` flag which emits a different table format than the row regex matches.

**Tools needed:**
- `k8s.exec(pod, cmd)` — run `vela show <c>` and `vela show <c> --format markdown` to compare formats
- `mcp.tool.test(server, tool, args)` — invoke catalog.describe directly to see what it returns
- File-side: `repo.read(path)` to inspect vela_client.py + the regex assumption

### B.2 — Webservice CD allows `nginx:1.27` placeholder + no `language:` (PR #13, Option C)

- **Detect:** OAM with `image: nginx:1.27` passes `vela dry-run`; ksvc CrashLoops.
- **Diagnose:** CD CUE has `image: string` (no regex constraint), `language?: string` (free-form, no enum).
- **Fix:** Add `image: *<default> | =~"^acr-pattern"` regex constraint + `language?: "python"|"java"|"nodejs"|"rasa"` enum + `framework: *"auto" | string` default.

**Tools needed:**
- `oam.dry_run(yaml)` — show what passes today
- `cue.lint(template)` — analyze parameter block for missing constraints
- `policy.check(image, allowed_registries)` — image-source policy
- After fix: `vela.dry_run` empirical test against deliberately-broken OAM to confirm rejection

### B.3 — `oam-apply` source.path was a file not directory (PR #14)

- **Detect:** ArgoCD app reports `ComparisonError: <path>.yaml: app path is not a directory`.
- **Diagnose:** Read `oam-apply.yaml`'s `create-argocd-application` template — it sets `source.path` from `gitops-path` parameter verbatim; capability-mcp passes the full file path.

**Tools needed:**
- `argocd.app.get(name)` — read `status.conditions[].message`
- `argo.template.get(name)` — read script body
- `argo.template.diff(name, repo_path)` — compare cluster cache vs file

### B.4 — argo-workflow-executor SA + ArgoCD application RBAC missing (PR #14)

- **Detect:** Workflow step Failed with `serviceaccount "argo-workflow-executor" not found` OR `applications.argoproj.io is forbidden`.
- **Diagnose:** RBAC inspection — SA exists? CRB grants the right verbs on argoproj.io/applications?

**Tools needed:**
- `k8s.get(sa, ns)` + `k8s.get(clusterrolebinding, name)` — RBAC inventory
- `rbac.check(subject, verb, resource)` — `can-i` style verification
- `rbac.apply_role(role, subject, verbs, resources)` — fix RBAC gaps

---

## C. Catalog MCP expansion (PR #13)

### C.1 — Discover gap: agent has 13 tools, sees only components, no traits/policies/recipes

- **Detect (operator-eligible meta-signal):** survey of MCP server tool surface vs metadata available on cluster shows missing tool coverage.
- **Fix:** Add 6 new MCP tools (`catalog.traits/describe_trait/traits_for/policies/workflow_steps/connectivity_recipes`) + 2 enrichments (`applicable_traits` in describe, `with_traits` in scaffold).

**Tools needed:**
- `mcp.server.tools_list(server)` — inventory existing
- `k8s.list(traitdefinition, all_namespaces)` — count what's NOT exposed
- `repo.write(file, content)` — implement the new tools
- `docker.build_push(dockerfile, tag)` — package
- `ksvc.update_image(name, image)` — deploy

### C.2 — vela does NOT support PolicyDefinition / WorkflowStepDefinition for `show`

- **Detect:** `vela show <policy>` errors with `could not find <name> in namespace`.
- **Fix:** Bypass vela; read CUE template from k8s API + parse with a lightweight `cue_param_parser.py`.

**Tools needed:**
- `k8s.exec(pod, "vela show <name>")` — empirical probe
- `cue.parse_parameter_block(template_string)` — local parser

---

## D. Cleanup of test artifacts (multiple cycles)

### D.1 — Recreation loop after deletion

- **Detect:** OAM Application gets re-created within 5min of `kubectl delete`.
- **Diagnose:**
  - ArgoCD has cached state from a now-deleted gitops repo (`syncStatus=Synced` to a commit, repo 404 now)
  - KubeVela renders the re-applied OAM → CD bootstrap output Job fires → workflow re-creates Claims + ArgoCD apps
  - argo-events sensor watches OAM Applications and fires sub-workflows
- **Fix:** ATOMIC delete — patch finalizers to null, delete ArgoCD apps + OAM + Claims + XR + ksvc + workflows in fast sequence so no time for re-application between steps.

**Tools needed:**
- `argocd.app.cache_state(name)` — show what ArgoCD has cached
- `argocd.app.disable_selfheal(name)` — strategic merge patch off syncPolicy
- `k8s.patch(kind, name, json_patch)` — null finalizers
- `k8s.delete(kind, name, --wait=false)` — fast delete
- `diagnose.recreation_loop(resource)` — meta-tool that maps which controllers are touching a resource (would explain "ArgoCD applied this, then KubeVela rendered, then CD bootstrap Job fired")
- `argo.workflow.terminate(name)` — kill in-flight workflows BEFORE deleting their artifacts

### D.2 — CPU saturation blocks new revisions

- **Detect:** Knative revisions stuck `Unschedulable: Insufficient cpu` while node CPU usage is 15-40% (i.e., requests > usage).
- **Diagnose:** Per-vCluster pods (activator + kourier + workload) reserve 1.1+ cores each; cumulative reservations > node capacity.

**Tools needed:**
- `k8s.node.allocations()` — `kubectl describe node` → "Allocated resources" table
- `k8s.top.pods(namespace?, sort_by="cpu_request")` — find biggest reservers
- `k8s.top.nodes()` — actual CPU usage vs reservations
- `diagnose.cpu_pressure()` — meta-tool aggregating the above + suggesting which workloads to scale down

### D.3 — GitHub repo deletion

- **Detect:** Test microservice's GitHub repos still exist after kubectl cleanup → gitops state continues to leak.
- **Fix:** DELETE via GitHub API with token that has `delete_repo` scope.

**Tools needed:**
- `gh.repo.delete(repo)` — **irreversible — needs guardrails / confirmation**
- `gh.token.scopes()` — verify the token has `delete_repo` before attempting

---

## E. Stage 1-7 consolidation (PRs #15, #16, #17, #18)

### E.1 — Fork microservice-standard-contract → oam-driven-contract (PR #15)

- **Detect (refactor-eligible):** Two workflow templates serve different consumer paths but their boilerplate is 95% identical. Consumer agent path (oam-apply) has different + broken behavior vs Slack path (microservice-standard-contract). Consolidate to one.
- **Tools needed:**
  - `repo.read(file)`, `repo.write(file)` — copy with metadata.name change
  - `k8s.apply(file)` — register the fork
  - `argo.workflow.run_template(template, params)` — empirically test the new fork

### E.2 — Adding `oam-application` parameter + apply-consumer-oam step

- **Detect:** Architect agent's `app.submit` needs to overlay consumer OAM on top of chain's boilerplate.
- **Tools needed:**
  - `argo.template.edit(template, new_step, position)` — insert step at right place
  - `argo.template.validate(template)` — argo's own dry-run

### E.3 — When-clause expression error (`Invalid 'when' expression 'YXBp...'`)

- **Detect:** Workflow Failed with the error string referencing the base64 OAM passed as a parameter.
- **Diagnose:** Argo `when:` clause uses govaluate; base64 strings aren't valid expressions. Need to no-op-conditional INSIDE the script not in the when-clause.

**Tools needed:**
- `argo.workflow.get(name)` — read the error
- `argo.expression.test(expr_template, sample_param)` — locally evaluate before deploying

### E.4 — Stage 6 cutover sed misses (pattern1_foundational.py L120/L167)

- **Detect:** Final audit grep reveals 3 file mentions of the legacy name not in `tests/`.
- **Diagnose:** Earlier sed used patterns specific to YAML/Python config patterns; missed inline default fallbacks like `config.get("workflow", "default")`.

**Tools needed:**
- `repo.grep(pattern, paths)` with classify (runtime code vs comment vs test) — would surface the 3 misses cleanly
- `code.ast_inspect(file, pattern)` — distinguish runtime from comment/string-literal occurrences

### E.5 — pattern2-compositional-workflow cluster cache stale

- **Detect:** File in repo has `oam-driven-contract` but cluster's WorkflowTemplate (cached) still references `microservice-standard-contract`.
- **Fix:** `kubectl apply -f <file>` to refresh.

**Tools needed:**
- `argo.template.diff(name, repo_file)` — surface cluster cache vs file drift

### E.6 — Notify-failure when-clause didn't cover apply-consumer-oam (today's last fix)

- **Detect:** Slack goes silent on failure of new step.
- **Diagnose:** Inspect notify-failure's `when:` expression; cross-reference workflow's step list to find new steps not in the expression.

**Tools needed:**
- `workflow.coverage(template)` — which steps' Failed state can fire which notify-*? Would flag the gap.

---

## F. CI maintenance (PRs #16 fix-chain)

### F.1 — spaCy 404 (URL with empty version)

- **Detect:** CI step `Install dependencies` failed with HTTP 404 on a malformed spacy-models URL.
- **Fix:** Pin model wheel URL directly.

**Tools needed:**
- `gh.pr.checks(repo, num)` — see failed step
- `gh.actions.log(job_id)` — read CI log
- `repo.write(file)` — fix the workflow yaml
- `git.push(branch)` — re-run CI

### F.2 — pytest-cov plugin missing

- **Detect:** CI step `Run unit tests` failed with `unrecognized arguments: --cov=src`.
- **Diagnose:** pytest.ini's `addopts` reference `--cov` flags from pytest-cov plugin not in requirements.txt.

**Tools needed:**
- `repo.read(pytest.ini)` + `repo.read(requirements.txt)` — cross-reference
- Same fix loop as F.1

### F.3 — 3-tier default change broke pre-existing tests

- **Detect:** Tests assert `auto_create_vcluster is True` / `get_vcluster_name() == "user-vcluster"` but the 3-tier change (in main, before this session) inverted defaults.
- **Fix:** Update test expectations.

**Tools needed:**
- `git.log -p <file>` — see when defaults flipped
- `repo.grep_with_context(pattern, paths)` — find test assertions matching old defaults

---

## Composite tool inventory (extends signals/README.md)

### Already in README ("Implied tools" section)
- `k8s.get`, `k8s.logs`, `k8s.events`, `k8s.describe`
- `argo.workflow.get`, `argo.workflow.node`
- `gh.pr.create`, `gh.repo.read`
- `git.diff`
- `cluster.context.switch`, `kubeconfig.list_contexts`
- `crossplane.object.get`
- `oam.app.status`

### NEW tools surfaced by today's session (priority-ordered)

| Category | Tool | Why needed |
|---|---|---|
| **Diagnostic meta-tools** | `diagnose.recreation_loop(resource)` | Maps which controllers touch a resource (ArgoCD/KubeVela/argo-events/CD-bootstrap) — would explain D.1 in seconds |
| | `diagnose.cpu_pressure()` | Aggregates node allocations + pod requests + suggests scale-down candidates (D.2) |
| | `workflow.coverage(template)` | Which steps' Failed state fires which notify-* (E.6) |
| **Argo** | `argo.workflow.logs(name, step?)` | Read step output (A.2, B.3) |
| | `argo.workflow.terminate(name)` | Kill in-flight workflows during cleanup (D.1) |
| | `argo.template.get(name)` | Inspect WorkflowTemplate spec (B.3, E.3) |
| | `argo.template.diff(name, repo_file)` | Cluster cache vs file drift (E.5) |
| | `argo.expression.test(expr, params)` | Evaluate when-clauses locally before deploy (E.3) |
| **ArgoCD** | `argocd.app.get(name)` | Sync status, source, conditions (B.3, D.1) |
| | `argocd.app.cache_state(name)` | What ArgoCD has cached from a now-404 repo (D.1) |
| | `argocd.app.disable_selfheal(name)` | Strategic merge patch off syncPolicy (D.1) |
| | `argocd.app.sync(name)` | Trigger sync (E.5 verification) |
| **Kubernetes** | `k8s.exec(pod, container, cmd)` | Empirical in-pod tests (A.3, C.2, B.1) — replaces "local-smoke-before-containerise" friction |
| | `k8s.node.allocations()` | Reservations vs available (D.2) |
| | `k8s.top.pods(sort_by="cpu_request")` | Find CPU hogs (D.2) |
| | `k8s.patch(kind, name, json_patch)` | Surgical edits incl. null finalizers (D.1) |
| **Crossplane** | `crossplane.object.list(filter)` | Bulk inventory (D.1) |
| | `crossplane.xr.list()` | XR composites (D.1) |
| | `crossplane.claim.list()` | All claims (D.1) |
| | `crossplane.composition.get(name)` | Read composition source for fix (A.1) |
| **OAM/KubeVela** | `vela.show(name)` + format-aware parser | Avoid format mismatch (B.1) |
| | `vela.dry_run(oam)` | Validate (already implicit; needs explicit operator tool) |
| | `cue.parse_parameter_block(template)` | For policies/workflow-steps (C.2) |
| | `cue.lint(template)` | Find missing `// +usage=` etc. (catalog quality audit) |
| | `oam.cd.simulate_render(name, props)` | Predict final k8s name + DNS-63 check |
| **GitHub** | `gh.repo.commits(repo, path, limit)` | Timeline of conflicting writes (A.4) |
| | `gh.repo.exists(repo)` | Pre-flight before clone (D.3) |
| | `gh.repo.delete(repo)` ⚠️ irreversible | Cleanup (D.3) — needs human-confirmation guardrail |
| | `gh.token.scopes()` | Verify capabilities before attempt (D.3) |
| | `gh.pr.checks(repo, num)` | CI status (F.1) |
| | `gh.pr.merge(repo, num, method)` | Once green |
| | `gh.actions.log(job_id)` | Read CI log line-by-line (F.1, F.2) |
| **Build/deploy** | `docker.build_push(dockerfile, tag, context)` | Image fixes (C.1, slack-api-server rebuild) |
| | `ksvc.update_image(svc, image)` | Knative-aware (not strategic-merge that breaks volumes) |
| | `ksvc.revision.list(svc)` | Debug rollouts (D.2) |
| | `ksvc.revision.bump(svc)` | Force new revision via template-annotation bump |
| **RBAC** | `rbac.check(subject, verb, resource, ns?)` | `kubectl auth can-i` style (B.4) |
| | `rbac.audit(serviceaccount)` | Find what bindings grant which verbs (B.4) |
| | `rbac.apply_role(role, subject, verbs, resources)` | Add missing perms (B.4) |
| **Policy** | `govern.evaluate(oam)` | Image-source / DNS-63 / language-required (B.2) — IS the cafe-spec govern adapter we already deployed |
| | `policy.image_source_check(image, allowed_prefixes)` | Standalone check (B.2) |
| **Code maintenance** | `repo.grep_classify(pattern, paths, classify_as=[runtime|comment|test|string])` | Audit before delete (E.4) |
| | `code.ast_inspect(file, pattern)` | Distinguish runtime vs comment (E.4) |
| | `git.log_at_path(path, pattern)` | When did X change? (F.3) |
| **Cleanup** | `cleanup.atomic_delete(resource_set)` | Sequence delete to break recreation loops (D.1) |
| | `cleanup.test_artifacts(name_pattern)` | Find all related resources (D.1) |
| | `cleanup.namespace_with_finalizers(ns)` ⚠️ destructive | Force-delete stuck namespaces |

---

## Open architectural questions the operator surfaces

Today's empirical patterns suggest the operator needs to know:

1. **Trust model:** which actions can it take unilaterally (read, edit, propose-PR) vs which need human consent (rebuild image, delete cluster resource, delete GitHub repo, push to main). Today's session shows the classifier already blocks the highest-risk ones (e.g. bulk namespace delete) — operator should expect similar gating.

2. **Recreation-loop detection** is a recurring theme. The operator needs a meta-tool that traces who-touches-what — otherwise it'll fight controllers in cleanup.

3. **CI fix loop is well-suited to autonomous operation:** fail → read log → propose fix → push → wait → repeat. Operator would benefit from a `gh.pr.ci_doctor(pr_num)` skill that runs that loop.

4. **Local-smoke-before-containerise** (memory `feedback-local-smoke-before-containerise`) is a constant tax. `k8s.exec(pod, cmd)` as a first-class operator tool would replace the build-cycle entirely for diagnostic work.

5. **Catalog-quality audit** (B.1, C.2) is operator-eligible work that compounds over time. As CDs are added, the operator should automatically catch ones with empty `parameters` schemas.

---

## What I'd consider building first

If the operator is to be built incrementally, my prioritization based on today's incident-density:

1. **`k8s.exec` + read-only Kubernetes (gets / logs / events / describe / list)** — covers 80% of diagnostics
2. **`argo.workflow.*` + `argocd.app.*` (read + diff + sync)** — covers all platform-workflow debugging
3. **`gh.pr.checks / gh.actions.log / gh.pr.merge`** — CI fix loop is a high-value autonomous skill
4. **`diagnose.recreation_loop` + `diagnose.cpu_pressure`** — the two meta-tools that would have saved the most time today
5. **`docker.build_push + ksvc.update_image + ksvc.revision.bump`** — closes the build→deploy→verify loop
6. **`gh.repo.delete + gh.token.scopes` + `cleanup.atomic_delete`** — guarded destructive actions
7. **`govern.evaluate + cue.lint + cue.parse_parameter_block`** — catalog-quality audit
8. **`workflow.coverage` + `repo.grep_classify`** — refactor-safety meta-tools

The first 3 categories would let the operator handle most "PR open + CI red" scenarios autonomously, which is the highest-ROI place to start.
