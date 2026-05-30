# S-CP-004 — pip3 install fails with PEP 668 externally-managed-environment

**Class:** S-CP (Crossplane managed-resource)
**Consumer impact:** LOW — leaves a permanently-Failed Job per microservice request. The PERSONAL_ACCESS_TOKEN secret it tries to install is unused by any generated workflow (verified: `deployment-update.yml`, `oam-sync-trigger.yml` only use `secrets.GITHUB_TOKEN`). Real cost is dashboard/alert noise that compounds on busy platforms.
**Discovered:** 2026-05-30

## What it looks like

After PR #10 added curl/jq to gitops-setup, the next failure surfaces:

```
+ apk add --no-cache python3 py3-pip
... (installs python 3.11.14-r0) ...
+ pip3 install pynacl
error: externally-managed-environment

× This environment is externally managed
╰─> The system-wide python installation should be maintained using the system
    package manager (apk) only.
note: See PEP 668 for the detailed specification.
```

Exit 1 → BackoffLimitExceeded. PUBLIC_KEY/KEY_ID retrieval succeeded; only the encryption-script setup is blocked.

## Root cause

Alpine 3.19+ ships python with a `EXTERNALLY-MANAGED` marker per PEP 668. Plain `pip3 install <pkg>` is rejected outside a venv. The composition was authored before Alpine adopted PEP 668.

Three sites in `crossplane/app-container-claim-composition.yaml`:
- L482 (source-setup, `pip3 install pynacl`)
- L1204 (gitops-setup, `pip3 install pynacl`)
- L1317 (different image — python:3.11-slim with apt — `pip install pynacl requests`)

## Fix

Add `--break-system-packages` flag. For the apt-based site, defensive form to support both old and new Python images.

## Verification

Live test of the updated gitops-setup script: pod reaches `✅ GitOps repository secrets created successfully` and exits 0. Job goes Complete instead of Failed.

## Why this isn't a no-op fix

When initially diagnosed (2026-05-30 morning) I assessed this as cosmetic because no consumer reads PERSONAL_ACCESS_TOKEN. That assessment is still true at the consumer level, BUT the per-request Failed Job is real operator-monitoring noise. On a busy platform this accumulates into dashboard pollution + false alerts. Fix per the consumer-impact gate (memory `feedback-consumer-impact-gate`) updated: include LOW-impact noise reductions when they're cheap one-line changes.

## Related

- S-CP-001 (PR #9) — idempotency. Necessary precursor.
- S-CP-002 (PR #10) — curl/jq. Necessary precursor (this signal was previously masked by curl missing).
- S-CP-006 — separate signal (OutOfSync app-of-apps) in same PR.
- S-CP-007 — separate signal (register-argocd Object reconcile loop) in same PR.
