# Archived Execute adapters

WorkflowTemplates that have been retired from the active substrate. They are kept
here (not deleted) for audit / rollback reference only. **They are not applied to
any cluster** and nothing in the codebase fires them.

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
