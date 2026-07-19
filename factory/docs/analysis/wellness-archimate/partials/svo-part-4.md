# S-V-O Decomposition — Part 4 (Redemption/Wallet/Partner Adapter + Gamification Scoring Engine)

Source catalogue: `partials/part-4.md` (BR-301..BR-323, RULE-301..RULE-335). Grammatical decomposition of each requirement/rule into (Subject → Active Structure, Action → Behaviour, Object → Passive Structure) triples. Implicit subjects inferred; scoring rules default to SCORE-SVC / scoring kernel.

## S-V-O triples

| Triple# | Source ID | Subject | Action | Object |
|---------|-----------|---------|--------|--------|
| 1 | BR-301 | EVENT-SVC | Publish schema-registry-backed event | Event (event_id/event_type/event_time/producer/trace_id/payload) |
| 2 | BR-302 | Redemption family services | Emit redemption lifecycle event | redemption.requested/reserved/fulfilled/failed/uncertain |
| 3 | BR-303 | Wallet family services (WALLET-SVC) | Emit wallet lifecycle event | wallet.reserved/debited/released/divergence-detected |
| 4 | BR-304 | Catalogue/voucher services (MARKET-SVC) | Emit voucher/catalogue event | voucher.issued/delivered/expired, catalog.item.activated, inventory.low |
| 5 | BR-305 | Orchestrator | Execute end-to-end redemption sequence | Redemption (happy/retry-exhausted/uncertain-timeout) |
| 6 | BR-306 | PartnerAdapter | Translate canonical contract bidirectionally | CanonicalContract / partner native API |
| 7 | BR-307 | PartnerAdapter | Implement adapter operations (list_products/dispatch/inquire/cancel/handle_webhook) | AdapterCapability |
| 8 | BR-308 | YouGotaGift adapter | Fulfil redemption (POST /incentives-send) | Voucher (voucher code) |
| 9 | BR-309 | Etisalat adapter | Fulfil redemption / sync catalogue (TMF622/TMF620) | ProductOrder / ProductOffering |
| 10 | BR-310 | Orchestrator | Inquire uncertain redemption (inquire()) | Redemption (uncertain) |
| 11 | BR-311 | Orchestrator | Select adapter per routing preference | RoutingPolicy / MarketplaceItem |
| 12 | BR-312 | Background sweeper | Sweep failure-path branches | Redemption (failure paths) |
| 13 | BR-313 | SCORE-SVC | Score daily goals (grade metrics, completion-score surveys, award Balanced Day) | DailyGoalScore / BalancedDayBonus |
| 14 | BR-314 | STREAK-SVC | Award weekly streak bonus | StreakBonus / StreakTier |
| 15 | BR-315 | Aggregator | Compute WeeklyScore, Sahatna Points, ChallengeScore + credit ledger | WeeklyScore / SahatnaPoints / ChallengeScore / WALLET ledger |
| 16 | BR-316 | Scoring kernel | Evaluate per-challenge criteria via ScoringPlan | ScoringPlan / ScoringPrimitive |
| 17 | BR-317 | Scoring kernel | Consume activity.verified/survey.completed, emit score.delta-applied | score.delta-applied event / ScoringPlan |
| 18 | BR-318 | Aggregator | Maintain running totals, apply weekly cap, compute rollups | AggregateTotal (user,challenge,week,dimension) |
| 19 | BR-319 | SCORE-SVC | Render score breakdown | ScoreBreakdown (six dimensions) |
| 20 | BR-320 | CMS author (Strapi) | Author in-challenge surveys; score +1 on submit | Survey (check-in / exit) |
| 21 | BR-321 | CHAL-SVC | Manage challenge/enrolment lifecycle; PUBLISH freezes; withdrawal voids | Challenge / Enrolment / ScoringRule / challenge.withdrawn |
| 22 | BR-322 | CHAL-SVC | Freeze scores, emit challenge.concluded, credit payout | challenge.concluded event / SahatnaPoints |
| 23 | BR-323 | DoH boundary interface | Ingest winners.announced cross-boundary event | winners.announced event |
| 24 | RULE-301 | Redemption family | Record failure after attempts=3 | redemption.failed (reason enum) |
| 25 | RULE-302 | Redemption family | Raise uncertain redemption | redemption.uncertain (reason=partner_timeout_after_dispatch) |
| 26 | RULE-303 | Wallet family | Carry release reason / divergence delta | wallet.released / wallet.divergence-detected |
| 27 | RULE-304 | PartnerAdapter | Respect 10s partner-call budget (dispatch timeout) | PartnerCallBudget (latency envelope) |
| 28 | RULE-305 | Orchestrator | Anchor idempotency on redemption_id; classify AdapterOutcome | CanonicalRedemption / AdapterOutcome |
| 29 | RULE-306 | Orchestrator | Constrain canonical field values (AED/inventory_mode/E.164/locale) | CanonicalRedemption (field constraints) |
| 30 | RULE-307 | YouGotaGift adapter | Write RedemptionAttempt, cache success, never auto-retry on timeout | RedemptionAttempt (idempotency overlay) |
| 31 | RULE-308 | Etisalat/Smiles routing | Serve Smiles as YGG Tourist Gift Cards (Smiles blockchain not integrated) | Smiles Rewards Exchange / Voucher |
| 32 | RULE-309 | Etisalat adapter | Set externalId=redemption_id for native idempotency | ProductOrder (externalId) |
| 33 | RULE-310 | Etisalat adapter | Sync catalogue 4×/day + webhook; auto-archive suspended offerings | MarketplaceItem / productOfferingStateChangeEvent |
| 34 | RULE-311 | Orchestrator | Apply routing default order (admin-pin→price→success-rate→round-robin) | RoutingPolicy |
| 35 | RULE-312 | WALLET-SVC / Redemption | Apply concurrency control; emit events post-commit (outbox) | WalletBalance / transactional outbox |
| 36 | RULE-313 | MARKET-SVC / CONS-SVC | Encrypt voucher code, rate-limit re-display, redact PII, gate partner PII on consent | Voucher code/pin / Consent (partner_voucher_delivery) |
| 37 | RULE-314 | API contract | Start sync redemption; switch async if p95>3s | RedemptionAPI contract |
| 38 | RULE-315 | CHAL-SVC | Author and version-pin scoring/recognition/lifecycle config | ScoringRule config / CMS copy |
| 39 | RULE-316 | SCORE-SVC | Grade Steps/Sleep to per-day cap; +1 check-ins; Balanced Day bonus | DailyGoalScore / BalancedDayBonus |
| 40 | RULE-317 | STREAK-SVC | Count days ≥1 goal; award once at week close; reset Monday | StreakTier / StreakBonus |
| 41 | RULE-318 | Aggregator | Compute WeeklyScore = min(100, Σ points + bonuses) | WeeklyScore |
| 42 | RULE-319 | Aggregator | Convert WeeklyScore×10, credit ledger at week close | SahatnaPoints / WALLET ledger |
| 43 | RULE-320 | Aggregator | Compute ChallengeScore = mean(WeeklyScore) | ChallengeScore |
| 44 | RULE-321 | Aggregator | Accumulate Sahatna Points, never reset | SahatnaPoints (cumulative) |
| 45 | RULE-322 | Scoring kernel / registry | Register new scoring primitive (only extensibility seam) | ScoringPrimitive |
| 46 | RULE-323 | Scoring kernel | Validate typed ScoringPlan against primitive param-schema; freeze at publish | ScoringPlan |
| 47 | RULE-324 | Scoring kernel | Evaluate reference ScoringPlan (healthy-living v3 params) | ScoringPlan (reference) |
| 48 | RULE-325 | STREAK-SVC | Apply streak tiers (4→5, 6→11, 7→16) | StreakTier (tiers param) |
| 49 | RULE-326 | Scoring kernel | Dispatch pure stateless, idempotent on source_event_id; emit score.delta-applied | score.delta-applied event |
| 50 | RULE-327 | Aggregator | Apply weekly cap, compute rollups as state machines/SQL | AggregateTotal / weekly cap |
| 51 | RULE-328 | CHAL-SVC / Scoring kernel | PUBLISH freeze+pin ScoringPlan/primitive; dry-run golden-master replay | ScoringPlan / ScoringPrimitive (versioned) |
| 52 | RULE-329 | Aggregator | Key aggregate by six canonical dimensions | AggregationDimension (Steps/Sleep/Wellbeing/Nutrition/Streak/BalancedDay) |
| 53 | RULE-330 | CMS author | Score +1 check-ins, retain answers for OLAP; exit survey no score | Questionnaire / Survey |
| 54 | CHAL-SVC | RULE-331 | Transition challenge lifecycle (draft→...→archived); PUBLISH freezes | Challenge lifecycle / ScoringRule |
| 55 | RULE-332 | CHAL-SVC | Void state on withdrawal (irreversible); emit challenge.withdrawn | Enrolment / challenge.withdrawn event |
| 56 | RULE-333 | Department of Health (DoH) | Select winners + fulfil prizes off-platform | winners.announced event |
| 57 | RULE-334 | SCORE-SVC / kernel+registry | Host kernel as monolith module (MVP); extract SCORE-SVC (Transitional) | ScoringPlan (typed JSON/table) |
| 58 | RULE-335 | Delivery team | Size implementation via 2^n t-shirt formula | ImplementationEstimate |

## Active Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| EVENT-SVC | Application Component | BR-301 |
| MARKET-SVC (catalogue/voucher) | Application Component | BR-304, RULE-310, RULE-313 |
| WALLET-SVC (wallet family) | Application Component | BR-303, RULE-303, RULE-312 |
| Orchestrator | Application Component | BR-305, BR-310, BR-311, RULE-305, RULE-306, RULE-311 |
| PartnerAdapter (canonical adapter) | Application Component | BR-306, BR-307, RULE-304 |
| YouGotaGift adapter | Application Component / PartnerAdapter | BR-308, RULE-307, RULE-308 |
| Etisalat (e&) adapter | Application Component / PartnerAdapter | BR-309, RULE-308, RULE-309, RULE-310 |
| Background sweeper | Application Component | BR-312 |
| SCORE-SVC (daily goal scoring) | Application Component | BR-313, BR-319, RULE-315, RULE-316, RULE-334 |
| STREAK-SVC (recognition) | Application Component | BR-314, RULE-317, RULE-325 |
| Aggregator | Application Component | BR-315, BR-318, RULE-318, RULE-319, RULE-320, RULE-321, RULE-327, RULE-329 |
| Scoring kernel (deterministic dispatcher) | Application Component | BR-316, BR-317, RULE-322, RULE-323, RULE-326, RULE-328 |
| Scoring primitive registry | Application Component | RULE-322, RULE-334 |
| CHAL-SVC (challenge/enrolment) | Application Component | BR-321, BR-322, RULE-315, RULE-328, RULE-331, RULE-332 |
| CMS author (Strapi) | Business Role | BR-320, RULE-330 |
| CONS-SVC (consent) | Application Component | RULE-313 |
| Department of Health (DoH) | Business Actor | BR-323, RULE-333 |
| DoH boundary interface (C11) | Application Interface | BR-323 |
| Delivery team | Business Role | RULE-335 |

## Behaviour elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Publish schema-registry event | Business Service | BR-301 |
| redemption.requested/reserved/fulfilled/failed/uncertain | Business Event | BR-302, RULE-301, RULE-302 |
| wallet.reserved/debited/released/divergence-detected | Business Event | BR-303, RULE-303 |
| voucher/catalogue events (issued/delivered/expired/activated/inventory.low) | Business Event | BR-304 |
| Execute redemption sequence | Business Process | BR-305 |
| Translate canonical contract (Partner Adapter) | Business Function | BR-306 |
| Adapter operations (list_products/dispatch/inquire/cancel/handle_webhook) | Business Interface | BR-307 |
| Fulfil redemption (YouGotaGift) | Business Service | BR-308, RULE-307 |
| Fulfil redemption / sync catalogue (Etisalat) | Business Service | BR-309, RULE-309, RULE-310 |
| Resolve uncertain redemption (inquire) | Business Process | BR-310 |
| Select adapter / route to partner | Business Function | BR-311, RULE-311 |
| Sweep failure paths | Business Process | BR-312, RULE-301 |
| Score daily goals | Business Function | BR-313, RULE-316 |
| Award streak bonus / apply streak tier | Business Function | BR-314, RULE-317, RULE-325 |
| Compute aggregation (WeeklyScore/Points/ChallengeScore) | Business Function | BR-315, BR-318, RULE-318, RULE-320, RULE-327 |
| Credit Sahatna Points to ledger | Business Process | BR-315, BR-322, RULE-319, RULE-321 |
| Evaluate ScoringPlan | Business Function | BR-316, RULE-323, RULE-324 |
| Dispatch scoring kernel (consume events, emit delta) | Business Process | BR-317, RULE-326 |
| score.delta-applied | Business Event | BR-317, RULE-326 |
| Render score breakdown | Business Service | BR-319 |
| Author surveys / score check-ins | Business Function | BR-320, RULE-330 |
| Manage challenge/enrolment lifecycle | Business Process | BR-321, RULE-331 |
| Withdraw enrolment (void state) | Business Process | RULE-332 |
| challenge.withdrawn | Business Event | BR-321, RULE-332 |
| Conclude challenge (freeze, payout) | Business Process | BR-322 |
| challenge.concluded | Business Event | BR-322 |
| Ingest DoH winners.announced | Business Interaction | BR-323, RULE-333 |
| winners.announced | Business Event | BR-323, RULE-333 |
| Register scoring primitive | Business Function | RULE-322, RULE-328 |
| Apply concurrency / transactional outbox | Business Function | RULE-312 |
| Enforce security (encrypt/rate-limit/redact/consent-gate) | Business Function | RULE-313 |
| Sync catalogue (4×/day + webhook) | Business Process | RULE-310 |
| Size implementation (t-shirt formula) | Business Function | RULE-335 |

## Passive Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Event (envelope: event_id/type/time/producer/trace_id/payload) | Data Object | BR-301 |
| Redemption / CanonicalRedemption | Business Object | BR-305, BR-310, BR-312, RULE-305, RULE-306 |
| AdapterOutcome | Business Object | RULE-305 |
| RedemptionAttempt (idempotency overlay) | Data Object | RULE-307 |
| AdapterCapability (operation set) | Business Object | BR-307 |
| CanonicalContract / partner native API | Contract | BR-306 |
| Voucher (voucher code/pin) | Business Object / Product | BR-304, BR-308, RULE-308, RULE-313 |
| ProductOrder (TMF622) | Data Object | BR-309, RULE-309 |
| ProductOffering (TMF620) | Data Object | BR-309, RULE-310 |
| MarketplaceItem | Business Object | BR-311, RULE-310 |
| RoutingPolicy | Business Object | BR-311, RULE-311 |
| PartnerCallBudget (10s latency envelope) | Business Object | RULE-304 |
| WalletBalance / WALLET ledger | Business Object | BR-303, BR-315, RULE-312, RULE-319 |
| Transactional outbox | Data Object | RULE-312 |
| Consent (purpose=partner_voucher_delivery) | Business Object | RULE-313 |
| ScoringRule | Business Object | BR-321, RULE-315, RULE-331 |
| ScoringPlan (typed, versioned, frozen) | Business Object | BR-316, BR-317, RULE-323, RULE-324, RULE-328, RULE-334 |
| ScoringPrimitive | Business Object | BR-316, RULE-322, RULE-328 |
| DailyGoalScore | Business Object | BR-313, RULE-316 |
| BalancedDayBonus | Business Object | BR-313, RULE-316 |
| StreakTier | Business Object | BR-314, RULE-317, RULE-325 |
| StreakBonus | Business Object | BR-314, RULE-317 |
| WeeklyScore | Business Object | BR-315, RULE-318 |
| SahatnaPoints (cumulative) | Business Object | BR-315, BR-322, RULE-319, RULE-321 |
| ChallengeScore | Business Object | BR-315, RULE-320 |
| AggregateTotal (user,challenge,week,dimension) | Business Object | BR-318, RULE-327, RULE-329 |
| AggregationDimension (six canonical) | Business Object | BR-319, RULE-329 |
| ScoreBreakdown | Representation | BR-319 |
| Survey / Questionnaire (check-in / exit) | Business Object | BR-320, RULE-330 |
| Challenge (lifecycle) | Business Object | BR-321, RULE-331 |
| Enrolment | Business Object | BR-321, RULE-332 |
| ImplementationEstimate (t-shirt sizing) | Business Object | RULE-335 |
| RedemptionAPI contract | Contract | RULE-314 |
| Smiles Rewards Exchange (blockchain, not integrated) | Business Object | RULE-308 |
