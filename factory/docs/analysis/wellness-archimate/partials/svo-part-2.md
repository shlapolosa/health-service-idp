# SVO Part 2 — Grammatical Decomposition of Part 2 ABB Requirements & Rules

Source: `partials/part-2.md` (BR-101..BR-128, RULE-101..RULE-126).
Method: each statement decomposed into (Subject, Action, Object) triples. Compound statements yield multiple triples; implicit subjects inferred from the ABB owner.

## S-V-O triples

| Triple# | Source ID | Subject | Action | Object |
|---------|-----------|---------|--------|--------|
| 1 | BR-101 | GOAL-SVC | Define goal | GoalDefinition |
| 2 | BR-101 | GOAL-SVC | Evaluate goal progress | GoalProgress |
| 3 | BR-101 | GOAL-SVC | Track goal progress | GoalProgress |
| 4 | BR-102 | GOAL-SVC | Evaluate verified activity against thresholds | VerifiedActivity |
| 5 | BR-102 | GOAL-SVC | Update goal progress | GoalProgress |
| 6 | BR-103 | GOAL-SVC | Provide progress views | GoalProgress |
| 7 | BR-104 | GOAL-SVC | Signal goal completion | GoalCompletedEvent |
| 8 | BR-105 | STREAK-SVC | Maintain streak state | StreakState |
| 9 | BR-106 | STREAK-SVC | Emit at-risk warning | StreakAtRiskEvent |
| 10 | BR-107 | STREAK-SVC | Detect and signal streak extension/break | StreakState |
| 11 | BR-108 | STREAK-SVC | Provide streak state | StreakState |
| 12 | BR-109 | BADGE-SVC | Award badge | Badge |
| 13 | BR-109 | BADGE-SVC | Store badge | BadgeGrant |
| 14 | BR-109 | BADGE-SVC | Surface badge | Badge |
| 15 | BR-110 | BADGE-SVC | Evaluate domain events against criteria | DomainEvent |
| 16 | BR-110 | BADGE-SVC | Grant badge | BadgeGrant |
| 17 | BR-111 | BADGE-SVC | Expose badge catalog | BadgeCatalog |
| 18 | BR-112 | ACTV-SVC | Ingest activity signals | ActivitySignal |
| 19 | BR-112 | ACTV-SVC | Validate activity signals | ActivitySignal |
| 20 | BR-112 | ACTV-SVC | Normalise activity into trusted events | VerifiedActivity |
| 21 | BR-113 | ACTV-SVC | Accept activity submissions | ActivitySubmission |
| 22 | BR-114 | ACTV-SVC | Emit verified-activity signal | VerifiedActivityEvent |
| 23 | BR-115 | ACTV-SVC | Provide activity audit views | ActivityEvent |
| 24 | BR-116 | CLIN-SVC | Receive and trust clinical signals | ClinicalSignal |
| 25 | BR-117 | CLIN-SVC | Provide screening completion history | ClinicalRecord |
| 26 | BR-117 | CLIN-SVC | Emit clinical-verified input | ClinicalVerifiedEvent |
| 27 | BR-118 | ID-SVC | Federate identity | Identity |
| 28 | BR-118 | ID-SVC | Issue and validate platform tokens | TokenSession |
| 29 | BR-118 | ID-SVC | Expose identity context | IdentityContext |
| 30 | BR-119 | ID-SVC | Handle OIDC callback and token exchange | TokenSession |
| 31 | BR-119 | ID-SVC | Publish JWKS | JWKS |
| 32 | BR-120 | ID-SVC | Signal identity link | IdentityLinkedEvent |
| 33 | BR-120 | ID-SVC | Signal identity unlink | IdentityUnlinkedEvent |
| 34 | BR-121 | FRAUD-SVC | Detect and prevent fraud | FraudCheck |
| 35 | BR-121 | FRAUD-SVC | Respond to fraud | FraudCase |
| 36 | BR-122 | FRAUD-SVC | Provide integrity check | FraudCheck |
| 37 | BR-122 | Wallet, Marketplace | Consume integrity check | FraudCheck |
| 38 | BR-123 | Fraud Analyst | Review and decide fraud case | FraudCase |
| 39 | BR-124 | EVENT-SVC | Provide event transport | Event |
| 40 | BR-125 | DATA-SVC | Persist platform events and state | DataWarehouseRecord |
| 41 | BR-126 | DATA-SVC | Provide SQL/warehouse access | DataWarehouseRecord |
| 42 | BR-126 | Power BI | Consume warehouse access | DataWarehouseRecord |
| 43 | BR-127 | REPORT-SVC | Surface programme-health insight | Dashboard |
| 44 | BR-127 | ADPHC, ADHDS, DH | Consume curated dashboards | Dashboard |
| 45 | BR-128 | REPORT-SVC | Provide report exports | Report |
| 46 | BR-128 | Programme Admin | Request report export | Report |
| 47 | RULE-101 | GOAL-SVC | Track goal progress per key against threshold | GoalProgress |
| 48 | RULE-101 | GOAL-SVC | Mark goal complete when completed_at set | GoalProgress |
| 49 | RULE-102 | GOAL-SVC | Version goal definitions | GoalDefinition |
| 50 | RULE-102 | Challenge Management | Own goal templates | GoalDefinition |
| 51 | RULE-103 | GOAL-SVC | Update goal progress only on verified activity | VerifiedActivityEvent |
| 52 | RULE-104 | STREAK-SVC | Maintain streak state per key | StreakState |
| 53 | RULE-104 | STREAK-SVC | Advance streak only on score delta applied | ScoreDeltaAppliedEvent |
| 54 | RULE-105 | STREAK-SVC | Govern streak continuity by rule | StreakRule |
| 55 | RULE-105 | STREAK-SVC | Break streak when no contribution in grace window | StreakState |
| 56 | RULE-106 | STREAK-SVC | Emit at-risk warning before break | StreakAtRiskEvent |
| 57 | RULE-107 | BADGE-SVC | Record triggering source event on grant | BadgeGrant |
| 58 | RULE-108 | BADGE-SVC | Award badge only on qualifying events | DomainEvent |
| 59 | RULE-109 | ACTV-SVC | Record provenance on activity event | ActivityEvent |
| 60 | RULE-110 | ACTV-SVC | Validate and normalise before emission | ActivitySignal |
| 61 | RULE-110 | ACTV-SVC | Emit verified signal only when validated | VerifiedActivityEvent |
| 62 | RULE-111 | ACTV-SVC | Flag anomalous activity | ActivityAnomalyEvent |
| 63 | RULE-111 | ACTV-SVC | Log anomalies | IngestionLog |
| 64 | RULE-112 | ACTV-SVC | Require identity and fraud before accepting signals | FraudCheck |
| 65 | RULE-113 | CLIN-SVC | Phase clinical signals by trusted source | ClinicalSignal |
| 66 | RULE-114 | CLIN-SVC | Require consent before trusting clinical data | Consent |
| 67 | RULE-115 | CLIN-SVC | Propagate point-of-disadvantage flag | ClinicalPodFlagEvent |
| 68 | RULE-116 | ID-SVC | Federate identity with primary and transition IdP | IdentityLink |
| 69 | RULE-116 | ID-SVC | Maintain unique identity link per user | IdentityLink |
| 70 | RULE-117 | ID-SVC | Scope and hash token sessions | TokenSession |
| 71 | RULE-117 | ID-SVC | Validate tokens against JWKS | JWKS |
| 72 | RULE-118 | ID-SVC | Trigger retention/cleanup on unlink | IdentityUnlinkedEvent |
| 73 | RULE-119 | FRAUD-SVC | Aggregate signals to decision | FraudCase |
| 74 | RULE-119 | FRAUD-SVC | Record audit fields on action | FraudAction |
| 75 | RULE-120 | FRAUD-SVC | Emit fraud action for audit | FraudActionEvent |
| 76 | RULE-120 | FRAUD-SVC | React to value-movement events | DomainEvent |
| 77 | RULE-121 | Wallet, Marketplace | Perform integrity check before value transfer | FraudCheck |
| 78 | RULE-122 | EVENT-SVC | Carry versioned schema on events | EventSchema |
| 79 | RULE-122 | EVENT-SVC | Capture undeliverable events | DeadLetterRecord |
| 80 | RULE-123 | EVENT-SVC | Provide durable ordered partitioned transport | Event |
| 81 | RULE-124 | DATA-SVC | Consume all events as sink | Event |
| 82 | RULE-124 | DATA-SVC | Archive events by date/domain | EventArchive |
| 83 | RULE-125 | REPORT-SVC | Define owner and access on dashboard | Dashboard |
| 84 | RULE-125 | REPORT-SVC | Read-only over warehouse | DataWarehouseRecord |
| 85 | RULE-126 | REPORT-SVC | Restrict consumers to governance bodies | Dashboard |

## Active Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| GOAL-SVC (Goal Engine) | Application Component | BR-101, BR-102, BR-103, BR-104, RULE-101, RULE-102, RULE-103 |
| STREAK-SVC (Streak Engine) | Application Component | BR-105, BR-106, BR-107, BR-108, RULE-104, RULE-105, RULE-106 |
| BADGE-SVC (Badge Service) | Application Component | BR-109, BR-110, BR-111, RULE-107, RULE-108 |
| ACTV-SVC (Activity Verification) | Application Component | BR-112, BR-113, BR-114, BR-115, RULE-109, RULE-110, RULE-111, RULE-112 |
| CLIN-SVC (Clinical Verification) | Application Component | BR-116, BR-117, RULE-113, RULE-114, RULE-115 |
| ID-SVC (Identity & Auth) | Application Component | BR-118, BR-119, BR-120, RULE-116, RULE-117, RULE-118 |
| FRAUD-SVC (Fraud & Integrity) | Application Component | BR-121, BR-122, BR-123, RULE-119, RULE-120 |
| EVENT-SVC (Event Hub) | Application Component | BR-124, RULE-122, RULE-123 |
| DATA-SVC (Data Lake & Warehouse) | Application Component | BR-125, BR-126, RULE-124 |
| REPORT-SVC (Reporting) | Application Component | BR-127, BR-128, RULE-125, RULE-126 |
| Wallet | Application Component | BR-122, RULE-121 |
| Marketplace | Application Component | BR-122, RULE-121 |
| Power BI | Application Component | BR-126 |
| Challenge Management | Business Role | RULE-102 |
| Fraud Analyst | Business Role | BR-123 |
| Programme Admin | Business Role | BR-128 |
| ADPHC | Business Actor | BR-127, RULE-126 |
| ADHDS | Business Actor | BR-127, RULE-126 |
| DH (Department of Health) | Business Actor | BR-127, RULE-126 |

## Behaviour elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| Goal Definition | Business Service | BR-101, RULE-102 |
| Goal Progress Evaluation | Business Process | BR-101, BR-102, RULE-101, RULE-103 |
| Goal Progress Tracking | Business Service | BR-101, RULE-101 |
| Goal Progress View | Business Service | BR-103 |
| Goal Completion Signalling | Business Event | BR-104 |
| Streak Maintenance | Business Service | BR-105, RULE-104, RULE-105 |
| Streak At-Risk Warning | Business Event | BR-106, RULE-106 |
| Streak Extension/Break Detection | Business Event | BR-107, RULE-105 |
| Streak State View | Business Service | BR-108 |
| Badge Awarding | Business Service | BR-109, RULE-107, RULE-108 |
| Badge Evaluation & Grant | Business Process | BR-110, RULE-107, RULE-108 |
| Badge Catalog Exposure | Business Service | BR-111 |
| Activity Ingestion | Business Service | BR-112, RULE-109, RULE-110 |
| Activity Validation & Normalisation | Business Process | BR-112, RULE-110 |
| Activity Submission Acceptance | Business Interaction | BR-113 |
| Activity Verification (verified-activity emission) | Business Event | BR-114, RULE-110 |
| Activity Anomaly Detection | Business Event | RULE-111 |
| Anomaly Logging | Business Process | RULE-111 |
| Activity Audit View | Business Service | BR-115 |
| Clinical Signal Reception | Business Service | BR-116, RULE-113, RULE-114 |
| Clinical Verification | Business Service | BR-117 |
| Clinical Verified Emission | Business Event | BR-117 |
| Clinical POD Flag Propagation | Business Event | RULE-115 |
| Identity Federation | Business Service | BR-118, RULE-116 |
| Token Issuance & Validation | Business Service | BR-118, BR-119, RULE-117 |
| OIDC Callback Handling | Business Process | BR-119 |
| JWKS Publication | Business Service | BR-119, RULE-117 |
| Identity Context Exposure | Business Service | BR-118 |
| Identity Link Signalling | Business Event | BR-120 |
| Identity Unlink Signalling | Business Event | BR-120, RULE-118 |
| Retention/Cleanup Processing | Business Process | RULE-118 |
| Fraud Detection & Prevention | Business Service | BR-121, RULE-119, RULE-120 |
| Integrity Check | Business Service | BR-122, RULE-112, RULE-121 |
| Fraud Case Review | Business Process | BR-123, RULE-119 |
| Fraud Action Emission | Business Event | RULE-120 |
| Event Transport | Business Service | BR-124, RULE-122, RULE-123 |
| Dead-Letter Capture | Business Process | RULE-122 |
| Event Persistence | Business Service | BR-125, RULE-124 |
| Event Archival | Business Process | RULE-124 |
| Warehouse Access | Business Service | BR-126, RULE-125 |
| Insight Surfacing (Dashboards) | Business Service | BR-127, RULE-125, RULE-126 |
| Report Export | Business Process | BR-128 |

## Passive Structure elements

| Element name | ArchiMate type | Source IDs |
|--------------|----------------|------------|
| GoalDefinition | Business Object | BR-101, RULE-102 |
| GoalProgress | Business Object | BR-101, BR-102, BR-103, RULE-101, RULE-103 |
| GoalCompletedEvent (`goal.completed`) | Business Event (representation) | BR-104 |
| StreakState | Business Object | BR-105, BR-107, BR-108, RULE-104, RULE-105 |
| StreakRule | Business Object | RULE-105 |
| StreakAtRiskEvent (`streak.at-risk`) | Business Event (representation) | BR-106, RULE-106 |
| Badge | Business Object | BR-109, BR-111 |
| BadgeGrant | Business Object | BR-109, BR-110, RULE-107 |
| BadgeCatalog | Business Object | BR-111 |
| DomainEvent | Business Object | BR-110, RULE-108, RULE-120 |
| ActivitySignal | Business Object | BR-112, RULE-110 |
| ActivitySubmission | Representation | BR-113 |
| ActivityEvent | Business Object | BR-115, RULE-109 |
| VerifiedActivity / VerifiedActivityEvent (`activity.verified`) | Business Object / Event | BR-102, BR-112, BR-114, RULE-110, RULE-103 |
| ActivityAnomalyEvent (`activity.anomaly-detected`) | Business Event (representation) | RULE-111 |
| IngestionLog | Business Object | RULE-111 |
| ClinicalSignal | Business Object | BR-116, RULE-113 |
| ClinicalRecord | Business Object | BR-117 |
| ClinicalVerifiedEvent | Business Event (representation) | BR-117 |
| ClinicalPodFlagEvent (`clinical.pod-flag-set`) | Business Event (representation) | RULE-115 |
| Consent | Business Object | RULE-114 |
| Identity / IdentityContext | Business Object | BR-118 |
| IdentityLink | Business Object | RULE-116 |
| TokenSession | Business Object | BR-118, BR-119, RULE-117 |
| JWKS | Representation | BR-119, RULE-117 |
| IdentityLinkedEvent (`identity.linked`) | Business Event (representation) | BR-120 |
| IdentityUnlinkedEvent (`identity.unlinked`) | Business Event (representation) | BR-120, RULE-118 |
| FraudCheck | Business Object | BR-121, BR-122, RULE-112, RULE-121 |
| FraudCase | Business Object | BR-121, BR-123, RULE-119 |
| FraudAction | Business Object | RULE-119 |
| FraudActionEvent (`fraud.action-taken`) | Business Event (representation) | RULE-120 |
| ScoreDeltaAppliedEvent (`score.delta-applied`) | Business Event (representation) | RULE-104 |
| Event | Business Object | BR-124, RULE-123, RULE-124 |
| EventSchema | Business Object | RULE-122 |
| DeadLetterRecord | Business Object | RULE-122 |
| EventArchive | Business Object | RULE-124 |
| DataWarehouseRecord | Business Object | BR-125, BR-126, RULE-125 |
| Dashboard | Business Object | BR-127, RULE-125, RULE-126 |
| Report | Representation | BR-128 |
