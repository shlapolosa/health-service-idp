# Traceability Matrix — Requirements → OAM (manual replay, layer by layer)

> A 1-by-1 replay of the pipeline, checking forward (nothing dropped) and backward (no orphans) at each
> transition. The unit is the **source service-slice** (the way the 114 BRs / 139 rules actually cluster
> in the doc); each maps to a requirement r1–r15 and a capability cap1–cap12. Status legend:
> ✓ traced to an OAM component · ◑ consolidated into another component (covered, by design) ·
> ❌ broken (no OAM realization).

## The spine (source SVC → capability → app component → OAM component)

| # | Source slice | Req | Cap | Business fn | App component | OAM component | Status |
|---|---|---|---|---|---|---|---|
| 1 | COHORT (segments) | r1 | cap1 | Cohort Planning | ac_cohort | **—** | ❌ dropped at OAM |
| 2 | CHAL (challenge) | r2 | cap2 | Challenge Lifecycle | ac_challenge | challenge-svc | ✓ |
| 3 | ENROL / eligibility | r1/r3 | cap1/4 | Eligibility Evaluation | ac_enrol | enrolment-eligibility | ✓ |
| 4 | SCORE | r4 | cap3 | Wellness Scoring | ac_scoring | scoring-svc | ✓ |
| 5 | GOAL | r4 | cap3 | (goal engine) | ac_scoring | scoring-svc | ◑ consolidated → Scoring & Recognition |
| 6 | STREAK | r4 | cap3 | (streak engine) | ac_scoring | scoring-svc | ◑ consolidated |
| 7 | TITLE (progression) | r15 | cap3 | Recognition tiers | ac_scoring | scoring-svc | ◑ consolidated (verify r15 is implemented) |
| 8 | BADGE | r4 | cap3 | (badges) | ac_scoring | scoring-svc | ◑ consolidated |
| 9 | ACTV (verification) | r3 | cap4 | Activity Verification | ac_verify | **—** | ❌ dropped at OAM (inv #3, o7) |
| 10 | CLIN (clinical/Malaffi) | r3 | cap4 | (clinical eligibility) | ac_malaffi (ext) | **—** | ❌ external never componentised (c9) |
| 11 | WALLET | r5 | cap5 | Reward Points & Wallet | ac_wallet | wallet-svc | ✓ |
| 12 | MARKET | r6 | cap6 | Marketplace & Redemption | ac_market | marketplace-svc | ✓ |
| 13 | PARTNER/SETTLE | r7 | cap7 | Partner Lifecycle & Settlement | ac_partner | partner-settlement-svc | ✓ |
| 14 | NUDGE | r8 | cap8 | Engagement & Nudging | ac_engage | engagement-svc | ✓ |
| 15 | CONS (consent) | r9/r14 | cap9 | Consent & Identity | ac_consent | consent-svc | ✓ (PDPL-rights r14 = logic) |
| 16 | ID (identity) | r9 | cap9 | Consent & Identity | (consent) | wellness-identity | ✓ |
| 17 | FRAUD | r12 | cap10 | Fraud & Integrity | ac_fraud | fraud-svc | ✓ |
| 18 | EVENT | r10 | cap11 | Integration & Interoperability | ac_event | event-spine | ✓ |
| 19 | DATA | r11 | cap12 | Analytics & Insight | ac_analytics | analytics | ✓ |
| 20 | REPORT (exports) | r11 | cap12 | (reporting/exports) | ac_analytics | analytics | ◑ consolidated → Analytics & Reporting (exports endpoint TBD) |
| — | AML / Stored-Value | r13 | cap5/10 | — | (none) | (none) | ❌ no component (cross-cutting control) |

## Per-transition verdict (the 1-by-1 replay)
1. **Source doc → Extraction.** ✓ PASS. 114 BR + 139 RULE, stable IDs, source-line provenance, ArchiMate
   tags; 8 invariants cite specific RULE IDs.
2. **Extraction → Motivation/Strategy.** ✓ PASS (now documented). The 20 slices abstract cleanly into
   r1–r15 + c1–c10; every requirement traces to a course-of-action and capability (coa1–coa8 ↔ cap1–cap12).
   *Caveat: this BR→requirement abstraction had no written map before — this matrix is it.*
3. **Strategy → Business (capabilities → services/functions).** ✓ PASS. 12 caps → 27 services → 30
   functions, each capability realized by ≥1 service.
4. **Business → Application.** ✓ PASS **with deliberate consolidations**: GOAL/STREAK/TITLE/BADGE/SCORE →
   `Scoring & Recognition` (cap3); REPORT → `Analytics & Reporting` (cap12). These are *covered, merged by
   design* — not drops. 13 app components realize the 13 business functions (8/8 member-journey verified).
5. **Application → OAM.**  ❌ **BREAK HERE.** Of 13 internal app components, **11 map to OAM components;
   `ac_cohort` and `ac_verify` have no OAM component**, and the external `ac_malaffi` (clinical
   integration) was never componentised. These are *silent drops*, not consolidations.
6. **OAM → Coverage (requirements).** r1 (cohort) and r3 (verify+clinical) **not met**; r13 (AML) has no
   component; r14 (PDPL rights), r15 (Title) covered only as service-internal logic.

## Where traceability actually broke (localised)
- **Transition #5 (Application → OAM)** is the single failure point. Everything upstream of it traces
  cleanly; the consolidations at #4 are documented and covered.
- **3 silent drops:** `cohort-svc` (cap1/r1/o1), `verification-svc` (cap4/r3/o7/**inv #3**),
  `malaffi-adapter` (clinical/c9). Verification is the most serious — it's a load-bearing invariant.
- **1 cross-cutting control never placed:** AML / Stored-Value (r13/coa8).
- **2 consolidations to confirm in code (not gaps):** Title & Progression (r15) inside scoring-svc;
  report/export endpoints inside analytics.

## Fix (closes transition #5)
Add to `wellness-platform-oam.yaml`:
```yaml
- { name: cohort-svc,       type: webservice, properties: { language: python, framework: fastapi, repository: wellness-platform, database: engine-db, realtime: event-spine } }
- { name: verification-svc, type: webservice, properties: { language: python, framework: fastapi, repository: wellness-platform, realtime: event-spine } }
- { name: malaffi-adapter,  type: webservice, properties: { language: python, framework: fastapi, repository: wellness-platform, identity: wellness-identity } }
```
And carry **r13 (AML), r14 (PDPL rights), r15 (Title), inv #2/#4/#7/#8** into the services' `REQUIREMENTS.md`
as acceptance criteria — they are behaviour/control obligations the OAM cannot express.

## Method lesson
The break was invisible at the high-level capability view (cap1/cap4 *looked* present via enrolment-eligibility/fraud) and only surfaced when traced at **slice granularity through transition #5**. A
continuous matrix at this granularity, re-run when the OAM is authored, would have caught all three drops
the moment they happened.


---
## TRANSITION #5 — now CLOSED
`cohort-svc` (local), `verification-svc`, `malaffi-adapter` added to the OAM (20 components). The
Application→OAM break is resolved; the recognition/report consolidations at #4 were already covered.
Corrected terminology folded through every layer (master journey, app eligibility view, solution C4,
data-ownership 07, and the motivation/capability/process generators).
