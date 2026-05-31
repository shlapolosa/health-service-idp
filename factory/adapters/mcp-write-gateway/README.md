# capability-factory-mcp

The **write surface** of the Capability Factory. One MCP tool: `factory.propose`. One read tool:
`factory.list_open_prs`. Nothing else — every other operation in the architect agent's reasoning
loop is read-only and served by the sibling `capability-mcp-server` at `/mcp/catalog`.

This MCP is the **membrane**: agents may only mutate the codebase by opening a PR through here.

## Trust boundaries

| Concern | Resolution |
|---|---|
| Who can call this MCP? | APIM `validate-jwt` requires audience `api://<factory-app-id>` + role `factory-proposer`. Only `sp-architect-writer` holds the role. |
| How does this MCP write to git? | GitHub App "Socrates-FactoryBot" (App ID 3893824) with `contents:write` + `pull_requests:write`. PEM in Key Vault `kv-socrates-6706` (RG `rg-ai-usecase-poc`), fetched via AKS Workload Identity (no static secrets in cluster). |
| Which repos can it touch? | `FACTORY_ALLOWED_REPOS` env (default: `health-service-idp,health-service-idp-gitops`). |
| Why a separate MCP from `capability-mcp-server`? | Different trust class — read vs write. Independent revocation, separate Knative service, separate SA, separate APIM API, separate SP. |

## Quick start (local dev)

```bash
# Mint a GitHub App + Installation manually (or via scripts/setup-factory-azure.sh) and export:
export GITHUB_APP_ID=<numeric>
export GITHUB_APP_INSTALLATION_ID=<numeric>
export GITHUB_APP_PEM_PATH=/path/to/factorybot.private-key.pem
export GITHUB_APP_AUTH_MODE=env_pem    # default in dev
export GITHUB_OWNER=shlapolosa
export FACTORY_ALLOWED_REPOS=health-service-idp,health-service-idp-gitops
export AUTH_DISABLED=true              # skip Entra check locally

pip install -r requirements.txt
python main.py

# Then:
curl -X POST http://localhost:8080/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{
    "name":"factory.list_open_prs","arguments":{"repo":"health-service-idp"}}}'
```

## Production deploy

1. Run `scripts/setup-factory-azure.sh` once to create the SP, federated identity, Key Vault secret,
   APIM API + role assignments.
2. `kubectl apply -f rbac.yaml` (replace `<SP_ARCHITECT_WRITER_CLIENT_ID>` first; the setup script
   prints it).
3. `kubectl apply -f knative-service.yaml` (after creating the `github-app-factorybot` Secret with
   `app-id` + `installation-id` keys).
4. `kubectl apply -f istio-gateway.yaml`.
5. Apply the APIM policy via `az rest PATCH …/apis/factory/policies/policy`.

## Tools exposed

### `factory.propose(repo, title, body, files, base?, branch_prefix?)`
Opens a PR. Audit-logged per call (caller OID + repo + branch + file list).

### `factory.list_open_prs(repo, head_prefix?)`
Read-only inspection of currently-open architect proposals.
