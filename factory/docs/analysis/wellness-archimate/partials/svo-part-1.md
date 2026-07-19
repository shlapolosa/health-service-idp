# Wellness Platform — S-V-O Decomposition, Part 1

Grammatical decomposition of every BR-* and RULE-* in `part-1.md` into (Subject, Action, Object) triples, then deduplicated Active / Behaviour / Passive inventories.

ABB convention: CHAL-SVC, SCORE-SVC, TITLE-SVC, WALLET-SVC, MARKET-SVC, NUDGE-SVC, CONS-SVC are Application Components (logical services) acting as Subjects. Human/org subjects (Citizen/Member, Admin, Department of Health) are Business Actors/Roles.

## S-V-O triples

| Triple# | Source ID | Subject | Action | Object |
|---------|-----------|---------|--------|--------|
| T-001 | BR-001 | SCORE-SVC / Cohort Analytics (OLAP) | Identify target cohorts | Cohort / Population History |
| T-002 | BR-002 | Cohort Analytics (OLAP) | Define / version cohort as publishable segment | Segment |
| T-003 | BR-003 | Reverse-ETL / Publication | Publish segment to operational side | Segment (Membership List + Predicate) |
| T-004 | BR-004 | CHAL-SVC | Bind challenge to segment_id + version | EligibilityBinding |
| T-005 | BR-005 | CHAL-SVC | Evaluate enrolment eligibility deterministically | Bound Segment |
| T-006 | BR-006 | CHAL-SVC | Author, version, lifecycle-manage | Challenge |
| T-007 | BR-007 | CHAL-SVC | Enrol citizen with consent capture | Enrolment |
| T-008 | BR-008 | CHAL-SVC | Accept for triage | ChallengeRequest |
| T-009 | BR-009 | CHAL-SVC | Transition through lifecycle states | Challenge |
| T-010 | BR-010 | CHAL-SVC | Conclude, hand winners/prizes | ChallengeConclusion |
| T-011 | BR-010 | Department of Health | Receive winners and prizes | Winners / Prizes |
| T-012 | BR-011 | SCORE-SVC | Compute, cap, explain in near-real-time | Wellness Score |
| T-013 | BR-012 | SCORE-SVC | Provide breakdown/explanation | Score Breakdown |
| T-014 | BR-013 | SCORE-SVC (Conclusion Orchestrator) | Freeze scoring on conclusion | Scoring / ScoreLedger |
| T-015 | BR-014 | TITLE-SVC | Maintain durable 7-level title state | Title State |
| T-016 | BR-015 | TITLE-SVC | Track history and progression | Title History |
| T-017 | BR-016 | TITLE-SVC (Decay Engine) | Decay titles on schedule | Title State |
| T-018 | BR-017 | WALLET-SVC | Hold authoritative balance (double-entry) | Reward Points Balance |
| T-019 | BR-018 | WALLET-SVC | Credit points (idempotent) on completion | Reward Points / ScoreLedger entry |
| T-020 | BR-019 | WALLET-SVC | Reserve / confirm / cancel points | WalletReservation |
| T-021 | BR-020 | WALLET-SVC | Reconcile balances, detect divergence | WalletBalance |
| T-022 | BR-021 | MARKET-SVC | Catalogue items, manage inventory | Marketplace Item / InventoryState |
| T-023 | BR-022 | MARKET-SVC | Orchestrate redemption, settle partner | Redemption |
| T-024 | BR-023 | MARKET-SVC | Issue and re-display | Voucher |
| T-025 | BR-024 | NUDGE-SVC | Decide, target, deliver message | Nudge / Message |
| T-026 | BR-025 | NUDGE-SVC | Provide inbox and preference management | Notification / UserNotificationState |
| T-027 | BR-026 | CONS-SVC | Maintain authoritative record | ConsentRecord |
| T-028 | BR-027 | CONS-SVC | Resolve consent on hot path | Consent |
| T-029 | BR-028 | CONS-SVC | Grant or withdraw per purpose | Consent / ConsentPurpose |
| T-030 | BR-029 | CONS-SVC | Accept and fulfil | Subject-Rights Request |
| T-031 | BR-030 | Publication / spine | Publish as async spine event | segment.published Event |
| T-032 | BR-031 | SCORE-SVC | Score daily activity/surveys against frozen rules | Activity / Survey / Wellness Score |
| T-033 | BR-032 | Event Hub spine | Convey cross-ABB communication asynchronously | Spine Event |
| T-034 | RULE-001 | Publication | Stamp segment_id + version + as_of | Segment |
| T-035 | RULE-002 | CHAL-SVC | Reference frozen segment snapshot | Challenge / Segment Snapshot |
| T-036 | RULE-003 | OLTP | Read only published artifacts (never query warehouse) | Published Artifact |
| T-037 | RULE-004 | Warehouse | Is never source of truth | State / Money |
| T-038 | RULE-005 | CHAL-SVC | Freeze {segmentId, segmentVersion} on PUBLISH | EligibilityBinding / Challenge Contract |
| T-039 | RULE-006 | CHAL-SVC | Evaluate deterministically <50ms | Enrolment Eligibility |
| T-040 | RULE-007 | CHAL-SVC | Admit late joiner via published predicate | Predicate / Enrolment |
| T-041 | RULE-008 | Publication | Support audit-time eligibility proof | Segment |
| T-042 | RULE-009 | CHAL-SVC | Void progress and rewards on withdrawal | Enrolment |
| T-043 | RULE-010 | CHAL-SVC | Constrain status to {enrolled, withdrawn, completed} | Enrolment |
| T-044 | RULE-011 | CHAL-SVC | Capture consent_set and terms_version | Enrolment |
| T-045 | RULE-012 | CHAL-SVC | Be durable, versionable, lifecycle-aware | Challenge |
| T-046 | RULE-013 | CHAL-SVC | Emit challenge.concluded (triggers freeze/credit/comms) | challenge.concluded Event |
| T-047 | RULE-014 | SCORE-SVC | Cap scoring (daily_cap, weekly_cap=100) | ScoringRule / Wellness Score |
| T-048 | RULE-015 | SCORE-SVC | Apply earning rates | ScoringRule |
| T-049 | RULE-016 | SCORE-SVC | Apply BalancedDayRule / StreakRule | ScoringRule |
| T-050 | RULE-017 | SCORE-SVC | Version per challenge | ScoringRule |
| T-051 | RULE-018 | SCORE-SVC | Append event-keyed entries | ScoreLedger |
| T-052 | RULE-019 | SCORE-SVC | Compute only from verified activity | activity.verified Event |
| T-053 | RULE-020 | SCORE-SVC | Emit score.cap-reached (triggers intervention) | score.cap-reached Event |
| T-054 | RULE-021 | TITLE-SVC | Keep durable across challenges (7-level) | Title State |
| T-055 | RULE-022 | TITLE-SVC | Define points_required + decay_schedule | TitleRule |
| T-056 | RULE-023 | TITLE-SVC (Decay Engine) | Decay only if enabled | Title State |
| T-057 | RULE-024 | TITLE-SVC | Be monotonic without decay / scheduled with decay | Title State |
| T-058 | RULE-025 | WALLET-SVC | Be append-only with two-phase reservation + reconciliation | WalletLedger |
| T-059 | RULE-026 | WALLET-SVC | Enforce double-entry semantics | Wallet Transaction |
| T-060 | RULE-027 | WALLET-SVC | Be idempotent on source_event_id | Reward Points / Credit |
| T-061 | RULE-028 | WALLET-SVC | Carry version for optimistic concurrency | WalletBalance |
| T-062 | RULE-029 | WALLET-SVC | Time out unconfirmed reservation (expires_at) | WalletReservation |
| T-063 | RULE-030 | WALLET-SVC | Emit wallet.divergence-detected | wallet.divergence-detected Event |
| T-064 | RULE-031 | MARKET-SVC | Cancel reservation on failed redemption | WalletReservation |
| T-065 | RULE-032 | MARKET-SVC | Trigger wallet debit on confirmed redemption | Redemption / Wallet Debit |
| T-066 | RULE-033 | MARKET-SVC | Set expires_at/redeemed; emit voucher.expired | Voucher / voucher.expired Event |
| T-067 | RULE-034 | MARKET-SVC | Filter by eligibility and stock | Marketplace Item / InventoryState |
| T-068 | RULE-035 | NUDGE-SVC | Consent-gate delivery; emit nudge.suppressed-by-consent | Nudge / nudge.suppressed-by-consent Event |
| T-069 | RULE-036 | NUDGE-SVC | Respect frequency budget; emit nudge.frequency-capped | Nudge / nudge.frequency-capped Event |
| T-070 | RULE-037 | NUDGE-SVC | Hold per-category consent + frequency budget | UserNotificationState |
| T-071 | RULE-038 | CONS-SVC | Version, record mechanism + granted_at | ConsentRecord |
| T-072 | RULE-039 | CONS-SVC | Trigger downstream cleanups on withdrawal | Consent / Leaderboard |
| T-073 | RULE-040 | CONS-SVC | Version with single current flag | ConsentPurpose |
| T-074 | RULE-041 | Department of Health | Recipient of winners and prizes | Winners / Prizes |
| T-075 | RULE-042a | Citizen (Member) | Enrol and earn | Enrolment / Wellness Score |
| T-076 | RULE-042b | Admin | Author and freeze challenges | Challenge |
| T-077 | RULE-043 | Event Hub spine | Convey cross-trust-boundary async events | Spine Event |

## Active Structure elements

| Element name | Proposed ArchiMate type | Source BR/RULE IDs |
|--------------|------------------------|--------------------|
| CHAL-SVC | Application Component | BR-004, BR-005, BR-006, BR-007, BR-008, BR-009, BR-010, RULE-002, RULE-005, RULE-006, RULE-007, RULE-009, RULE-010, RULE-011, RULE-012, RULE-013 |
| SCORE-SVC | Application Component | BR-001, BR-011, BR-012, BR-013, BR-031, RULE-014, RULE-015, RULE-016, RULE-017, RULE-018, RULE-019, RULE-020 |
| TITLE-SVC | Application Component | BR-014, BR-015, BR-016, RULE-021, RULE-022, RULE-023, RULE-024 |
| TITLE-SVC / Decay Engine | Application Component (conditional) | BR-016, RULE-023 |
| WALLET-SVC | Application Component | BR-017, BR-018, BR-019, BR-020, RULE-025, RULE-026, RULE-027, RULE-028, RULE-029, RULE-030 |
| MARKET-SVC | Application Component | BR-021, BR-022, BR-023, RULE-031, RULE-032, RULE-033, RULE-034 |
| NUDGE-SVC | Application Component | BR-024, BR-025, RULE-035, RULE-036, RULE-037 |
| CONS-SVC | Application Component | BR-026, BR-027, BR-028, BR-029, RULE-038, RULE-039, RULE-040 |
| Cohort Analytics (OLAP / Warehouse) | Application Component | BR-001, BR-002, RULE-004 |
| Reverse-ETL / Publication | Application Component | BR-003, BR-030, RULE-001, RULE-008 |
| OLTP Read Store | Application Component | RULE-003 |
| Event Hub spine | Application Component (Collaboration/Bus) | BR-032, BR-030, RULE-043 |
| Conclusion Orchestrator | Application Component | BR-013, RULE-013 |
| Citizen (Member) | Business Actor / Role | BR-007, RULE-042 |
| Admin | Business Role | RULE-042 |
| Department of Health | Business Actor / Role | BR-010, RULE-041 |

Distinct Active Structure elements: 16

## Behaviour elements

| Element name | Proposed ArchiMate type | Source IDs |
|--------------|------------------------|-----------|
| Cohort Identification | Business Function | BR-001 |
| Segment Definition & Versioning | Business Service | BR-002, RULE-001 |
| Segment Publication (Reverse-ETL) | Business Service | BR-003, RULE-008 |
| Segment Published (spine event) | Business Event | BR-030 |
| Eligibility Binding / Freeze-on-Publish | Business Process | BR-004, RULE-005 |
| Enrolment Eligibility Evaluation | Business Service | BR-005, RULE-006, RULE-007 |
| Challenge Authoring & Lifecycle Management | Business Service | BR-006, RULE-012 |
| Lifecycle State Transition | Business Process | BR-009 |
| Citizen Enrolment (with consent capture) | Business Process | BR-007, RULE-011 |
| Enrolment Withdrawal / Void | Business Process | RULE-009, RULE-010 |
| Challenge Request Triage | Business Process | BR-008 |
| Challenge Conclusion / Handover | Business Process | BR-010, RULE-013 |
| Challenge Concluded (event) | Business Event | RULE-013 |
| Wellness Score Computation & Capping | Business Service | BR-011, BR-031, RULE-014, RULE-015, RULE-016, RULE-019 |
| Score Breakdown / Explanation | Business Service | BR-012 |
| Scoring Freeze on Conclusion | Business Process | BR-013 |
| Score Ledger Append | Business Function | RULE-018 |
| Cap Reached (event) | Business Event | RULE-020 |
| Title State Maintenance (7-level) | Business Service | BR-014, RULE-021, RULE-024 |
| Title History & Progression Tracking | Business Service | BR-015 |
| Title Decay (scheduled) | Business Function | BR-016, RULE-023 |
| Reward Points Custody (double-entry) | Business Service | BR-017, RULE-025, RULE-026 |
| Points Credit (idempotent) | Business Process | BR-018, RULE-027 |
| Two-Phase Reservation (reserve/confirm/cancel) | Business Process | BR-019, RULE-029, RULE-031 |
| Wallet Reconciliation / Divergence Detection | Business Function | BR-020, RULE-028 |
| Divergence Detected (event) | Business Event | RULE-030 |
| Marketplace Catalogue & Inventory Management | Business Service | BR-021, RULE-034 |
| Redemption Orchestration & Settlement | Business Process | BR-022, RULE-032 |
| Wallet Debit | Business Process | RULE-032 |
| Voucher Issuance & Re-display | Business Service | BR-023, RULE-033 |
| Voucher Expired (event) | Business Event | RULE-033 |
| Nudge Decisioning & Delivery | Business Service | BR-024 |
| Nudge Suppressed-by-Consent (event) | Business Event | RULE-035 |
| Nudge Frequency-Capped (event) | Business Event | RULE-036 |
| Inbox & Notification Preference Management | Business Service | BR-025 |
| Consent Record-Keeping | Business Service | BR-026, RULE-038 |
| Consent Resolution (hot path) | Business Service | BR-027 |
| Consent Grant / Withdraw | Business Process | BR-028, RULE-039, RULE-040 |
| Subject-Rights Request Fulfilment | Business Process | BR-029 |
| Async Spine Conveyance | Business Service | BR-032, RULE-043 |

Distinct Behaviour elements: 40

## Passive Structure elements

| Element name | Proposed ArchiMate type | Source IDs |
|--------------|------------------------|-----------|
| Cohort | Business Object | BR-001, BR-002 |
| Population History | Business Object | BR-001 |
| Segment | Business Object | BR-002, BR-003, RULE-001, RULE-008 |
| Segment Snapshot (membership list + predicate) | Representation | BR-003, BR-007 (RULE-002, RULE-007) |
| EligibilityBinding | Contract | BR-004, RULE-005 |
| Challenge | Business Object | BR-006, BR-009, RULE-002, RULE-012 |
| Challenge Contract | Contract | RULE-005 |
| ChallengeRequest | Business Object | BR-008 |
| Enrolment | Business Object | BR-007, RULE-009, RULE-010, RULE-011 |
| ChallengeConclusion | Business Object | BR-010 |
| Winners / Prizes | Product | BR-010, RULE-041 |
| Wellness Score | Business Object | BR-011, BR-031 |
| Score Breakdown / Explanation | Representation | BR-012 |
| ScoringRule | Business Object | RULE-014, RULE-015, RULE-016, RULE-017 |
| ScoreLedger | Business Object | BR-013, RULE-018 |
| Title State | Business Object | BR-014, BR-016, RULE-021, RULE-024 |
| Title History | Business Object | BR-015 |
| TitleRule | Business Object | RULE-022 |
| Reward Points Balance | Business Object | BR-017 |
| WalletLedger | Business Object | RULE-025 |
| Wallet Transaction | Business Object | RULE-026 |
| WalletBalance | Business Object | BR-020, RULE-028 |
| WalletReservation | Business Object | BR-019, RULE-029, RULE-031 |
| Marketplace Item | Product | BR-021, RULE-034 |
| InventoryState | Business Object | BR-021, RULE-034 |
| Redemption | Business Object | BR-022, RULE-032 |
| Voucher | Representation / Product | BR-023, RULE-033 |
| Nudge / Message | Business Object | BR-024 |
| Notification | Business Object | BR-025 |
| UserNotificationState | Business Object | BR-025, RULE-037 |
| ConsentRecord | Business Object | BR-026, RULE-038 |
| Consent | Business Object | BR-027, BR-028, RULE-039 |
| ConsentPurpose | Business Object | BR-028, RULE-040 |
| Subject-Rights Request | Business Object | BR-029 |
| Published Artifact | Business Object | RULE-003 |
| Spine Event | Business Event / Data Object | BR-030, BR-032, RULE-043 |
| Leaderboard | Business Object | RULE-039 |

Distinct Passive Structure elements: 37
