# S-CP-006 — app-of-apps ArgoCD app has wrong destination namespace

**Class:** S-CP (Crossplane managed-resource)
**Consumer impact:** MEDIUM — every microservice request leaves a permanently-OutOfSync ArgoCD Application. Dashboard pollution + ArgoCD may try (and fail) to reconcile resources in the wrong namespace.
**Discovered:** 2026-05-30 (py-demo-svc-v2 E2E test after PR #11 merged)

## What it looks like

```
NAME                          SYNC STATUS   HEALTH STATUS
py-demo-svc-v2-app-of-apps    OutOfSync     Healthy
```

The app's drift status shows child Applications (`py-demo-svc-v2-app-of-apps` recursively + `py-demo-svc-v2-oam-application`) are OutOfSync. Inspecting the spec:

```yaml
spec:
  destination:
    server: https://kubernetes.default.svc
    namespace: py-demo-svc-v2   # ← BUG
  source:
    path: apps
```

The `apps/` directory contains `app-of-apps.yaml` and `oam-application.yaml` — both `kind: Application` resources. ArgoCD Application resources MUST live in the `argocd` namespace (or wherever ArgoCD is configured to look). The `destination.namespace: py-demo-svc-v2` tells ArgoCD "create these Applications in the service's own namespace", but ArgoCD's actual Applications live in `argocd`. Result: drift between target (`py-demo-svc-v2/Application/X`) and live (`argocd/Application/X`).

## Root cause

`crossplane/app-container-claim-composition.yaml` L905 (the `cat > apps/app-of-apps.yaml` HEREDOC inside the gitops-setup Job):

```yaml
destination:
  server: https://kubernetes.default.svc
  namespace: $APP_NAME   # bug — should be argocd
```

The author likely confused "where do the deployed workloads live?" (correct: service's namespace) with "where do the ArgoCD Application resources live?" (correct: argocd ns).

## Fix

Change `namespace: $APP_NAME` to `namespace: argocd` in that one HEREDOC line. The other ArgoCD-related HEREDOCs in the codebase (`vcluster/.../argocd-app.yaml` at L862, `apps/oam-application.yaml`) target workload-managing apps which correctly use `namespace: default` or similar.

## Verification

Fresh `/microservice` request → `kubectl -n argocd get application <name>-app-of-apps`: should show `SYNCED Healthy` (not OutOfSync).

## Blast radius

**MEDIUM.** Every microservice request since the platform shipped has left this drift. Doesn't break deployment (the `-oam-application` ArgoCD app correctly syncs the OAM resource), but pollutes ArgoCD UI. May cause confusion for operators who can't tell which OOS apps are "real" drift vs "this known bug".

## Related

- S-CP-004 — same PR, different signal.
- S-CP-007 — same PR, different signal.
