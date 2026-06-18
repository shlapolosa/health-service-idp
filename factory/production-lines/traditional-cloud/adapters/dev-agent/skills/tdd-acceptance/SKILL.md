---
name: tdd-acceptance
description: Use when the dev-agent implements a service from its REQUIREMENTS.md structured acceptance block — drives Superpowers TDD (red→green→refactor) against each criterion and the platform's coverage gate. Invoke for every service that has a ```acceptance block.
license: MIT
allowed-tools:
  - read
  - write
  - bash
metadata:
  version: "1.0"
---

# tdd-acceptance — implement a service from its acceptance block

Wraps the **test-driven-development** skill (RED→GREEN→REFACTOR, Iron Law: *no production code
without a failing test first*) and **verification-before-completion** (*evidence before claims*),
and binds them to this platform's structured acceptance contract
(`factory/docs/contracts/requirements-acceptance-block.md`).

> Honour the test-driven-development skill in full. This skill only adds *which* tests to write
> (the acceptance criteria) and *how* the work is gated (the coverage checker). **ACT — persist edits
> to disk immediately; do not narrate.**

## Inputs (the entrypoint passes these)
- `SVC` — the service name (`microservices/<SVC>/`).
- `REQUIREMENTS.md` — contains a ` ```acceptance ` block for `SVC`.
- Helper scripts on PATH: `parse_acceptance.py`, `check_acceptance.py`.

## Procedure
1. **Read the contract.** Run:
   `parse_acceptance.py REQUIREMENTS.md --service "$SVC"`
   → JSON `criteria[]`. Each has `id`, `kind` (test|config|accepted-gap), `given/when/then`.
   Only `kind: test` criteria become tests. (`config`/`accepted-gap` are recorded, not coded.)

2. **RED — one failing test per `kind: test` id.** Under `microservices/$SVC/tests/`, write a pytest
   `test_<id>_*` (id `-`→`_`, e.g. `ing-2` → `test_ing_2_rejects_missing_sensor_id`) asserting the
   criterion's `then` given its `given`/`when`. **Write NO implementation yet.** Run pytest and
   **watch it fail** — if it passes on first write, the test is wrong (Iron Law). One id ↔ exactly one
   test; never delete/skip/`xfail`/weaken a generated test (anti-gaming).

3. **GREEN — minimal implementation.** Edit only `microservices/$SVC/src/handlers.py` (or, for a rasa
   service, its variant files). Write the least code to make all tests pass. Run pytest → all green.

4. **REFACTOR — stay green.** Apply DI / GoF / Onion cleanups (per the repo CLAUDE.md) without changing
   any test outcome.

5. **VERIFY (gate).** Run pytest **from inside the service dir** (so `src/handlers.py` imports resolve
   the same way the platform gate runs them — running from the repo root will break the import):
   `cd microservices/$SVC && PYTHONPATH="$PWD:$PWD/src" pytest tests/ --junitxml=/tmp/$SVC.xml -q`
   `check_acceptance.py <REQUIREMENTS-path> --service "$SVC" --junit /tmp/$SVC.xml`
   (use the absolute REQUIREMENTS path the entrypoint gave you, since you changed directory).
   It must report **COVERED** (every `kind: test` id → a passing `test_<id>_*`). If not, return to RED
   for the uncovered ids. (verification-before-completion: no completion claim without this evidence.)

## Edit surface (hard limits)
- Touch ONLY `microservices/$SVC/src/**` and `microservices/$SVC/tests/**`.
- Never write secrets/tokens. Never edit anything outside `microservices/`.
- The deterministic `TRACEABILITY.md` + the push + the post-deploy contract test are produced by the
  entrypoint, not by you — your job ends when `check_acceptance` is COVERED.
