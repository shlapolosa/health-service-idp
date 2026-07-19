# Wellness Gamification Platform — Business Architecture Extraction (Part 4)

Source slice: `/tmp/wellness_doc.txt` lines 660–919. Covers Part 7 continued (event/message models, redemption sequence, partner adapter pattern, non-functional concerns, open decisions) and Part 8 (Gamification Value Path: scoring, recognition, aggregation, scoring engine, surveys, enrolment lifecycle, DoH boundary).

## Business Requirements

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| BR-301 | Schema-registry-backed event publication (EVENT-SVC) where every event carries event_id, event_type, event_time, producer, trace_id plus a typed payload. | 7.6 Event/message models | Business Service | 660 |
| BR-302 | Emit redemption lifecycle events (requested, reserved, fulfilled, failed, uncertain) across the redemption family. | 7.6 Redemption family | Business Event | 661–678 |
| BR-303 | Emit wallet lifecycle events (reserved, debited, released, divergence-detected) across the wallet family. | 7.6 Wallet family | Business Event | 679–692 |
| BR-304 | Emit voucher/catalogue events (voucher.issued, voucher.delivered, voucher.expired, catalog.item.activated, inventory.low). | 7.6 Voucher & catalogue | Business Event | 693–707 |
| BR-305 | Execute the end-to-end Phase-3 redemption sequence (happy, retry-exhausted, uncertain-timeout paths) with concrete partner API calls within the latency envelope. | 7.7 End-to-end redemption sequence | Business Process | 708–711 |
| BR-306 | Provide a Partner Adapter capability where the orchestrator speaks one canonical contract and each adapter translates bidirectionally to the partner's native API. | 7.8 Partner adapter pattern | Business Function | 712–713 |
| BR-307 | Each PartnerAdapter must implement list_products (scheduled catalogue sync), dispatch (synchronous fulfilment), inquire (status lookup for uncertain reconciliation), cancel (refund/wind-down), and optional handle_webhook. | 7.8 PartnerAdapter interface | Business Interface | 714–738 |
| BR-308 | YouGotaGift adapter fulfils redemptions via HTTP Basic auth POST /incentives-send/download/ returning the voucher code synchronously for storage and in-app/NUDGE delivery. | 7.8 YouGotaGift adapter | Business Service | 769–771 |
| BR-309 | Etisalat (e&) adapter fulfils redemptions via TMF622 productOrder (OAuth2 bearer) and syncs catalogue via TMF620 productOffering. | 7.8 Etisalat adapter | Business Service | 773–828 |
| BR-310 | Resolve "uncertain" redemptions automatically via inquire() against partner lifecycle state (Etisalat TMF622 GET productOrder). | 7.8 Status inquiry | Business Process | 827–828 |
| BR-311 | Orchestrator selects an adapter per MarketplaceItem routing preference when multiple adapters can serve a brand. | 7.8 Routing policy | Business Function | 830–831 |
| BR-312 | Run background sweepers to handle failure-path branches mapped from BPMN Phase 3. | 7.9 Failure paths & background sweepers | Business Process | 832–834 |
| BR-313 | Daily goal scoring grades Steps/Sleep device metrics to a per-day cap, completion-scores the two check-in surveys, and awards a same-day all-goals Balanced Day bonus (SCORE-SVC). | 8.1 Daily goal scoring | Business Function | 859–860 |
| BR-314 | Recognition awards a weekly streak bonus once at week close based on days with at least one goal completed (STREAK-SVC). | 8.2 Recognition – streak tiers | Business Function | 861–862 |
| BR-315 | Aggregation computes WeeklyScore, Sahatna Points credit, and ChallengeScore, crediting points to the WALLET ledger at week close. | 8.3 Aggregation | Business Function | 863–867 |
| BR-316 | Scoring engine evaluates per-challenge criteria via a typed versioned ScoringPlan dispatched by a deterministic kernel over a registry of code-implemented scoring primitives. | 8.4 Scoring engine | Business Function | 868–873 |
| BR-317 | Scoring kernel consumes activity.verified/survey.completed events against the frozen ScoringPlan pinned to the enrolment and emits score.delta-applied, idempotent on source_event_id. | 8.4 Scoring kernel | Business Process | 892–893 |
| BR-318 | A separate aggregator maintains running per-(user,challenge,week,dimension) totals, applies the weekly cap, and at week close computes weekly score, x10 points credit, and mean-of-weeks challenge score. | 8.4 Aggregation stays separate | Business Function | 894–895 |
| BR-319 | Render the score breakdown ("How you earned your score") keyed by the six canonical aggregation dimensions. | 8.5 Score breakdown | Business Service | 902–903 |
| BR-320 | In-challenge surveys are CMS-authored (Strapi dynamic-questionnaires); the two daily check-ins score +1 on submit, the exit survey carries no score. | 8.6 In-challenge surveys | Business Function | 904–905 |
| BR-321 | Manage challenge and enrolment lifecycles (CHAL-SVC); PUBLISH version-pins and freezes ScoringRule/Goals/Reward; withdrawal voids state and emits challenge.withdrawn. | 8.7 Enrolment lifecycle & withdrawal | Business Process | 906–907 |
| BR-322 | On conclusion freeze scores, emit challenge.concluded with per-dimension breakdown, and credit the Sahatna-points payout. | 8.8 Conclusion & DoH boundary | Business Process | 908–909 |
| BR-323 | Ingest DoH winners.announced as asynchronous cross-trust-boundary events surfaced on C11; the platform does not select winners or fulfil prizes. | 8.8 Department of Health boundary | Business Interaction | 908–909 |

## Business Rules

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| RULE-301 | redemption.failed reason is one of partner_unavailable, permanent_partner_error, out_of_stock; failure recorded after attempts=3. | 7.6 Redemption family | Business Object | 671–674 |
| RULE-302 | redemption.uncertain is raised with reason=partner_timeout_after_dispatch (call may have succeeded server-side). | 7.6 Redemption family | Business Object | 676–678 |
| RULE-303 | wallet.released reason is cancelled or expired; wallet.divergence-detected carries ledger_sum, balance and delta. | 7.6 Wallet family | Business Object | 687–692 |
| RULE-304 | The partner-call budget is 10 seconds and dominates the citizen-facing latency envelope; dispatch() must respect the 10s timeout. | 7.7/7.8 Latency budget | Business Rule | 709, 726 |
| RULE-305 | redemption_id is the idempotency anchor for CanonicalRedemption; AdapterOutcome.kind ∈ {success, transient, permanent, uncertain, auth, unsupported}. | 7.8 Canonical types | Business Object | 751–768 |
| RULE-306 | Currency is fixed AED; inventory_mode ∈ {unlimited, limited, partner_managed}; recipient_phone in E.164 (+9715XXXXXXXX); locale ∈ {en, ar}. | 7.8 Canonical types | Business Object | 740–760 |
| RULE-307 | YGG idempotency overlay: write RedemptionAttempt row outcome=in_flight before calling; on retry return cached prior-success payload; on timeout NEVER auto-retry — route to ops reconciliation. | 7.8 YouGotaGift adapter | Business Rule | 771 |
| RULE-308 | Smiles direct points exchange runs on the partnership-gated private Smiles Rewards Exchange blockchain and is not integrated; Smiles content is served as YouGotaGift Smiles Tourist Gift Cards instead. | 7.8 Etisalat adapter | Business Rule | 776 |
| RULE-309 | Etisalat uses TMF622 externalId = redemption_id for native server-side idempotency; the YGG-style adapter overlay is unnecessary for Etisalat. | 7.8 Etisalat idempotency | Business Rule | 783, 824–825 |
| RULE-310 | Etisalat catalogue sync runs 4×/day plus webhook on productOfferingStateChangeEvent; suspended offerings auto-archive MarketplaceItem rows. | 7.8 Catalogue sync (TMF620) | Business Rule | 822–823 |
| RULE-311 | Routing default order: admin-pinned partner → cheapest unit price → highest 7-day success rate → round-robin; admin-pin deterministically routes Smiles via YGG and e& data bundles via Etisalat. | 7.8 Routing policy | Business Rule | 830–831 |
| RULE-312 | Consistency: WalletBalance uses optimistic concurrency (version check); redemption uses pessimistic row lock during state transitions; events emitted only after DB commit (transactional outbox). | 7.10 Consistency | Business Rule | 836–837 |
| RULE-313 | Security: voucher code/pin encrypted at rest (column-level KMS), decryption logged; re-display rate-limited 5/min per voucher and 30/hour per user; partner credentials never logged; PII redacted in adapter payload columns; PII flows to partner only after CONS-SVC verification with consent purpose partner_voucher_delivery. | 7.10 Security | Business Rule | 839–840 |
| RULE-314 | API contract recommendation: start sync for POST /marketplace/redemptions; switch to async only if p95 exceeds 3s. | 7.12 Open decisions | Business Rule | 850 |
| RULE-315 | Gamification scoring/recognition/lifecycle rules are CHAL-authored config, frozen and version-pinned on publish; arithmetic is SCORE-SVC OLTP; CMS holds only copy, imagery and questionnaire wording. | Part 8 intro | Business Rule | 858 |
| RULE-316 | Steps and Sleep are device-metric goals graded to a per-day cap; the two check-ins are +1-on-submit completion surveys (content not graded); Balanced Day is a same-day all-goals bonus. | 8.1 Daily goal scoring | Business Rule | 860 |
| RULE-317 | Streak counts days in the week with ≥1 goal completed; bonus awarded once at week close; streak cycle resets every Monday; streak-at-risk nudges deferred to Transitional+ (not MVP). | 8.2 Recognition – streak tiers | Business Rule | 862 |
| RULE-318 | WeeklyScore = min(100, Σ daily-goal points + Σ balanced-day bonus + streak bonus). | 8.3 Aggregation | Business Rule | 864 |
| RULE-319 | SahatnaPoints(week) = WeeklyScore × 10, credited to the WALLET ledger at week close. | 8.3 Aggregation | Business Rule | 865 |
| RULE-320 | ChallengeScore = mean(WeeklyScore across weeks), shown out of 100, finalised at conclusion. | 8.3 Aggregation | Business Rule | 866 |
| RULE-321 | Sahatna Points are cumulative and never reset across weeks or challenges (worked example: 72→720, 84→840, running total 1,560). | 8.3 Aggregation | Business Rule | 867 |
| RULE-322 | A novel mechanic is a NEW registered scoring primitive — code-reviewed, tested, versioned (the only extensibility seam); authors cannot write freeform production logic. | 8.4 Scoring primitives | Business Rule | 870–871 |
| RULE-323 | The ScoringPlan is typed data validated against each primitive's param-schema, version-pinned and frozen at publish; a new challenge is data, not code. | 8.4 ScoringPlan | Business Object | 872–891 |
| RULE-324 | Reference ScoringPlan (challengeId healthy-living v3): steps THRESHOLD@1 target=7000 points=5; sleep THRESHOLD@1 target=420 points=2; wellbeing/nutrition COMPLETION@1 points=1; balancedDay ALL_OF_BONUS@1 requires all four goals bonus=3; streak STREAK_TIERS@1 tiers=[[4,5],[6,11],[7,16]] window=week reset=MON; weekly cap=100; conversion pointsPerScore=10; challengeScore MEAN_OF_WEEKS@1. | 8.4 ScoringPlan example | Business Object | 874–891 |
| RULE-325 | Streak tiers: 4 days→5 points, 6 days→11 points, 7 days→16 points (tiers param [[4,5],[6,11],[7,16]]). | 8.4 ScoringPlan (streak) | Business Rule | 888 |
| RULE-326 | Scoring kernel is a pure stateless dispatcher, O(goals) per event, idempotent on source_event_id, emitting score.delta-applied {dimension, points, explanation, source_event_id}; it is not a rules engine. | 8.4 Scoring kernel | Business Rule | 892–893 |
| RULE-327 | The aggregator applies the weekly cap (100) and computes rollups as explicit state machines/SQL — never in the kernel, never in config, and never co-located with the wallet ledger. | 8.4 Aggregation stays separate | Business Rule | 894–895 |
| RULE-328 | Versioning: PUBLISH freezes and pins both the ScoringPlan and each primitive so historical replay re-runs the exact strategy@version + params (essential on a money-crediting path); each plan is dry-run against synthetic events and covered by golden-master/replay tests; goal ids referenced by balancedDay must exist. | 8.4 Versioning, validation, testing | Business Rule | 900–901 |
| RULE-329 | The six canonical aggregation/reporting dimensions are Steps, Sleep, Wellbeing check-in, Nutrition check-in, Streak bonus, Balanced day bonus; aggregate key = (user, challenge_id, week, dimension) → points. | 8.5 Score breakdown | Business Object | 902–903 |
| RULE-330 | Three CMS questionnaires: the two daily check-ins score a fixed +1 on submit (answers retained for OLAP, not graded); the exit survey carries no score. | 8.6 In-challenge surveys | Business Rule | 904–905 |
| RULE-331 | Challenge lifecycle: draft → scheduled → live → (paused) → concluded → archived; PUBLISH version-pins and freezes ScoringRule/Goals/Reward. | 8.7 Enrolment lifecycle | Business Object | 906–907 |
| RULE-332 | Enrolment: enrolled → completed on normal conclusion, or enrolled → withdrawn on leave. Withdrawal is IRREVERSIBLE ("all progress and rewards permanently removed") — SCORE/STREAK state is voided, no WALLET credit is issued, and CHAL emits challenge.withdrawn{reason}. | 8.7 Withdrawal | Business Rule | 907 |
| RULE-333 | Winner selection and grand-prize fulfilment are OFF-platform (Department of Health trust boundary); the platform does not pick winners and ingests DoH winners.announced as async announcement events (distinct from DOH-ESB settlement). | 8.8 DoH boundary | Business Role/Actor | 908–909 |
| RULE-334 | Maturity boundary: MVP keeps the kernel + registry as a module in the monolith with the ScoringPlan as typed JSON/table seeded via config; Transitional extracts SCORE-SVC and adds the Designer UI and schema validation. | 8.4 Versioning/maturity | Business Rule | 901 |
| RULE-335 | Implementation sizing uses a 2^n t-shirt formula in days: XS=1d, S=2d, M=4d, L=8d, XL=16d, XXL=32d (~11.2 engineer-weeks, ~4–5 calendar weeks across 3 backend engineers). | 7.11 Implementation estimate | Business Rule | 843–844 |
