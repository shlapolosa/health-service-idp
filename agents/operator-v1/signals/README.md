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

| ID | Source | One-line | File |
|---|---|---|---|
| S-CP-001 | Crossplane Object Job | gitops/source-setup git commit not idempotent on retry → BackoffLimitExceeded | [s-cp-001-gitops-setup-not-idempotent.md](s-cp-001-gitops-setup-not-idempotent.md) |
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
