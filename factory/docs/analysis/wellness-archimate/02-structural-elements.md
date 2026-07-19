# Wellness Platform — Master Structural-Element Inventory (deduplicated across Parts 1-4)

Consolidates the Active / Behaviour / Passive ArchiMate inventories from `partials/svo-part-1.md` … `svo-part-4.md`.
Same element appearing in multiple slices collapses to ONE row; `Source IDs` is the UNION of contributing BR/RULE IDs; `Slices` lists contributing parts (1-4). Naming variants resolved to a canonical name with the alias noted.

## Counts

| Dimension | Distinct (post-dedup) | Cross-slice merges |
|-----------|-----------------------|--------------------|
| Active Structure   | 41 | 11 |
| Behaviour          | 78 | 6  |
| Passive Structure  | 63 | 12 |
| **Total**          | **182** | **29** |

A "cross-slice merge" = a canonical element whose `Slices` column lists more than one part.

---

## 1. Active Structure

### (a) Application Components — the ABBs

| Canonical name | ArchiMate type | Slices | Source IDs | Note / alias |
|----------------|----------------|--------|------------|--------------|
| CHAL-SVC (Challenge & Enrolment) | Application Component | 1,4 | BR-004…010, BR-321, BR-322, RULE-002, RULE-005…013, RULE-315, RULE-328, RULE-331, RULE-332 | alias "CHAL-SVC (challenge/enrolment)" |
| SCORE-SVC (Wellness/Goal Scoring) | Application Component | 1,4 | BR-001, BR-011, BR-012, BR-013, BR-031, BR-313, BR-319, RULE-014…020, RULE-315, RULE-316, RULE-334 | alias "SCORE-SVC (daily goal scoring)" |
| TITLE-SVC (Title & Decay) | Application Component | 1 | BR-014, BR-015, BR-016, RULE-021…024 | absorbs "TITLE-SVC / Decay Engine" |
| WALLET-SVC (Wallet family) | Application Component | 1,3,4 | BR-017…020, BR-220, BR-230, BR-303, RULE-025…031, RULE-202, RULE-210, RULE-233, RULE-303, RULE-312 | merges Part-2 "Wallet", Part-3 "Wallet SVC" |
| MARKET-SVC (Marketplace/Catalogue) | Application Component | 1,3,4 | BR-021, BR-022, BR-023, BR-228, BR-304, RULE-031…034, RULE-202, RULE-233, RULE-310, RULE-313 | merges Part-2 "Marketplace", Part-3 "Marketplace SVC" |
| NUDGE-SVC (Nudge & Inbox) | Application Component | 1 | BR-024, BR-025, RULE-035, RULE-036, RULE-037 | |
| CONS-SVC (Consent) | Application Component | 1,4 | BR-026…029, RULE-038, RULE-039, RULE-040, RULE-313 | merges "Consent Resolver" (Part-3) — see note |
| GOAL-SVC (Goal Engine) | Application Component | 2 | BR-101…104, RULE-101, RULE-102, RULE-103 | |
| STREAK-SVC (Streak/Recognition) | Application Component | 2,4 | BR-105…108, BR-314, RULE-104, RULE-105, RULE-106, RULE-317, RULE-325 | alias "STREAK-SVC (recognition)" |
| BADGE-SVC (Badge Service) | Application Component | 2 | BR-109, BR-110, BR-111, RULE-107, RULE-108 | |
| ACTV-SVC (Activity Verification) | Application Component | 2 | BR-112…115, RULE-109…112 | |
| CLIN-SVC (Clinical Verification) | Application Component | 2 | BR-116, BR-117, RULE-113, RULE-114, RULE-115 | |
| ID-SVC (Identity & Auth) | Application Component | 2,3 | BR-118, BR-119, BR-120, RULE-116, RULE-117, RULE-118, RULE-235 | merges Part-3 "Platform Token Service" + "User Profile Mirror" |
| FRAUD-SVC (Fraud & Integrity) | Application Component | 2,3 | BR-121, BR-122, BR-123, BR-221, RULE-119, RULE-120, RULE-212, RULE-233 | |
| EVENT-SVC (Event Hub) | Application Component | 1,2,4 | BR-030, BR-032, BR-124, BR-301, RULE-043, RULE-122, RULE-123 | merges Part-1 "Event Hub spine" + Part-3 "Event Consumer"; type note: Component (acts as collaboration/bus) |
| DATA-SVC (Data Lake & Warehouse) | Application Component | 1,2 | BR-001, BR-002, BR-125, BR-126, RULE-004, RULE-124 | merges Part-1 "Cohort Analytics (OLAP/Warehouse)" + "OLTP Read Store" |
| REPORT-SVC (Reporting) | Application Component | 1,2 | BR-003, BR-030, BR-127, BR-128, RULE-001, RULE-008, RULE-125, RULE-126 | merges Part-1 "Reverse-ETL / Publication" |
| Orchestrator (Redemption Conclusion Orchestrator) | Application Component | 1,4 | BR-013, BR-305, BR-310, BR-311, RULE-013, RULE-305, RULE-306, RULE-311 | merges Part-1 "Conclusion Orchestrator" |
| PartnerAdapter (canonical adapter) | Application Component | 3,4 | BR-226, BR-306, BR-307, RULE-304 | type note: surfaced as Application Interface in Parts 3/4 (BR-226, BR-323) but the adapter itself is a Component |
| YouGotaGift adapter | Application Component | 4 | BR-308, RULE-307, RULE-308 | specialises PartnerAdapter |
| Etisalat (e&) adapter | Application Component | 4 | BR-309, RULE-308, RULE-309, RULE-310 | specialises PartnerAdapter |
| Background sweeper | Application Component | 4 | BR-312 | |
| Aggregator (scoring aggregator) | Application Component | 4 | BR-315, BR-318, RULE-318…321, RULE-327, RULE-329 | distinct from external "Aggregator" actor (Part-3) — see actors |
| Scoring kernel | Application Component | 4 | BR-316, BR-317, RULE-322, RULE-323, RULE-326, RULE-328 | canonical for "scoring kernel"/"SCORE-SVC scoring kernel (deterministic dispatcher)" |
| Scoring primitive registry | Application Component | 4 | RULE-322, RULE-334 | |
| CMS (Strapi / cms-service) | Application Component | 3 | RULE-201 | |
| CHAL/SCORE/STREAK contract | Application Component | 3 | RULE-201 | content-contract facade; could fold into respective SVCs |
| Eligibility Resolver | Application Component | 3 | RULE-204, RULE-231 | |
| Power BI | Application Component | 2 | BR-126 | external BI tool |
| Government API Marketplace gateway | Application Component | 3 | BR-227, RULE-208 | also modelled as external actor — see note |

### (b) Business Actors & Roles

| Canonical name | ArchiMate type | Slices | Source IDs | Note / alias |
|----------------|----------------|--------|------------|--------------|
| Member (Citizen) | Business Role | 1,3 | BR-007, BR-205, BR-207, BR-211, BR-220, BR-228, RULE-042, RULE-212, RULE-233 | merges Part-1 "Citizen (Member)" |
| Partner | Business Actor (external) | 3 | BR-218, BR-220, RULE-207, RULE-211, RULE-226, RULE-233, RULE-234 | |
| Department of Health (DoH) | Business Actor | 1,2,4 | BR-010, BR-127, BR-323, RULE-041, RULE-126, RULE-333 | merges Part-2 "DH"; type note: Actor (Parts list as Actor/Role) |
| ADPHC | Business Actor | 2 | BR-127, RULE-126 | DoH sub-entity |
| ADHDS | Business Actor | 2 | BR-127, RULE-126 | DoH sub-entity |
| Platform Admin (Programme Admin) | Business Role | 1,2,3 | BR-128, BR-229, RULE-042, RULE-222, RULE-233 | merges Part-1 "Admin", Part-2 "Programme Admin" |
| Challenge Management | Business Role | 2 | RULE-102 | |
| Fraud Analyst | Business Role | 2 | BR-123, RULE-119 | |
| CMS author (Strapi) | Business Role | 4 | BR-320, RULE-330 | |
| Delivery team | Business Role | 4 | RULE-335 | sizing/estimation role |
| Settlement Timer | Business Role (triggering) | 3 | RULE-213 | scheduled trigger |
| Aggregator (YouGotaGift / Reloadly / e& / Smiles) | Business Actor (external) | 3 | BR-226, RULE-232 | external voucher aggregators; distinct from internal scoring "Aggregator" component |
| Government API Marketplace | Business Actor (external) | 3 | BR-227, RULE-208 | external; see component twin |

### (c) Collaborations & Interfaces

| Canonical name | ArchiMate type | Slices | Source IDs | Note / alias |
|----------------|----------------|--------|------------|--------------|
| Platform / BFF | Business Collaboration | 3 | BR-201…231 (most), RULE-201, RULE-206, RULE-208, RULE-209, RULE-212, RULE-214…220, RULE-223, RULE-225, RULE-227, RULE-229…231, RULE-235 | aggregating collaboration over component set |
| Adapter operations interface | Application/Business Interface | 4 | BR-307 | list_products/dispatch/inquire/cancel/handle_webhook |
| DoH boundary interface (C11) | Application Interface | 4 | BR-323 | |

---

## 2. Behaviour

### (i) Business Services

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Segment Definition & Versioning | Business Service | 1 | BR-002, RULE-001 |
| Segment Publication (Reverse-ETL) | Business Service | 1 | BR-003, RULE-008 |
| Enrolment Eligibility Evaluation | Business Service | 1 | BR-005, RULE-006, RULE-007 |
| Challenge Authoring & Lifecycle Management | Business Service | 1 | BR-006, RULE-012 |
| Wellness Score Computation & Capping | Business Service | 1 | BR-011, BR-031, RULE-014…016, RULE-019 |
| Score Breakdown / Explanation | Business Service | 1,4 | BR-012, BR-319 | 
| Title State Maintenance (7-level) | Business Service | 1 | BR-014, RULE-021, RULE-024 |
| Title History & Progression Tracking | Business Service | 1 | BR-015 |
| Reward Points Custody (double-entry) | Business Service | 1 | BR-017, RULE-025, RULE-026 |
| Marketplace Catalogue & Inventory Management | Business Service | 1,4 | BR-021, RULE-034, BR-226, RULE-232 |
| Voucher Issuance & Re-display | Business Service | 1,3 | BR-023, BR-231, RULE-033, RULE-227 |
| Nudge Decisioning & Delivery | Business Service | 1 | BR-024 |
| Inbox & Notification Preference Management | Business Service | 1 | BR-025 |
| Consent Record-Keeping | Business Service | 1 | BR-026, RULE-038 |
| Consent Resolution (hot path) | Business Service | 1,3 | BR-027, RULE-204, RULE-205 |
| Async Spine Conveyance | Business Service | 1 | BR-032, RULE-043 |
| Goal Definition | Business Service | 2 | BR-101, RULE-102 |
| Goal Progress Tracking | Business Service | 2 | BR-101, RULE-101 |
| Goal Progress View | Business Service | 2 | BR-103 |
| Streak Maintenance | Business Service | 2 | BR-105, RULE-104, RULE-105 |
| Streak State View | Business Service | 2 | BR-108 |
| Badge Awarding | Business Service | 2 | BR-109, RULE-107, RULE-108 |
| Badge Catalog Exposure | Business Service | 2 | BR-111 |
| Activity Ingestion | Business Service | 2 | BR-112, RULE-109, RULE-110 |
| Activity Audit View | Business Service | 2 | BR-115 |
| Clinical Signal Reception | Business Service | 2 | BR-116, RULE-113, RULE-114 |
| Clinical Verification | Business Service | 2 | BR-117 |
| Onboarding intro experience | Business Service | 3 | BR-201, BR-202 |
| Browse challenges / catalogue | Business Service | 3 | BR-203, BR-204, BR-228 |
| Provide rewards module | Business Service | 3 | BR-212 |
| Source marketplace catalogue | Business Service | 3 | BR-226, RULE-232 |
| Publish schema-registry event | Business Service | 4 | BR-301 |
| Fulfil redemption (YouGotaGift) | Business Service | 4 | BR-308, RULE-307 |
| Fulfil redemption / sync catalogue (Etisalat) | Business Service | 4 | BR-309, RULE-309, RULE-310 |

### (ii) Business Processes

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Eligibility Binding / Freeze-on-Publish | Business Process | 1 | BR-004, RULE-005 |
| Lifecycle State Transition | Business Process | 1 | BR-009 |
| Citizen Enrolment (with consent capture) | Business Process | 1,3 | BR-007, BR-205, RULE-011 |
| Enrolment Withdrawal / Void | Business Process | 1,3,4 | RULE-009, RULE-010, BR-211, RULE-332 |
| Challenge Request Triage | Business Process | 1 | BR-008 |
| Challenge Conclusion / Handover | Business Process | 1,4 | BR-010, BR-322, RULE-013 |
| Scoring Freeze on Conclusion | Business Process | 1 | BR-013 |
| Points Credit (idempotent) | Business Process | 1 | BR-018, RULE-027 |
| Two-Phase Reservation (reserve/confirm/cancel) | Business Process | 1,3 | BR-019, BR-230, RULE-029, RULE-031, RULE-202, RULE-219, RULE-220, RULE-221, RULE-223 |
| Redemption Orchestration & Settlement | Business Process | 1,4 | BR-022, BR-305, RULE-032 |
| Wallet Debit | Business Process | 1 | RULE-032 |
| Consent Grant / Withdraw | Business Process | 1 | BR-028, RULE-039, RULE-040 |
| Subject-Rights Request Fulfilment | Business Process | 1 | BR-029 |
| Goal Progress Evaluation | Business Process | 2 | BR-101, BR-102, RULE-101, RULE-103 |
| Badge Evaluation & Grant | Business Process | 2 | BR-110, RULE-107, RULE-108 |
| Activity Validation & Normalisation | Business Process | 2 | BR-112, RULE-110 |
| Anomaly Logging | Business Process | 2 | RULE-111 |
| Track challenge / check-in | Business Process | 3 | BR-206, BR-207 |
| Accept Terms & Conditions | Business Process | 3 | BR-205 |
| Onboard partner (KYB intake) | Business Process | 3 | BR-214, RULE-207 |
| Decide partner approval | Business Process | 3 | BR-216 |
| Provision sandbox credentials | Business Process | 3 | BR-217 |
| Push & validate catalogue item | Business Process | 3 | BR-218, RULE-209, RULE-230 |
| Release production credentials | Business Process | 3 | BR-219 |
| Member redemption loop | Business Process | 3 | BR-220, BR-228, RULE-210, RULE-211, RULE-231 |
| Handle redemption failure | Business Process | 3 | BR-221, RULE-212, RULE-222 |
| Run settlement / reconcile | Business Process | 3 | BR-222, RULE-213, RULE-214 |
| Generate invoice & route payment | Business Process | 3 | BR-223, RULE-215, RULE-216 |
| Offboard partner | Business Process | 3 | BR-224, BR-225, RULE-206, RULE-217, RULE-218 |
| Manage partner lifecycle (admin) | Business Process | 3 | BR-229, RULE-233, RULE-234 |
| Execute redemption sequence | Business Process | 4 | BR-305 |
| Resolve uncertain redemption (inquire) | Business Process | 4 | BR-310 |
| Sweep failure paths | Business Process | 4 | BR-312, RULE-301 |
| Credit Sahatna Points to ledger | Business Process | 4 | BR-315, BR-322, RULE-319, RULE-321 |
| Dispatch scoring kernel (consume events, emit delta) | Business Process | 4 | BR-317, RULE-326 |
| Manage challenge/enrolment lifecycle | Business Process | 4 | BR-321, RULE-331 |
| Sync catalogue (4×/day + webhook) | Business Process | 4 | RULE-310 |

### (iii) Business Functions

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Cohort Identification | Business Function | 1 | BR-001 |
| Score Ledger Append | Business Function | 1 | RULE-018 |
| Title Decay (scheduled) | Business Function | 1 | BR-016, RULE-023 |
| Wallet Reconciliation / Divergence Detection | Business Function | 1 | BR-020, RULE-028 |
| Perform KYB due-diligence | Business Function | 3 | BR-215, BR-227, RULE-208 |
| Translate canonical contract (Partner Adapter) | Business Function | 4 | BR-306 |
| Select adapter / route to partner | Business Function | 4 | BR-311, RULE-311 |
| Score daily goals | Business Function | 4 | BR-313, RULE-316 |
| Award streak bonus / apply streak tier | Business Function | 4 | BR-314, RULE-317, RULE-325 |
| Compute aggregation (WeeklyScore/Points/ChallengeScore) | Business Function | 4 | BR-315, BR-318, RULE-318, RULE-320, RULE-327 |
| Evaluate ScoringPlan | Business Function | 4 | BR-316, RULE-323, RULE-324 |
| Author surveys / score check-ins | Business Function | 4 | BR-320, RULE-330 |
| Register scoring primitive | Business Function | 4 | RULE-322, RULE-328 |
| Apply concurrency / transactional outbox | Business Function | 4 | RULE-312 |
| Enforce security (encrypt/rate-limit/redact/consent-gate) | Business Function | 4 | RULE-313 |
| Size implementation (t-shirt formula) | Business Function | 4 | RULE-335 |

### (iv) Application Services & Functions (cross-cutting, Part 3)

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Resolve eligibility / consent | Application Service | 3 | RULE-204, RULE-205 |
| Authenticate API request | Application Service | 3 | RULE-229 |
| Validate / mirror identity token | Application Service | 3 | RULE-235 |
| Enforce idempotency | Application Function | 3 | RULE-203, RULE-220, RULE-228 |
| Snapshot points cost | Application Function | 3 | RULE-223, RULE-224 |
| Encrypt / redact at rest | Application Function | 3 | RULE-225, RULE-227 |

### (v) Business Interactions

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Activity Submission Acceptance | Business Interaction | 2 | BR-113 |
| Adapter operations (list_products/dispatch/inquire/cancel/handle_webhook) | Business Interaction | 4 | BR-307 |
| Ingest DoH winners.announced | Business Interaction | 4 | BR-323, RULE-333 |

### (vi) Business Events (state-changes — kept together)

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| `segment.published` (Segment Published, spine event) | Business Event | 1 | BR-030 |
| `challenge.concluded` (Challenge Concluded) | Business Event | 1,4 | RULE-013, BR-322 |
| `challenge.withdrawn` | Business Event | 4 | BR-321, RULE-332 |
| `score.cap-reached` (Cap Reached) | Business Event | 1 | RULE-020 |
| `wallet.divergence-detected` (Divergence Detected) | Business Event | 1,4 | RULE-030, BR-303, RULE-303 |
| `voucher.expired` (Voucher Expired) | Business Event | 1 | RULE-033 |
| `nudge.suppressed-by-consent` | Business Event | 1 | RULE-035 |
| `nudge.frequency-capped` | Business Event | 1 | RULE-036 |
| `goal.completed` (Goal Completion Signalling) | Business Event | 2 | BR-104 |
| `streak.at-risk` (Streak At-Risk Warning) | Business Event | 2 | BR-106, RULE-106 |
| `streak.extended` / `streak.broken` (Extension/Break Detection) | Business Event | 2 | BR-107, RULE-105 |
| `activity.verified` (Activity Verification emission) | Business Event | 2 | BR-114, RULE-110 |
| `activity.anomaly-detected` (Activity Anomaly Detection) | Business Event | 2 | RULE-111 |
| Completion acknowledgement (goal/week/challenge) | Business Event | 3 | BR-208, BR-209, BR-210, BR-213 |
| `settlement.triggered` (Settlement monthly timer) | Business Event | 3 | RULE-213 |
| `redemption.requested/reserved/fulfilled/failed/uncertain` | Business Event | 4 | BR-302, RULE-301, RULE-302 |
| `wallet.reserved/debited/released` | Business Event | 4 | BR-303, RULE-303 |
| `voucher.issued/delivered/expired/activated/inventory.low` | Business Event | 4 | BR-304 |
| `score.delta-applied` | Business Event | 2,4 | RULE-104, BR-317, RULE-326 |
| `winners.announced` | Business Event | 4 | BR-323, RULE-333 |

---

## 3. Passive Structure

### Business Objects

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Cohort | Business Object | 1 | BR-001, BR-002 |
| Population History | Business Object | 1 | BR-001 |
| Segment | Business Object | 1 | BR-002, BR-003, RULE-001, RULE-008 |
| Challenge | Business Object | 1,3,4 | BR-006, BR-009, BR-203…206, BR-211, BR-321, RULE-002, RULE-012, RULE-331 |
| ChallengeRequest | Business Object | 1 | BR-008 |
| ChallengeConclusion | Business Object | 1 | BR-010 |
| Enrolment | Business Object | 1,3,4 | BR-007, BR-205, BR-321, RULE-009…011, RULE-332 |
| Wellness Score | Business Object | 1 | BR-011, BR-031 |
| ScoringRule | Business Object | 1,4 | BR-321, RULE-014…017, RULE-315, RULE-331 |
| ScoreLedger | Business Object | 1 | BR-013, RULE-018 |
| Title State | Business Object | 1 | BR-014, BR-016, RULE-021, RULE-024 |
| Title History | Business Object | 1 | BR-015 |
| TitleRule | Business Object | 1 | RULE-022 |
| Reward Points Balance | Business Object | 1 | BR-017 |
| WalletLedger / WalletTransaction | Business Object | 1,3 | RULE-025, RULE-026, BR-222, RULE-214, RULE-219, RULE-220 |
| WalletBalance | Business Object | 1,3,4 | BR-020, BR-230, BR-303, BR-315, RULE-028, RULE-219, RULE-312, RULE-319 |
| WalletReservation (Reservation) | Business Object | 1,3 | BR-019, BR-220, BR-221, RULE-029, RULE-031, RULE-210, RULE-219, RULE-220, RULE-221 | 
| InventoryState | Business Object | 1 | BR-021, RULE-034 |
| Redemption / CanonicalRedemption | Business Object | 1,3,4 | BR-022, BR-220, BR-221, BR-305, BR-310, BR-312, RULE-032, RULE-211, RULE-222, RULE-223, RULE-231, RULE-305, RULE-306 |
| MarketplaceItem (Catalogue) | Business Object | 3,4 | BR-218, BR-225, BR-226, BR-311, RULE-209, RULE-224, RULE-230, RULE-310 |
| Voucher | Business Object / Product | 1,3,4 | BR-023, BR-225, BR-231, BR-304, BR-308, RULE-033, RULE-218, RULE-227, RULE-308, RULE-313 | type note: Product where catalogued, Object/Representation where issued |
| Nudge / Message | Business Object | 1 | BR-024 |
| Notification | Business Object | 1 | BR-025 |
| UserNotificationState | Business Object | 1 | BR-025, RULE-037 |
| ConsentRecord | Business Object | 1 | BR-026, RULE-038 |
| Consent | Business Object | 1,2,4 | BR-027, BR-028, RULE-039, RULE-114, RULE-313 |
| ConsentPurpose | Business Object | 1 | BR-028, RULE-040 |
| Subject-Rights Request | Business Object | 1 | BR-029 |
| Published Artifact | Business Object | 1 | RULE-003 |
| Leaderboard | Business Object | 1 | RULE-039 |
| GoalDefinition | Business Object | 2 | BR-101, RULE-102 |
| GoalProgress | Business Object | 2 | BR-101, BR-102, BR-103, RULE-101, RULE-103 |
| StreakState | Business Object | 2 | BR-105, BR-107, BR-108, RULE-104, RULE-105 |
| StreakRule | Business Object | 2 | RULE-105 |
| Badge | Business Object | 2 | BR-109, BR-111 |
| BadgeGrant | Business Object | 2 | BR-109, BR-110, RULE-107 |
| BadgeCatalog | Business Object | 2 | BR-111 |
| DomainEvent | Business Object | 2 | BR-110, RULE-108, RULE-120 |
| ActivitySignal | Business Object | 2 | BR-112, RULE-110 |
| ActivityEvent | Business Object | 2 | BR-115, RULE-109 |
| VerifiedActivity | Business Object | 2 | BR-102, BR-112, BR-114, RULE-103, RULE-110 | alias VerifiedActivityEvent (`activity.verified`) |
| IngestionLog | Business Object | 2 | RULE-111 |
| ClinicalSignal | Business Object | 2 | BR-116, RULE-113 |
| ClinicalRecord | Business Object | 2 | BR-117 |
| IdentityContext | Business Object | 2 | BR-118 |
| IdentityLink | Business Object | 2 | RULE-116 |
| TokenSession | Business Object | 2 | BR-118, BR-119, RULE-117 |
| FraudCheck | Business Object | 2 | BR-121, BR-122, RULE-112, RULE-121 |
| FraudCase | Business Object | 2 | BR-121, BR-123, RULE-119 |
| FraudAction | Business Object | 2 | RULE-119 |
| Event / EventSchema | Business Object | 2 | BR-124, RULE-122, RULE-123, RULE-124 |
| DeadLetterRecord | Business Object | 2 | RULE-122 |
| KYB record | Business Object | 3 | BR-215, BR-227, RULE-207, RULE-208 |
| Partner application / Partner record | Business Object | 3 | BR-214, RULE-206, RULE-207, RULE-225, RULE-234 |
| Partner approval decision | Business Object | 3 | BR-216 |
| Settlement | Business Object | 3 | BR-222, RULE-213, RULE-214, RULE-215 |
| Payment | Business Object | 3 | BR-223, RULE-216 |
| Consent / Eligibility record | Business Object | 3 | RULE-204, RULE-205, RULE-231 |
| Redemption incident / fraud log | Business Object | 3 | BR-221, RULE-212 |
| AdapterOutcome | Business Object | 4 | RULE-305 |
| AdapterCapability | Business Object | 4 | BR-307 |
| RoutingPolicy | Business Object | 4 | BR-311, RULE-311 |
| PartnerCallBudget | Business Object | 4 | RULE-304 |
| ScoringPlan (typed, versioned, frozen) | Business Object | 4 | BR-316, BR-317, RULE-323, RULE-324, RULE-328, RULE-334 |
| ScoringPrimitive | Business Object | 4 | BR-316, RULE-322, RULE-328 |
| DailyGoalScore / BalancedDayBonus | Business Object | 4 | BR-313, RULE-316 |
| StreakTier / StreakBonus | Business Object | 4 | BR-314, RULE-317, RULE-325 |
| WeeklyScore | Business Object | 4 | BR-315, RULE-318 |
| SahatnaPoints (cumulative) | Business Object | 4 | BR-315, BR-322, RULE-319, RULE-321 |
| ChallengeScore | Business Object | 4 | BR-315, RULE-320 |
| AggregateTotal / AggregationDimension | Business Object | 4 | BR-318, BR-319, RULE-327, RULE-329 |
| Survey / Questionnaire | Business Object | 4 | BR-320, RULE-330 |
| ImplementationEstimate | Business Object | 4 | RULE-335 |
| Smiles Rewards Exchange (blockchain, not integrated) | Business Object | 4 | RULE-308 |

### Data Objects

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Spine Event / Event envelope | Data Object | 1,4 | BR-030, BR-032, BR-301, RULE-043 | type note: also surfaced as Business Event; envelope persisted = Data Object |
| Partner credentials | Data Object | 3 | BR-217, BR-219, RULE-225 |
| Ledger / WalletTransaction (persisted) | Data Object | 3 | BR-222, RULE-214, RULE-219, RULE-220 |
| source_event_id / Idempotency-Key | Data Object | 3,4 | RULE-203, RULE-220, RULE-228, RULE-307 |
| User profile (mirror) | Data Object | 3 | RULE-235 |
| Identity token | Data Object | 3 | RULE-229, RULE-235 |
| RedemptionAttempt (idempotency overlay) | Data Object | 4 | RULE-307 |
| ProductOrder (TMF622) | Data Object | 4 | BR-309, RULE-309 |
| ProductOffering (TMF620) | Data Object | 4 | BR-309, RULE-310 |
| Transactional outbox | Data Object | 4 | RULE-312 |

### Contracts

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| EligibilityBinding | Contract | 1 | BR-004, RULE-005 |
| Challenge Contract | Contract | 1 | RULE-005 |
| Contract (PDPL addendum) | Contract | 3 | RULE-226 |
| CanonicalContract / partner native API | Contract | 4 | BR-306 |
| RedemptionAPI contract | Contract | 4 | RULE-314 |

### Representations

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Segment Snapshot (membership list + predicate) | Representation | 1 | BR-003, BR-007, RULE-002, RULE-007 |
| Score Breakdown / Explanation | Representation | 1,4 | BR-012, BR-319 |
| Terms & Conditions | Representation | 3 | BR-205 |
| VAT invoice | Representation | 3 | BR-223 |
| Presentation content (CMS) | Representation | 3 | RULE-201 |
| JWKS | Representation | 2 | BR-119, RULE-117 |
| Daily check-in | Representation | 3 | BR-207 |
| ActivitySubmission | Representation | 2 | BR-113 |

### Products

| Canonical name | ArchiMate type | Slices | Source IDs |
|----------------|----------------|--------|------------|
| Winners / Prizes | Product | 1 | BR-010, RULE-041 |

---

## Modelling notes

- **WALLET / MARKET / Voucher / Redemption / Reservation are the heaviest cross-slice merges** (3-4 parts each). Parts 1 and 4 model them as the internal WALLET-SVC/MARKET-SVC families; Part 3 models the same things from the partner-onboarding/settlement angle ("Wallet SVC", "Marketplace SVC"). Treated as single canonical components/objects — confirm the Part-3 "Reward points / WalletBalance" really is the same balance as Part-4 SahatnaPoints (likely a different ledger: Reward Points vs Sahatna Points — flagged).
- **"Aggregator" is overloaded.** Part-3 lists external voucher *aggregators* (YouGotaGift/Reloadly/e&/Smiles) as Business Actors; Part-4 lists an internal scoring *Aggregator* Application Component. Kept as two distinct rows — a human should confirm the naming so they are never conflated.
- **EVENT-SVC / Event Hub spine / Event Consumer / Spine Event** collapse to one component plus one passive envelope, but the envelope appears as both Business Event (state-change) and Data Object (persisted record). Chose to list the persisted form under Data Objects and the state-changes under Business Events; the schema-registry "Event/EventSchema/DeadLetterRecord" stay Business Objects.
- **Type disagreements resolved:** PartnerAdapter is Component (Parts 3/4 sometimes tag it Application Interface — that is the exposed interface, not the adapter); DoH is Actor (one slice said Actor/Role); Voucher is Product when catalogued / Object-or-Representation when issued (note carried inline).
- **CONS-SVC vs Consent Resolver / Eligibility Resolver:** folded Part-3 "Consent Resolver" into CONS-SVC but kept "Eligibility Resolver" separate (eligibility is a distinct concern from consent). Confirm whether these are one service or two.
- **Government API Marketplace** appears as both an external Business Actor and a gateway Application Component — left as two rows; a human should decide if the platform-side gateway warrants its own component.
- **Unresolved for human review:** (a) "CHAL/SCORE/STREAK contract" (Part-3 RULE-201) may just be a content facade that folds into the three SVCs; (b) Part-2 "Reward Points" ledger vs Part-4 "Sahatna Points" — same or different currency?; (c) Title-Decay Engine modelled as a function inside TITLE-SVC rather than a separate component.
