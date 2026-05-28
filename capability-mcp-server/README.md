# capability-mcp-server

MCP server (Streamable-HTTP) that exposes the **live OAM catalog** and the **OAM-first provisioning
trigger** for the Capability Factory. See `docs/capability-factory-design.md` (§4b consumer flow,
§8-P2 phase).

## Tools (MCP surface)
**Read (consumer-facing):**
- `catalog.list` — published OAM ComponentDefinitions (live).
- `catalog.describe(name)` — schema rendered LIVE by `vela show` (not the `component-schema-*` ConfigMaps).
- `catalog.search(category, qualityAttributes, weights?)` — deterministic scoring from `capability-factory/`.
- `catalog.scaffold(component, app_name?, namespace?)` — minimal valid OAM Application snippet.
- `catalog.validate(oam_yaml)` — `vela dry-run`.

**Action (gated):**
- `app.submit(oam_yaml)` — **validate → commit OAM to gitops (gate) → trigger `oam-apply`**. Never a raw apply.

## Architecture (onion)
```
src/
  domain/models.py             — pure dataclasses
  infrastructure/
    argo_client.py             — focused lift of slack-api-server's create_workflow_from_template
    github_client.py           — net-new commit_file (Contents API) = the gitops gate
    k8s_catalog_client.py      — live ComponentDefinitions/TraitDefinitions via CustomObjectsApi
    vela_client.py             — `vela show` (live schema) + `vela dry-run`
  application/
    scoring.py                 — deterministic filter+weighted-distance scorer
    catalog_use_cases.py       — list/describe/search/scaffold/validate
    submit_use_case.py         — app.submit (validate → commit → trigger oam-apply)
  interface/
    auth.py                    — Entra JWT middleware (APIM-fronted; AUTH_DISABLED for dev)
    dependencies.py            — @lru_cache DI factories
    mcp_server.py              — FastMCP tools + Streamable-HTTP ASGI app
main.py                        — uvicorn entrypoint
```

## Build
**Build context = repo root** (the image bundles `capability-factory/`):
```sh
docker build -f capability-mcp-server/Dockerfile -t healthidpuaeacr.azurecr.io/capability-mcp-server:<tag> .
docker push healthidpuaeacr.azurecr.io/capability-mcp-server:<tag>
```

## Deploy (in-cluster prerequisites)
- `acr-credentials` (default ns) — ACR pull secret (exists).
- `github-credentials/personal-access-token` — for the gitops `commit_file` (exists).
- `argo-token` (default ns) — bearer for the Argo REST API (mirrors slack-api-server; reused).
- KubeVela + ArgoCD + Knative + Istio (already on-platform).

```sh
kubectl apply -f capability-mcp-server/rbac.yaml
kubectl apply -f capability-mcp-server/knative-service.yaml
kubectl apply -f capability-mcp-server/istio-gateway.yaml
```

## Quick verification (post-deploy)
```sh
# health
curl -fsS http://<istio-ingress>/healthz

# catalog (Streamable-HTTP — needs an MCP client; from curl, JSON-RPC over HTTP):
curl -sX POST http://<istio-ingress>/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Phase-0 / open items
The Knative env defaults to **`AUTH_DISABLED=true`** because the APIM/Entra coordinates
(`APIM_AUDIENCE`, `ENTRA_TENANT`, `ALLOWED_OIDS`) are injected by Phase-0 (DEFERRED, copilots).
Phase 0 also fronts this MCP with the APIM gateway (JWT pass-through, rate-limit).
