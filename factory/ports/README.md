# factory/ports/

This directory is intentionally light. The **canonical CAFE port contracts**
live in the sibling spec repo, not here:

- `/Users/socrateshlapolosa/Development/cafe-spec/ports/` — per-port
  contract docs (each port = one subdir)
- `/Users/socrateshlapolosa/Development/cafe-spec/cafe-spec/` — the shared
  cross-cutting specs (`m1-archetypes.json`, `m2-decision-tree.yaml`,
  `m3-invariants/`, `m4-capability-schema.json`, `domain-definitions.json`)
- `/Users/socrateshlapolosa/Development/cafe-spec/manufacturers/` — per-mfg
  manifests and ports (see its
  [`README.md`](../../../cafe-spec/manufacturers/README.md) for the
  cross-mfg vs per-mfg cut)

Anything in this directory must be **either**:

1. A pointer doc linking back to the sibling spec, **or**
2. A factory-specific refinement of a port (e.g. an additional invariant
   imposed only by this particular factory deployment).

## The 9 CAFE ports

Authoritative classification per
[`cafe-spec/manufacturers/README.md`](../../../cafe-spec/manufacturers/README.md):

| Port | Scope | Adapter in this factory |
|---|---|---|
| **Intake** | cross-mfg | [`../adapters/intake-slack`](../adapters/intake-slack) |
| **UI** | cross-mfg | [`../adapters/mcp-web-gateway`](../adapters/mcp-web-gateway) (discovery surface) |
| **Classify** | cross-mfg | — (lives in architect-v1 flow) |
| **Approve** | cross-mfg | — (PR approval via GitHub; surfaced via write gateway) |
| **Govern** | cross-mfg | [`../adapters/operator`](../adapters/operator) + OPA reference adapter (sibling repo) |
| **Observe** | cross-mfg | [`../adapters/operator`](../adapters/operator) |
| **Compose** | **per-mfg** | lives under `factory/production-lines/<mfg>/` |
| **Catalog** | **per-mfg** | lives under `factory/production-lines/<mfg>/`; factory read/write tooling is in [`../adapters/mcp-read-gateway`](../adapters/mcp-read-gateway) and [`../adapters/mcp-write-gateway`](../adapters/mcp-write-gateway) |
| **Execute** | **per-mfg** | lives under `factory/production-lines/<mfg>/`; factory PR-path entry is in [`../adapters/mcp-write-gateway`](../adapters/mcp-write-gateway) |

Six cross-mfg ports are configured at the **deployment** level (this repo).
Three per-mfg ports are declared in each manufacturer's `manifest.yaml`.
