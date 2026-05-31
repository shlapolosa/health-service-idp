# capability-web-mcp

DISCOVER surface for the architect agent. Two tools:
- `web.search(query, limit)` — SearXNG-backed search (no API keys, no quotas)
- `web.fetch(url, max_bytes)` — size-capped HTTP GET, text/html/json only

Called by `architect-v1` during Phase 3a (DISCOVER) when the catalog has no fitting candidate
for a capability request. Per the architect's system prompt, the LLM shortlists 2-4 candidate
technologies, then the deterministic scorer re-applies hard filters before any synthesis runs.

## Backend

In-cluster SearXNG (`http://searxng.search.svc.cluster.local:8080`). Set `SEARXNG_URL` env to
override (e.g. point at the user's local Docker SearXNG during dev).

## Deploy

```bash
# 1. SearXNG (one-time)
kubectl apply -f capability-web-mcp/searxng-deployment.yaml

# 2. Build + push web MCP image
docker build -f capability-web-mcp/Dockerfile -t healthidpuaeacr.azurecr.io/capability-web-mcp:v0.1 .
docker push healthidpuaeacr.azurecr.io/capability-web-mcp:v0.1

# 3. Apply MCP service
kubectl apply -f capability-web-mcp/rbac.yaml
kubectl apply -f capability-web-mcp/knative-service.yaml
```

## APIM wiring

Wire the web MCP under `mcp/web` on the existing APIM gateway, attach to `mcp-internal`
product (sub-key auth, same as architect's catalog access). Foundry connection stores
the sub-key as `Ocp-Apim-Subscription-Key` header.

```bash
# APIM API
az apim api create --service-name aigw-apim-dev-w4x7ibwk4e2is --resource-group rg-ai-gateway-dev-uae \
  --api-id mcp-web --path mcp/web \
  --display-name "Capability Web MCP" \
  --service-url "http://capability-web-mcp.default.20.233.105.82.nip.io" \
  --protocols https --subscription-required true
# Attach to mcp-internal product → sub-key auth
az rest --method PUT \
  --uri "/subscriptions/<sub>/.../service/aigw-apim-dev-w4x7ibwk4e2is/products/mcp-internal/apis/mcp-web?api-version=2022-08-01"
```

## Safety

- `ALLOWED_FETCH_DOMAINS` env (CSV) — empty = no restriction; set to e.g. `microsoft.com,github.com,docs.kubernetes.io` for prod
- `BLOCKED_SEARCH_TERMS` env (CSV) — bans hard-coded phrases from search queries
- `FETCH_MAX_BYTES` — default 200KB
- Audit log line on every search + fetch with caller context (when JWT validation is enabled)
