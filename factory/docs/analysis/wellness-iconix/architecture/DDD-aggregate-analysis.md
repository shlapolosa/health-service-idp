# DDD Aggregate Analysis — Wellness Gamification Platform

## Method
A true **aggregate** is a *transactional consistency boundary*: it owns a **system-of-record (SoR)**, protects at
least one **invariant**, is modified **one-at-a-time per transaction**, and is referenced from outside **by root id only**.
Tell-tales that something is *not* an aggregate:
- **Read model / projection** — derived, rebuildable, protects no write invariant (a query result, not a SoR).
- **Reference data** — a catalogue/template owned elsewhere, read by many.

The decisive lens (the one that prompted this): **what does the context *return*, and does it *own* what it returns?**

## Aggregate inventory (per bounded context)
| Context (svc) | Root | Invariant it protects | SoR? | Verdict |
|---|---|---|---|---|
| Challenge (`challenge-svc`) | **Challenge** (composes EligibilityRule, WinningCriteria, ScoringPlan, ScoreComponent, Goal-defs) | Σ ScoreComponent.weeklyAllocation = 100; Draft→Active→Completed→Archived | ✅ | **Aggregate** |
| Challenge | **ChallengeRequest** | request lifecycle Submitted→Approved/Rejected | ✅ | **Aggregate** |
| **Eligibility (`eligibility-svc`)** | CohortScope | — (enforces *Challenge's* audience rules) | ❌ (eligibility-cache is rebuildable) | **READ MODEL** — not an aggregate |
| Enrolment (`enrolment-svc`) | **Member** (kernel: profile, consents) | identity + consent integrity | ✅ | **Aggregate** (shared kernel) |
| Enrolment | **Enrollment** (embeds EligibilitySnapshot) | immutable snapshot (B3.1), 1-per-member-per-challenge, withdrawal-voids-score | ✅ | **Aggregate** (strong) |
| Enrolment | **WellnessDataConnection** | ingestion grant/consent | ✅ | **Aggregate** |
| Ingestion (`ingestion-svc`) | **Activity** / **IngestionLog** | dedup/idempotency; append-only audit | ✅ | **Aggregate** |
| Scoring (`scoring-svc`) | **WeeklyScore** (embeds Streak), **DailyResult**, **MemberProgression** | week-closure, finalize immutable, tie-break, streak rules | ✅ | **Aggregate** |
| Scoring | Ranking (scoring-side ordered result), WellnessScore | — (computed from WeeklyScores) | ~ | **mostly projection** ⚠️ (see overlap) |
| Leaderboard (`leaderboard-svc`) | Leaderboard (+LeaderboardEntry) | — (derived from finalized scores) | ❌ | **READ MODEL** |
| Leaderboard | **RankingSnapshot** (frozen rows at end) | immutable standings at challenge end | ✅ | **Aggregate** |
| Recognition (`recognition-svc`) | **BadgeAward**, **ShareCard** (Badge = reference catalogue) | award-once, in-progress %, artifact integrity | ✅ | **Aggregate** |
| Rewards (`rewards-svc`) | **Wallet** (+PointTransaction ledger) | balance = Σ tx, append-only, idempotent | ✅ | **Aggregate** (financial-grade) |
| Rewards | **MarketplaceItem** (+InventoryCounters), **Redemption** (saga), **Partner** | inventory limits; reserve→issue idempotency | ✅ | **Aggregate** |
| Settlement (`settlement-svc`) | **WinnersList** (+WinnerEntry), **ChallengeConclusion** | winner determination + review/confirm gate | ✅ | **Aggregate** |
| Notification (`notification-svc`) | **NotificationConsent**, **NotificationMessage** | consent gate; send-audit | ✅ | **Aggregate** |
| **Reporting (`reporting-svc`)** | ChallengeMetrics (+EngagementFunnelStage) | — (OLAP projection) | ❌ | **READ MODEL** — not an aggregate |

## Key findings
1. **Two contexts own NO write aggregate — they are read models, not core contexts:**
   - **`eligibility-svc`** — `CohortScope` is a *projection* (rebuildable from Challenge audience rules + Member profile + Malaffi membership). It enforces **Challenge's** rules, not its own. It returns **filtered challenges** — a *view of Challenge*.
   - **`reporting-svc`** — `ChallengeMetrics` is an OLAP projection over Enrolment/Scoring/Leaderboard.
   Both are **supporting query/integration services**, justified to stay separate only to **isolate an integration/seam** (eligibility = the Malaffi clinical ACL + OLTP→OLAP read-model; reporting = the analytics store).
2. **`leaderboard-svc` is mostly a read model** (`Leaderboard` is a projection of finalized scores) with **one** real aggregate, `RankingSnapshot` (the immutable end-of-challenge freeze).
3. **Aggregate overlap to resolve ⚠️:** scoring's `Ranking` and leaderboard's `Leaderboard`/`RankingSnapshot` are two "ordered-standings" representations. Clean split: **Scoring owns the finalized *scores* (SoR)**; **Leaderboard *projects* them for display** and owns only the immutable `RankingSnapshot`. `Ranking` on the scoring side should be the finalized score-ordering SoR, and Leaderboard should not duplicate it — confirm or collapse.

## Exposure rule that follows (this is the answer to "should eligibility be exposed?")
**A context is an external front door only for commands/queries against its OWN aggregate. A read model is never a citizen-facing front door — it is consulted internally.**

| Use case | External front door (owns the aggregate) | Internal call(s) |
|---|---|---|
| **Discovery — "get challenges"** | **`challenge-svc`** (query over the Challenge aggregate: which challenges exist) | → `eligibility-svc.resolveVisibility()` (read model + Malaffi ACL) to filter |
| **Enroll** | **`enrolment-svc`** (command on the Enrollment aggregate) | → `eligibility-svc.snapshotEligibility()` for the frozen snapshot |
| **Reporting dashboards** | **`reporting-svc`** — **Admin/back-office only**, never citizen | reads internal stores |

⇒ **`eligibility-svc` has no external surface.** It is a downstream supporting service called by `challenge-svc`
(discovery) and `enrolment-svc` (snapshot). The current eligibility sequences expose it directly to the citizen
path (`Mobile → APIM-south → eligibility-svc`) — that should be re-routed: **citizen → `challenge-svc` (get challenges)
→ internally `eligibility-svc`**. Chip impact: in discovery, `challenge-svc` becomes 🟥 (receives the citizen request)
and `eligibility-svc` becomes 🟦-only (its inbound is now a peer call from `challenge-svc`; it still calls Malaffi).

## Recommended actions
1. **Re-route the eligibility *discovery* journey**: front door = `challenge-svc.getEligibleChallenges()`; `eligibility-svc`
   internal. Enrollment-snapshot journey already flows `enrolment-svc → eligibility-svc` (already internal) — keep.
2. **Re-label `eligibility-svc` and `reporting-svc` as *supporting* (read-model) services**, not core contexts, in the
   context map / logic doc.
3. **Resolve the Scoring/Leaderboard `Ranking` overlap** (Scoring = score SoR; Leaderboard = projection + RankingSnapshot).
