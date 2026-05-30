# S-CP-007 — register-argocd Object stuck in CannotUpdateExternalResource loop

**Class:** S-CP (Crossplane managed-resource)
**Consumer impact:** LOW — every microservice request leaves a Crossplane Object permanently Ready=False (looks like the Job "Running" but no pod active). Continuous reconcile-loop warnings every ~2-3 min.
**Discovered:** 2026-05-30 (py-demo-svc-v2 E2E test)

## What it looks like

```
$ kubectl get job py-demo-svc-v2-register-argocd
NAME                              STATUS    COMPLETIONS   DURATION   AGE
py-demo-svc-v2-register-argocd    Running   0/1           11m        11m

$ kubectl get events --field-selector involvedObject.name=py-demo-svc-v2-register-argocd
LAST SEEN  TYPE      REASON                         MESSAGE
13m        Normal    CreatedExternalResource        Successfully requested creation of external resource
2m55s      Warning   CannotUpdateExternalResource   cannot apply object: cannot patch object:
                                                    Job.batch "py-demo-svc-v2-register-argocd" is invalid:
                                                    spec.template: Invalid value: ...
```

Job appears "Running" with 0 active pods, 0/1 completions. The Crossplane Object's CannotUpdateExternalResource warning fires every ~2-3 min, indefinitely.

## Root cause

`crossplane/application-claim-composition.yaml` L430 defines a Crossplane `Object` whose manifest is a `Job`. The Job's script has an early-exit branch (L464):

```sh
if [ "${VCLUSTER_NAME}" = "host" ] || [ -z "${VCLUSTER_NAME}" ]; then
  echo "🏠 Deploying to host cluster - skipping vCluster registration"
  exit 0
fi
```

For host deployments (the default), the pod runs `exit 0` in milliseconds. The Job's pod completes too quickly for Kubernetes' Job controller to set `.status.conditions[Complete]=True` before the pod is GC'd by `ttlSecondsAfterFinished: 600`. Job ends up in a limbo state with `succeeded: 0, active: 0, conditions: []`.

Crossplane's Object controller sees this incomplete status as "not Ready" → triggers reconcile → tries to patch the Job's spec.template → **Kubernetes rejects: `Job.spec.template` is immutable after creation** → CannotUpdateExternalResource → retry on next reconcile loop → forever.

## Fix

Set `spec.managementPolicies: ["Create", "Observe", "Delete"]` on the Object. Crossplane will create the Job once, observe its state, eventually delete it on composite teardown, but never try to patch it. Removes the immutability-error loop entirely.

Why not apply to other Job-based Objects (gitops-setup, source-setup, microservice-creator, etc.)? Empirically they work — their pods run longer (the scripts do real work), so Kubernetes' Job controller has time to write proper status conditions before pods are GC'd. Crossplane reads a definitive status (Succeeded/Failed) and never tries to patch. Only register-argocd's fast-early-exit path hits this race.

## Verification

Fresh `/microservice` request with `target-vcluster=host`:
- `kubectl get job <name>-register-argocd`: STATUS = Complete (not Running limbo)
- `kubectl get object.kubernetes.crossplane.io <name>-register-argocd -o jsonpath='{.status.conditions}'`: Ready=True
- `kubectl get events --field-selector involvedObject.name=<name>-register-argocd`: only Normal events, no recurring CannotUpdateExternalResource Warning

## Blast radius

**LOW** functionally — the Job did its work (the early-exit logic is correct for host deploys). High noise: every host-deployment microservice produces this orphan Object forever, contributing to ArgoCD/Crossplane status pollution. Compounds on busy platforms.

## Why I assessed this LOW not HIGH

Same gate as S-CP-004/S-CP-006: no consumer depends on `register-argocd` Object's Ready status for host deployments. The Object is empirically inert (its workload didn't run because vCluster registration isn't needed for host). Fix is one line, worth shipping.

## Related

- Same PR as S-CP-004 + S-CP-006.
- Other Job-Object pairs in the same composition use the default `managementPolicies: ["*"]` and work fine — only this one hits the race. Don't blanket-apply the fix.
