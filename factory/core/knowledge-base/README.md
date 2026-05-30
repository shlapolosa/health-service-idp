# capability-factory/

Git-versioned **source of truth** for the Capability Factory (see `docs/capability-factory-design.md`
and `docs/capability-quality-attributes-v0.md`). Pure data — read by the MCP server, not executed.

```
schema/quality-attributes-v0.yaml   # the shared quality-attribute vocabulary (DRAFT v0)
weightings/category-defaults.yaml    # per-category default attribute weights (high=3/med=2/low=1)
kb/<tech>.yaml                       # capability knowledge base: one profiled technology per file
requests/                            # CapabilityRequest intake artifacts (one per request)
```

## How it's consumed
- **`catalog.search(intent)`** loads `schema/` + `weightings/` + `kb/` and runs the deterministic match:
  hard-constraint filter → weighted-distance soft rank → tie-break (costClass, then maturity).
- **The architect's upgrade loop** watches each KB entry's `upstreamSource` for new versions/CVEs.
- A KB entry's `maturity` flips `kb → published` when its capability is live in the catalog.

## Adding a capability
1. Add `kb/<tech>.yaml` profiled with the vocabulary in `schema/quality-attributes-v0.yaml`.
2. (Architect flow) a `CapabilityRequest` in `requests/` scores it; on approval the publisher synthesises
   the ComponentDefinition + Composition + traits (a separate PR) and flips `maturity: published`.
