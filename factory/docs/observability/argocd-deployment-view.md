# ArgoCD — Platform Deployment-Visibility Surface (OBS-A)

ArgoCD's **Applications list** is the canonical view of *what is actually deployed*
across the platform plus *drift* (live-vs-git delta). This doc covers how to reach
it, log in, and read it. Nothing new was installed — ArgoCD already runs in the
`argocd` namespace; OBS-A only added a network route.

## URL

    http://argocd.20.233.105.82.nip.io/

- Reachable through the shared `default/capability-mcp-gateway` (Istio ingress, HTTP:80).
- Route defined in `factory/substrate/services/argocd-ui-vs.yaml`
  (VirtualService `argocd-ui` + DestinationRule `argocd-ui-tls`), GitOps-managed by
  the `substrate-services` ArgoCD Application.
- `argocd-server` serves **only HTTPS** (no `--insecure`). The route TLS-originates
  from the mesh to `argocd-server:443` (SIMPLE + insecureSkipVerify for its
  self-signed serving cert) — the same proven pattern as the `argocd-webhook` route.

## Login

ArgoCD's own auth is **ON** (unauthenticated API calls return `401`). Do not disable it.

- Username: `admin`
- Password: in secret `argocd-initial-admin-secret` (namespace `argocd`), key `.data.password`.
  Never print or commit the value. Retrieve at use time:

      kubectl get secret argocd-initial-admin-secret -n argocd \
        -o jsonpath='{.data.password}' | base64 -d

- CLI: `argocd login argocd.20.233.105.82.nip.io --username admin --grpc-web --plaintext`
  (the gateway terminates client TLS at HTTP:80; use `--plaintext`/`--grpc-web`).

## Reading the all-apps view = deployment inventory

The **Applications** page lists every deployed app with two columns that ARE the
inventory + drift signal:

- **Sync status** — `Synced` = live matches git; `OutOfSync` = **drift** (live
  diverges from the desired git state).
- **Health status** — `Healthy` / `Progressing` / `Degraded` = runtime health.

Click an app → **Diff** tab (or `argocd app diff <app>`) to see the exact
live-vs-desired delta per Kubernetes resource. This is built-in drift detection;
no extra tooling required.

## Live evidence (2026-06-13)

ArgoCD v3.4.3. Snapshot of the all-apps inventory through the new route:

| Application | Sync | Health |
|---|---|---|
| rtdemo2-app-of-apps | OutOfSync | Healthy |
| rtdemo2-gateway-app | Synced | Healthy |
| rtdemo2-ingest-app | OutOfSync | Healthy |
| rtdemo2-oam | Synced | Degraded |
| rtdemo2-oam-application | OutOfSync | Healthy |
| rtdemo2-processor-app | OutOfSync | Healthy |
| webhookdemo-bridge-app-of-apps | Synced | Healthy |
| webhookdemo-bridge-app | OutOfSync | Healthy |
| webhookdemo-bridge-oam | Synced | Healthy |
| webhookdemo-bridge-oam-application | OutOfSync | Healthy |
| platform-definitions | OutOfSync | Degraded |
| substrate-services | OutOfSync | Healthy |
| chatdemo-app-of-apps | OutOfSync | Healthy |
| patient9-app-of-apps | OutOfSync | Healthy |
| rtdemo-app-of-apps | OutOfSync | Healthy |
| rtdemo-ingest-app | OutOfSync | Progressing |
| rtdemo-worker-app | OutOfSync | Progressing |

Drift example — `substrate-services` is `OutOfSync` because three live Knative
Services diverge from git (their image tags / controller-owned fields drift after
out-of-band `kubectl apply`s):

- `Service/capability-mcp-factory` — OutOfSync
- `Service/capability-mcp-mfg-tc` — OutOfSync
- `Service/slack-api-server` — OutOfSync

`argocd app diff substrate-services` (or the UI Diff tab) shows the field-level delta.
