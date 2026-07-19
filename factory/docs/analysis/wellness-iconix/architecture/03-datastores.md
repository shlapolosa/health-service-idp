# Solution Structure — Data Layer: Datastore Inventory (Database-per-Service)

**Derivation**: each bounded context in `02-logic-bounded-contexts.md` owns its own datastore (database-per-service). No store is shared across contexts; cross-context data flows as **events** or **read-model replicas**, never as a shared table.
**Inputs**: the 43 domain classes in `02-domain-model.md` + the aggregate roots assigned per context.
**Scope**: Phase-1 individual-only. `[P2]`/`[P3]` entities live in their P1-owning context's store but carry no P1 write path.

**Store-type policy**
- **PostgreSQL** — relational/transactional system-of-record (challenge config, membership, scoring finalization, redemptions, settlement).
- **Append-only ledger** — immutable, double-entry, balance = fold-of-transactions (points wallet) and high-volume immutable ingest (activity).
- **Cache / read-model (Redis)** — derived, rebuildable, low-latency reads (leaderboards, eligibility projections). Never a system-of-record.
- **Object storage** — binary artifacts (reward images, share-card images).
- **Event log / stream** — cross-context integration backbone (the event bus carrying domain events between services).

---

## 1. Datastore Inventory

| # | Store | Type | Aggregates / Entities persisted | Owning context → microservice | Consistency notes |
|---|-------|------|----------------------------------|-------------------------------|-------------------|
| D1 | `challenge-db` | PostgreSQL | Challenge, ChallengeRequest, EligibilityRule, WinningCriteria, ScoringPlan, ScoreComponent, Goal (definition), Segment, NotificationType, **Content metadata + asset URIs** | C1 Authoring → `challenge-svc` | Strong/ACID. Invariant: Σ ScoreComponent.weeklyAllocation = 100; status lifecycle Draft→Active→Completed→Archived enforced in-aggregate. Source-of-record for challenge config; published immutably to downstream via `ChallengePublished` event. Holds **references** (URIs) to content blobs, not the blobs. |
| D1b | `challenge-content-store` | Object storage | Challenge **content assets** — images, icons, localized (AR/EN) rich descriptions / media authored for a challenge | C1 Authoring → `challenge-svc` | Binary/large blobs authored into the bucket during configuration (UC-A4/A6); referenced by URI from `challenge-db`. Served read-only to the Mobile App (via BFF/CDN) once published. Sibling to `reward-image-store`. |
| D2 | `eligibility-cache` | Cache / read-model (Redis) | CohortScope (+ projected Segment↔EligibilityRule match index) | C2 Eligibility → `eligibility-svc` | Derived & rebuildable from `challenge-db` + member-identity kernel. NOT a system-of-record — can be regenerated. Eventually consistent with Challenge publication. |
| D3 | `membership-db` | PostgreSQL | **Member** (member-identity kernel root), Enrollment, WellnessDataConnection, Goal (locked instance), `[P2]` Team / TeamInvitation, `[P3]` District | C3 Enrolment → `enrolment-svc` | Strong/ACID. Owns the shared `member-identity` kernel (memberId, displayName, initials, consents) — published read-only to other contexts as replicated read-model. Invariant: goal-set locked at enrolment; eligibility snapshotted; disenroll → status=Left, no rejoin. |
| D4 | `activity-log` | Append-only ledger (event log / time-series) | Activity (accepted), IngestionLog (every attempt incl. rejected) | C4 Ingestion → `ingestion-svc` | Append-only, immutable, high write-volume. Idempotent ingest keyed on windowKey (duplicate-reject). IngestionLog is the full audit trail; Activity is the accepted projection. No updates/deletes. |
| D5 | `scoring-db` | PostgreSQL | DailyResult, WeeklyScore, Streak, WellnessScore, Ranking, MemberProgression, `[P2]` Title | C5 Scoring → `scoring-svc` | Strong/ACID at finalization. Invariant: weeklyMax=100; a finalized week is immutable (no retroactive recompute even if late activity arrives); deterministic tie-break; final score = avg(completed weeks). Emits `WeeklyScoreFinalized`. |
| D6a | `leaderboard-cache` | Cache / read-model (Redis sorted-set) | Leaderboard, LeaderboardEntry (live) | C6 Leaderboard → `leaderboard-svc` | Derived from `scoring-db` WellnessScore + CohortScope; rebuildable. Eventually consistent (refresh cadence). Privacy masking (name vs initials) applied at read. NOT system-of-record. |
| D6b | `leaderboard-snapshots` | PostgreSQL | RankingSnapshot (frozen end-of-challenge rows) | C6 Leaderboard → `leaderboard-svc` | Strong/ACID. System-of-record for *final positions*. Written once at challenge end; immutable thereafter. Distinct from the volatile live cache. |
| D7a | `recognition-db` | PostgreSQL | Badge (catalog), BadgeAward, ShareCard (metadata) | C7 Recognition → `recognition-svc` | Strong/ACID. Invariant: tier thresholds; in-progress % monotonic; event/screening points awarded once within window. |
| D7b | `sharecard-store` | Object storage | ShareCard rendered images | C7 Recognition → `recognition-svc` | Binary blobs (generated share images). Referenced by `imageRef` in `recognition-db`. Immutable per generation; served via signed URL / deep link. |
| D8a | `points-ledger` | **Append-only ledger** | **Wallet** (root), PointTransaction (earn/redeem/adjust) | C8 Rewards → `rewards-svc` | **Append-only, immutable, double-entry.** Balance is NEVER mutated in place — `currentBalance` = fold of PointTransactions. Accrual idempotent + capped ≤1000/wk + once-per-week + ignores retroactive score change. Redeem debit + adjust are new entries. Auditable & reconcilable by txnId/sourceRef. |
| D8b | `marketplace-db` | PostgreSQL | MarketplaceItem, InventoryCounters, Redemption, Voucher, Partner, SahatnaEvent (config), Screening (config), `[P2]` CitymoovQuest | C8 Rewards → `rewards-svc` | Strong/ACID + concurrency control. Invariant: reserve→issue saga (validate-balance → check-limits → re-check-stock → deduct → decrement-inventory → issue-voucher). InventoryCounters (reserved/issued/remaining) enforces total-inventory limit under concurrency. Redemption debit is transactionally paired with a `points-ledger` redeem entry (saga, eventual consistency across the two stores). |
| D8c | `reward-image-store` | Object storage | MarketplaceItem partner reward images | C8 Rewards → `rewards-svc` | Binary blobs. Sept Challenge = partner images submitted **manually to Malaffi team** (no upload UI) then registered; later increment = CMS-managed upload. Referenced by image ref in `marketplace-db`. |
| D9 | `settlement-db` | PostgreSQL | WinnersList, WinnerEntry / WinnerAllocation, ChallengeConclusion | C9 Settlement → `settlement-svc` | Strong/ACID. System-of-record for confirmed winners + conclusion. Invariant: no announcement before WinnersList confirmed (gate); conclusion immutable after publish; reward routing (offline/points/hybrid) recorded with fulfilmentStatus. Reads Ranking/RankingSnapshot/Member-contact — owns none. |
| D10 | `notification-db` | PostgreSQL | NotificationConsent, NotificationMessage (sent log) | C10 Notification → `notification-svc` | Strong/ACID. Consent state is authoritative gate; every send writes a NotificationMessage audit row only after passing consent + email-on-file check. Reads NotificationType enable-flags from `challenge-db` (replica). |
| D11 | `analytics-db` | PostgreSQL (read-model / OLAP projection) | ChallengeMetrics, EngagementFunnelStage | C11 Reporting → `reporting-svc` | Derived/rebuildable read-model — no authoritative writes. Aggregates Enrolment funnel + Scoring consistency/streak + Leaderboard ranking. Eventually consistent. Segmentation by age/gender/conditions `[P1]`, district `[P3]`. |
| D0 | `domain-event-log` | Event log / stream | Cross-context domain events: ChallengePublished, EligibleAudienceResolved, EnrollmentLocked, DataConnectionGranted, ActivityAccepted, WeeklyScoreFinalized, RankingFinalized, RankingSnapshotted, PointsEarned, WinnersConfirmed, ChallengeConcluded, ShareCardGenerated, NotificationRequested | **Shared integration backbone** (all contexts publish/subscribe; owned operationally by platform, not a domain context) | Append-only, ordered per partition. The single integration mechanism — no context reads another context's database. At-least-once delivery; consumers idempotent (esp. Scoring→Rewards accrual, Rewards redeem saga). |

---

## 2. Store-type rationale (the four special stores)

- **`points-ledger` (append-only ledger)** — the BRD treats points as money: lifetimeEarned/lifetimeRedeemed must reconcile, accrual is capped and once-per-week, redemptions debit. A mutable balance column would lose auditability and race under concurrent earn/redeem. Modelled as an immutable transaction log; balance is a materialized fold. This is the financial-grade store.
- **`activity-log` (append-only)** — wearable/IFHAS ingest is high-volume and the BRD requires "every update logged with timestamp + source" plus duplicate rejection. Append-only + windowKey idempotency suits this far better than row-update PostgreSQL.
- **`leaderboard-cache` + `eligibility-cache` (Redis read-models)** — leaderboards demand sub-second ranked reads at scale (NFR-Performance) and eligibility is a hot visibility check; both are pure projections, rebuildable from systems-of-record, so a cache (not a database) is correct. The *final* leaderboard positions get a durable PostgreSQL snapshot (`leaderboard-snapshots`).
- **`reward-image-store` + `sharecard-store` (object storage)** — binary images don't belong in a relational row; partner reward images (Sept = manual-to-Malaffi) and generated share-card images are blobs referenced by id.

## 3. Domain-class → store coverage (no orphans)

All 43 domain classes + the 4 robustness/notification additions are persisted in exactly one owning store (definitions vs locked-instances of Goal split across `challenge-db`/`membership-db` by lifecycle; LeaderboardEntry/Member/Team generalization persisted in the entry's own store). Cross-context references are held by **id only** (foreign aggregate not duplicated as writable state) — e.g. Settlement holds `winningCriteriaRef`/`memberRef`, never owns WinningCriteria or Member.

| Domain class | Store | Domain class | Store |
|---|---|---|---|
| Member | membership-db (kernel) | Wallet | points-ledger |
| Segment | challenge-db | PointTransaction | points-ledger |
| Challenge | challenge-db | MarketplaceItem | marketplace-db |
| EligibilityRule | challenge-db | Redemption | marketplace-db |
| WinningCriteria | challenge-db | Voucher | marketplace-db |
| ChallengeRequest | challenge-db | Partner | marketplace-db |
| Enrollment | membership-db | InventoryCounters | marketplace-db |
| Goal (def / locked) | challenge-db / membership-db | SahatnaEvent | marketplace-db (config) |
| ScoringPlan | challenge-db | Screening | marketplace-db (config) |
| ScoreComponent | challenge-db | WellnessDataConnection | membership-db |
| Activity | activity-log | IngestionLog | activity-log |
| DailyResult | scoring-db | Ranking | scoring-db |
| WeeklyScore | scoring-db | RankingSnapshot | leaderboard-snapshots |
| WellnessScore | scoring-db | CohortScope | eligibility-cache |
| Streak | scoring-db | ShareCard | sharecard-store / recognition-db |
| Badge | recognition-db | WinnersList | settlement-db |
| BadgeAward | recognition-db | WinnerEntry | settlement-db |
| Title `[P2]` | scoring-db | ChallengeMetrics | analytics-db |
| MemberProgression | scoring-db | EngagementFunnelStage | analytics-db |
| Leaderboard | leaderboard-cache | TeamInvitation `[P2]` | membership-db |
| LeaderboardEntry | leaderboard-cache | Team `[P2]` | membership-db |
| NotificationConsent | notification-db | District `[P3]` | membership-db |
| NotificationType | challenge-db | CitymoovQuest `[P2]` | marketplace-db |
| NotificationMessage | notification-db | ChallengeConclusion | settlement-db |

---

## 4. External systems (data crosses an ACL, never a shared store)

| External | Touches context (store) | Direction | ACL note |
|---|---|---|---|
| Malaffi / DoH-ADHDS | C8 Rewards (`reward-image-store`), C9 Settlement (`settlement-db`) | in (manual reward images) / out (offline-winner contact + confirm gate) | Foreign DoH model wrapped; manual image intake (Sept), winner edit/confirm authority. |
| Wearables (Apple Health / Google Fit) | C4 Ingestion (`activity-log`) | in (metric sync) | Provider payloads normalized by adapter; never stored raw. |
| IFHAS Screening Module | C4 Ingestion / C7 Recognition | in (screening events) | Screening completion validated behind ACL. |
| Sahatna Events | C7 Recognition / C8 Rewards | in (event sign-up/check-in) | Event participation → bonus PointsEarned. |
| Notification Provider (push/email) | C10 Notification | out (delivery) | Gateway adapter; consent gate upstream of provider. |
| Reward Partners | C8 Rewards (`marketplace-db`, `reward-image-store`) | in (reward + image submission) | Partner-supplied SKUs/images behind PartnerRewardSubmission ACL. |
| Citymoov `[P2]` | C8 Rewards (`marketplace-db`) | in (quest completion) | P2 quest points behind ACL. |
