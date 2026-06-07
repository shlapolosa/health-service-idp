# ADR: UNIFY-1 — Restore the monorepo-per-OAM AppContainer pattern (#153)

- Status: Accepted
- Date: 2026-06-07
- Supersedes (behaviourally): per-component AppContainerClaim fan-out introduced by
  the `auto-scaffold-bootstrap` trait + the day-0 claim being named after the first
  component.

## Context

The original design intent (visible in the AppContainerClaim composition's own
scaffold README text — "microservices container", `ApplicationClaim.spec.appContainer`,
the `detect-changes` CI that builds changed `microservices/*` subdirs — and in
CLAUDE.md TODO #1 "Default Unified Repository Pattern", HIGH PRIORITY) was:

> ONE repo per OAM Application, with `microservices/<name>/` per service.

The system had drifted to the opposite. One OAM with N webservice components produced:

- N `AppContainerClaim`s → N source repos + N gitops repos + ~4N ArgoCD Applications,
- each per-service gitops repo seeded a **phantom** single-component OAM Application
  from the composition's *blank template* (because `OAM_APPLICATION_B64` seeding was
  not the only writer of `oam/applications/application.yaml`).

### Evidence (patient4)

Observed on `patient4`: **6 repos, 12 ArgoCD apps, 3 OAM apps** — of which **2 were
phantoms** with the wrong bindings — and a **stuck `workflowFailed`**. The phantom
OAMs came from the blank single-component template overwriting/seeding alongside the
real consumer OAM; the repo/app fan-out came from one claim per component.

## Decision

The tenancy unit is the **OAM Application**. One OAM → one AppContainerClaim → one
source repo + one gitops repo + one ArgoCD Application. Each webservice component is
scaffolded into `microservices/<name>/` of the **shared** repo.

Concretely:

1. **XRD** (`app-container-claim-xrd.yaml`): added optional `spec.services[]`
   (`{name, language[python|java|rasa|nodejs], framework?}`). Top-level
   `language`/`framework` retained for single-service backward compat.
2. **Composition** (`app-container-claim-composition.yaml`):
   - When `services[]` is present, the conditional-delivery step ranges over it and
     emits one `ApplicationClaim` per service, all with `appContainer == <claim name>`
     (the shared repo). `framework` is derived from `language` when unset
     (python→fastapi, java→springboot, rasa→chatbot, nodejs→graphql-gateway).
   - Source/gitops repos and the ArgoCD Application remain **singular**.
   - `gitops-repo-setup` now **never writes the blank single-component template when
     `oamApplication` is set** — it (re)seeds the consumer OAM verbatim. This kills
     the phantoms.
   - Claims **without** `services[]` behave exactly as before.
3. **app.submit** (`submit_use_case.py`): derives `services[]` from the OAM's
   webservice components and sets it on the single AppContainerClaim, named after the
   OAM. The shared repo is `<app>-gitops`. On the **update** path it reconciles —
   patching the existing claim to add any webservice component missing from
   `services[]`, so adding a component to an existing OAM scaffolds its folder with
   **no trait needed**. `SubmitResult` shape and tool signatures are unchanged.
4. **`auto-scaffold-bootstrap` trait**: marked DEPRECATED in its description
   (still functional for backward compat; not deleted).

### Concurrency (the new main race)

In the new world N `mscv` Jobs clone and push to the **same** shared repo concurrently
(the legacy per-service-repo world had no contention; one claim ⇒ one repo). The
`mscv` script previously did a single `git pull --rebase || true` then a bare
`git push` — non-atomic: a sibling Job can land a commit between the rebase and the
push, making the push a non-fast-forward (rejected, Job fails).

Fix (in `application-claim-composition.yaml` mscv script): a bounded push-retry loop —
on rejection, `git fetch` + `git pull --rebase` onto the new remote HEAD and push
again (10 attempts, jittered sleep). Because each Job's commit only touches
`microservices/$SERVICE_NAME/`, rebases against sibling services are conflict-free.
The commit is also made idempotent (skip if no staged diff) for Crossplane Object
retries. The pre-existing wait-for-CI-workflow-file loop still makes sense unchanged —
it just waits for the file to appear in the remote regardless of which Job pushed it.

## Image naming alignment

`comprehensive-gitops` builds each `microservices/<svc>/` (those with a `Dockerfile`)
as `<registry>/<svc>:<tag>`, where `<svc>` is the subdir name. The webservice CD's
default image is `<component-name>:latest`. Since OAM component name == microservices
subdir name == image name, the build output and the CD default line up with no change.

## Trade-offs

- **Tenancy unit = OAM.** All services in one OAM share one repo pair, one ArgoCD app,
  and one CI pipeline. This is the explicit goal (developer-experience, fewer moving
  parts) and matches the `detect-changes` CI that already builds changed subdirs.
- **Per-service external delivery.** A team that genuinely needs an isolated repo /
  ArgoCD app for a single service should model it as its **own OAM** (its own
  AppContainerClaim), rather than relying on per-component fan-out within one OAM.
- **Backing services (database/cache)** are claim-level knobs shared across the
  monorepo (resolved from the first scaffold component), as before.

## Migration

Purely additive. Existing single-service `AppContainerClaim`s (no `services[]`) keep
working unchanged — the composition falls back to the original single-claim path.
The deprecated `auto-scaffold-bootstrap` trait still renders for any OAM that still
attaches it. New OAMs go through `app.submit`, which produces the monorepo layout.
Legacy per-service claims created before this change are not rewritten; they continue
to reconcile their existing repos.
