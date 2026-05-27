# vCluster Provisioning — Audit, Fixes & Lessons (2026-05-27)

End-to-end audit of the Slack `/microservice` → running Knative-in-vCluster flow on the
**AKS** host cluster (`internal-developer-platform`, RG `health-service-idp-uae-rg`).
Traced two live runs (`accounts-payable`, `audit-svc`), fixed the chain of bugs that made
*every* prior project `workflowFailed`, and audited resource consumption.

## TL;DR

- The flow **works now** end-to-end: Slack → Argo workflow → repos + claims + namespace →
  vCluster → Knative installed in-vCluster → registered with host KubeVela → OAM app
  `running` → Knative Service deployed into the vCluster.
- It was broken by a **7-bug chain** (below), all now fixed in
  `crossplane/vcluster-environment-claim-composition.yaml`.
- It is **resource-heavy and leaks**: one `/microservice` ≈ **+31 pods at peak, ~+20 permanent**.
  Root causes: no Job TTL (completed pods never GC), default `backoffLimit=6`, and a **full
  vCluster + full Knative stack per microservice** (`auto_create_vcluster=True`).

## The provisioning flow (as traced)

```
Slack POST /slack/command (/microservice create <name>)        slack-api-server (onion FastAPI, reverted-v1.2.0)
  → verifies HMAC (SLACK_SIGNING_SECRET from k8s secret slack-credentials/signing-secret)
  → dispatcher=argo → submits Argo Workflow "microservice-creation-*" in ns argo
     → creates 3 Crossplane claims in `default`: applicationclaim, appcontainerclaim, vclusterenvironmentclaim
        → vclusterenvironmentclaim composition (14 composed Objects, 4 Jobs):
             vcluster-create → crd-setup → knative-installer → register-clustergateway → kubevela-access SA/CRB/token
        → appcontainer/application compositions (~10 Jobs in `default`): repos, gitops, argocd, oam-updater, ...
  → OAM Application "<name>" (core.oam.dev) with topology policy deploy-to-vcluster
  → after registration: KubeVela renders the webservice component → Knative Service synced into the vCluster
```

Knative Services are **rendered by the host KubeVela** (definitions live in the host) and pushed
into the vCluster via the **ClusterGateway** (created by `vela cluster join`). The vCluster does
NOT run KubeVela; it only needs Knative + the registration credential.

## The 7-bug chain (all fixed in vcluster-environment-claim-composition.yaml)

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | `vcluster create` fails `unknown field genericSync` | CLI pulled from `releases/latest` → v0.20 rejects the v0.19 values schema | **pin v0.19.5** (all 3 download sites) |
| 2 | `knative-installer`: `vcluster: not found` | step never installed the CLI | add `/tmp/vcluster` download |
| 3 | register: "Waiting for DNS… 30/30" | endpoint extraction returned empty | use the `<name>-lb` LoadBalancer external IP |
| 4 | `vela join`: `control characters are not allowed` / `current-context is not set` | `vcluster connect --print` emits status, not a kubeconfig | **build kubeconfig from the `vc-<name>` secret**, repoint server→LB-IP, drop CA, add `insecure-skip-tls-verify` |
| 5 | `syntax error: unexpected end of file (expecting fi)` | `WD_EOF` heredoc closing delimiter was indented → never terminated | un-indent delimiter to column 0 (kubectl accepts 2-space-indented body) |
| 6 | `no matches for kind "WorkloadDefinition"` | applying a KubeVela WD *into* the vCluster (no KubeVela CRDs there) | make non-fatal (`|| echo skip`) — host renders & syncs |
| 7 | claim stuck `Ready=False` | host ProviderConfig reads `vc-<name>/config` (server `localhost:8443`, unreachable) | patch `vc-<name>` secret config to LB-IP (see caveat) |

Plus: the OAM app must be re-run after registration — it fails the first time
("virtualclusters … not found") because it deploys before the vCluster is registered.
`vela workflow restart <app>` re-runs it.

### Manual recovery / how to register a vCluster by hand
```sh
LB_IP=$(kubectl get svc <name>-lb -n <name> -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
kubectl get secret vc-<name> -n <name> -o jsonpath='{.data.config}' | base64 -d \
  | sed "s|server: https://localhost:8443|server: https://${LB_IP}:443|" \
  | sed "/certificate-authority-data:/d" \
  | yq e '.clusters[0].cluster."insecure-skip-tls-verify" = true' - > /tmp/vc.kubeconfig
vela cluster join /tmp/vc.kubeconfig --name <name>
vela workflow restart <name> -n default   # re-run the OAM app
```

## Resource audit (the flakiness + heaviness)

Measured: one `/microservice` creation added **+31 pods at peak**, settling to **~+20 permanent**
(8 running vCluster+Knative pods + ~12 lingering Completed job pods). Two test runs → 137 pods.

Leaks / amplifiers found:
1. **No `ttlSecondsAfterFinished` on any of the 17 Jobs** → completed job pods never garbage-collected. (Biggest, easiest fix.)
2. **`backoffLimit` unset → defaults to 6** → a failing job spawns up to 6 retry pods (this is what produced the CrashLoopBackOff storms during debugging).
3. **`auto_create_vcluster=True` default** (`slack-api-server/src/infrastructure/nlp_parser.py`) → **every microservice gets its own full vCluster + full Knative stack** (serving-core + kourier ≈ 8 perpetual pods + vcluster control plane). This is the dominant cost; firing N microservices = N Knative installs.
4. **No teardown flow** — nothing removes a project's claims/OAM-app/vcluster/namespace. Orphans accumulate (this is why 227 ArgoCD apps / 71 OAM apps / 25 vClusters had built up). Use `cleanup-noncore-resources.sh` (in repo root) — delete OAM apps FIRST (they regenerate claims), then claims, ArgoCD apps, vCluster registration secrets, namespaces.
5. **13 `latest` references remain** across compositions — including a **second, still-unfixed `vcluster releases/latest` in `application-claim-composition.yaml:473`** (will break identically to bug #1), plus `argocd releases/latest` (468) and various `:latest` image tags. `latest` = non-reproducible + breaks on upstream releases.

## Recommended improvements (prioritized)

**P0 — correctness (will break again otherwise)**
- Pin `application-claim-composition.yaml:473` vcluster CLI to **v0.19.5** (same bug as #1, unfixed).
- Pin `argocd releases/latest` (application-claim:468) and other CLI downloads to fixed versions.

**P1 — stop the leaks (cheap, high impact)**
- Add `ttlSecondsAfterFinished: 600` to all 17 Jobs across the compositions → completed pods auto-clean.
- Set explicit `backoffLimit: 2` on all Jobs → cap failed-pod sprawl.
- Fix bug #7 cleanly: point the vcluster `ProviderConfig` at a **separate, non-synced secret**
  (vCluster's syncer reverts the patched `vc-<name>` secret, so the claim's `Ready` flag still flaps;
  deployment works via the ClusterGateway regardless).

**P2 — resource model (the real heaviness)**
- Reconsider `auto_create_vcluster=True` default. A full vCluster + Knative per microservice is very
  heavy. Options: (a) shared/team vCluster (target an existing one via `in vcluster <name>`),
  (b) make auto-create opt-in, (c) deploy small services to the host cluster (no targetEnvironment).
- Consider one shared Knative install per vCluster reused across many services, rather than per-service vClusters.

**P3 — operability**
- Add a first-class teardown (Slack `/microservice delete <name>` → delete OAM app → claims → vcluster → ns).
- Pin `:latest` image tags to digests/versions for reproducibility + supply-chain safety.

## Slack-from-UI requirements (not yet satisfied)
- Slash command `/microservice` (+ `/vcluster`, `/appcontainer`) with Request URL = **HTTPS**.
  Today only HTTP-on-IP exists (`http://20.233.105.82/slack/command`); no Gateway has a 443/TLS
  server and no cert exists. Need cert-manager + a domain (e.g. `slack.<ip>.nip.io`) or a tunnel.
- Sync the signing secret: k8s `slack-credentials/signing-secret` (`1f50…`) must equal the Slack
  app's signing secret (`090e…`) — update the k8s secret + restart `slack-api-server`.

## 3-tier isolation (implemented 2026-05-27)

Default is now **host deployment**; vCluster isolation is opt-in. Maps onto the existing
`VCLUSTER_TARGET=="host"` branch in `application-claim-composition.yaml` (host → strip topology
policy → deploy to host cluster).

| Tier | Slack command | `target-vcluster` value | vCluster created? |
|---|---|---|---|
| **Host** (default) | `/microservice create svc` | `host` | no — deploys to host cluster |
| **Shared** | `/microservice create svc in vcluster team-x` | `team-x` | created if missing, reused |
| **Dedicated** | `/microservice create svc dedicated` (or `isolated`) | `svc-vcluster` | yes, per service |

**Changes:**
- `slack-api-server/src/infrastructure/nlp_parser.py` — `auto_create_vcluster` default flipped to `False`; `dedicated`/`isolated` keywords → `True`.
- `slack-api-server/src/domain/models.py` — `MicroserviceRequest.get_vcluster_name()` returns `host` / `<team>` / `<repo>-vcluster`; `to_argo_payload()` emits it as `target-vcluster`.
- `argo-workflows/microservice-standard-contract.yaml` — `ensure-target-vcluster` step gated with `… && '{{inputs.parameters.target-vcluster}}' != 'host'`.
- `determine-repository-name` already passes a non-empty `target-vcluster` through unchanged (so `host` propagates to the claim).

**Activation:** the workflow + composition changes are live. The parser/model changes require a
**`slack-api-server` image rebuild + redeploy** (the running image still defaults to dedicated):
```sh
cd slack-api-server
az acr login --name healthidpuaeacr
docker build -t healthidpuaeacr.azurecr.io/slack-api-server:3tier .
docker push healthidpuaeacr.azurecr.io/slack-api-server:3tier
# point the Knative service at the new tag (or let CI/gitops roll it):
kubectl set image ksvc/slack-api-server -n default <container>=healthidpuaeacr.azurecr.io/slack-api-server:3tier
```
(Or push the branch and let `.github/workflows/comprehensive-gitops.yml` build + ArgoCD roll it.)
Until rebuilt, behaviour is unchanged (dedicated vCluster per service) — the workflow's host-gate is
forward-compatible (the old image never emits `host`).

## Control-plane note
The Free-tier AKS API server 503-storms under this platform's reconcile load (227 apps + Crossplane
+ argo-events + Knative). Upgraded to **Standard tier** (2026-05-27) — required for stability. Prefer
`az aks nodepool scale` over `az aks stop` for cost savings (full stop cold-restarts everything at once).
