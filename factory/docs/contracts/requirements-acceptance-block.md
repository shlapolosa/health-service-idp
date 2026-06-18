# REQUIREMENTS.md — structured `acceptance` block (architect ↔ dev-agent contract)

`REQUIREMENTS.md` is **prose-first** (human-readable, authored by the architect). To make the load-bearing
invariants machine-enforceable, the architect appends **one fenced ` ```acceptance ` block per service**.
The dev-agent parses it, turns each `kind: test` criterion into a **gating test (TDD)**, and emits a
`TRACEABILITY.md` proving coverage. This is the same golden-thread discipline as `traceability.check`:
**no requirement is silently dropped.**

## Schema (YAML inside a fenced ` ```acceptance ` block)
~~~
```acceptance
service: <service-name>            # the microservices/<svc> this block governs
criteria:
  - id: ac-1                       # stable, unique within the service; -> test name test_ac_1_*
    statement: "credits and debits are idempotent"
    invariant: inv-4               # OPTIONAL ref to a load-bearing invariant (free-form)
    kind: test                     # test | config | accepted-gap   (see below)
    given: "the same credit request id applied twice"     # required for kind:test
    when:  "credit is invoked"                            # required for kind:test
    then:  "balance changes exactly once"                # required for kind:test
  - id: ac-2
    statement: "AML stored-value cap enforced"
    invariant: inv-4
    kind: accepted-gap
    reason: "platform AML policy (r13), not service-internal logic"   # required for accepted-gap
```
~~~

## `kind` semantics
- **`test`** — MUST become a gating pytest `test_<id>_*` under `microservices/<svc>/tests/`. The dev-agent
  writes it FAILING first (TDD red), then implements until GREEN. Requires `given`/`when`/`then`.
- **`config`** — a non-code obligation (env/secret/policy) recorded in `TRACEABILITY.md` but **not**
  pytest-gated. Requires `statement`.
- **`accepted-gap`** — a deferred obligation the OAM/service does not realize (carried elsewhere, e.g. a
  platform control). **Requires `reason`.** Declared so it is never a silent drop — exactly the
  `accepted_gaps` discipline from the golden-thread validator.

## Rules (enforced by `parse_acceptance.py` / `check_acceptance.py`)
1. `id` unique per service; `statement` + `kind` mandatory on every criterion.
2. `kind: test` ⇒ `given`/`when`/`then` present. `kind: accepted-gap` ⇒ `reason` present.
3. **Malformed block ⇒ hard fail** (the dev-agent Job aborts) — never silently fall back; a malformed
   block hides drift.
4. **Block fully absent ⇒ legacy path** (the dev-agent runs its v0.2.0 single-call behaviour; the
   free-form prose still drives implementation).
5. Coverage gate: every `kind: test` id has exactly one matching **passing** `test_<id>_*`; the model may
   not delete/skip/xfail/weaken a generated test (anti-gaming).

## Travel (unchanged from SPEC-1)
`REQUIREMENTS.md` reaches the dev-agent via the 3-location fallback: source-repo root →
`<app>-gitops` root → central ledger `health-service-idp-gitops/oam/applications/<app>-REQUIREMENTS.md`.
The architect authors it and passes it as the `requirements` arg to `app.submit`/`app.submit_wait`.

## Authoring (architect)
Author one criterion per **observable** invariant/acceptance the service must uphold; tag `invariant:`
where it maps to a named load-bearing invariant; declare deferred obligations as `accepted-gap` with a
`reason`. Do not invent an unobservable `then:`. Keep the prose sections; the block is additive.
