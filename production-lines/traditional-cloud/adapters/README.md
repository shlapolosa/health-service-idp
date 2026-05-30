# MFG-TC Adapters

MFG-TC's per-line adapter set. Each subdir implements one **port** (a factory-wide contract) for the Traditional Cloud assembly line. Ports are defined cross-manufacturer; adapters here are how MFG-TC binds to them.

| Subdir | Port | Adapter implementation |
|---|---|---|
| `compose/` | **Compose** | `architect-v1` Foundry agent — reads use-case brief, writes OAM Application YAML. Contains system prompt, manifest, versioned baselines. |
| `compose-mcp/` | **Catalog** (per-line) | `capability-mcp-mfg-tc` Knative service — exposes this line's catalog over MCP so the architect agent can query what's available. |
| `catalog/` | **Catalog data layer** | The actual parts inventory: `ComponentDefinition`, `TraitDefinition`, `PolicyDefinition`, `WorkloadDefinition` YAMLs + supporting CRDs/RBAC. |
| `composition/` | **Execute — provisioning** | Crossplane `Composition` that turns an OAM-derived XR (e.g. `ApplicationClaim`) into actual Kubernetes resources. |
| `execute/` | **Execute — orchestration** | Argo `WorkflowTemplate`s that drive end-to-end build/deploy of an application. |

## Why ports-and-adapters?

The factory layer (`/factory/`) defines port contracts once. Each manufacturer (TC, on-prem, edge, mobile, ...) supplies its own adapter set under `production-lines/<name>/adapters/`. The lifecycle orchestrator never needs to know which manufacturer handled a request — it only speaks to ports.
