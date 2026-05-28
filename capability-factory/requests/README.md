# requests/

`CapabilityRequest` intake artifacts — one `<id>.yaml` per request, emitted by the orchestrator/intake
and consumed by the architect's selection flow. Schema (see `docs/capability-quality-attributes-v0.md`):

```yaml
intent: "<original natural-language ask — preserved for the ADR>"
category: messaging                                  # one of schema/quality-attributes-v0.yaml:categories
qualityAttributes:
  durability:   { level: strong, required: true }    # hard constraint → filter
  readPattern:  { level: fan-out, required: true }
  latencyP99Ms: { max: 50, required: true }
  footprint:    light                                # soft → category-default weight unless overridden
weights: {}                                          # optional per-attribute override of category defaults
constraints: { runtime: aks, costCeiling: medium }
requestedBy: <agent|human>
```
