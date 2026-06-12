# factory/substrate/services — GitOps-owned platform services

Manifests here are reconciled by the ArgoCD Application **`substrate-services`**
(`factory/substrate/argocd/substrate-services.yaml`, automated sync + selfHeal,
ServerSideApply, prune disabled). **Never `kubectl apply` these by hand** —
selfHeal will revert any out-of-band change.

| Service | Manifest | Image repo | Source / Dockerfile |
|---|---|---|---|
| capability-mcp-mfg-tc | `capability-mcp-mfg-tc/knative-service.yaml` (+ `rbac.yaml`) | `healthidpuaeacr.azurecr.io/capability-mcp-mfg-tc` | `factory/production-lines/traditional-cloud/adapters/compose-mcp/` |
| capability-mcp-factory | `capability-mcp-factory/knative-service.yaml` | `healthidpuaeacr.azurecr.io/capability-mcp-factory` | `factory/adapters/mcp-read-gateway/` |
| slack-api-server | `slack-api-server/knative-service.yaml` | `healthidpuaeacr.azurecr.io/slack-api-server` | `factory/adapters/intake-slack/` |

## Release workflow (replaces hand `kubectl apply`)

1. Build + push with a **new immutable tag** (never reuse / never `:latest`),
   from the repo root (build context must be repo root):

   ```bash
   az acr build --registry healthidpuaeacr \
     --image capability-mcp-mfg-tc:<new-tag> \
     --platform linux/amd64 \
     -f factory/production-lines/traditional-cloud/adapters/compose-mcp/Dockerfile .
   ```

2. Edit the `image:` tag in the service's `knative-service.yaml` here.
3. `git commit` + `git push` to `main`.
4. ArgoCD syncs `substrate-services` (≤3 min, or `argocd app sync substrate-services`).
   Knative rolls a new revision; verify with
   `kubectl get ksvc <name> -n default`.

`factory/utilities/bootstrap/images.sh` discovers tags from these manifests
(single source of truth) and the bootstrap scripts still apply them once on a
fresh cluster; steady-state ownership is ArgoCD.

## Adoption notes (first sync)

- Manifests were moved here byte-identical (plus a header comment) from their
  old hand-apply locations; `capability-mcp-mfg-tc` carries the live image
  `rt2-04ae27e` (live revision 00019) so adoption is a no-op.
- Before the first apply of the ArgoCD app, confirm `capability-mcp-factory`
  (git: `user1000`) and `slack-api-server` (git: `retire-wft-3c0af95`) git tags
  still match the live ksvc images — if the live image is newer, update git
  FIRST, otherwise selfHeal will roll the service back.
- `slack-api-server`'s companion resources (istio-gateway.yaml,
  oam-webhook-registration.yaml, registry-config ConfigMap dependency) remain
  in `factory/adapters/intake-slack/` and are still hand-applied; only the ksvc
  is GitOps-owned here.
- Candidates for the same treatment later: `capability-factory-mcp`
  (mcp-write-gateway) and `capability-web-mcp` (mcp-web-gateway).
