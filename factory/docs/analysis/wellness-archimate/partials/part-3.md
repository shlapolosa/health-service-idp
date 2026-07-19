# Wellness-Gamification Platform — Business Architecture Extraction (Part 3)

Source: `/tmp/wellness_doc.txt` lines 365–660 (Part 2 screens, Part 3 cross-cutting, Part 5 Partner Lifecycle BPMN, Part 6 UAE Partner Landscape, Part 7 Value Path WALLET-SVC / MARKET-SVC).

## Business Requirements

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| BR-201 | Provide an onboarding intro-carousel experience that introduces the gamification + rewards journey to the member. | 2.1 Onboarding | Business Service | 367 |
| BR-202 | Present a host-home entry point from which the member enters the wellness journey. | 2.2 Host home | Business Service | 368 |
| BR-203 | Display a challenges dashboard supporting multiple concurrent challenges per member. | 2.3 Challenges dashboard | Business Service | 369 |
| BR-204 | Show pre-enrolment challenge details including a "how scoring works" explainer. | 2.4 Challenge details | Business Service | 370 |
| BR-205 | Allow a member to enrol in a challenge via a Join → T&C acceptance → Success flow. | 2.5 Enrolment | Business Process | 371 |
| BR-206 | Provide a challenge tracker (week/day) with supporting info sheets during an active challenge. | 2.6 Challenge tracker | Business Service | 372 |
| BR-207 | Capture member daily check-ins for wellbeing and nutrition. | 2.7 Daily check-ins | Business Process | 373 |
| BR-208 | Acknowledge completion of daily goals to the member. | 2.8 Daily goals completed | Business Event | 374 |
| BR-209 | Acknowledge week completion to the member. | 2.9 Week completed | Business Event | 375 |
| BR-210 | Acknowledge challenge completion to the member. | 2.10 Challenge completed | Business Event | 376 |
| BR-211 | Allow a member to leave/withdraw from a challenge. | 2.11 Leave challenge | Business Process | 377 |
| BR-212 | Provide a rewards module combining a marketplace and a points wallet. | 2.12 Rewards module | Business Service | 378 |
| BR-213 | Show a challenge-conclusion celebration automatically (event-triggered) when the member next opens the app after an enrolled challenge concluded. | 3 Pending decisions (C11) | Business Event | 405–406 |
| BR-214 | Onboard a partner by intake of an application (trade licence, VAT registration, authorised-signatory details). | 5.1 Phase 1 Onboarding & KYB | Business Process | 447–448 |
| BR-215 | Perform KYB due-diligence screening on each partner application. | 5.1 Phase 1 | Business Function | 448 |
| BR-216 | Decide partner approval as a binary gateway (approve → Phase 2, reject → terminal). | 5.1 Phase 1 | Business Process | 448 |
| BR-217 | Provision sandbox-first partner credentials before production access. | 5.2 Phase 2 Contracting & Catalogue Setup | Business Process | 451 |
| BR-218 | Allow partner to push catalogue items via API and validate each item before indexing. | 5.2 Phase 2 | Business Process | 451 |
| BR-219 | Release production credentials only after successful catalogue indexing. | 5.2 Phase 2 | Business Process | 451 |
| BR-220 | Operate the member redemption loop: browse → select → confirm → reserve → partner fulfil → commit → notify. | 5.3 Phase 3 Member Redemption | Business Process | 453–454 |
| BR-221 | On redemption failure, release the reservation, notify the member, and log the incident to FRAUD-SVC for pattern analysis. | 5.3 Phase 3 | Business Process | 454 |
| BR-222 | Run monthly settlement: aggregate redemptions by partner and SKU and reconcile the ledger against redemption events. | 5.4 Phase 4 Settlement | Business Process | 456–457 |
| BR-223 | Generate a VAT-compliant invoice per partner and route payment via DOH ESB (regulated) or direct API (retail). | 5.4 Phase 4 | Business Process | 457 |
| BR-224 | Offboard a partner on contract expiry, partner request, or compliance breach, with a voluntary-vs-breach gateway. | 5.5 Phase 5 Offboarding & Exit | Business Process | 459–460 |
| BR-225 | Depublish catalogue items at offboarding while honouring unredeemed vouchers through a wind-down period. | 5.5 Phase 5 | Business Process | 460 |
| BR-226 | Source the marketplace catalogue via a mix of gift-card aggregators (breadth) and direct partner integrations (depth) behind one canonical PartnerAdapter interface. | 6 / 6.2 Sourcing | Business Service | 463, 467 |
| BR-227 | Validate KYB licences in Phase 1 using government API marketplaces. | 6.3 Direct APIs | Business Function | 469 |
| BR-228 | Provide members a self-service marketplace browse/redeem and wallet balance/transaction/voucher view. | 7.5 API contracts (citizen-facing) | Business Service | 602–625 |
| BR-229 | Provide platform admins partner-lifecycle and catalogue management operations (onboard, approve, credentials, contract, offboard, item approve/suspend/inventory, resolve uncertain redemptions). | 7.5 API contracts (admin-facing) | Business Process | 626–640 |
| BR-230 | Reserve member points (two-phase reserve-then-confirm) before calling the partner, and credit points on challenge conclusion. | 7.5 Internal API / 5.3 | Business Process | 641–658 |
| BR-231 | Issue and store a redemption voucher (code/pin/url/qr) to the member on successful fulfilment. | 5.3 / 7.3 Voucher entity | Business Service | 454, 568–582 |

## Business Rules

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| RULE-201 | Field ownership split: presentation (copy, imagery, questionnaires) is CMS-owned (Strapi/cms-service); economics, eligibility and state are the CHAL/SCORE/STREAK/WALLET contract. | Part 2 intro | Business Rule | 366 |
| RULE-202 | Wallet and Marketplace must both use the same two-phase reserve-then-confirm pattern: identical timeout policy, idempotency keys, and compensation-on-failure. | 3 Architectural patterns | Business Rule | 382–383 |
| RULE-203 | Every event consumer (Score Computer, Goal Evaluator, Credit Issuer, Streak Calculator, Award Engine, Title Progression, Late-Sync Reconciler, Nudge Dispatcher, Fraud Anomaly Detector) must be idempotent on a stable `source_event_id`. | 3 Architectural patterns | Business Rule | 384–385 |
| RULE-204 | Eligibility resolution and Consent resolution must meet <50ms p95 read latency and use a common caching + explicit invalidation contract. | 3 Architectural patterns | Business Rule | 386–387 |
| RULE-205 | Consent Resolver is strongly consistent with a <30ms p95 resolver target and is a critical-path service (its availability = platform availability for leaderboard/nudge/analytics flows). | 3 Pending decisions | Business Rule | 395–396 |
| RULE-206 | Partner data is retained for 7 years per UAE commercial law, with PII masked at the 2-year mark. | 5.5 Phase 5 | Business Rule | 460 |
| RULE-207 | KYB application requires a trade licence (DED or free-zone), VAT registration, and authorised-signatory details. | 5.1 Phase 1 | Business Rule | 448 |
| RULE-208 | KYB due diligence must screen against UAE Central Bank AML watchlists and validate MOHRE/DLD licences as applicable. | 5.1 Phase 1 | Business Rule | 448 |
| RULE-209 | Catalogue item validation must check point-cost equivalence (AED-value floor), category compliance, and inventory; invalid items loop back to the partner for correction. | 5.2 Phase 2 | Business Rule | 451 |
| RULE-210 | Wallet reservation TTL is 5 minutes (300 seconds) during redemption. | 5.3 Phase 3 / 7.4b | Business Rule | 454, 516, 599 |
| RULE-211 | Partner fulfilment API call uses a 10-second timeout. | 5.3 Phase 3 | Business Rule | 454 |
| RULE-212 | On three exhausted retries, release the reservation, notify the member, and log the incident to FRAUD-SVC. | 5.3 Phase 3 | Business Rule | 454 |
| RULE-213 | Settlement is triggered by a monthly timer (default: 1st of month). | 5.4 Phase 4 | Business Event | 457 |
| RULE-214 | Any ledger-vs-redemption discrepancy greater than 0.1% is flagged during settlement reconciliation. | 5.4 Phase 4 | Business Rule | 457 |
| RULE-215 | A 5% settlement holdback is released only after a 30-day dispute window. | 5.4 Phase 4 | Business Rule | 457 |
| RULE-216 | Payment routing depends on partner class: DOH ESB for regulated partners, direct API for retail. | 5.4 Phase 4 | Business Rule | 457 |
| RULE-217 | Offboarding voluntary-vs-breach gateway: voluntary exit issues a 30-day warning before credential revocation; breach revokes without the warning. | 5.5 Phase 5 | Business Rule | 460 |
| RULE-218 | At offboarding, unredeemed vouchers remain valid through a 90-day wind-down; final settlement runs after the wind-down. | 5.5 Phase 5 | Business Rule | 460 |
| RULE-219 | Wallet balance and reserved amounts must never go negative (CHECK balance >= 0, reserved >= 0); ledger is append-only with strong balance consistency. | 3 / 7.3 WalletBalance | Business Rule | 393–394, 490–496 |
| RULE-220 | `WalletTransaction.source_event_id` and `WalletReservation.idempotency_key` are UNIQUE — the idempotency anchors collapsing redelivery/retries. | 7.3 entities | Business Rule | 504, 514 |
| RULE-221 | WalletReservation lifecycle states: open → confirmed/cancelled/expired; expires_at = created_at + 300s. | 7.3 / 7.4b | Business Object | 515–516, 598–599 |
| RULE-222 | Redemption is held in an `uncertain` terminal state out of auto-retry to prevent duplicate partner debits; uncertain cases are resolved manually by admin. | 7.4 / 7.5 admin | Business Rule | 596–597, 639–640 |
| RULE-223 | Redemption `points_cost` is snapshotted at request time (immutable on the Redemption record). | 7.3 Redemption entity | Business Rule | 545 |
| RULE-224 | Every MarketplaceItem carries both `points_cost` (INT) and `aed_value` (DECIMAL) — the points-to-voucher economic mapping. | 7.3 MarketplaceItem | Business Object | 521–532 |
| RULE-225 | Partner credentials are stored only as a Key Vault reference (`credentials_ref`), never inline. | 7.3 Partner entity | Business Rule | 590 |
| RULE-226 | Partner record requires a signed PDPL addendum (`pdpl_addendum_signed_at`) and a contract end date. | 7.3 Partner entity | Business Rule | 591–592 |
| RULE-227 | Voucher `code` and `pin` are column-encrypted at rest; redemption request/response payloads are redacted at rest. | 7.3 Voucher/RedemptionAttempt | Business Rule | 561–575 |
| RULE-228 | Every mutating endpoint requires a client-generated `Idempotency-Key` header; replay returns the prior result (409 IDEMPOTENCY_REPLAY). | 7.5 API contracts | Business Rule | 601, 610, 645 |
| RULE-229 | Citizen-facing endpoints use JWT bearer auth; internal/admin endpoints use mTLS + service token. | 7.5 API contracts | Business Rule | 601 |
| RULE-230 | Catalogue item deletion is soft-archive only (no hard delete). | 7.5 admin API | Business Rule | 636 |
| RULE-231 | Redemption insufficient-points returns 402; unavailable item 410; eligibility-rejected 422 — eligibility and balance are gating preconditions to redemption. | 7.5 citizen API | Business Rule | 614–616 |
| RULE-232 | Recommended sourcing: YouGotaGift = primary UAE-native catalogue (incl. Smiles Tourist Gift Cards); Reloadly = secondary global + the only webhook async-confirmation aggregator; Etisalat (e&) direct via TMF620/TMF622 with native externalId idempotency; native Smiles points exchange (Smiles Rewards Exchange blockchain) is a v2 partnership item. | 6.5 Sourcing strategy | Business Rule | 475–479 |
| RULE-233 | Platform actors / roles: Member, Platform Admin, Wallet SVC, Marketplace SVC, FRAUD-SVC, and external Partner; Phase 3 is steady-state, Phases 1/2/5 are lifecycle transitions, Phase 4 fires on monthly timer; Phase 5 reachable from any post-Phase-2 state. | 5 Partner Lifecycle | Business Role/Actor | 444–446 |
| RULE-234 | Partner status lifecycle: onboarded → contracted → active → suspended → offboarded. | 7.3 Partner entity | Business Object | 588 |
| RULE-235 | Identity downtime degrades but does not fail the platform; Platform Token Service must validate tokens without synchronous UAE Pass calls on the hot path (User Profile Mirror is the read-side cache). | 3 Pending decisions (Identity) | Business Rule | 401–402 |
