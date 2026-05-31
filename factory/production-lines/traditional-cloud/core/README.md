# MFG-TC Core Spec — Pointer

MFG-TC's **defining recipe** does not live in this repo. It lives in the sibling `cafe-spec` repo, which is the single source of truth for what makes a Traditional Cloud line tick.

## Canonical location

```
/Users/socrateshlapolosa/Development/cafe-spec/manufacturers/traditional-cloud/
├── manifest.yaml          # the manufacturer manifest registered with the factory
├── m1-archetypes.json     # M1: which archetypes this line supports
├── m2-decision-tree.yaml  # M2: routing decision tree
├── m3-invariants/         # M3: invariant set (and any per-line overrides)
├── m4-catalog/            # M4: catalog schema this line publishes against
├── m5-templates/          # M5: templates for compose adapter
└── governance/            # OPA policies & governance bundles
```

## What lives here (in this repo)

This directory holds:

- A pointer (this file) so engineers working in the runtime repo know where the spec is.
- MFG-TC-specific local docs that **augment** the sibling spec — design notes, post-mortems, ADRs scoped to MFG-TC, decisions not yet promoted upstream.

## Rule

If a change is to MFG-TC's contract or recipe (manifest, M1-M5, governance) — edit it in `cafe-spec` and bump the manifest version. If a change is to MFG-TC's runtime behaviour — edit the relevant `adapters/` subdir here.
