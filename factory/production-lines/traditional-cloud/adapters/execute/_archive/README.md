# Archived Execute adapters

WorkflowTemplates (and other retired substrate artifacts) that have been removed
from the active substrate. They are kept here (not deleted) for audit / rollback
reference only. **They are not applied to any cluster** and nothing in the
codebase fires them.

## realtime-xrds.yaml (archived 2026-06-07)

- **Archived:** 2026-06-07 (workstream XP-MODERN, #158/#156). Duplicate / stale
  XRD bundle for the realtime platform.
- **Why:** it redefined the SAME XRD as the canonical, RT-1-extended
  `factory/substrate/crossplane/realtime-platform-claim-xrd.yaml`
  (`xrealtimeplatformclaims.platform.example.org`, kind `XRealtimePlatformClaim`),
  but with a DIVERGENT, stale schema — nested `kafkaConfig.topics` (array of
  strings), `mqttConfig`, `snowflakeConfig`, and NO `appContainer` and NO flat
  `spec.topics[]` (name/partitions/retention). The active
  `realtime-platform-claim-composition.yaml` reads `spec.name` and (post-RT-1)
  `spec.topics[]`, i.e. it is wired to the CANONICAL XRD, not this one. Two XRDs
  with the same `metadata.name` are a last-apply-wins collision; the canonical
  file is the live/conceptual shape, so this duplicate is the one to retire.
- **Also bundled (and equally dead):** three XRDs with NO Composition and NO
  reference anywhere in the repo — `XIoTBrokerClaim`, `XStreamProcessorClaim`,
  `XAnalyticsDashboardClaim`. Archived with the file rather than split out.
- **Replaced by:** `factory/substrate/crossplane/realtime-platform-claim-xrd.yaml`
  (canonical, RT-1 `spec.topics[]`), consumed by the XP-MODERN pipeline-mode
  `realtime-platform-claim-composition.yaml`.
- **To resurrect:** `git mv` it back to
  `factory/substrate/crossplane/realtime-xrds.yaml` — but first reconcile its
  schema against the canonical XRD to avoid the duplicate-name collision, and add
  Compositions for the three orphan XRD kinds if you actually want them.

---


## oam-driven-contract.yaml

- **Retired:** 2026-06-06 for the webservice / `app.submit` / Slack `/microservice`
  paths (workstream RETIRE-WFT, #149, declarative-spine migration). Briefly
  archived then un-archived in #149 because four ComponentDefinitions still
  rendered Argo Workflows referencing it by name at OAM-reconcile time.
- **Fully archived:** 2026-06-07 (workstream RETIRE-WFT-2, #152). The last four
  CD dependencies were migrated off the WFT, so nothing fires this template any
  longer.
- **Replaced by:** the AppContainerClaim path. Two flavours:
  - `app.submit` → `K8sClaimClient.create_app_container_claim` → AppContainerClaim
    composition (owns repo creation, OAM seeding, ArgoCD Application). See
    `factory/shared-libs/capability-mcp-core/src/application/submit_use_case.py`
    (`_declarative_scaffold`).
  - ComponentDefinition CUE templates now emit an `AppContainerClaim`
    (`scaffold-claim` output) directly instead of a curl-Job that POSTed an Argo
    Workflow. This is the same declarative pattern as the (now-deprecated)
    `auto-scaffold-bootstrap` trait and the webservice CD.
- **CDs migrated in #152 (RETIRE-WFT-2):**
  - `rasa-chatbot.cd.yaml` — emits AppContainerClaim language `rasa`,
    framework `chatbot`.
  - `graphql-gateway.cd.yaml` — emits AppContainerClaim language `nodejs`,
    framework `graphql-gateway`.
  - `realtime-platform.cd.yaml` — emits AppContainerClaim (scaffolding only).
    Backing infra was already provisioned by the always-created
    `RealtimePlatformClaim` output, which is unchanged. Language mapped onto the
    ApplicationClaim XRD enum (`java`/`nodejs` passthrough, else default
    `python`; `go` has no template and falls to `python`).
  - `camunda-orchestrator.cd.yaml` — emits AppContainerClaim (scaffolding only).
    Backing infra (Zeebe/event-streaming/saga) was already provisioned by the
    always-created `OrchestrationPlatformClaim` output and the UI stack by Knative
    outputs; both unchanged. Language mapped onto the XRD enum as for realtime.
- **Why now:** the claim path was proven end-to-end by the zero-touch
  `patient3`/`patient4`/`patient5` E2Es (2026-06-07) on top of the original
  `patient2-api` spine E2E (2026-06-06). With both day-0 scaffolds and the
  per-service repo update path exercised, the legacy 9-step imperative
  WorkflowTemplate is no longer reachable.
- **History:** this template was a fork of `microservice-standard-contract`
  (annotation `fork-of: microservice-standard-contract`). W7 had already demoted
  it by stripping its Tier-3 enum-validation bash. RETIRE-WFT (#149) retired the
  submit/Slack paths; RETIRE-WFT-2 (#152) retired the last CD dependencies.

To resurrect: `git mv` the file back to `../oam-driven-contract.yaml`, re-add the
`oam-driven-contract` ArgoCD/substrate include, reinstate the WFT routing in
`submit_use_case.py` / intake-slack `argo_client.py`, and revert the four CD
`scaffold-claim` outputs back to their `workflow-trigger` curl-Jobs.

## CORRECTION (post-merge review, 2026-06-07)

"No live dependencies" above is NOT fully accurate: `pattern2-compositional-workflow`
(this same execute/ dir, wired into intake-slack's /oam/webhook path via
Pattern2CompositionalHandler) still carries a live `workflowTemplateRef:
oam-driven-contract` at its step level, and BOTH WorkflowTemplates remain live
on the cluster. This git archival is therefore record-keeping only — do NOT
delete the on-cluster oam-driven-contract WorkflowTemplate until pattern2 is
migrated or retired (tracked as RETIRE-WFT-3).

### RESOLVED by RETIRE-WFT-3 (#154, 2026-06-13)

`pattern2-compositional-workflow` was the LAST live referencer of
`oam-driven-contract` (its `route-component-handler` template carried
`templateRef: oam-driven-contract` at the `create-appcontainer` step). It is now
retired, which finishes the declarative-spine migration. Both WorkflowTemplate
objects were deleted from the cluster (`kubectl delete workflowtemplate -n argo
oam-driven-contract pattern2-compositional-workflow`).

Proof nothing referenced them at retire time (empirical, 2026-06-13):
- **No Argo Workflow run** referenced either WFT (`kubectl get workflows -n argo`
  templateRef scan → none).
- **No sensor / eventsource** referenced either. The live OAM-intake sensor
  `oam-to-slack-api` (argo-events) POSTs to `slack-api-server/oam/webhook`; that
  path runs `PatternOrchestrator → Pattern2CompositionalHandler`, but RETIRE-WFT-2
  (#152) had already migrated all four compositional CDs (rasa-chatbot,
  graphql-gateway, realtime-platform, camunda-orchestrator) to emit
  `AppContainerClaim` directly at OAM-reconcile time, so the webhook no longer
  reaches the WFT-submitting branch.
- **No other WorkflowTemplate** referenced `pattern2-compositional-workflow`
  (only `pattern2` referenced `oam-driven-contract`, and `oam-driven-contract`
  referenced only itself).
- **No non-archived YAML / CD / substrate include** referenced either WFT.

Dead config removed in the same commit: the `pattern2-compositional-workflow`
literals in `intake-slack/src/domain/strategies/pattern2_compositional.py`
(`COMPOSITIONAL_TYPES[*].workflow` for rasa-chatbot/graphql-gateway and the
`get_workflow_name` fallback) were repointed to the claim-based path they actually
take (`handle_via_application_claim` already used `oam-driven-contract`→now the
AppContainerClaim path is the real route; the WFT-submitting `super().handle()`
branch is dead). The handler, orchestrator, and `/oam/webhook` route are
otherwise unchanged and still serve the claims path.

## pattern2-compositional-workflow.yaml (archived 2026-06-13)

- **Archived + on-cluster WFT deleted:** 2026-06-13 (workstream RETIRE-WFT-3,
  #154). See "RESOLVED by RETIRE-WFT-3" above for the full proof-of-no-dependency.
- **What it was:** a 9-template Argo WorkflowTemplate that orchestrated multi-service
  compositional OAM components (rasa-chatbot, graphql-gateway, graphql-platform,
  identity-service) by routing to sub-workflows. Its `create-appcontainer` step
  `templateRef`'d `oam-driven-contract`, making it the last live referencer of that
  legacy WFT.
- **Replaced by:** the declarative AppContainerClaim path (RETIRE-WFT-2 #152). The
  compositional CDs emit `AppContainerClaim` directly at OAM-reconcile; the
  intake-slack `Pattern2CompositionalHandler.handle_via_application_claim` routes
  source-code components through the claim path, not this WFT.
- **To resurrect:** `git mv` both this file and `oam-driven-contract.yaml` back to
  `../`, re-add their substrate/ArgoCD includes, and revert the four CD
  `scaffold-claim` outputs to `workflow-trigger` curl-Jobs (per the
  oam-driven-contract resurrect note above).

## oam-webhook-registration.yaml (archived 2026-06-07)

Legacy pre-spine admission machinery: a MutatingWebhookConfiguration
(oam-microservice-creator) pointing at a plain-Deployment slack-api-server.
Superseded by the declarative spine (app.submit + claims) and the Knative
slack-api-server. It sat unnoticed in factory/substrate/argo-events/ until
the platform-definitions GitOps app synced it and resurrected the legacy
Deployment, which then fought Knative for Service ownership. Belongs to the
RETIRE-WFT-3 (#154) cleanup scope.
