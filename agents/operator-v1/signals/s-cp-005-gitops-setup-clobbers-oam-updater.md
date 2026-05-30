# S-CP-005 — gitops-setup blank template clobbers oam-updater's commits on retry

**Class:** S-CP (Crossplane managed-resource)
**Severity:** HIGH — generated OAM Application ends up with wrong `clusters: [<service-name>]` targeting a non-existent KubeVela cluster → workflow fails at `deploy-deploy-to-vcluster` → **no ksvc ever appears**.
**Discovered:** 2026-05-30 (`data-analytices-service` E2E test after PR #9/#10 merged)

## What it looks like (consumer-facing)

- Slack: `/microservice create <name> python with database and redis`
- Workflow `microservice-creation-<id>` Succeeds in ~2 min
- AppContainerClaim + ApplicationClaim both go Ready=True
- Gitops repo populated with 4-5 commits
- **No ksvc**. OAM Application status: `workflowFailed` at `deploy-deploy-to-vcluster`:
  > `failed to get cluster <service-name>: virtualclusters.cluster.core.oam.dev "<service-name>" not found`

## Empirical root cause

The Slack command sent `target-vcluster=host` (default). The ApplicationClaim correctly received `spec.targetVCluster=host`. The `oam-updater` Job (in `application-claim-composition.yaml` L779-790) correctly removed the topology policy because host deployments need none.

BUT: Crossplane Object retry re-fired the **gitops-setup** Job (in `app-container-claim-composition.yaml` L682-734), which `cat > oam/applications/application.yaml << EOF` unconditionally — overwriting oam-updater's commits with the stale blank template. That template hardcodes `clusters: ["$APP_NAME"]` → `clusters: ["data-analytices-service"]`.

Result: the file in gitops becomes a broken OAM that targets a vCluster named after the service (which doesn't exist in KubeVela's registry — the loft.sh vCluster wasn't registered via `vela cluster join` because `ensure-target-vcluster` skipped when target was `host`).

Verified via the commit timeline in `shlapolosa/data-analytices-service-gitops`:
1. `a42fdd8e Initial commit` — empty repo
2. `9f74fec0 Initialize GitOps repository structure` — gitops-setup first run, wrote blank template with bad clusters
3. `5243e5a8 Add data-analytices-service webservice component to OAM Application` — oam-updater wrote correct OAM (with topology policy stripped for host)
4. `4ac50253 Add GitOps manifests for data-analytices-service microservice`
5. `bf60dc82 Initialize GitOps repository structure` — **gitops-setup ran AGAIN (Crossplane retry), clobbered oam-updater's correct OAM with the bad blank template**

## Fix shape (this signal)

Two changes in `crossplane/app-container-claim-composition.yaml`:

**1. Guard the blank-template write.** Only write when the file doesn't already exist OR still contains the placeholder marker. Prevents clobber on retry:

```sh
if [ -f oam/applications/application.yaml ] && \
   ! grep -q "Will be updated with actual vCluster name" oam/applications/application.yaml; then
  echo "📄 oam/applications/application.yaml already exists with non-template content — preserving"
else
  cat > oam/applications/application.yaml << EOF
  ...
  EOF
fi
```

**2. Remove the hardcoded topology policy from the blank template.** `oam-updater` adds it correctly (or removes it) based on `ApplicationClaim.spec.targetVCluster`. For host deployments the policy must be ABSENT — hardcoding `clusters: ["$APP_NAME"]` here is wrong by default.

## Verification

1. Apply updated composition.
2. Submit a fresh `/microservice` request with no target-vcluster (defaults to host).
3. Watch workflow → Succeeds; ApplicationClaim Ready=True; OAM Application status `running` (not `workflowFailed`); ksvc appears within ~60s.
4. Inspect the gitops repo's `oam/applications/application.yaml`: no `deploy-to-vcluster` policy.
5. Optionally: delete the gitops-setup Job mid-flight to force Crossplane retry. New pod hits the guard branch, oam-updater's content preserved.

## Blast radius

**HIGH.** Affects every microservice request where:
- Crossplane retries the gitops-setup Object (likely on most requests since other latent script issues — S-CP-004 PEP 668 — cause non-zero exits), AND
- Target is host (the default — no `target-vcluster` argument)

Combined: probably most `/microservice` requests in the last ~6 months never produced a working ksvc on first try. Surviving microservices on the cluster either (a) had `vela cluster join` done manually for a same-name vCluster, or (b) hit a lucky race where gitops-setup didn't retry.

## Related

- S-CP-001 (PR #9) — idempotent commits. Necessary but not sufficient.
- S-CP-002 (PR #10) — alpine/git missing curl. Cosmetic per consumer-impact gate.
- S-CP-004 (deferred) — PEP 668 pip install. Cosmetic per consumer-impact gate.
- S-CP-005 (this) — first signal AFTER #9/#10 with **real consumer impact** (no ksvc).
- S-VC-001 (candidate, not yet authored) — `ensure-target-vcluster` step skips when target=host but the OAM still references a per-service vCluster. Fixed implicitly by S-CP-005 (the OAM no longer references it).
