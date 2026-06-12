# mcp-read-gateway (capability-mcp-factory)

The **factory-level** MCP gateway. Hosts only cross-manufacturer tools.

Lives at `factory/adapters/mcp-read-gateway/` post-refactor; the deployed
image / Knative service / APIM upstream is still named `capability-mcp-factory`
so APIM routes do not need to change.

## Why this service exists

Before the 2026-05-30 refactor, all MCP tools lived in one monolithic
`capability-mcp-server`. That conflated **factory-level** concerns (works for
any production line) with **per-line** concerns (specific to MFG-TC). Per
the factory / production-line abstraction (see
`docs/architecture/MANUFACTURER.md`), these belong in separate services.

The monolith has since been split:

- shared use cases → `factory/shared-libs/capability-mcp-core/` (importable library)
- this gateway → `factory/adapters/mcp-read-gateway/` (factory-scoped tools)
- per-line tools → `factory/production-lines/traditional-cloud/adapters/...`

## Tools surface

| Tool | Purpose | Scope |
|---|---|---|
| `oam.dry_run` | Validate an OAM Application | Any mfg producing OAM |
| `crossplane.dry_run` | Validate Crossplane XRD/Composition/MR | Any mfg using Crossplane |
| `examples.patterns` | List exemplar patterns | Cross-mfg library |
| `examples.read` | Read an exemplar's YAML | Cross-mfg library |
| `examples.pattern_for` | Pick exemplar by kind | Cross-mfg library |
| `kb.read` | Read a knowledge-base entry | Factory knowledge |
| `kb.list` | List KB entries | Factory knowledge |
| `kb.diff` | Diff KB entry against current | Factory knowledge |
| `factory.route` | Route a use-case → which manufacturer | Factory routing |
| `factory.list_manufacturers` | List registered manufacturers | Factory metadata |
| `lifecycle.state` | Query lifecycle state for a use-case id | Factory observability |

**Not here:** `catalog.*`, `app.submit`, `app.submit_wait` — those are
per-line (MFG-TC) and live in the MFG-TC adapter MCP.

## Implementation note

This service imports use cases directly from
`factory/shared-libs/capability-mcp-core/src/` (baked in as the `capability_mcp_core`
package at image build time). No HTTP-proxy hop. Identical results to the
former monolith by construction.

## Deployment

Build context is still **repo root**; only the `COPY` source paths
moved. The Dockerfile path is now under `factory/adapters/mcp-read-gateway/`.

The Knative Service manifest is GitOps-owned (#163 SUBSTRATE-GITOPS): it lives
in `factory/substrate/services/capability-mcp-factory/knative-service.yaml`
and is synced by the ArgoCD Application `substrate-services` — **do not
`kubectl apply` by hand**.

```bash
# Build from repo root with a NEW immutable tag
az acr build --registry healthidpuaeacr \
  --image capability-mcp-factory:<new-immutable-tag> \
  --platform linux/amd64 \
  -f factory/adapters/mcp-read-gateway/Dockerfile .
# then: edit image tag in factory/substrate/services/capability-mcp-factory/knative-service.yaml,
# git commit + push to main — ArgoCD rolls the new revision.
```

The image name (`capability-mcp-factory`) and the Knative service name are
intentionally **kept stable** so existing APIM upstream routes continue to
work. Renaming them would be a breaking change for APIM and any pinned
consumers.

## Verification

```bash
# Health
curl https://capability-mcp-factory.default.<extip>.nip.io/healthz

# factory.list_manufacturers via Streamable-HTTP MCP (or via APIM /openai/v1/responses)
```
