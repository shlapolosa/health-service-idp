# ICONIX Step 1 — Domain Model (Wellness Gamification)

**Process**: ICONIX (Rosenberg), use-case-driven and milestone-driven.
**Source**: `factory/docs/analysis/wellness-archimate/wellness-brd-clean.md`
**Scope tag legend**: `[P1]` Phase-1 (individual-based) · `[P2]` Phase-2 (teams, baseline goals, titles, citymoov) · `[P3]` Phase-3 (districts). Phase-1 is the build scope; P2/P3 classes are modelled for forward-traceability but are out of build scope.

This is **analysis-level**: real-world nouns with attributes and associations only. No methods, no controllers, no UI/boundary objects (those arrive in Robustness / Step 2). Multiplicities read `source → target`.

---

## 1. Class Diagram (Mermaid)

```mermaid
classDiagram
    direction TB

    %% ===== ACTORS / PARTICIPANTS =====
    class Member {
        +memberId
        +displayName
        +initials
        +email
        +phone
        +age
        +gender
        +conditions
        +accessibilityFlag_POD
        +districtAddress
        +pushConsent
        +emailConsent
        +wellnessDataConnected
    }

    %% Segment (with LocalSegment/ClinicalSegment) is owned by the segmentation concern,
    %% NOT challenge-svc. Challenge/EligibilityRule reference it by segmentId only.
    %% (updated: segment referenced, segmentation is separate)
    class Segment {
        <<abstract>>
        +segmentId
        +ageRange
        +gender
        +conditions
        +accessibilityClassification
        +whitelisted
        +district
    }

    %% ===== ELIGIBILITY CLINICAL-SPLIT (added in eligibility clinical-split) =====
    class LocalSegment {
        +segmentId
        +ageRange
        +gender
        +district
        +telemetryAccessibility
    }

    class ClinicalSegment {
        +segmentId
        +conditions
        +accessibilityClassification_POD
        +malaffiSegmentMetadataRef
        +membershipSource_Malaffi_scopedQuery
    }

    class EligibilitySnapshot {
        +snapshotId
        +capturedAt
        +localMatchResult
        +frozenClinicalMembership
        +malaffiQueryScope
        +immutable_flag
    }

    %% ===== CHALLENGE CORE =====
    class Challenge {
        +challengeId
        +name
        +description
        +type_Individual_Team_District
        +publishedDateTime
        +startDateTime
        +endDateTime
        +status_Draft_Active_Completed_Archived
        +rewardPointsEnabled_flag
        +redemptionMethod_offline_points_hybrid
        +pointsFeatureFlag
    }

    %% (updated: segment referenced, segmentation is separate) — holds segmentId refs, not raw criteria
    class EligibilityRule {
        +ruleId
        +boundSegmentIds_ref
        +ageRange
        +gender
        +conditions
        +district
        +accessibilityClassification
        +whitelistedAudience
    }

    class WinningCriteria {
        +criteriaId
        +type
        +rankCount
        +scoreThreshold
        +consecutiveDays
        +cohortDimension
        +mappedReward
    }

    class ChallengeRequest {
        +requestId
        +origin_internal_user
        +submitterRef
        +proposalDetails
        +reviewStatus
    }

    class Enrollment {
        +enrollmentId
        +enrollmentDate
        +participationMode_individual_team_district
        +leaderboardConsent_name_initials
        +snapshotEligibility
        +status_Active_Left_Completed
    }

    %% ===== GOALS & SCORING PLAN =====
    class Goal {
        +goalId
        +metric
        +threshold
        +frequency_daily_weekly_onetime_event
        +dataSource
        +assignmentModel_segment_baseline
        +contributesToScore_flag
        +rewardsPointsOnly_flag
        +accessibilitySpecific_flag
        +locked
    }

    class ScoringPlan {
        +scoringPlanId
        +weeklyMax_100
        +tieBreakRules
    }

    class ScoreComponent {
        +componentId
        +goalRef
        +weeklyAllocation
        +scoringLogic
        +isConsistencyBonus_flag
    }

    %% ===== ACTIVITY & SCORE LEDGER =====
    class Activity {
        +activityId
        +metric
        +value
        +timestamp
        +source
        +dayKey
    }

    class DailyResult {
        +dayKey
        +isSuccessfulDay
        +goalsMet
        +balancedDay_flag
        +evaluatedAfterClose
    }

    class WeeklyScore {
        +weekId
        +weekStart
        +weekEnd
        +scoreValue_0_100
        +componentBreakdown
        +finalized_flag
        +finalizedTimestamp
    }

    class WellnessScore {
        +challengeRef
        +value
        +avgOfCompletedWeeks
        +locked_flag
    }

    class Streak {
        +weekId
        +successfulDays_0_7
        +tier_bronze_silver_gold
        +resetsWeekly
    }

    %% ===== BADGES / TITLES =====
    class Badge {
        +badgeId
        +name
        +category
        +triggerType
        +tiered_flag
    }

    class BadgeAward {
        +awardId
        +earnedDate
        +tierLevel
        +inProgressPercent
    }

    class Title {
        +titleId
        +levelNumber
        +name
        +completedWeeksThreshold
        +perfectWeeksThreshold
    }

    class MemberProgression {
        +totalCompletedWeeks
        +totalPerfectWeeks
        +totalCompletedChallenges
        +currentTitleRef
    }

    %% ===== LEADERBOARD =====
    class Leaderboard {
        +leaderboardId
        +scope_individual_team_hybrid_district
        +lastRefresh
        +finalized_flag
    }

    class LeaderboardEntry {
        +rank
        +entityType_individual_team_district
        +displayName
        +score
        +isCurrentUser_flag
        +isTop3_flag
    }

    %% ===== REWARD POINTS / MARKETPLACE =====
    class Wallet {
        +walletId
        +currentBalance
        +lifetimeEarned
        +lifetimeRedeemed
    }

    class PointTransaction {
        +txnId
        +type_earn_redeem_adjust
        +points
        +weekIdentifier
        +challengeIdentifier
        +timestamp
        +sourceRef
    }

    class MarketplaceItem {
        +itemId
        +name
        +description
        +image
        +pointCost
        +rewardType_voucher_qr
        +inventoryLimit
        +availabilityStatus
        +validityPeriod
        +redemptionLimitPerUser
        +redemptionLimitPerPeriod
        %% ----- marketplace supplement (BRD-SUPPLEMENT) -----
        +rewardDiscountType_PERCENTAGE_CURRENCY_AMOUNT
        +rewardDiscountAmount
        +rewardPointCost
        +expiryRulesPostRedemption
        +rewardId_SKU
        +partnerRef
        +rewardCategory_voucher_discount_physicalGood_experience_service
        +currency_ISO4217
        +localizedName_AR_EN
        +localizedDescription_AR_EN
        +status_draft_active_paused_archived
        +availabilityGoLiveDate
        +redemptionMethod_onlineCode_QR_offlineManual
        +voucherCodeFormat
        +termsAndConditions
        +eligibilityConstraints_segment_tier_age
        +minPointsBalance_costTier
        +featured_sortPriority
        +taxVatApplicability
    }

    %% ===== REWARD SUPPLEMENT (BRD-SUPPLEMENT marketplace) =====
    class Partner {
        +partnerId
        +name
        +contactRef
        +imageSubmissionMode_manualToMalaffi_CMS
    }

    class InventoryCounters {
        +counterId
        +totalInventoryLimit
        +reserved
        +issued
        +remaining
    }

    class Redemption {
        +redemptionId
        +redeemedDate
        +pointsDeducted
        +status
    }

    class Voucher {
        +voucherId
        +code_or_QR
        +artifactType_code_qr
        +issuedDate
        +expiryDate
        +used_flag
    }

    %% ===== EVENTS / SCREENINGS / QUESTS (point-only goal sources) =====
    class SahatnaEvent {
        +eventId
        +name
        +signupPoints
        +checkinPoints
        +eligibleForSignup_flag
        +eligibleForCheckin_flag
    }

    class Screening {
        +screeningId
        +type_IFHAS
        +pointsPerInstance
        +maxRewardedInstances
    }

    %% ===== ADDED IN ROBUSTNESS (Step 2 back-propagation) =====
    %% These nouns were forced by reconciling use-case text against the model;
    %% all absent from the original Step-1 model. Tag: (added in robustness).
    class WellnessDataConnection {
        +connectionId
        +provider_apple_google
        +scopesGranted
        +status_connected_denied_pending
        +linkedDateTime
    }

    class IngestionLog {
        +logId
        +metric
        +rawValue
        +sourceRef
        +timestamp
        +windowKey
        +decision_accepted_rejectedDuplicate_lateSync
    }

    class Ranking {
        +rankingId
        +challengeRef
        +orderedEntries
        +tieBreakApplied_flag
        +finalized_flag
        +finalizedTimestamp
    }

    class RankingSnapshot {
        +snapshotId
        +leaderboardRef
        +frozenOrderedRows
        +tieBreakOutcome
        +capturedAtChallengeEnd
    }

    class CohortScope {
        +cohortScopeId
        +segmentRef
        +dimensionKeys_age_gender_conditions_district
        +viewerSharedBoardKey
    }

    class ShareCard {
        +shareCardId
        +badgeAwardRef
        +imageRef
        +prefilledText
        +deepLink
        +generatedAt
    }

    class WinnersList {
        +winnersListId
        +challengeRef
        +criteriaApplied
        +confirmed_flag
        +confirmedBy
        +confirmedTimestamp
    }

    class WinnerEntry {
        +winnerEntryId
        +memberRef
        +winningCriteriaRef
        +rank
        +mappedReward
        +contactEmail
        +contactPhone
    }

    class ChallengeMetrics {
        +metricsId
        +challengeRef
        +adoptionCount
        +completionRate
        +retentionRate
        +streakDistribution
        +segmentedBy
    }

    class EngagementFunnelStage {
        +stageId
        +stageName_view_enroll_active_complete
        +count
        +conversionFromPrev
    }

    class TeamInvitation {
        +invitationId
        +teamRef
        +targetEmailOrPhone
        +uniqueLink
        +code
        +status_pending_accepted_expired
        +expiry
    }

    %% ===== ADDED IN ARCHITECTURE ENHANCEMENTS =====
    %% Surfaced while building the layered architecture (ENHANCEMENTS-spec).
    %% Tag: (added in architecture enhancements).
    class ContentAsset {
        +assetId
        +type_image_icon_media
        +localizedVariant_AR_EN
        +assetUri
        +storedIn_challengeContentStore
        +mimeType
        +uploadedAt
    }

    class Survey {
        +surveyId
        +name
        +description
        +pillar_mental_nutrition_sleep
        +questions
        +localizedContent_AR_EN
        +status
    }

    class SurveyResponse {
        +responseId
        +surveyRef
        +memberRef
        +answers
        +submittedAt
        +source_selfReported_checkin
    }

    %% ===== PHASE 2 / 3 =====
    class Team {
        +teamId
        +teamName
        +creatorRef
        +maxSize
        +inviteCode
        +teamScore_avg
    }

    class District {
        +districtId
        +name
        +districtScore_avg
        +participantCount
        +affiliationMethod_derived_selected
    }

    class CitymoovQuest {
        +questId
        +category
        +pointsPerCompletion
        +maxRewardedQuests
    }

    %% ===== ASSOCIATIONS =====
    Member "1" --> "0..*" Enrollment : enrolls via
    Challenge "1" --> "0..*" Enrollment : has
    Enrollment "1" --> "1..*" Goal : assigns (locked)
    Challenge "1" --> "1..*" Goal : defines
    Challenge "1" --> "1" EligibilityRule : restricted by
    Challenge "1" --> "1..*" WinningCriteria : evaluated by
    Challenge "1" --> "1" ScoringPlan : scored by
    EligibilityRule "0..*" ..> "0..*" Segment : references by segmentId (updated: segment referenced, segmentation is separate)
    ChallengeRequest "0..*" --> "0..1" Challenge : may become

    ScoringPlan "1" *-- "1..*" ScoreComponent : composed of
    ScoreComponent "0..1" --> "1" Goal : weights

    Member "1" --> "0..*" Activity : logs/syncs
    Activity "1..*" --> "1" DailyResult : aggregates into
    Enrollment "1" --> "0..*" DailyResult : tracks
    DailyResult "1..*" --> "1" WeeklyScore : rolls up to
    Enrollment "1" --> "1..*" WeeklyScore : produces
    WeeklyScore "1..*" --> "1" WellnessScore : averaged into
    Enrollment "1" --> "1" WellnessScore : yields
    WeeklyScore "1" --> "1" Streak : embeds
    Enrollment "1" --> "0..*" Streak : has weekly

    Member "1" --> "0..*" BadgeAward : earns
    BadgeAward "0..*" --> "1" Badge : instance of
    Member "1" --> "1" MemberProgression : accumulates
    MemberProgression "0..*" --> "1" Title : holds highest
    Title ..> Title : level ladder

    Challenge "1" --> "1" Leaderboard : ranked by
    Leaderboard "1" *-- "0..*" LeaderboardEntry : contains
    LeaderboardEntry "0..1" --> "1" WellnessScore : reflects

    Member "1" --> "1" Wallet : owns
    Wallet "1" *-- "0..*" PointTransaction : records
    WeeklyScore "1" --> "0..1" PointTransaction : credits (score x10)
    Wallet "1" --> "0..*" Redemption : spends via
    Redemption "0..*" --> "1" MarketplaceItem : redeems
    Redemption "1" --> "1" Voucher : issues
    Redemption "1" --> "1" PointTransaction : debits

    %% ----- Associations added in marketplace supplement -----
    MarketplaceItem "0..*" --> "1" Partner : supplied by (added in marketplace supplement)
    MarketplaceItem "1" --> "1..*" Voucher : issuable as (added in marketplace supplement)
    MarketplaceItem "1" --> "1" InventoryCounters : stock tracked by (added in marketplace supplement)

    Challenge "0..*" --> "0..*" SahatnaEvent : awards points for
    Challenge "0..*" --> "0..*" Screening : awards points for
    SahatnaEvent "0..*" --> "0..*" PointTransaction : bonus credits
    Screening "0..*" --> "0..*" PointTransaction : bonus credits

    %% ----- Associations added in robustness (Step 2) -----
    Member "1" --> "0..*" WellnessDataConnection : connects (added in robustness)
    WellnessDataConnection "1" --> "0..*" Activity : enables ingest of (added in robustness)
    Activity "1" --> "0..*" IngestionLog : audited by (added in robustness)
    Goal "1" --> "0..*" IngestionLog : tagged in (added in robustness)
    Challenge "1" --> "0..1" Ranking : finalized as (added in robustness)
    Ranking "1..*" --> "1" WellnessScore : orders (added in robustness)
    Leaderboard "1" --> "0..1" RankingSnapshot : frozen as (added in robustness)
    RankingSnapshot "0..1" --> "1" Ranking : reflects (added in robustness)
    Leaderboard "1" --> "0..1" CohortScope : limited by (added in robustness)
    CohortScope "0..*" --> "1" Segment : slice of (added in robustness)
    BadgeAward "1" --> "0..*" ShareCard : rendered as (added in robustness)
    Challenge "1" --> "0..1" WinnersList : concludes with (added in robustness)
    WinnersList "1" *-- "0..*" WinnerEntry : contains (added in robustness)
    WinnerEntry "0..*" --> "1" Member : names (added in robustness)
    WinnerEntry "0..*" --> "1" WinningCriteria : per (added in robustness)
    Challenge "1" --> "0..1" ChallengeMetrics : reported by (added in robustness)
    ChallengeMetrics "1" *-- "0..*" EngagementFunnelStage : composed of (added in robustness)
    Team "1" --> "0..*" TeamInvitation : issues [P2] (added in robustness)

    %% ----- Associations added in architecture enhancements -----
    Challenge "1" *-- "0..*" ContentAsset : owns (added in architecture enhancements)
    Survey "1" --> "0..*" SurveyResponse : defines (added in architecture enhancements)
    Member "1" --> "0..*" SurveyResponse : submits (added in architecture enhancements)
    SurveyResponse "1" --> "0..*" Activity : sourced as self-reported (added in architecture enhancements)
    SurveyResponse "1" --> "0..*" IngestionLog : ingested via (added in architecture enhancements)

    %% ----- Generalizations -----
    LeaderboardEntry <|-- Member : individual entry [P1]
    LeaderboardEntry <|-- Team : team entry [P2]
    LeaderboardEntry <|-- District : district entry [P3]

    %% ----- Generalizations + associations added in eligibility clinical-split -----
    Segment <|-- LocalSegment : local (added in eligibility clinical-split)
    Segment <|-- ClinicalSegment : clinical (added in eligibility clinical-split)
    Enrollment "1" --> "0..1" EligibilitySnapshot : freezes (added in eligibility clinical-split)
    EligibilitySnapshot "0..*" --> "0..*" ClinicalSegment : frozen membership (added in eligibility clinical-split)

    %% ----- Phase 2 / 3 associations -----
    Team "0..1" --> "0..*" Member : has members [P2]
    Enrollment "0..*" --> "0..1" Team : as team [P2]
    Team "1" --> "1" WellnessScore : team avg [P2]
    District "1" --> "0..*" Enrollment : represented by [P3]
    District "1" --> "1" WellnessScore : district avg [P3]
    Challenge "0..*" --> "0..*" CitymoovQuest : awards points for [P2]
    Goal "0..1" --> "0..1" Member : baseline-personalized [P2]
```

---

## 2. Class List, Attributes & Associations Table

| # | Class | Scope | Key Attributes | Key Associations (multiplicity) | BRD trace |
|---|-------|-------|----------------|----------------------------------|-----------|
| 1 | **Member** | P1 | displayName, initials, email, phone, age, gender, conditions, accessibilityFlag(POD), districtAddress, pushConsent, emailConsent, wellnessDataConnected | enrolls 0..* Enrollment; owns 1 Wallet; earns 0..* BadgeAward; accumulates 1 MemberProgression; logs 0..* Activity | Req1, Req11, Enrollment Flow, NFR-Privacy |
| 2 | **Segment** *(updated: segment referenced, segmentation is separate)* | P1 | ageRange, gender, conditions, accessibilityClassification, whitelisted, district | **owned by the segmentation concern, not challenge-svc**; referenced by 0..* EligibilityRule via segmentId; basis for segment-based Goal thresholds | Req2b, Req3, Goal Assignment Models |
| 3 | **Challenge** | P1 | name, type(Ind/Team/District), published/start/end dateTime, status, rewardPointsEnabled flag, redemptionMethod, pointsFeatureFlag | has 0..* Enrollment; defines 1..* Goal; 1 EligibilityRule; 1..* WinningCriteria; 1 ScoringPlan; 1 Leaderboard | Req1,3,14, Challenge Structure & Lifecycle |
| 4 | **EligibilityRule** | P1 | ageRange, gender, conditions, district, accessibilityClassification, whitelistedAudience | restricts 1 Challenge; visibility = profile match | Req3, Eligibility & Audience Targeting |
| 5 | **WinningCriteria** | P1 | type (HighestScore/MostBalancedDays/PillarChampion/ConsistentEngagement/ScoreMaintenance), rankCount, scoreThreshold, consecutiveDays, cohortDimension, mappedReward | evaluates 1 Challenge; maps to reward | Req12, Winning Criteria & Reward Mapping |
| 6 | **ChallengeRequest** | P1 | origin(internal/user), submitterRef, proposalDetails, reviewStatus | may become 0..1 Challenge | Req4, Challenge Request Submission |
| 7 | **Enrollment** | P1 | enrollmentDate, participationMode, leaderboardConsent(name/initials), snapshotEligibility, status | links Member↔Challenge; assigns 1..* Goal; produces 1..* WeeklyScore; yields 1 WellnessScore | Req1, General Enrollment Flow, Disenrollment |
| 8 | **Goal** | P1 | metric, threshold, frequency(daily/weekly/onetime/event), dataSource, assignmentModel(segment[P1]/baseline[P2]), contributesToScore, rewardsPointsOnly, accessibilitySpecific[P2], locked | defined by Challenge; assigned by Enrollment; weighted by ScoreComponent | Req2a,5; Appendix Goals, Goal Locking |
| 9 | **ScoringPlan** | P1 | weeklyMax=100, tieBreakRules | scores 1 Challenge; composed of 1..* ScoreComponent | Appendix Scoring, Tie-Breaking |
| 10 | **ScoreComponent** | P1 | goalRef, weeklyAllocation, scoringLogic, isConsistencyBonus | part-of ScoringPlan (aggregation); weights 1 Goal | Weekly Score Structure, Consistency Allocation |
| 11 | **Activity** | P1 | metric, value, timestamp, source, dayKey | logged by Member; aggregates into DailyResult | Req5, Appendix data sources, Score Validation |
| 12 | **DailyResult** | P1 | dayKey, isSuccessfulDay, goalsMet, balancedDay, evaluatedAfterClose | tracked by Enrollment; rolls up to WeeklyScore; feeds Streak | Streaks Daily Success, Winning(Balanced Days) |
| 13 | **WeeklyScore** | P1 | weekStart/End, scoreValue(0–100), componentBreakdown, finalized, finalizedTimestamp | produced by Enrollment; averaged into WellnessScore; embeds Streak; credits PointTransaction | Req5,6; Individual Weekly Score Calc |
| 14 | **WellnessScore** | P1 | value, avgOfCompletedWeeks, locked | yielded by Enrollment; drives LeaderboardEntry | Final Challenge Score, Score Visibility |
| 15 | **Streak** | P1 | successfulDays(0–7), tier(Bronze/Silver/Gold), resetsWeekly | embedded in WeeklyScore; has weekly per Enrollment | Req6,7; Streaks section |
| 16 | **Badge** | P1 | name, category, triggerType, tiered | template for 0..* BadgeAward | Req15–17, Badges section |
| 17 | **BadgeAward** | P1 | earnedDate, tierLevel, inProgressPercent | earned by Member; instance-of Badge | Req15,16, In-progress tracking |
| 18 | **Title / Level** | **P2** | levelNumber, name, completedWeeksThreshold, perfectWeeksThreshold | held (highest) by MemberProgression; level ladder | P2 Req10,11; Titles section |
| 19 | **MemberProgression** | P1* | totalCompletedWeeks, totalPerfectWeeks, totalCompletedChallenges, currentTitleRef | accumulates per Member; holds highest Title | Titles Progression Criteria (counters P1, Title display P2) |
| 20 | **Leaderboard** | P1 | scope, lastRefresh, finalized | ranks 1 Challenge; contains 0..* LeaderboardEntry | Req8, Leaderboard section, NFR Performance |
| 21 | **LeaderboardEntry** | P1 | rank, entityType, displayName, score, isCurrentUser, isTop3 | part-of Leaderboard; reflects 1 WellnessScore; generalized by Member[P1]/Team[P2]/District[P3] | Individual/Hybrid/District Leaderboard |
| 22 | **Wallet** | P1 | currentBalance, lifetimeEarned, lifetimeRedeemed | owned by Member; records 0..* PointTransaction | Req18, Wallet Structure |
| 23 | **PointTransaction** | P1 | type(earn/redeem/adjust), points, weekIdentifier, challengeIdentifier, timestamp, sourceRef | part-of Wallet; credited by WeeklyScore/Event/Screening; debited by Redemption | Reward Points Earning/Audit |
| 24 | **MarketplaceItem** (Reward) | P1 | name, description, image, pointCost, rewardType(voucher/qr), inventoryLimit, availabilityStatus, validity, redemptionLimits **+ (added in marketplace supplement): rewardDiscountType(PERCENTAGE/CURRENCY_AMOUNT), rewardDiscountAmount, rewardPointCost, expiryRulesPostRedemption, rewardId/SKU, partnerRef, rewardCategory, currency(ISO-4217), localizedName/Description(AR/EN), status(draft/active/paused/archived), availabilityGoLiveDate, redemptionMethod(onlineCode/QR/offlineManual), voucherCodeFormat, termsAndConditions, eligibilityConstraints, minPointsBalance, featured/sortPriority, taxVatApplicability** | redeemed by 0..* Redemption; **supplied by 1 Partner; issuable as 1..* Voucher; stock tracked by 1 InventoryCounters (added in marketplace supplement)** | Req19, Marketplace Catalog/Inventory, **BRD-SUPPLEMENT-marketplace-reward** |
| 25 | **Redemption** | P1 | redeemedDate, pointsDeducted, status | spends Wallet; redeems 1 MarketplaceItem; issues 1 Voucher; debits 1 PointTransaction | Req20, Redemption Flow |
| 26 | **Voucher** | P1 | code_or_QR, artifactType, issuedDate, expiryDate, used | issued by Redemption (stored in "My Rewards") | Req20, Reward Types, Expiry Handling |
| 27 | **SahatnaEvent** | P1 | name, signupPoints, checkinPoints, eligibleForSignup, eligibleForCheckin | awards points for Challenge; bonus PointTransaction | Req9,10; Event Participation config |
| 28 | **Screening** | P1 | type(IFHAS), pointsPerInstance, maxRewardedInstances | awards points for Challenge; bonus PointTransaction | Appendix Screening (IFHAS) |
| 29 | **Team** | **P2** | teamName, creatorRef, maxSize, inviteCode, teamScore(avg) | has 0..* Member; team Enrollment; team WellnessScore; leaderboard entry | P2 Req6–9; Team Score Calc, Team Enrollment |
| 30 | **District** | **P3** | name, districtScore(avg), participantCount, affiliationMethod | represented by 0..* Enrollment; district WellnessScore; two-level leaderboard | P3 Req1–3; District Score Calc, Heatmap |
| 31 | **CitymoovQuest** | **P2** | category, pointsPerCompletion, maxRewardedQuests | awards points for Challenge; bonus PointTransaction | P2 Req2; Citymoov Quest Integration |
| 31a | **Partner** *(added in marketplace supplement)* | P1 | partnerId, name, contactRef, imageSubmissionMode(manualToMalaffi[Sept]/CMS[later]) | supplies 0..* MarketplaceItem; provides reward images (Sept Challenge = **manual submission to Malaffi team**, no upload UI; CMS-managed upload is a later increment) | BRD-SUPPLEMENT-marketplace-reward |
| 31b | **InventoryCounters** *(added in marketplace supplement)* | P1 | counterId, totalInventoryLimit, reserved, issued, remaining | tracks stock for 1 MarketplaceItem; enforces total-inventory limit under concurrency (reserve→issue saga) | BRD-SUPPLEMENT-marketplace-reward |
| 31c | **ContentAsset** *(added in architecture enhancements)* | P1 | assetId, type(image/icon/media), localizedVariant(AR/EN), assetUri, storedIn(challenge-content-store), mimeType, uploadedAt | owned (aggregation) by 1 Challenge; **blob persisted in challenge-content-store bucket**, challenge-db keeps only metadata + asset URIs | ENHANCEMENTS-spec E1 (challenge-authoring) |
| 31d | **Survey** *(added in architecture enhancements)* | P1 | surveyId, name, description, pillar(mental/nutrition/sleep), questions, localizedContent(AR/EN), status | definition served by Sahatna Survey API (sync read); defines 0..* SurveyResponse | ENHANCEMENTS-spec E3 (earn-scoring) |
| 31e | **SurveyResponse** *(added in architecture enhancements)* | P1 | responseId, surveyRef, memberRef, answers, submittedAt, source(self-reported/check-in) | defined by 1 Survey; submitted by Member; **self-reported activity-source** → sourced as 0..* Activity and ingested via 0..* IngestionLog (same async path as wearable metrics through ingestion-svc) | ENHANCEMENTS-spec E3 (earn-scoring) |

\* *MemberProgression counters (Completed/Perfect Weeks) are produced by Phase-1 scoring, but the **Title** they feed is the user-facing Phase-2 feature; counters tracked early for forward-traceability.*

### 2a. Classes added in robustness analysis (Step 2 back-propagation)

These nouns were surfaced while reconciling each use-case narrative against this model during robustness analysis (`03-robustness/`). They were **absent** from the original Step-1 model and are folded in here to honour the backward-traceability obligation. Marked **(added in robustness)** on the diagram.

| # | Class | Scope | Why forced (use-case text) | Surfaced in | Key Associations |
|---|-------|-------|----------------------------|-------------|------------------|
| 32 | **WellnessDataConnection** | P1 | UC-C4/C3 require connecting Apple/Google Health with an explicit denied/pending state; `Member.wellnessDataConnected` is only a boolean — the connection (provider, scopes, status) has no class | enrolment (UC-C3/C4), earn-scoring (UC-D1) | Member connects 0..*; enables 0..* Activity |
| 33 | **IngestionLog** | P1 | UC-D1 "every update logged with timestamp + source reference" + UC-D1.1 duplicate-rejection; `Activity` holds the *accepted* value, the audit of *every* attempt (incl. rejected) is a separate noun | earn-scoring (UC-D1) | audits Activity; tagged to Goal |
| 34 | **Ranking** | P1 | UC-D6 "finalizes rankings" + tie-break; the immutable scoring-side ordered result, distinct from the leaderboard *view* | earn-scoring (UC-D6) | Challenge finalized as 0..1; orders WellnessScore |
| 35 | **RankingSnapshot** | P1 | UC-E1.2/E2/E3 "at challenge end → positions final"; the frozen ordered rows, distinct from live `Leaderboard` | leaderboard (UC-E1/E3) | Leaderboard frozen as 0..1; reflects Ranking |
| 36 | **CohortScope** | P1 | UC-E1 "cohort-limited" board / NFR-2; `Leaderboard.scope` stores only the *kind*, not *which* viewers share a board | leaderboard (UC-E1/E3) | Leaderboard limited by 0..1; slice of Segment |
| 37 | **ShareCard** | P1 | UC-F4 "native phone share with pre-populated text"; the shareable artifact (image ref + caption + deep link) has no class | track-engage (UC-F4) | derived from BadgeAward |
| 38 | **WinnersList** | P1 | UC-J2/I2 retrieve + confirm winners; the computed/confirmed list is a first-class conclusion artifact | reporting (UC-J2), settlement (UC-I2) | Challenge concludes with 0..1; ◇— WinnerEntry |
| 39 | **WinnerEntry** | P1 | UC-J2 per-winner row (member, criterion, rank, mapped reward, contact) — part of WinnersList | reporting (UC-J2) | part-of WinnersList; names Member; per WinningCriteria |
| 40 | **ChallengeMetrics** | P1 | UC-J1 dashboard adoption/engagement/retention figures are a computed reporting entity, not on `Challenge` | reporting (UC-J1) | Challenge reported by 0..1; ◇— EngagementFunnelStage |
| 41 | **EngagementFunnelStage** | P1 | UC-J1 view→enroll→active→complete funnel stage — part of ChallengeMetrics | reporting (UC-J1) | part-of ChallengeMetrics |
| 42 | **TeamInvitation** | **P2** | UC-C6/C7 "unique link + code", per-invitee/expirable; `Team.inviteCode` is a single attribute, not a trackable artifact | enrolment (UC-C6/C7) | Team issues 0..* [P2] |

---

## 3. Aggregations & Generalizations (explicit)

- **Aggregation (whole–part)**: `ScoringPlan ◇— ScoreComponent`; `Leaderboard ◇— LeaderboardEntry`; `Wallet ◇— PointTransaction`. Parts have no meaning outside their whole.
- **Generalization**: `LeaderboardEntry` is the abstract competitor; specialized as `Member` (individual, P1), `Team` (P2), `District` (P3) — the Hybrid/District leaderboard polymorphism.
- **Title ladder**: `Title → Title` self-association forms the 7-level progression ladder (Starter → Legend).

## 4. Phase Boundary Notes (traceability guard)
- **Pure P1 build set**: Member, Segment, Challenge, EligibilityRule, WinningCriteria, ChallengeRequest, Enrollment(individual mode only), Goal(segment-based only), ScoringPlan, ScoreComponent, Activity, DailyResult, WeeklyScore, WellnessScore, Streak, Badge, BadgeAward, MemberProgression(counters), Leaderboard(individual scope), LeaderboardEntry(Member), Wallet, PointTransaction, MarketplaceItem, Redemption, Voucher, SahatnaEvent, Screening **+ (added in robustness): WellnessDataConnection, IngestionLog, Ranking, RankingSnapshot, CohortScope, ShareCard, WinnersList, WinnerEntry, ChallengeMetrics, EngagementFunnelStage**.
- **Deferred**: Title/Level + Title display (P2), Team + team enrollment/scoring/leaderboard (P2), **TeamInvitation (P2, added in robustness)**, baseline-personalized Goal assignment (P2), CitymoovQuest (P2), District + district enrollment/scoring/heatmap leaderboard (P3).
- These deferred classes are kept in the model (greyed via `[P2]`/`[P3]` tags) so Step-2 use cases and later sequence messages retain backward links and no future requirement is orphaned.
