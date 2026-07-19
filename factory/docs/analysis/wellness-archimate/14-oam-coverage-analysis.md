# OAM Solution vs Motivation/Strategy/Business — Coverage Analysis

> Does `wellness-platform-oam.yaml` realize all goals/outcomes/requirements, and align with every
> course of action? Verdict: **mostly yes for the realizable parts, but 3 real component gaps + a class
> of invariants the OAM cannot enforce.** An OAM provisions the *runtime substrate*; deterministic /
> version-pinned / compliance behaviour lives in the service code + config, not in OAM bindings.

## 1. Capability coverage (12 strategy/business capabilities → OAM)
| Capability | OAM component | Status |
|---|---|---|
| cap1 Cohort Identification & Segmentation | — | **GAP** (no cohort/segmentation service) |
| cap2 Challenge Lifecycle | challenge-svc | ✅ |
| cap3 Wellness Scoring & Recognition | scoring-svc | ✅ (recognition/Title tier r15 = app logic) |
| cap4 Activity & Clinical Verification | — | **GAP** (no verification service) |
| cap5 Reward Points & Wallet | wallet-svc + wallet-db | ✅ |
| cap6 Marketplace & Redemption | marketplace-svc + market-db | ✅ |
| cap7 Partner Lifecycle & Settlement | partner-settlement-svc | ✅ |
| cap8 Engagement & Nudging | engagement-svc | ✅ |
| cap9 Consent, Identity & Compliance | consent-svc + wellness-identity | ◑ (consent ✅; residency/retention/ADHICS not expressed) |
| cap10 Fraud & Integrity | fraud-svc | ✅ |
| cap11 Event Streaming & Integration | event-spine | ✅ |
| cap12 Data, Analytics & Reporting | analytics | ✅ |

→ **10/12 covered; cap1 and cap4 have no component.**

## 2. The 3 concrete component GAPS (architecture has them; OAM doesn't)
1. **Cohort & Segmentation service** — the architecture's `Cohort & Segmentation` (builds & version-pins
   segments). Without it, **o1 "cohorts identified & version-pinned"** and the local-membership branch of
   eligibility have no home. *Add:* a `webservice` (e.g. `cohort-svc`, db: engine-db, realtime: event-spine).
2. **Verification service** — the `verified-signal gate` (**invariant #3**, **o7 "only verified activity
   scores"**, **r3**). fraud-svc ≠ verification. This is load-bearing: scoring must only run on
   `activity.verified`. *Add:* a `webservice` (`verification-svc`, realtime: event-spine).
3. **Malaffi / HIE clinical integration** — clinical membership/eligibility is a black-box external
   (special-category clinical data, **c9**). No component/binding represents the HIE adapter. *Add:* an
   adapter `webservice` (+ external endpoint secret) that enrolment-eligibility calls; or a
   `webhook-platform` for the inbound clinical callbacks.

Plus a softer one: **AML / Stored-Value controls (r13, coa8)** have no dedicated component — wallet-svc
holds points but the AML/KYC program isn't a distinct control.

## 3. Courses of action — alignment
| Course of action | Aligned? |
|---|---|
| coa1 OLAP/OLTP seam (CDC + reverse-ETL) | ✅ analytics-platform + postgres; *note OAM uses `ingestion.mode: gateway`, not CDC* |
| coa2 Event-driven ABB decomposition on a versioned spine | ✅ event-spine (schema registry) + services |
| coa3 Versioned strategy-registry scoring engine | ◑ scoring-svc exists; **version-pinned registry / replayability (g3, o9, inv #2) not expressed in OAM** |
| coa4 Two-phase reservation + double-entry ledger | ✅ component present (ledger discipline = app logic) |
| coa5 Aggregator-first UAE partner sourcing | ◑ partner-settlement + marketplace; **no external provider adapter / partner-callback component** |
| coa6 Inline fraud guard + idempotency | ✅ fraud-svc (synchronous gate) |
| coa7 Privacy-by-design & consent (PDPL/ADHICS) | ◑ consent + identity ✅; **residency (c10), retention 7y/mask 2y (c5), ADHICS, PDPL rights (r14) not expressed** |
| coa8 Points as regulated stored value (AML/KYC) | ◑ wallet + fraud; **no AML/SVF control (r13)** |

→ **5 fully aligned, 3 partial** (coa3, coa5, coa7, coa8 — all because the OAM provisions the runtime but
not the controls/logic those courses of action demand).

## 4. Invariants the OAM **cannot** enforce (deferred to implementation + config)
These are not OAM gaps per se — an OAM declares *what runs*, not *how it behaves*:
- **inv #2 Frozen-on-publish & replayable** (g3, o9, c1) — version-pinning, frozen `{segmentId,
  segmentVersion}+ScoringPlan`, event replay → **service logic + a strategy registry**, not a binding.
- **inv #4 Financial-grade wallet** (two-phase, double-entry, idempotent) → wallet-svc internals.
- **inv #7 Points economy** (Points = WeeklyScore×10, cap 100, never reset) → scoring/wallet logic.
- **inv #8 Redemption/settlement discipline** (300s reservation, 10s/3-retry, 5% holdback, 30-day
  dispute, 0.1% discrepancy, irreversible withdrawal) → app logic + config.
- **Compliance config** (retention/masking/residency, AML thresholds) → policy + secrets, not bindings.
- **o2 eligibility <50ms** → a performance requirement the platform enables (OLTP postgres) but doesn't
  guarantee.

## 5. Verdict
- **Could the OAM solve all goals/outcomes/requirements?** Not as written. It covers **10/12 capabilities
  and most outcomes**, but is **missing Cohort/Segmentation, Verification, and the Malaffi clinical
  integration** — and Verification (o7/inv #3) is load-bearing, so o1, o7 (and partially g3) are **not met**.
- **Is it inline with all courses of action?** **5/8 fully**, 3 partial — and those partials reflect a
  structural truth: **coa3/coa5/coa7/coa8 demand controls & invariants (versioning, AML, residency,
  retention, replay) that an OAM does not express.** Those land on the **service implementations and
  platform policy**, i.e. the dev-agent + ops, not the deployment manifest.

## 6. To close the gaps — minimal OAM additions
```yaml
- { name: cohort-svc,       type: webservice, properties: { language: python, framework: fastapi,
    repository: wellness-platform, database: engine-db, realtime: event-spine } }
- { name: verification-svc, type: webservice, properties: { language: python, framework: fastapi,
    repository: wellness-platform, realtime: event-spine } }                 # the verified-signal gate
- { name: malaffi-adapter,  type: webservice, properties: { language: python, framework: fastapi,
    repository: wellness-platform, identity: wellness-identity } }           # HIE clinical eligibility
```
The remaining items (AML controls, version registry, retention/residency, ledger discipline) are
**implementation + config obligations** to encode in the services and the platform's policy/secrets —
they belong in the dev-agent's brief, which this whole exercise was building toward.


---
## RESOLVED (terminology + traceability pass, 18-...)
The 3 component gaps are now CLOSED in `wellness-platform-oam.yaml` (now **20 components**): **`cohort-svc`**
(LOCAL demographic/telemetry segmentation — clinical segmentation is external), **`verification-svc`**
(the verified-signal gate, inv-3), **`malaffi-adapter`** (the two Malaffi APIs: segment-metadata for
authoring + scoped membership-query for eligibility). cap1/cap4, o1/o7, r1/r3 now trace to a component.
The **logic/config invariants** (inv-2/4/7/8, AML r13, retention/residency) remain implementation +
config obligations — carried in each service's `REQUIREMENTS.md`, not the OAM.
