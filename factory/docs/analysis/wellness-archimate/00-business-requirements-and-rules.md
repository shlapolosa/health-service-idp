# Wellness Platform — Business Requirements & Rules Catalogue

> **Source:** `wellness_platform_architecture_consolidated (1).docx` (~15,800 words, 8 parts)
> **Purpose:** Ground-up ArchiMate analysis — **Step 1: extract all business requirements and rules.**
> This catalogue is the Motivation- and Business-layer input. Subsequent steps map these onto
> ArchiMate Business / Application / Technology layers and derive the platform-native OAM shape.

## Method

Four parallel passes over the document, each tagging every extracted item with a proposed
ArchiMate element type and source-line traceability. **Business Requirements (BR-*)** = capabilities
/ services / functions the business needs. **Business Rules (RULE-*)** = constraints, policies,
invariants, eligibility gates, scoring/earning formulas, state-transition and versioning rules.

| Slice | Coverage | BRs | RULEs | File |
|---|---|---|---|---|
| Part 1 | Exec summary · Part 0 BPMN (Phases A–D, OLAP/OLTP seam) · Part 1 ABBs: CHAL, SCORE, TITLE, WALLET, MARKET, NUDGE, CONS | 32 | 43 | [partials/part-1.md](partials/part-1.md) |
| Part 2 | Part 1 ABBs: GOAL, STREAK, BADGE, ACTV, CLIN, ID, FRAUD, EVENT, DATA, REPORT | 28 | 26 | [partials/part-2.md](partials/part-2.md) |
| Part 3 | Part 2 screens/journeys · Part 3 cross-cutting · Part 5 partner lifecycle BPMN · Part 6 UAE partners · Part 7 value-path start | 31 | 35 | [partials/part-3.md](partials/part-3.md) |
| Part 4 | Part 7 adapters/NFR/redemption · Part 8 gamification scoring engine | 23 | 35 | [partials/part-4.md](partials/part-4.md) |
| **Total** | | **114** | **139** | |

## ArchiMate element-type legend

Each item carries a proposed mapping to guide Step 2 modelling:

- **Business Service** — externally visible behaviour offered to a consumer (member, partner, DoH).
- **Business Process / Function / Interaction** — internal behaviour realising a service.
- **Business Event** — a state change that triggers behaviour (e.g. `activity.verified`, `challenge.withdrawn`).
- **Business Object** — an informational concept (Challenge, Segment, ScoringPlan, WalletLedger, Redemption, Voucher).
- **Business Rule** — modelled in the Motivation layer as a **Constraint** (or Driver/Assessment) shaping the above.
- **Business Role / Actor** — Member, Partner, Department of Health, Fraud analyst, CMS author.

## The load-bearing invariants (cross-slice synthesis)

These eight rules constrain the whole architecture; everything else hangs off them.

1. **OLAP/OLTP seam** — OLTP serves enrolment/earning reads from *published artifacts* in <50 ms; the
   warehouse is **never** the source of truth for state or money (RULE-003/004).
2. **Frozen-on-publish** — a Challenge freezes its `{segmentId, segmentVersion}` binding AND its
   `ScoringPlan` (every primitive pinned `strategy@version + params`) on PUBLISH, so eligibility and
   scoring are exactly replayable months later — mandatory because it sits on a money-crediting path
   (RULE-002/005, RULE-328/323).
3. **Verified-signal gate** — only validated, normalised activity becomes `activity.verified`; goals,
   streaks and scores advance **only** on that signal. ACTV-SVC is the trust gate of the scoring chain (RULE-110/103).
4. **Financial-grade Wallet** — append-only, double-entry, strongly consistent ledger with two-phase
   reservation and idempotent credits; this cascades into Marketplace integrity (RULE-025).
5. **Inline fraud guard** — Wallet/Marketplace must call synchronous `GET /fraud/check/{user}` before any
   value transfer; FRAUD-SVC is a mandatory inline guard on the money path, not just async (RULE-121).
6. **Versioned event spine** — all async flows over versioned `EventSchema` on durable, ordered,
   partitioned, dead-lettered transport; EVENT-SVC is the single async backbone (RULE-122/123).
7. **Sahatna Points economy** — `SahatnaPoints(week) = WeeklyScore × 10`, credited at week close,
   cumulative and never reset; `WeeklyScore = min(100, Σ daily-goal + Σ balanced-day + streak bonus)` (RULE-318/319/321).
8. **Redemption & settlement discipline** — 300 s point reservation, 10 s partner-call timeout, 3 retries
   then release+notify+log; 5% settlement holdback released after a 30-day dispute window; ledger-vs-redemption
   discrepancy >0.1% flagged (RULE-210/211/212, RULE-214/215). Withdrawal is irreversible: score/streak voided,
   no credit, `challenge.withdrawn{reason}` emitted; winners/prizes are an off-platform DoH trust-boundary concern (RULE-332/333).

## Detailed catalogue

The full numbered tables (114 BRs, 139 RULEs) live in the four partial files linked above. Step 2
(ArchiMate layering) and Step 3 (OAM mapping) consume these IDs directly for traceability.
