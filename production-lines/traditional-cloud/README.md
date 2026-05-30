# Manufacturer: Traditional Cloud (MFG-TC)

This directory is one **assembly line** in the platform's factory.

## Real-world analogy

Think of MFG-TC as a Traditional Cloud assembly line in a car factory:

1. A use-case arrives at the line (an OAM `Application` request).
2. **Design** (`adapters/compose/`) — the architect agent reads the customer brief and writes a blueprint (OAM YAML).
3. **Parts inventory** (`adapters/catalog/`) — the actual ComponentDefinitions, TraitDefinitions, and PolicyDefinitions on the shelf.
4. **Inventory desk** (`adapters/compose-mcp/`) — per-line MCP service that tells the architect what parts are on the shelf.
5. **Quality check + provisioning** (`adapters/composition/`) — Crossplane Composition turns the blueprint into real Kubernetes resources.
6. **Assembly** (`adapters/execute/`) — Argo WorkflowTemplates run the build steps end-to-end.
7. The finished product is a running OAM Application on the vCluster.

## Layout

| Path | Role |
|---|---|
| `adapters/` | MFG-TC's per-line port adapters — the concrete implementations that bind this line to the factory's port contracts |
| `core/` | Pointer to MFG-TC's defining recipe (lives in sibling `cafe-spec/manufacturers/traditional-cloud/`) — M1-M5 |
| `ports/` | MFG-TC's port refinements (M3 invariant overrides, domain weight tweaks) |
| `evals/` | Eval suite for the `architect-v1` compose agent |
| `examples/` | Sample OAM Applications consuming this line |

## Where the canonical spec lives

The defining manifest, archetypes (M1), decision tree (M2), invariants (M3), catalog schema (M4), and templates (M5) for MFG-TC live in the sibling `cafe-spec` repo:

```
/Users/socrateshlapolosa/Development/cafe-spec/manufacturers/traditional-cloud/
```

This repo holds the **runtime adapters** that implement that spec.
