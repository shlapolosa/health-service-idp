# operator-v1 — Signals Catalog

The operator-v1 agent's primary goal: **every compliant request succeeds its run.**

A "signal" is a concrete, observable failure pattern with: (a) where it surfaces, (b) what it looks like, (c) what fix-shape resolves it (definition-only — no feature work), (d) blast radius.

Signals are authored *before* tools are selected. Each signal implies one or more required tools; the union forms the operator's tool surface.

## Signal taxonomy

| Class | Source layer | Fix venue |
|---|---|---|
| **S-WF-*** | Argo Workflows step failure | gitops repo OR composition |
| **S-CP-*** | Crossplane managed-resource Ready=False / BackoffLimit | composition OR XRD |
| **S-CD-*** | OAM ComponentDefinition CUE error / parse failure | crossplane/oam |
| **S-OAM-*** | OAM Application sync error (workflowFailed / DNS-63) | gitops oam/applications |
| **S-RBAC-*** | RBAC denied / SA missing | crossplane/rbac OR provider SA binding |
| **S-K8S-*** | Knative service Ready=False after correct manifest | image, ingress, probes |
| **S-CFG-*** | Wrong env / secret / param | gitops or composition |

## Index

The **Consumer Impact** column is the gate the operator must check before raising a PR. A failure with no consumer impact is dead-code noise — don't burn cycles fixing it unless a real consumer is added.

| ID | Source | Consumer Impact | One-line | File |
|---|---|---|---|---|
| S-CP-001 | Crossplane Object Job | **HIGH** — blocks AppContainerClaim Ready=True; wait-for-microservice-ready times out | gitops/source-setup git commit not idempotent on retry → BackoffLimitExceeded | [s-cp-001-gitops-setup-not-idempotent.md](s-cp-001-gitops-setup-not-idempotent.md) |
| S-CP-002 | Crossplane Object Job | **NONE** — PERSONAL_ACCESS_TOKEN secret not referenced by any generated workflow (verified: `deployment-update.yml`, `oam-sync-trigger.yml` only use `secrets.GITHUB_TOKEN`). Job exits non-zero but consumers are healthy. | gitops-setup image (alpine/git) missing curl/jq → secret-setup step exits 127 | [s-cp-002-gitops-setup-missing-curl.md](s-cp-002-gitops-setup-missing-curl.md) |
| S-CP-005 | Crossplane Object Job | **HIGH** — gitops-setup unconditionally overwrites `oam/applications/application.yaml` on retry, clobbering oam-updater's correct OAM with a stale blank template that hardcodes `clusters: ["$APP_NAME"]`. OAM Application then targets a non-existent vCluster → `deploy-deploy-to-vcluster` fails → no ksvc ever appears. | gitops-setup blank template clobbers oam-updater's commits | [s-cp-005-gitops-setup-clobbers-oam-updater.md](s-cp-005-gitops-setup-clobbers-oam-updater.md) |
| S-CP-004 | Crossplane Object Job | **LOW** — leaves a permanently-Failed Job per request (operator noise). PERSONAL_ACCESS_TOKEN secret it tries to install is unused by any generated workflow. | pip3 install pynacl fails on Alpine 3.19+ with PEP 668 externally-managed-environment | [s-cp-004-pip-pep668-externally-managed.md](s-cp-004-pip-pep668-externally-managed.md) |
| S-CP-006 | Crossplane Object Job | **MEDIUM** — every request leaves a permanently-OutOfSync ArgoCD app. Pollutes ArgoCD UI; operators can't tell real drift from this known bug. | `apps/app-of-apps.yaml` `destination.namespace: $APP_NAME` should be `argocd` (it manages Application resources, which live in argocd ns) | [s-cp-006-app-of-apps-wrong-destination-namespace.md](s-cp-006-app-of-apps-wrong-destination-namespace.md) |
| S-CP-007 | Crossplane Object | **LOW** — register-argocd Object stuck in CannotUpdateExternalResource reconcile loop forever for host deployments. Job appears "Running" with no active pod. | Job.spec.template is immutable; Crossplane keeps trying to patch it when Job status is incomplete (early-exit pod GC'd before status set) | [s-cp-007-register-argocd-immutable-job-loop.md](s-cp-007-register-argocd-immutable-job-loop.md) |
| S-WF-001 | Argo `wait-for-microservice-ready` | timeout has no awareness of Crossplane Object retry cycle | [s-wf-001-wait-for-msvc-timeout-no-retry-awareness.md](s-wf-001-wait-for-msvc-timeout-no-retry-awareness.md) |
| S-OAM-001 | KubeVela | component name + CD suffix exceeds 63-char DNS label | [s-oam-001-dns-label-63.md](s-oam-001-dns-label-63.md) |
| S-OAM-002 | KubeVela `workflowFailed` | won't re-render until `app.oam.dev/publishVersion` bumps | [s-oam-002-publishversion-stuck.md](s-oam-002-publishversion-stuck.md) |
| S-CD-001 | webservice CD | `language:` not set → no microservice-standard-contract scaffold → image is placeholder → CrashLoop | [s-cd-001-webservice-no-language-no-scaffold.md](s-cd-001-webservice-no-language-no-scaffold.md) |
| S-CD-002 | webservice CD | `framework:` value not in allow-list (`fastapi\|springboot\|gin\|express\|axum\|auto\|chatbot\|graphql-gateway`) → validate-parameters fails | [s-cd-002-framework-not-in-allowlist.md](s-cd-002-framework-not-in-allowlist.md) |
| S-CD-003 | postgresql CD | CUE template uses `context.appRev` not `context.name` → render error (RESOLVED 2026-05-28 per memory) | [s-cd-003-postgresql-cue-context.md](s-cd-003-postgresql-cue-context.md) |
| S-RBAC-001 | crossplane helm provider | two provider-helm SAs exist; RBAC bound to wrong one | [s-rbac-001-helm-provider-sa.md](s-rbac-001-helm-provider-sa.md) |
| S-CFG-001 | kustomize image transformer | `kustomization.yaml` overrides `image:` in ksvc.yaml | [s-cfg-001-kustomize-image-override.md](s-cfg-001-kustomize-image-override.md) |

## Scope guardrails

The operator can fix any **definition** issue (CD CUE, composition Job script, RBAC binding, kustomize transformer) by raising a PR. It **cannot**:
- Extend a feature (e.g. add a new CD parameter)
- Create new ComponentDefinitions / WorkloadDefinitions / TraitDefinitions
- Change OAM Application *semantics* in a way that alters consumer intent

For anything beyond fix-shape, operator escalates to architect-v1.

## Session retros

The 2026-05-30 session produced 3 companion docs that together specify what operator-v1 needs to be (capabilities, reasoning, classification). Read in this order:

- **[2026-05-30 tools-needed](../2026-05-30-tools-needed.md)** — comprehensive tool inventory (6 sections A-F mapping each incident → tools required). What the operator can DO.
- **[2026-05-30 processes + prompts](../2026-05-30-processes-and-prompts.md)** — methodologies (M1-M6), iteration processes (P1-P6), system-prompt skeleton, diagnostic prompt templates (D1-D6), subagent-spawn template, empirical failure-modes catalog (F1-F20), AND **classification matrix** for 23 of today's incidents across 8 dimensions + decision rules for routing. What the operator REASONS like.
- This signals/README — per-signal entries (S-CP-001, S-CP-002, etc.). What the operator HAS SEEN.

## Implied tools (derived bottom-up)

| Tool | Required for |
|---|---|
| `k8s.get(resource, namespace)` | every signal |
| `k8s.logs(pod, container, tailLines)` | S-CP-*, S-K8S-*, S-WF-* |
| `k8s.events(involvedObject)` | S-CP-*, S-K8S-*, S-RBAC-* |
| `k8s.describe(resource)` | every signal |
| `argo.workflow.get(name)` + `argo.workflow.node(workflowName, nodeId)` | S-WF-* |
| `gh.pr.create(repo, branch, title, body, files)` | every fix delivery |
| `gh.repo.read(repo, path)` | look up composition files before patching |
| `git.diff(path)` | check fix correctness before opening PR |
| `cluster.context.switch(name)` | host vs vcluster |
| `kubeconfig.list_contexts()` | sanity |
| `crossplane.object.get(name)` | S-CP-* |
| `oam.app.status(name, namespace)` | S-OAM-* |

A NEW signal added here may add a tool; the operator agent's MCP wiring follows from this catalog.

## Build-out order

1. Author signals (this directory) — populate as failures are observed empirically.
2. Select tools from the implied set; build/extend `operator-mcp-server`.
3. Author operator-v1 system prompt: phases = OBSERVE → CLASSIFY (signal match) → DIAGNOSE → PROPOSE-FIX → DRY-RUN → OPEN-PR → MONITOR.
4. Foundry agent registration + APIM wiring (mirror architect-v1).
5. Continuous-mode loop (poll every N minutes, scoped to namespaces).
