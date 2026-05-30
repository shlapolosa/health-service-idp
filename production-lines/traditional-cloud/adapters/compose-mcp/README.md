# compose-mcp (MFG-TC)

The **Compose adapter** for the Traditional Cloud production line —
exposes MFG-TC's line-scoped MCP tool surface used by architect-v1
and other Foundry consumers.

Path: `production-lines/traditional-cloud/adapters/compose-mcp/`
Image name (preserved for APIM routes): `capability-mcp-mfg-tc`

## Role within MFG-TC's adapter set

MFG-TC's adapters (siblings under `production-lines/traditional-cloud/adapters/`):

| Adapter | Role |
|---|---|
| `catalog/` | OAM ComponentDefinitions + TraitDefinitions + PolicyDefinitions (M4 catalog data) |
| `composition/` | Crossplane composition (ApplicationClaim → infra) |
| `compose-mcp/` | **this service** — MCP tool surface that exposes catalog/composition for compose-time use |

This adapter is the read+gated-action interface to MFG-TC for any
consumer that speaks MCP (architect-v1, factory router, lifecycle bots).
Factory-level tools (`oam.dry_run`, `examples.*`, `kb.*`, `factory.route`,
`factory.list_manufacturers`) live in the factory MCP, not here, per
the factory/production-line abstraction in `docs/architecture/MANUFACTURER.md`.

## Tools surface

| Tool | Purpose |
|---|---|
| `catalog.list` | List MFG-TC ComponentDefinitions |
| `catalog.describe` | Describe a CD + parameters + applicable traits |
| `catalog.search` | Rank CDs by use-case relevance |
| `catalog.scaffold` | Generate OAM skeleton |
| `catalog.validate` | Validate OAM via vela dry-run |
| `catalog.traits` / `describe_trait` / `traits_for` | MFG-TC TraitDefinitions |
| `catalog.policies` / `describe_policy` | MFG-TC PolicyDefinitions |
| `catalog.workflow_steps` / `describe_workflow_step` | MFG-TC WorkflowStepDefinitions |
| `catalog.connectivity_recipes` | Cross-component composition recipes |
| `app.submit` | Provision OAM via gitops + oam-driven-contract |
| `app.submit_wait` | Deferred provision via oam-apply-wait |

## Adding new capabilities (definition-only)

A new MFG-TC capability = a new ComponentDefinition under
`production-lines/traditional-cloud/adapters/catalog/`. This service's
`catalog.list` auto-discovers the CD via the k8s API — no code change here.

Full procedure: see `cafe-spec/manufacturers/traditional-cloud/EXTENDING.md`.

## Implementation note

Imports use cases from `shared-libs/capability-mcp-core/` (baked in
as `capability_mcp_core` at image build time). The shared core is the
same library used by every per-line compose-mcp adapter, ensuring
identical use-case behaviour across manufacturers.

## Deployment

Build context is always the repo root.

```bash
docker build -f production-lines/traditional-cloud/adapters/compose-mcp/Dockerfile \
  -t healthidpuaeacr.azurecr.io/capability-mcp-mfg-tc:v0.2 .
az acr login --name healthidpuaeacr
docker push healthidpuaeacr.azurecr.io/capability-mcp-mfg-tc:v0.2
kubectl apply -f production-lines/traditional-cloud/adapters/compose-mcp/knative-service.yaml
```

The image name `capability-mcp-mfg-tc` is intentionally preserved to
keep existing APIM routes and Knative Service identity unchanged across
the path refactor.
