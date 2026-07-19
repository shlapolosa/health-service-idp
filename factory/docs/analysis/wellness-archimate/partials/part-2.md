# Part 2 — Logical Architecture ABBs (GOAL, STREAK, BADGE, ACTV, CLIN, ID, FRAUD, EVENT, DATA, REPORT)

Source: `/tmp/wellness_doc.txt` lines 200–365 (Part 1 Logical architecture ABBs).

## Business Requirements

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| BR-101 | Define, evaluate and track per-user goal progress for each configured goal type within a challenge. | GOAL-SVC (Goal Engine) | Business Service | 200–214 |
| BR-102 | Evaluate inbound verified activity against goal thresholds to update goal progress. | GOAL-SVC | Business Process | 210–211 |
| BR-103 | Provide per-challenge and per-goal progress views to the UI (drill-down). | GOAL-SVC sync interfaces | Business Service | 207–208 |
| BR-104 | Signal goal milestone completion to drive nudges and badge awarding. | GOAL-SVC `goal.completed` | Business Event | 212 |
| BR-105 | Maintain daily and weekly streak state per user and per active challenge. | STREAK-SVC (Streak Engine) | Business Service | 216–222 |
| BR-106 | Emit at-risk warnings before a streak break to enable preventive nudges. | STREAK-SVC `streak.at-risk` | Business Event | 217, 229 |
| BR-107 | Detect and signal streak extension and streak break for comms/analytics. | STREAK-SVC `streak.extended`/`broken` | Business Event | 227–228 |
| BR-108 | Provide current streak state to the UI. | STREAK-SVC `GET /streaks` | Business Service | 224 |
| BR-109 | Award, store and surface achievement badges based on event-driven criteria. | BADGE-SVC (Badge Service) | Business Service | 233–245 |
| BR-110 | Evaluate qualifying domain events against badge criteria and grant badges. | BADGE-SVC consumes events | Business Process | 244–245 |
| BR-111 | Expose a badge catalog (admin/UI) and a citizen badge view. | BADGE-SVC sync interfaces | Business Service | 241–242 |
| BR-112 | Ingest, validate and normalise activity signals from wearables, surveys and event check-ins into trusted activity events. | ACTV-SVC (Activity Verification) | Business Service | 249–263 |
| BR-113 | Accept wearable activity (Sahatna proxy), in-app survey, and event check-in submissions. | ACTV-SVC sync interfaces | Business Interaction | 257–259 |
| BR-114 | Emit the verified-activity signal as the primary platform-wide score-affecting input. | ACTV-SVC `activity.verified` | Business Event | 262 |
| BR-115 | Provide per-user per-day activity audit/explain views. | ACTV-SVC `GET /activities` | Business Service | 260 |
| BR-116 | Receive and trust clinical signals from national health systems (IFHAS P1, Malaffi P2, Riayati/Nabidh target). | CLIN-SVC (Clinical Verification) | Business Service | 267–281 |
| BR-117 | Provide screening completion history per user and emit clinical-verified input to scoring. | CLIN-SVC interfaces/events | Business Service | 276, 278 |
| BR-118 | Federate identity across UAE Pass (target) and Sahatna identity (transition); issue and validate platform tokens; expose identity context to all services. | ID-SVC (Identity & Auth) | Business Service | 283–294 |
| BR-119 | Handle OIDC callback, token exchange, downstream claims, and publish JWKS for token validation. | ID-SVC sync interfaces | Business Process | 291–294 |
| BR-120 | Signal first-time identity link (triggers onboarding) and identity unlink (triggers retention/cleanup). | ID-SVC `identity.linked`/`unlinked` | Business Event | 296–297 |
| BR-121 | Detect, prevent and respond to points-system gaming, identity fraud, partner abuse and false activity claims. | FRAUD-SVC (Fraud & Integrity) | Business Service | 301–316 |
| BR-122 | Provide a synchronous integrity check consumed by Wallet and Marketplace before value transfer. | FRAUD-SVC `GET /fraud/check` | Business Service | 312 |
| BR-123 | Provide admin case review and decision capability over raised fraud signals. | FRAUD-SVC case interfaces | Business Process | 310–311 |
| BR-124 | Provide durable, ordered, partitioned event transport for all asynchronous platform communication. | EVENT-SVC (Event Hub) | Business Service | 320–330 |
| BR-125 | Persist platform events and state for analytics, reporting, longitudinal research and audit replay. | DATA-SVC (Data Lake & Warehouse) | Business Service | 334–346 |
| BR-126 | Provide curated SQL/warehouse access for Power BI and ad-hoc analytics. | DATA-SVC interfaces | Business Service | 342 |
| BR-127 | Surface operational and programme-health insight to ADPHC, ADHDS and DH via curated dashboards. | REPORT-SVC (Reporting) | Business Service | 350–358 |
| BR-128 | Provide scheduled and on-demand report exports to admins. | REPORT-SVC `POST /reports/exports` | Business Process | 356, 359 |

## Business Rules

| ID | Statement | Source | ArchiMate type | Lines |
|----|-----------|--------|----------------|-------|
| RULE-101 | A goal is the unit of measurable behaviour; goal progress is tracked per (user_id, challenge_id, goal_id) against a defined threshold and is only complete when `completed_at` is set. | GOAL-SVC GoalProgress | Business Object | 201, 205 |
| RULE-102 | Goal definitions are versioned (id, type, params, version); goal templates are owned by Challenge Management. | GOAL-SVC GoalDefinition | Business Rule | 204, 214 |
| RULE-103 | Goal progress may only be updated in response to a verified activity event (`activity.verified`); raw/unverified activity must not advance goals. | GOAL-SVC consumes | Business Rule | 210 |
| RULE-104 | Streak state is maintained per (user_id, challenge_id) with current_length and peak_length, advanced only by a score delta being applied (`score.delta-applied`). | STREAK-SVC StreakState | Business Object | 221, 226 |
| RULE-105 | Streak continuity is governed by a per-challenge StreakRule defining grace_hours and reset_policy; a streak breaks when no contribution occurs within the grace window. | STREAK-SVC StreakRule | Business Rule | 222 |
| RULE-106 | An at-risk warning must be emitted before the streak break occurs (preventive, not retrospective). | STREAK-SVC `streak.at-risk` | Business Rule | 217, 229 |
| RULE-107 | A badge grant records its triggering source event (source_event_id), making every award traceable to the event that caused it. | BADGE-SVC BadgeGrant | Business Rule | 239 |
| RULE-108 | Badges are awarded only on defined qualifying events: streak.extended, title.advanced, challenge.concluded, score.cap-reached. | BADGE-SVC consumes | Business Rule | 244 |
| RULE-109 | Every activity event records both occurred_at and recorded_at and its source, establishing provenance for the trust backbone. | ACTV-SVC ActivityEvent | Business Object | 254 |
| RULE-110 | Activity ingestion must be validated and normalised before emission; only validated signals become `activity.verified`, the trusted platform-wide signal. | ACTV-SVC mission/event | Business Rule | 250, 262 |
| RULE-111 | Anomalous activity must be flagged via `activity.anomaly-detected` and logged (IngestionLog anomalies) for fraud/ops. | ACTV-SVC IngestionLog/event | Business Rule | 255, 263 |
| RULE-112 | Activity verification requires Identity & Auth and Fraud & Integrity to be satisfied (trust dependencies) before signals are accepted. | ACTV-SVC depends on | Business Rule | 265 |
| RULE-113 | Clinical signals are phased by trusted source: IFHAS in Phase 1, Malaffi in Phase 2, Riayati/Nabidh in target state. | CLIN-SVC mission | Business Rule | 268 |
| RULE-114 | Clinical event ingestion requires Consent Management (consent must be present before clinical data is trusted/used). | CLIN-SVC depends on | Business Rule | 281 |
| RULE-115 | A clinical point-of-disadvantage flag (`clinical.pod-flag-set`) is an equity-relevant signal that must propagate downstream. | CLIN-SVC event | Business Rule | 279 |
| RULE-116 | Identity is federated with UAE Pass as primary/target IdP and Sahatna identity only as transition; each user has a unique IdentityLink (platform_user_id ↔ external_idp_id, idp_type). | ID-SVC IdentityLink | Business Rule | 284, 288 |
| RULE-117 | Platform tokens are scoped, hashed sessions with issued_at/expires_at; tokens are validated against published JWKS (and at Azure APIM). | ID-SVC TokenSession | Business Object | 289, 294, 299 |
| RULE-118 | Identity unlink must trigger retention/cleanup processing (data lifecycle on de-linking). | ID-SVC `identity.unlinked` | Business Rule | 297 |
| RULE-119 | A FraudCase aggregates signals to a decision with an explicit status; every FraudAction records type, applied_at and applied_by for audit. | FRAUD-SVC FraudCase/Action | Business Rule | 307–308 |
| RULE-120 | Fraud actions are emitted as `fraud.action-taken` for audit, and fraud reacts to value-movement events (wallet.credited/debited, redemption.confirmed, score.cap-reached). | FRAUD-SVC events/consumes | Business Rule | 314, 316 |
| RULE-121 | Wallet and Marketplace must perform a synchronous integrity check (`GET /fraud/check/{user}`) before completing value transfer. | FRAUD-SVC sync interface | Business Rule | 312 |
| RULE-122 | All asynchronous events carry a versioned EventSchema (id, name, version, payload_shape); undeliverable events are captured as DeadLetterRecord. | EVENT-SVC entities | Business Object | 325–326 |
| RULE-123 | Event transport must be durable, ordered and partitioned across all platform event families (activity, score, streak, title, badge, challenge, wallet, redemption, consent, fraud, identity). | EVENT-SVC mission/transport | Business Rule | 321, 330 |
| RULE-124 | The warehouse is a sink (consumes all platform events, emits none at this stage); events are archived by date/domain with counts for audit replay. | DATA-SVC events/EventArchive | Business Rule | 339, 345–346 |
| RULE-125 | Dashboards carry an explicit owner and access definition; reporting is strictly read-only over the warehouse (no events emitted). | REPORT-SVC Dashboard | Business Rule | 355, 361 |
| RULE-126 | Reporting consumers are restricted to programme governance bodies ADPHC, ADHDS and DH. | REPORT-SVC mission | Business Role/Actor | 351 |
