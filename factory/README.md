# factory/

The **factory** hosts the cross-manufacturer (factory-level) ports and adapters
that every production line plugs into. Think of it as a factory's **central
services**: the intake desk that takes orders, the dispatcher that opens work
orders, the operator on duty who keeps the line running, and the central
library that holds the recipes and toolkit specifications.

The factory **contains** its production lines, **sits on** the substrate it
runs on, and **owns** its shared tooling. See [`production-lines/`](./production-lines/):
a manufacturer is a production line that turns the shared core into one specific
class of output (AI agents, traditional cloud, mobile, etc.). Per-manufacturer
ports (Compose, Catalog, Execute) live with each manufacturer. **Cross-mfg**
ports (Intake, UI, Classify, Approve, Govern, Observe) live here.

## Layout

```
factory/
├── adapters/         # implementations of cross-mfg ports
├── core/             # factory-level state (knowledge base, recipes, schemas)
├── ports/            # pointer docs to cafe-spec port contracts
├── production-lines/ # per-manufacturer production lines (e.g. traditional-cloud)
├── substrate/        # platform the factory sits on (Crossplane, Knative, Argo, ArgoCD)
├── shared-libs/      # shared tooling owned by the factory (capability-mcp-core, common)
└── README.md         # this file
```

## Adapters in this factory

| Adapter | Real-world role |
|---|---|
| [`adapters/intake-slack`](./adapters/intake-slack) | Intake desk — Slack channel front door |
| [`adapters/mcp-read-gateway`](./adapters/mcp-read-gateway) | Reference library counter — read-only catalog/KB tools |
| [`adapters/mcp-write-gateway`](./adapters/mcp-write-gateway) | Dispatcher — opens PRs / mutating tool surface |
| [`adapters/mcp-web-gateway`](./adapters/mcp-web-gateway) | Discovery desk — web-facing capability discovery |
| [`adapters/operator`](./adapters/operator) | Operator on duty — factory-level steward agent (operator-v1) |

## Core

| Dir | Role |
|---|---|
| [`core/knowledge-base`](./core/knowledge-base) | The factory library: KB entries, recipes, schemas, weightings |

## Ports

Canonical port contracts live in the sibling
[`cafe-spec/`](../../cafe-spec/) repo. See [`ports/README.md`](./ports/README.md)
for the pointer map and the cross-mfg vs per-mfg classification.
