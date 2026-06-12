# archive/ — stale pre-Crossplane-v2 files (CLEAN-XP #158, 2026-06-12)

Files moved here are NOT synced by ArgoCD (`platform-definitions` syncs
`factory/substrate/crossplane/` with `recurse: false`, so subdirectories —
including this one and `templates/` — are excluded). Moving them in git does
not delete anything from the cluster (`prune: false`, and none were in the
previous narrow include glob anyway).

Classification was evidence-based: repo-wide grep for each filename/resource
name, composition mode (Crossplane v2 removed `spec.resources`; only
`mode: Pipeline` compositions reconcile on the current v2 / provider-kubernetes
v1.2.1 stack), and git last-touch.

## Why each file is stale (one line each)

| File | Reason |
|---|---|
| aws-provider-config.yaml | AWS IRSA ProviderConfigs — EKS-era; platform runs on AKS, provider-aws unused. |
| cluster-secret-store.yaml | ClusterSecretStore `aws-secretsmanager` (us-west-2) — EKS-era; live external-secrets config is `factory/substrate/external-secrets/`. |
| crossplane-network-policy.yaml | EKS-era NetworkPolicy locking crossplane egress to its own namespace — syncing it would break provider egress on the live cluster. |
| external-secret-templates.yaml | Auth0 ExternalSecret template referencing the archived `aws-secretsmanager` store; zero repo references. |
| external-secrets-composition.yaml | Legacy `spec.resources` Composition (invalid under Crossplane v2); zero repo references. |
| external-secrets-rbac.yaml | RBAC for the archived external-secrets composition; zero repo references. |
| external-secrets-xrd.yaml | XRD `xexternalsecrets` — pair of the archived composition; zero repo references. |
| graphql-gateway-application.yaml | Hand-test OAM Application — syncing would deploy a live graphql-gateway app (same hazard as the telemetry-platform example caught in RT-1). |
| graphql-platform-claim-composition-hasura-backup.yaml | Explicit pre-v2 backup (legacy `spec.resources`); superseded by the XP-MODERN pipeline rewrite of graphql-platform-claim-composition.yaml. |
| infrastructure-claim-composition.yaml | Legacy `spec.resources` Composition; zero repo references. |
| infrastructure-claim-xrd.yaml | XRD `xinfrastructureclaims.platform.io` — pair of the archived composition; only legacy install-script references. |
| orchestration-platform-claim-xrd.yaml | Pre-v2 orchestration platform XRD; no live claim path. |
| orchestration-platform-composition.yaml | Legacy `spec.resources` Composition; only referenced by the legacy health-check script. |
| provider-secret-claim-composition.yaml | Legacy `spec.resources` Composition; zero repo references. |
| provider-secret-claim-xrd.yaml | XRD `xprovidersecretclaims.platform.io` — pair of the above; zero repo references. |
| providers.yaml | Mixed bootstrap provider set: provider-aws (EKS-era) + contrib provider-github v0.6.0 (superseded by provider-upjet-github v0.18.0, kept top-level); syncing would install provider-aws and risk re-pinning live provider-helm/provider-kubernetes (v1.2.1) versions. |
| secret-injector-composition.yaml | Legacy `spec.resources` Job-based secret injection; superseded by the binding contract (`<comp>-conn` secrets + envFrom, 2026-06-06). |
| secret-injector-xrd.yaml | XRD `xsecretinjectors` — pair of the archived composition. |
| vcluster-environment-claim-composition.yaml | Legacy `spec.resources` — cannot reconcile under Crossplane v2; the vcluster leg needs an XP-MODERN pipeline rewrite if resurrected (execute/vcluster-standard-contract.yaml still mentions it). |
| vcluster-environment-claim-xrd.yaml | Pair of the above vcluster composition. |

## Deliberately NOT archived

- `templates/comprehensive-gitops-template.yml` + `templates/gitops-deployment-update.yml`
  — fetched at scaffold time by raw.githubusercontent.com URL from
  app-container-claim-composition.yaml; moving them breaks every future
  scaffold. URL path unchanged.
- `registry-config.yaml` — ConfigMap consumed by the live slack-api-server ksvc.
- `crossplane-admin-sa.yaml` — SA used by the live application-claim-composition Jobs.
- `github-provider-config.yaml` — ProviderConfig `github-provider` is referenced
  by the live app-container composition, but the file also contains a Secret
  with a literal `${PERSONAL_ACCESS_TOKEN}` placeholder, so it is **excluded
  from the ArgoCD include set** (selfHeal would clobber the live secret).
