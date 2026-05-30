# This repo hosts the Traditional Cloud manufacturer (MFG-TC)

This repository contains the **per-manufacturer adapters and catalog** for
the **Traditional Cloud** production line of the CAFE factory. It is **not**
the factory itself — that role belongs to the sibling
[`cafe-spec`](https://github.com/shlapolosa/cafe-spec) repo.

## Vocabulary

| Term | Where it lives | What it is |
|---|---|---|
| **CAFE** = spec / contracts | `cafe-spec/` (sibling) | The factory-level rules every manufacturer must honor |
| **CAM** = per-manufacturer blueprint | `cafe-spec/manufacturers/<id>/manifest.yaml` | One per production line |
| **Factory Floor** | the deployed AKS cluster + APIM + ArgoCD + observe-audit-sink | The running instance |
| **Production line ≡ Manufacturer** | `cafe-spec/manufacturers/<id>/` + per-mfg adapters | The thing that takes a use-case and produces a running product |

This repo is **MFG-TC's** per-mfg adapter set: catalog (capability-mcp-server),
compose (architect-v1 Foundry agent prompt + system), execute (oam-driven-contract
WorkflowTemplate + Crossplane composition + ArgoCD-managed gitops).

## What lives here vs the sibling cafe-spec repo

| Artifact | This repo | Sibling `cafe-spec/` |
|---|---|---|
| MFG-TC manifest | — | `manufacturers/traditional-cloud/manifest.yaml` |
| M1 — archetypes (per-mfg) | — | `manufacturers/traditional-cloud/m1-archetypes.json` |
| M2 — decision tree (per-mfg) | — | `manufacturers/traditional-cloud/m2-decision-tree.yaml` |
| M3 — invariants (per-mfg, .rego) | — | `manufacturers/traditional-cloud/m3-invariants/` |
| M4 — catalog wire-shape schemas | — | `manufacturers/traditional-cloud/m4-catalog/` |
| M4 — catalog runtime (CRDs) | `crossplane/oam/*.yaml` (ComponentDefinitions, TraitDefinitions, PolicyDefinitions) | — |
| M5 — golden OAM exemplars | — | `manufacturers/traditional-cloud/m5-templates/*.yaml` |
| Compose adapter (architect-v1) | `agents/architect-v1/` | listed in manifest under `spec.ports.compose.adapters` |
| Catalog adapter (capability-mcp-server) | `capability-mcp-server/` | listed in manifest under `spec.ports.catalog.adapters` |
| Execute adapter (workflow) | `argo-workflows/oam-driven-contract.yaml` (+ `oam-apply.yaml` legacy) | listed in manifest under `spec.ports.execute.adapters` |
| Crossplane composition | `crossplane/application-claim-composition.yaml` | — |
| GitOps state | `health-service-idp-gitops` (separate repo) | — |

**Cross-manufacturer (factory-level) adapters** live entirely in
`cafe-spec/adapters/`:
- `classify-router/` — Classify port
- `lifecycle-orchestrator/` — Lifecycle choreography
- `govern-opa/` — Govern port
- `approve-pr/` — Approve port
- `observe-audit-sink/` — Observe port
- `compose-canonical/`, `ui-cli/` — additional

The sibling [`cafe-spec/manufacturers/README.md`](https://github.com/shlapolosa/cafe-spec/blob/main/manufacturers/README.md)
explains why per-mfg vs cross-mfg ports split this way.

## How to consume this repo as MFG-TC

When you point a deployment at this repo:

1. Apply `crossplane/oam/*.yaml` — gives you MFG-TC's runtime catalog
   (ComponentDefinitions for webservice, kafka, redis, postgresql, etc.)
2. Apply `argo-workflows/oam-driven-contract.yaml` + `oam-apply.yaml` +
   `oam-apply-wait.yaml` — gives you the Execute adapter
3. Deploy `capability-mcp-server` from this repo — gives you the Catalog
   adapter (MCP-protocol surface for the compose adapter)
4. Register the `agents/architect-v1` system prompt as a Foundry agent —
   gives you the Compose adapter

These four together honor MFG-TC's contract as declared in
`cafe-spec/manufacturers/traditional-cloud/manifest.yaml`.

## Ownership signal

If you find yourself adding a file under `crossplane/oam/` or
`argo-workflows/` or `capability-mcp-server/`, ask: **is this
MFG-TC-specific, or is it factory-wide?**

- MFG-TC-specific → this repo is correct
- Factory-wide → it belongs in `cafe-spec/` instead, and a future
  manufacturer (MFG-AI, MFG-AZ, MFG-MOBILE) should be able to consume
  it without modification

The current entanglement (some factory-level concerns leaking into
this repo) is being unwound by the S1-S5 refactoring sequence — see
`/Users/socrateshlapolosa/.claude/plans/buzzing-hugging-sunset.md`.

## Extending MFG-TC = adding a new definition (no code changes)

Adding a new capability (a datastore, an integration point, an
ingress option) MUST be a **definition-only** change:

| Step | File | Repo |
|---|---|---|
| 1 | New `<name>.yaml` ComponentDefinition | this repo, `crossplane/oam/` |
| 2 | New `<name>.schema.json` (M4 wire shape) | sibling, `manufacturers/traditional-cloud/m4-catalog/` |
| 3 | New entry in `catalog.index.json` | sibling, same path |
| 4 (opt) | New `.rego` invariant | sibling, `m3-invariants/` |
| 5 (opt) | New OAM exemplar | sibling, `m5-templates/` |

**No** agent prompt edits, **no** capability-mcp-server code edits, **no**
oam-driven-contract workflow edits, **no** Crossplane composition edits.

The Catalog port (capability-mcp-server's `catalog.list/describe/...`)
auto-discovers new ComponentDefinitions from the cluster — the
architect-v1 agent sees them immediately. The Execute port
(oam-driven-contract) is generic OAM apply; it doesn't know or care which
CDs exist. The composition is generic XRD; it dispatches on whatever
the OAM declares.

Full procedure: see `cafe-spec/manufacturers/traditional-cloud/EXTENDING.md`.

### Parity audit

Drift between this repo's CDs and the sibling's M4 catalog is detectable:

```bash
python3 /Users/socrateshlapolosa/Development/cafe-spec/scripts/audit-mfg-tc-parity.py
```

Exit 0 = parity. Exit 1 = drift, with the missing artifacts listed.
As of 2026-05-30 the audit shows 5 known drifts (CDs lacking M4
schemas): `camunda-orchestrator`, `graphql-gateway`, `identity-service`,
`rasa-chatbot`, `realtime-platform`. These work at runtime but the
compose agent has no formal wire-shape contract for them — separate
gap-closing PR.

### Future definition-only friction reductions

Currently the 5-step checklist requires touching two repos. Friction
reductions tracked as future S-series work:

- Pre-commit hook in this repo that runs the parity audit and blocks
  commits introducing a new CD without a matching M4 schema in the
  sibling
- Auto-generation of M4 schemas from CD CUE `parameter:` blocks
  (deriving the schema instead of authoring it)
- Single-command `capability add <name>` that scaffolds all 3-5 files

## Relation to operator-v1

The operator-v1 agent (under `agents/operator-v1/`) uses MFG-TC's
contract surface to diagnose failures in MFG-TC's running solutions.
Its signals catalog (`agents/operator-v1/signals/README.md`) is
MFG-TC-scoped today; future manufacturers will need their own
signal catalogs or a multi-mfg dispatcher.
