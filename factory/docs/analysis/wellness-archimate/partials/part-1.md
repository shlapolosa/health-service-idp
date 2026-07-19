# Wellness Platform — ArchiMate Extraction, Part 1 (lines 1–200)

Source: `/tmp/wellness_doc.txt`, Executive summary + Part 0 (BPMN process overview) + Part 1 Logical ABBs (CHAL-SVC, SCORE-SVC, TITLE-SVC, WALLET-SVC, MARKET-SVC, NUDGE-SVC, CONS-SVC).

## Business Requirements

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| BR-001 | Identify target cohorts from population history to answer "who should this challenge target?" | Phase A — Cohort identification | Business Function | 20–24 |
| BR-002 | Define a cohort as a named, versioned, publishable segment that a challenge can bind to | Cohort vs segment, and versioning | Business Service | 25–26 |
| BR-003 | Publish a segment to the operational side (reverse-ETL) as a membership list and/or portable predicate via the async spine and a fast read store | How a segment is published | Business Service | 27–29 |
| BR-004 | Bind a challenge to a specific segment_id + version at authoring time via an EligibilityBinding | Binding and the enrolment-time eligibility gate | Business Process | 30–31 |
| BR-005 | Evaluate enrolment eligibility deterministically (set lookup or predicate) against the bound segment at the enrolment moment | Binding / OLAP-OLTP seam | Business Service | 31, 37–38 |
| BR-006 | Author, version and lifecycle-manage challenges from authoring through retirement | CHAL-SVC mission | Business Service | 49–50 |
| BR-007 | Enrol a citizen into a challenge with consent capture | CHAL-SVC sync interfaces | Business Process | 62 |
| BR-008 | Accept citizen-submitted challenge requests for triage | CHAL-SVC (ChallengeRequest) | Business Process | 57, 65 |
| BR-009 | Transition a challenge through its lifecycle states (publish, conclude, archive) | CHAL-SVC lifecycle | Business Process | 64, 68–71 |
| BR-010 | Conclude a challenge, handing winners and prizes to the Department of Health | Spine / ChallengeConclusion | Business Process | 17, 58, 70 |
| BR-011 | Compute, cap and explain the Wellness Score for every active member-challenge in near-real time | SCORE-SVC mission | Business Service | 75–76 |
| BR-012 | Provide a score breakdown/explanation to the UI | SCORE-SVC interfaces | Business Service | 85 |
| BR-013 | Freeze scoring on conclusion (admin / Conclusion Orchestrator trigger) | SCORE-SVC freeze | Business Process | 86, 91 |
| BR-014 | Maintain a durable 7-level Title state per member, independent of any challenge | TITLE-SVC mission | Business Service | 95–96 |
| BR-015 | Track longitudinal title history and progression to next level | TITLE-SVC interfaces | Business Service | 104–105 |
| BR-016 | Optionally decay titles on a schedule (conditional Decay Engine) | Key decisions / TITLE-SVC | Business Function | 10, 48, 102, 109 |
| BR-017 | Hold the authoritative Reward Points balance per user with double-entry semantics | WALLET-SVC mission | Business Service | 113–114 |
| BR-018 | Credit reward points (idempotent on source event) on challenge completion | WALLET-SVC credits | Business Process | 124, 128 |
| BR-019 | Reserve, confirm or cancel points for the redemption flow (two-phase reservation) | WALLET-SVC reservations | Business Process | 11, 125–126 |
| BR-020 | Reconcile wallet balances and detect divergence | WALLET-SVC divergence | Business Function | 11, 131 |
| BR-021 | Catalogue redeemable items and manage inventory | MARKET-SVC mission | Business Service | 135–136 |
| BR-022 | Orchestrate redemption end-to-end including voucher delivery and partner settlement | MARKET-SVC redemption | Business Process | 136, 147, 151 |
| BR-023 | Issue and re-display vouchers (code + QR token) | MARKET-SVC vouchers | Business Service | 143, 148 |
| BR-024 | Decide, target and deliver the right message to the right user at the right time across push/email/in-app | NUDGE-SVC mission | Business Service | 158–159 |
| BR-025 | Provide a citizen inbox/notifications view and notification preference management | NUDGE-SVC interfaces | Business Service | 169–170 |
| BR-026 | Maintain the authoritative record of who consented to what, when, and via which mechanism | CONS-SVC mission | Business Service | 179–180 |
| BR-027 | Resolve consent on the hot path for every consent-gated action | CONS-SVC resolver | Business Service | 181, 188 |
| BR-028 | Grant or withdraw consent per purpose | CONS-SVC interfaces | Business Process | 189 |
| BR-029 | Accept and fulfil subject-rights requests | CONS-SVC subject-rights | Business Process | 186, 191, 195 |
| BR-030 | Publish a segment as an asynchronous spine event (segment.published) | Publication / spine | Business Event | 29, 33 |
| BR-031 | Score daily activity and surveys against the frozen rules, crediting weekly score x10 | Spine one-liner / earning loop | Business Process | 17, 36 |
| BR-032 | Cross-ABB communication defaults to asynchronous events via the Event Hub spine | Spatial view | Business Service | 44 |

## Business Rules

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| RULE-001 | A segment must be stamped with segment_id + version + as_of when published (versioned artifact) | Cohort vs segment, and versioning | Business Object | 26 |
| RULE-002 | A challenge must reference a frozen segment snapshot so eligibility is reproducible and auditable | Cohort vs segment, and versioning | Business Rule (Constraint) | 26 |
| RULE-003 | Hard invariant: OLTP reads only published artifacts; it never queries the warehouse live | How a segment is published / OLAP-OLTP seam | Business Rule (Constraint) | 29, 38 |
| RULE-004 | The warehouse is never the source of truth for state or money | Publication / OLAP-OLTP seam | Business Rule (Constraint) | 29, 38 |
| RULE-005 | The eligibility binding {segmentId, segmentVersion} is frozen into the challenge contract on PUBLISH | Binding and the eligibility gate | Business Rule (Constraint) | 31 |
| RULE-006 | Enrolment eligibility must be evaluated deterministically and return in <50ms | Binding / OLAP-OLTP seam | Business Rule (Constraint) | 31, 38 |
| RULE-007 | A late joiner not in the membership snapshot may still pass via the published predicate path | Binding / worked example | Business Rule (Constraint) | 31, 33 |
| RULE-008 | A published segment must support audit-time proof of why a given user was eligible months later | Versioning / worked example | Business Rule (Driver) | 26, 33 |
| RULE-009 | Enrolment withdrawal is irreversible: progress and rewards are voided | CHAL-SVC Enrolment entity | Business Rule (Constraint) | 56 |
| RULE-010 | An Enrolment status is constrained to {enrolled, withdrawn, completed} | CHAL-SVC Enrolment entity | Business Object | 56 |
| RULE-011 | An Enrolment must capture consent_set and terms_version at enrolment | CHAL-SVC Enrolment / enrol interface | Business Rule (Constraint) | 56, 62 |
| RULE-012 | A Challenge is a durable, versionable, lifecycle-aware entity (id, version, status) | CHAL-SVC mission / entity | Business Object | 50, 54 |
| RULE-013 | challenge.concluded triggers Scoring freeze, Wallet credit, and Comms | CHAL-SVC events | Business Event | 70 |
| RULE-014 | Scoring is capped: daily_cap per activity and weekly_cap=100 | SCORE-SVC ScoringRule | Business Rule (Constraint) | 82 |
| RULE-015 | Earning rates: Steps +5/day, Sleep +2/day, Wellbeing/Nutrition check-in +1/day (completion-scored) | SCORE-SVC ScoringRule | Business Rule (Constraint) | 82 |
| RULE-016 | BalancedDayRule awards +3 for all-goals-met in a day; StreakRule applies (per Part 8) | SCORE-SVC ScoringRule | Business Rule (Constraint) | 82 |
| RULE-017 | A ScoringRule is versioned per challenge (challenge_id, version) | SCORE-SVC ScoringRule | Business Object | 82 |
| RULE-018 | ScoreLedger is append-only / event-keyed (user_id, challenge_id, event_id, delta) | SCORE-SVC ScoreLedger | Business Object | 80 |
| RULE-019 | Score is computed only from verified activity (consumes activity.verified) | SCORE-SVC events | Business Rule (Constraint) | 88 |
| RULE-020 | Reaching the cap emits score.cap-reached, triggering a behavioural intervention | SCORE-SVC events | Business Event | 90 |
| RULE-021 | Title state is durable across challenges and follows a 7-level progression | TITLE-SVC mission | Business Rule (Constraint) | 96 |
| RULE-022 | A TitleRule defines points_required per level and an optional decay_schedule per version | TITLE-SVC TitleRule | Business Object | 102 |
| RULE-023 | Title decay only occurs if decay is enabled (Decay Engine is the only conditional component) | Key decisions / TITLE-SVC | Business Rule (Assessment) | 10, 48, 109 |
| RULE-024 | Without decay, Title is a monotonic state machine; with decay it becomes a scheduled-job service | Key decisions surfaced | Business Rule (Assessment) | 10 |
| RULE-025 | The Wallet is an append-only ledger with two-phase reservation, strong balance consistency and reconciliation (financial-grade) | Key decisions / WALLET-SVC mission | Business Rule (Constraint) | 11, 114 |
| RULE-026 | Every wallet transaction must enforce double-entry semantics | WALLET-SVC mission | Business Rule (Constraint) | 114 |
| RULE-027 | Wallet credits are idempotent on source_event_id | WALLET-SVC credits | Business Rule (Constraint) | 124 |
| RULE-028 | WalletBalance carries a version for optimistic-concurrency / strong consistency | WALLET-SVC WalletBalance | Business Object | 118 |
| RULE-029 | A WalletReservation has an expires_at and confirmed flag (reservations time out if unconfirmed) | WALLET-SVC WalletReservation | Business Object | 120 |
| RULE-030 | Detected balance divergence emits wallet.divergence-detected as an operations alert | WALLET-SVC events | Business Event | 131 |
| RULE-031 | A failed redemption cancels the wallet reservation | MARKET-SVC events | Business Rule (Constraint) | 152 |
| RULE-032 | A confirmed redemption triggers the wallet debit | MARKET-SVC events | Business Rule (Constraint) | 151 |
| RULE-033 | A Voucher has expires_at and a redeemed flag; expiry emits voucher.expired with advance warning | MARKET-SVC Voucher / events | Business Object | 143, 154 |
| RULE-034 | Marketplace items are filtered by eligibility and stock; inventory tracks available/reserved/threshold | MARKET-SVC interfaces / InventoryState | Business Rule (Constraint) | 141, 145 |
| RULE-035 | Nudge delivery is fully consent-gated; suppressed deliveries emit nudge.suppressed-by-consent for audit | NUDGE-SVC mission / events | Business Rule (Constraint) | 159, 174 |
| RULE-036 | Nudge delivery respects a per-user, per-channel frequency budget; over-budget emits nudge.frequency-capped | NUDGE-SVC UserNotificationState / events | Business Rule (Constraint) | 166, 175 |
| RULE-037 | UserNotificationState holds per-category consent and frequency budget per channel | NUDGE-SVC entity | Business Object | 166 |
| RULE-038 | A ConsentRecord is versioned and records the mechanism and granted_at | CONS-SVC ConsentRecord | Business Object | 184 |
| RULE-039 | Consent withdrawal triggers downstream cleanups (e.g., leaderboard removal) | CONS-SVC events | Business Rule (Constraint) | 194 |
| RULE-040 | A ConsentPurpose is versioned with a current flag (only one current version per purpose) | CONS-SVC ConsentPurpose | Business Object | 185 |
| RULE-041 | The Department of Health is the recipient actor for concluded-challenge winners and prizes | Spine one-liner | Business Role/Actor | 17 |
| RULE-042 | The citizen (member) is the actor who enrols and earns; the admin authors and freezes challenges | Spine one-liner | Business Role/Actor | 17 |
| RULE-043 | Cross-trust-boundary steps and async spine events are first-class process constructs (boundary ‖ / event ✉) | Part 0 notation | Business Rule (Constraint) | 18 |
