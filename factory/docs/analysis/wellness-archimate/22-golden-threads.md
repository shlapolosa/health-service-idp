# Golden-Thread Traceability Backbone — Wellness Platform

> **Deliverables:** `traceability.yaml` (the machine-checkable model) ·
> `check_traceability.py` (the per-transition sanity check) · this document (the readable matrix).
> **Re-run:** `python3 check_traceability.py` (from this directory).

## The golden-thread principle

A *golden thread* is an unbroken chain of realization links from the **why** (a goal/outcome) down to
the **what-runs** (a deployable OAM component) — and back. We model the full chain:

```
goal → outcome → requirement → course_of_action → capability → process
     → app_component → sbb (ComponentDefinition type) → solution_component → oam_component
```

The thread is *sanity-checked at every transition*, in both directions:

- **Forward coverage** — every upstream element realizes **≥1** downstream element, *or* it is a
  declared **accepted gap**. A missing forward link is a **silent drop** (the failure mode `16-…`
  found at Application→OAM: `ac_cohort`/`ac_verify`/`ac_malaffi` were dropped).
- **Backward coverage** — every downstream element is realized **from** the upstream layer. A
  missing backward link is an **orphan** (an unjustified solution element with no architectural
  pedigree).

**Accepted gaps are declared, not silent.** Some motivation elements intentionally have *no*
downstream deployable — they are behaviour/control/compliance obligations the OAM cannot express
(AML controls, PDPL-rights logic). Declaring them lets the checker treat them as *expected* so they
never masquerade as a clean thread, and never hide a real break.

Element IDs in the model are the **real IDs** from the source artifacts (`03` motivation/strategy,
`05` capability realization, `06` process cooperation, `08`/`09` application layer, `11` technology
ABB→SBB, `12`+`c4-data.json` solution C4, `13`+`wellness-platform-oam.yaml` the deployable, with the
seed mappings reused from `14`/`16`). Where the motivation view under-enumerates a layer (the 9
member-facing Outcomes don't back the platform/governance Requirements), stable IDs `o10`–`o15` were
minted and annotated with their source goal — see *Open breaks closed* below.

---

## Representative end-to-end golden threads

Ten threads spanning eligibility, earn, redeem, settle, consent, integration, analytics, fraud — and
the three previously-broken threads (cohort / verification / malaffi) now closed. Each row is a full
walk of the chain; the trailing column is the invariant the thread carries into `REQUIREMENTS.md`.

| # | goal | outcome | requirement | coa | capability | process | app | SBB | solution | OAM | invariant |
|---|------|---------|-------------|-----|------------|---------|-----|-----|----------|-----|-----------|
| 1 Eligibility | g1 | o1 | r1 | coa1 | cap1 | c_enrol | ac_enrol | webservice/postgresql | en_enrol/en_eligorch | enrolment-eligibility | — (o2 <50ms perf) |
| 2 Cohort *(was broken)* | g1 | o1 | r1 | coa2 | cap1 | c_cohort | ac_cohort | webservice | en_cohort | **cohort-svc** | inv-2 (frozen/replay) |
| 3 Verification *(was broken)* | g6 | o7 | r3 | coa6 | cap4 | c_earn | ac_verify | webservice | en_verify | **verification-svc** | inv-1 (verified-signal gate) |
| 4 Clinical/Malaffi *(was broken)* | g6 | o7 | r3 | coa6 | cap4 | c_earn | ac_malaffi | webservice | en_maladapter | **malaffi-adapter** | inv-1 |
| 5 Earn/Score | g3 | o3 | r4 | coa3 | cap3 | c_earn | ac_scoring | webservice | en_score | scoring-svc | inv-2, inv-7 |
| 6 Redeem | g5 | o5 | r6 | coa4 | cap6 | c_reward | ac_market | webservice/postgresql | wm_market/ps_market | marketplace-svc | inv-8 (300s reservation) |
| 7 Settle | g5 | o6 | r7 | coa5 | cap7 | c_set | ac_partner | webservice | wm_partner | partner-settlement-svc | inv-8 (5% holdback) |
| 8 Wallet | g2 | o4 | r5 | coa4 | cap5 | c_earn | ac_wallet | webservice/postgresql | wm_wallet/ps_wallet | wallet-svc | inv-4 (double-entry) |
| 9 Consent | g6 | o11 | r9 | coa7 | cap9 | c_enrol | ac_consent | webservice/auth0-idp | pf_consent/pf_id | consent-svc / wellness-identity | — (r14 PDPL = logic) |
| 10 Fraud | g7 | o14 | r12 | coa6 | cap10 | c_earn | ac_fraud | webservice | wm_fraud | fraud-svc | inv-5 (inline guard) |

*(Threads 2/3/4 are the drops `16-traceability-matrix.md` localised at transition #5; they now resolve
to real OAM components — the Application→OAM break is closed.)*

---

## Per-transition coverage summary

Output of `python3 check_traceability.py` (verbatim). Every transition is clean forward **and**
backward; `up N`/`down N` are the element counts per layer.

```
transition                          up N  down N  fwd-orphans  bwd-orphans
--------------------------------------------------------------------------
goal -> outcome                        8      15            -            -
outcome -> requirement                15      15            -            -
requirement -> course_of_action       15       8            -            -
course_of_action -> capability         8      12            -            -
capability -> process                 12      11            -            -
process -> app_component              11      14            -            -
app_component -> sbb                  14       7            -            -
sbb -> solution_component              7      21            -            -
solution_component -> oam_component    21      20            -            -

VERDICT: CLEAN — every transition has full forward+backward coverage;
         the only non-realized elements are the declared accepted_gaps.
```

> Note the fan-in/fan-out at `app_component → sbb` (14→7: the 7 SBB types are reused across 14
> components) and `sbb → solution_component` (7→21: each SBB type realizes several C4 components) —
> both legal, since the check only requires ≥1 realization per node in each direction.

---

## Accepted-gap register

The items the OAM *cannot* realize (declared in `traceability.yaml:accepted_gaps`), and where they
actually live. These are control/behaviour obligations, carried in the services' `REQUIREMENTS.md`
(the dev-agent's brief) and platform policy/secrets — **not** OAM bindings.

| Element | Layer | Why no downstream OAM realization | Lives in |
|---|---|---|---|
| **r13** AML / stored-value controls | requirement | A cross-cutting regulatory control (coa8), not a deployable component | `wallet-svc` + `fraud-svc` `REQUIREMENTS.md`; platform policy |
| **r14** PDPL data-subject rights | requirement | Service-internal logic on consent-svc, not an OAM binding | `consent-svc` `REQUIREMENTS.md` |

Related config-only obligations surfaced by `14-oam-coverage-analysis.md` (residency `c10`, retention
7y/mask 2y `c5`, ADHICS, version-pinned registry for `coa3`) ride the **invariant** side-links below
rather than the chain — an OAM declares *what runs*, not *how it behaves*.

### Invariants → REQUIREMENTS.md obligations (side-links)

| Invariant | Binds (app/oam) | Obligation carried into REQUIREMENTS.md |
|---|---|---|
| inv-1 Verified-signal gate | verification-svc, malaffi-adapter | Reject unverified activity/clinical signals before scoring (o7, r3) |
| inv-2 Frozen-on-publish & replayable | scoring-svc, cohort-svc | Version-pin `{segmentId,segmentVersion}+ScoringPlan`; event replay (g3, o9, c1) |
| inv-3 Warehouse-not-source-of-truth | analytics, event-spine | OLAP derived; OLTP postgres remains system of record (coa1) |
| inv-4 Financial-grade wallet | wallet-svc | Double-entry ledger, idempotent credits/debits (coa4) |
| inv-5 Inline fraud guard | fraud-svc | Synchronous fraud check on earn/redeem; idempotency keys (coa6, r12) |
| inv-6 Versioned event spine | event-spine | Schema-registered, versioned topics; backward-compatible evolution (coa2, r10) |
| inv-7 Points economy | scoring-svc, wallet-svc | Points = WeeklyScore×10, cap 100, never reset (o4) |
| inv-8 Redemption/settlement discipline | marketplace-svc, partner-settlement-svc, wallet-svc | 300s reservation, 10s/3-retry, 5% holdback, 30-day dispute, 0.1% discrepancy (coa4/coa5) |

---

## Open breaks to close

`check_traceability.py` exits **0** — there are **no unexpected breaks** beyond the two declared
accepted gaps (r13, r14). One genuine modelling break was found and closed during construction:

- **outcome → requirement (BACKWARD)** — the motivation view's 9 measurable Outcomes (`o1`–`o9`)
  concentrate on the member-facing flow and left 6 platform/governance Requirements
  (`r2`,`r9`,`r10`,`r11`,`r12`,`r15`) as orphans. The ArchiMate metamodel *permits* a Requirement to
  realize a Goal directly, but the strict golden-thread chain does not model that shortcut. Fixed by
  minting 6 operational/governance Outcomes (`o10`–`o15`), each annotated with its source Goal
  (`g3`/`g4`/`g6`/`g7`/`g8`) — restoring an unbroken `goal→outcome→requirement` chain. This is a
  faithful extension of the source, not a fabrication: those goals are explicitly the realization hubs
  for the corresponding requirement clusters in `03`/`14`.

The Application→OAM break that `16-traceability-matrix.md` localised at transition #5
(`ac_cohort`/`ac_verify`/`ac_malaffi` dropped) is **already closed** in `wellness-platform-oam.yaml`
(20 components) via `cohort-svc`/`verification-svc`/`malaffi-adapter`, and the model + checker confirm
it — those threads (rows 2/3/4 above) now run end-to-end.

---

## How to re-run

```bash
cd factory/docs/analysis/wellness-archimate
python3 check_traceability.py     # exit 0 = clean; exit 1 = unexpected break; exit 2 = bad model
```

The checker also validates **model integrity**: edges must reference known nodes and connect only
*adjacent* layers, and every invariant `binds:` must reference a real node. Edit `traceability.yaml`
(add a node, add the realization edge, or declare an `accepted_gap`) and re-run — this is the
re-runnable sanity check meant to fire the moment a future OAM edit drops or orphans an element.
