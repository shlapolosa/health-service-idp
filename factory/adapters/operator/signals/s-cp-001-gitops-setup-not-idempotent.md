# S-CP-001 — gitops/source-setup Job script not idempotent

**Class:** S-CP (Crossplane managed-resource)
**Severity:** blocks every microservice creation request when retry occurs
**Discovered:** 2026-05-30 (user-service `microservice-creation-r2mlg`)
**Reproducer:** `/microservice create <name> python with database and redis` via Slack

## What it looks like (observable)

- Argo workflow `microservice-creation-<id>` Failed at `wait-for-microservice-ready` after 600s.
- Job `<name>-gitops-setup` (and/or `<name>-source-setup`):
  - First pod: `Completed`.
  - Crossplane Object re-fires → second pod: `Error`, GC'd quickly.
  - Job-level event: `BackoffLimitExceeded`.
- AppContainerClaim `default/<name>` shows `SYNCED=True READY=False` indefinitely.
- ApplicationClaim shows `SYNCED=True READY=False` indefinitely.
- GitHub repo `shlapolosa/<name>` and `shlapolosa/<name>-gitops` both exist with initial commits intact.

## Root cause

Composition `crossplane/app-container-claim-composition.yaml` runs two Jobs that mutate gitops state:

| Line | Job | Pattern |
|---|---|---|
| 449-462 | source-setup | `git add README.md` → `git commit -m "Initial commit..."` → `git add .` → `git commit -m "Initialize..."` → `git push` |
| 1163-1171 | gitops-setup | `git add .` → `git commit -m "Initialize GitOps..."` → `git push` |

Script preamble is `set -e`. On Crossplane's automatic retry of the Object, the repos are already initialized → `git add .` stages nothing → `git commit` exits non-zero with "nothing to commit, working tree clean" → script exits 1 → BackoffLimitExceeded.

## Fix shape (definition-only — operator-eligible)

Wrap each commit:

```sh
git add .
git diff --cached --quiet || git commit -m "..."
git push origin HEAD || true
```

Three rules:
1. **Stage first, then check.** `git diff --cached --quiet` returns 0 if nothing staged → skip commit.
2. **Push tolerant.** `|| true` because pushing with no new local commits is a no-op but some git/remote combos error.
3. **Don't bypass `set -e` globally.** Only the commit/push lines need tolerance; other failures (clone, secret encryption, file generation) must still fail loudly.

Apply same pattern to all three commit sites:
- Line 450 (`Initial commit - create repository`) — first commit in fresh repo; on retry the README is identical so safe to skip.
- Line 454 (`Initialize CLAUDE.md-compliant app container structure`) — main source-setup commit.
- Line 1164 (`Initialize GitOps repository structure`) — main gitops-setup commit.

## Verification

1. Apply PR → bump composition image revision (if any) or wait for ArgoCD to sync the CRD.
2. Delete the failed Jobs: `kubectl delete job -n default <name>-gitops-setup <name>-source-setup`.
3. Crossplane recreates them → second run hits the idempotency branch → both go `Completed` cleanly.
4. AppContainerClaim flips Ready=True.
5. Or: submit a new `/microservice` request with a fresh name; full chain green.

## Blast radius

**HIGH.** Every microservice creation that triggers Crossplane retry of the Object (any race, any slow Job, any spurious reconciliation) hits this. Likely affects most multi-component requests because composition resources don't all settle on first reconcile.

## Related

- S-WF-001 — the workflow's wait step has no awareness of this retry cycle; even with the fix, the 600s ceiling may still be insufficient for cold-start cases.
- S-CD-001 — wearables case where webservice without `language:` produced placeholder images (different failure class but same incident family).
