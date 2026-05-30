# S-CP-002 — gitops-setup Job missing curl/jq in image

**Class:** S-CP (Crossplane managed-resource)
**Severity:** blocks gitops-setup completion; GitHub Actions secrets never created on the gitops repo
**Discovered:** 2026-05-30 (one-shot test of updated composition after PR #9 merged)

## What it looks like

`user-service-gitops-setup` Job pod logs (with `set -ex`):

```
+ echo 'Setting up GitHub repository secrets for GitOps...'
+ curl -s -H 'Authorization: token ghp_***' https://api.github.com/repos/shlapolosa/user-service-gitops/actions/secrets/public-key
/bin/sh: curl: not found
+ PUBLIC_KEY_RESPONSE=
```

Exit 127 → BackoffLimitExceeded. AppContainerClaim Ready logic doesn't depend on this Job's exit code (proven empirically: claim went Ready=True after PR #9 even with this still failing), but the gitops repo never gets its `PERSONAL_ACCESS_TOKEN` Actions secret installed → downstream CI workflows (oam-sync-trigger, deployment-update) can't authenticate.

## Root cause

`crossplane/app-container-claim-composition.yaml` L637 sets `image: alpine/git:2.43.0` which is git-only — no curl, no jq, no python3. The script then calls `curl ... /actions/secrets/public-key`, pipes to `jq -r '.key'`, and finally installs python3 mid-script with `apk add --no-cache python3 py3-pip` (L481) for the encryption step.

The source-setup Job at L140 does `apk add --no-cache git curl jq python3 py3-pip` up-front — that's why source-setup works. gitops-setup just never added this line.

## Fix shape

Add `apk add --no-cache curl jq >/dev/null` at the top of the gitops-setup script (after `set -e`, before any other command). Matches the source-setup pattern.

```sh
set -e
apk add --no-cache curl jq >/dev/null
echo "Setting up GitOps repository structure for $APP_NAME..."
```

The mid-script `apk add --no-cache python3 py3-pip` at L481 can stay where it is (it's gated by `if PUBLIC_KEY && KEY_ID` so won't always run).

## Verification

1. Apply updated composition.
2. Delete `<name>-gitops-setup` Job → Crossplane re-fires Object → new pod runs with curl present.
3. Pod should reach `✅ GitOps repository secrets created successfully` line.
4. Confirm secret on GitHub: `curl -H "Authorization: token $PAT" https://api.github.com/repos/shlapolosa/<name>-gitops/actions/secrets` should list `PERSONAL_ACCESS_TOKEN`.

## Blast radius

**MEDIUM.** Has been silently broken for every microservice creation. The lack of `PERSONAL_ACCESS_TOKEN` secret on the gitops repo means deployment-update CI workflows must rely on workflow-runner default `GITHUB_TOKEN`, which doesn't have cross-repo write. Most teams probably haven't noticed because the source-repo CI handles deploys via repository_dispatch.

## Related

- S-CP-001 — idempotency fix (PR #9) made this signal *visible*; under the old non-idempotent script the BackoffLimitExceeded happened earlier (at the empty commit) and masked this.
- S-CP-003 (candidate, not confirmed) — heredoc parsing in sh appeared to misbehave in the live trace, but the gitops repo's `application.yaml` exists with correct content from prior runs, meaning either the heredoc *does* parse OR another Job (microservice-creator) writes that file. Defer until empirical evidence of a missing file shows up.
