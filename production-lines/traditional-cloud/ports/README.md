# MFG-TC Port Refinements

The factory's port contracts (Compose, Catalog, Govern, Execute, Lifecycle) are defined once at the cross-manufacturer layer. Each manufacturer is allowed to **refine** those contracts within bounds — for example, by overriding selected M3 invariants or adjusting domain weights.

## Where refinements actually live

The authoritative refinement surface for MFG-TC is in the sibling `cafe-spec` repo:

```
/Users/socrateshlapolosa/Development/cafe-spec/manufacturers/traditional-cloud/
├── manifest.yaml         # declares which ports MFG-TC binds to + version
└── m3-invariants/        # per-line invariant overrides (if any)
```

## What lives here (in this repo)

This directory holds engineering notes and decision records about how MFG-TC refines the canonical port contracts — the "why" behind the entries in the sibling manifest. Examples:

- Rationale for any M3 invariant override.
- Domain-weight adjustment reasoning (e.g. why MFG-TC weights `compliance` differently from MFG-edge).
- Open questions about port-contract evolution affecting MFG-TC.

## Rule

The sibling `manifest.yaml` + `m3-invariants/` are the source of truth that the factory and other manufacturers read. This directory is human-facing context, not consumed by any runtime.
