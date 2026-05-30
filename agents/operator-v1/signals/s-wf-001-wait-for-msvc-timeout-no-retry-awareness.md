# S-WF-001 — `wait-for-microservice-ready` times out without retry awareness

**Class:** S-WF (Argo Workflows step)
**Severity:** masks downstream issues — surfaces as `Failed` even when an Object retry would have eventually succeeded
**Discovered:** 2026-05-30 (user-service `microservice-creation-r2mlg`)

## What it looks like

Workflow `microservice-creation-<id>` polls `ApplicationClaim/<name>` Ready=True in 15s ticks. Logs show:

```
Checking ApplicationClaim status... (15s/600s)
Checking ApplicationClaim status... (30s/600s)
...
Checking ApplicationClaim status... (600s/600s)
Error (exit code 1)
```

Step `wait-for-microservice-ready` exits 1; whole workflow goes Failed. No detail about WHICH composition resource was blocking Ready=True.

## Root cause

The step is a flat poll loop. It does not:
1. Surface the ApplicationClaim's `.status.conditions[].reason/message` on timeout.
2. Differentiate "first apply still in progress" from "Object is retrying and will never settle".
3. Inspect downstream Jobs (e.g., gitops-setup) for `BackoffLimitExceeded`.

## Fix shape (definition-only)

Edit the WorkflowTemplate (find via `kubectl get workflowtemplate -A | grep microservice-standard-contract`; the wait-for-microservice-ready template lives in `argo-workflows/microservice-standard-contract.yaml` or similar in the gitops repo).

On timeout, emit a diagnostic block:

```sh
echo "=== TIMEOUT DIAGNOSTICS ==="
kubectl get applicationclaim "${APP_NAME}" -o jsonpath='{.status.conditions}' | jq
echo "=== Failed/Pending Jobs ==="
kubectl get jobs -l "app=${APP_NAME}" -o json | \
  jq -r '.items[] | select(.status.conditions[]?.type=="Failed" or .status.active>0) | "\(.metadata.name) — \(.status.conditions[0].message // "active")"'
echo "=== Crossplane Object events ==="
kubectl get events --field-selector "involvedObject.name=${APP_NAME}-gitops-setup" --sort-by=.lastTimestamp | tail -5
kubectl get events --field-selector "involvedObject.name=${APP_NAME}-source-setup" --sort-by=.lastTimestamp | tail -5
```

This converts a silent timeout into a triagable failure that the operator (or human) can act on in one read.

## Verification

Force a timeout in a test environment:
- Create an AppContainerClaim with an intentionally-broken composition Job.
- Run the workflow; confirm the timeout block prints failed Jobs + conditions.

## Blast radius

**MEDIUM.** Doesn't cause failures — but every failure here is currently opaque. Fixing this reduces operator MTTR on every S-CP-* incident.

## Related

- S-CP-001 — primary failure class this signal would have surfaced earlier.
