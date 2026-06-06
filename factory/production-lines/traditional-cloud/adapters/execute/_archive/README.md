# Archived Execute adapters

WorkflowTemplates that have been retired from the active substrate. They are kept
here (not deleted) for audit / rollback reference only. **They are not applied to
any cluster** and nothing in the codebase fires them.

## oam-driven-contract.yaml

- **Retired:** 2026-06-06 (workstream RETIRE-WFT, #149, declarative-spine migration)
- **Replaced by:** the AppContainerClaim path (`app.submit` →
  `K8sClaimClient.create_app_container_claim` → AppContainerClaim composition,
  which owns repo creation, OAM seeding and the ArgoCD Application). See
  `factory/shared-libs/capability-mcp-core/src/application/submit_use_case.py`
  (`_declarative_scaffold`).
- **Why now:** the declarative spine was proven end-to-end against the
  `patient2-api` service (spine E2E patient2-api, 2026-06-06). With the claim
  path delivering day-0 scaffolds AND the per-service repo update path both
  exercised, the legacy 9-step imperative WorkflowTemplate (and its
  `SUBMIT_USE_WFT` env escape hatch in `submit_use_case.py`, plus the legacy
  direct-WFT-fire fallback in intake-slack `argo_client.py`) were removed.
- **History:** this template was a fork of `microservice-standard-contract`
  (annotation `fork-of: microservice-standard-contract`). W7 had already demoted
  it by stripping its Tier-3 enum-validation bash. RETIRE-WFT completes the
  retirement.

To resurrect: `git mv` the file back to `../oam-driven-contract.yaml`, re-add the
`oam-driven-contract` ArgoCD/substrate include, and reinstate the WFT routing in
`submit_use_case.py` / intake-slack `argo_client.py`.
