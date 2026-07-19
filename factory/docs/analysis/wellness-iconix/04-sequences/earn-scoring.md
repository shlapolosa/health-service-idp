# ICONIX Step 3 — Sequence Diagrams: Package D "Earn / Scoring" (`earn-scoring`)

> **Process**: ICONIX (Rosenberg) — use-case-driven, milestone-driven. This is the Step-3 sequence
> deliverable for the **Earn / Scoring** package. Each sequence diagram is allocated directly from its
> Step-2 robustness diagram (`03-robustness/earn-scoring.md`): the **boundary** and **entity** objects
> become lifelines, and each **control** object's responsibilities become concrete **messages**
> allocated to the entity that *owns the data* (Rosenberg's allocation-of-behaviour rule). Lifeline
> stereotypes carry through as `«B»`, `«C»`, `«E»`.
>
> **Allocation rule applied**: a controller is not a "god object." Where an operation reads/writes a
> single entity, the method is **placed on that entity** and the controller merely orchestrates the
> call sequence. Pure cross-entity logic (cap clamp, averaging, tie-break ordering) stays on the
> controller because no single entity owns it.
>
> **Traceability**: every diagram has a *Backward trace* table mapping each message back to its
> use-case basic/alternate course and to the robustness object it came from. Forward links to design
> (Step 4) are the operations now allocated to each entity class.
>
> **Phase tags**: 🟢 P1 in-scope · 🟡 P2 deferred · 🔵 P3 deferred. Deferred use cases (UC-D8/D9/D10)
> are drawn for forward-traceability and tagged; they are **not** in the Phase-1 build.

---

## UC-D1 — Ingest Goal Performance Data 🟢 P1

**Basic course**: a data-source actor POSTs a metric to the Ingestion API → controller tags it to the
Goal + time window, dedupe-checks, persists `Activity`, writes the `IngestionLog` audit row.
**Alternates**: D1.1 duplicate-in-window → reject but still log; D1.2 late device sync → accept within
the Goal's late-sync window and log the decision.

```mermaid
sequenceDiagram
    autonumber
    actor SRC as Wearable / IFHAS / Events / Survey 🟢
    participant BAPI as «B» Ingestion API
    participant CING as «C» GoalDataIngestionController
    participant EGOAL as «E» Goal
    participant EACT as «E» Activity
    participant ELOG as «E» IngestionLog

    SRC->>BAPI: POST metric(value, timestamp, source, goalRef)
    BAPI->>CING: ingest(metricPayload)
    CING->>EGOAL: resolveWindow(goalRef, timestamp)
    EGOAL-->>CING: window(dayKey, frequency, lateSyncLimit)
    CING->>EACT: findInWindow(goalRef, dayKey, source)
    EACT-->>CING: existing?

    alt D1.1 duplicate within window
        CING->>ELOG: record(timestamp, source, decision="REJECTED_DUPLICATE")
        CING-->>BAPI: 409 duplicate
    else D1.2 late device sync
        CING->>EGOAL: isWithinLateSyncLimit(timestamp)
        EGOAL-->>CING: true
        CING->>EACT: create(metric, value, timestamp, source, dayKey)
        CING->>ELOG: record(timestamp, source, decision="ACCEPTED_LATE")
        CING-->>BAPI: 202 accepted (late)
    else basic course — accept
        CING->>EACT: create(metric, value, timestamp, source, dayKey)
        CING->>ELOG: record(timestamp, source, decision="ACCEPTED")
        CING-->>BAPI: 201 created
    end
    BAPI-->>SRC: ack
```

**Backward trace — UC-D1**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| ingest | `GoalDataIngestionController.ingest` | D1 basic (ingest) | `«C» GoalDataIngestionController` |
| resolveWindow / isWithinLateSyncLimit | `Goal` | D1 (tag-to-goal+window) / D1.2 (late-sync check) | `«E» Goal` |
| findInWindow | `Activity` | D1.1 (dedupe-check) | `«E» Activity` |
| create | `Activity` | D1 basic / D1.2 | `«E» Activity` |
| record | `IngestionLog` | D1 (log every update), D1.1, D1.2 | `«E» IngestionLog (new)` |

---

## UC-D1a — Stream Wearable Telemetry (Health Connect SDK) 🟢 P1 ⊕

**Basic course (E2)**: the member's **on-device** `Health Connect SDK` reads Apple Health / Google Fit and
**streams** telemetry async through APIM-north → BFF Wearable Ingest → APIM-south → ingestion-svc.
ingestion-svc verifies, dedupe-checks against the Goal window, persists `Activity` (+ `IngestionLog`), and emits
`activity.verified`. This is a frontend stream, **not** a server-side wearables-cloud pull.
**Alternates**: D1a.1 duplicate-in-window → reject but still log; D1a.2 late device sync → accept within the
Goal's late-sync window and log the decision.

```mermaid
sequenceDiagram
    autonumber
    actor MEM as Member on-device 🟢
    participant HCS as Health Connect SDK
    participant APN as APIM-north
    participant BWI as BFF Wearable Ingest
    participant APS as APIM-south
    participant ING as ingestion-svc
    participant CH as challenge-svc
    participant SC as scoring-svc

    MEM->>HCS: grant + read Apple Health / Google Fit
    HCS-)APN: stream telemetry (value, ts, source, goalRef)
    APN-)BWI: forward telemetry batch
    BWI-)APS: relay to ingestion (async)
    APS-)ING: ingest(metricPayload)
    ING->>CH: resolveGoalWindow(goalRef, ts)
    CH-->>ING: window (dayKey, frequency, lateSyncLimit)

    alt D1a.1 duplicate within window
        ING->>ING: record IngestionLog (decision REJECTED_DUPLICATE)
    else D1a.2 late device sync
        ING->>ING: verify within lateSyncLimit, create Activity
        ING->>ING: record IngestionLog (decision ACCEPTED_LATE)
    else basic course
        ING->>ING: verify, create Activity
        ING->>ING: record IngestionLog (decision ACCEPTED)
    end
    ING--)SC: event activity.verified(enrollment, goalRef, dayKey)
```

**Backward trace — UC-D1a ⊕**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| stream telemetry | `Health Connect SDK` → `BFF Wearable Ingest` | D1a basic (on-device frontend stream) | `«B» Health Connect SDK`, `«B» BFF Wearable Ingest` |
| ingest | `WearableIngestController` (ingestion-svc) | D1a basic (verify) | `«C» WearableIngestController` + `«B» Ingestion API` |
| resolveGoalWindow | `Goal` | D1a (tag-to-goal+window) / D1a.2 | `«E» Goal` |
| create Activity | `Activity` | D1a basic / D1a.2 | `«E» Activity` |
| record IngestionLog | `IngestionLog` | D1a, D1a.1, D1a.2 | `«E» IngestionLog (new)` |
| activity.verified | `WearableIngestController` | D1a (emit verified event) | `«C» WearableIngestController` |

---

## UC-D1b — Submit Survey / Check-in Response 🟢 P1 ⊕

**Basic course (E3)**: the member's **on-device** `Surveys / Check-ins` screen fetches **survey info**
(definitions/questions) **sync** from the `Sahatna Survey API`, then **submits** a response. The `SurveyResponse`
**streams the SAME way as wearables** — async through APIM-north → Sahatna Survey API → APIM-south →
ingestion-svc — where it is ingested as **self-reported activity** (a check-in), feeding scoring like a verified
wearable metric.
**Alternates**: D1b.1 survey-info read is sync (no ingestion); D1b.2 duplicate check-in in window → reject but
still log.

```mermaid
sequenceDiagram
    autonumber
    actor MEM as Member on-device 🟢
    participant SUR as Surveys / Check-ins
    participant APN as APIM-north
    participant SSA as Sahatna Survey API
    participant APS as APIM-south
    participant ING as ingestion-svc
    participant SC as scoring-svc

    Note over MEM,SSA: D1b.1 survey-info read is sync, no ingestion
    MEM->>SUR: open check-in
    SUR->>APN: GET survey info
    APN->>SSA: getSurvey(surveyRef)
    SSA-->>SUR: Survey (questions, AR/EN)

    MEM->>SUR: submit response
    SUR-)APN: stream SurveyResponse (answers, ts, goalRef)
    APN-)SSA: ingest survey response (async)
    SSA-)APS: relay to ingestion as self-reported activity
    APS-)ING: ingest(selfReportedPayload)

    alt D1b.2 duplicate check-in in window
        ING->>ING: record IngestionLog (decision REJECTED_DUPLICATE)
    else basic course
        ING->>ING: map SurveyResponse to self-reported Activity, create
        ING->>ING: record IngestionLog (decision ACCEPTED)
    end
    ING--)SC: event activity.verified(enrollment, goalRef, dayKey)
```

**Backward trace — UC-D1b ⊕**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| getSurvey | `Sahatna Survey API` → `Survey` | D1b.1 (sync survey-info read) | `«B» Sahatna Survey API`, `«E» Survey (new)` |
| stream SurveyResponse | `Surveys / Check-ins` → `Sahatna Survey API` | D1b basic (async submit) | `«B» Surveys / Check-ins`, `«B» Sahatna Survey API` |
| ingest (self-reported) | `SurveyResponseController` (ingestion-svc) | D1b basic (ingest as activity) | `«C» SurveyResponseController` + `«B» Ingestion API` |
| map to Activity / create | `SurveyResponse` → `Activity` | D1b basic (self-reported activity) | `«E» SurveyResponse (new)`, `«E» Activity` |
| record IngestionLog | `IngestionLog` | D1b, D1b.2 | `«E» IngestionLog (new)` |
| activity.verified | `SurveyResponseController` | D1b (feed scoring) | `«C» SurveyResponseController` |

---

## UC-D2 — Evaluate Daily Goal Success 🟢 P1

**Basic course**: at day-close the Clock fires the Day-Close Trigger → controller, per enrollment,
evaluates each daily Goal's threshold against the day's Activity, writes `DailyResult`
(`isSuccessfulDay = ≥1 daily goal met`), and feeds the `Streak` counter.
**Alternates**: D2.1 only fires after day-close (no mid-day path); D2.2 mid-week enrollment → days prior
to `enrollmentDate` yield empty `DailyResult`.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock / Scheduler 🟢
    participant BDC as «B» Day-Close Trigger
    participant CEVAL as «C» DailyEvaluationController
    participant EENR as «E» Enrollment
    participant EGOAL as «E» Goal
    participant EACT as «E» Activity
    participant EDR as «E» DailyResult
    participant ESTK as «E» Streak

    CLK->>BDC: dayClose(dayKey)
    BDC->>CEVAL: evaluateDay(dayKey)
    CEVAL->>EENR: listActive(dayKey)
    EENR-->>CEVAL: enrollments[]

    loop per active enrollment
        alt D2.2 day before enrollmentDate
            CEVAL->>EENR: isEnrolledOn(dayKey)
            EENR-->>CEVAL: false
            CEVAL->>EDR: createEmpty(dayKey, enrollment)
        else basic course — evaluate thresholds
            CEVAL->>EGOAL: dailyGoals(enrollment)
            EGOAL-->>CEVAL: goals[]
            CEVAL->>EACT: valuesForDay(enrollment, dayKey)
            EACT-->>CEVAL: activities[]
            CEVAL->>EDR: create(dayKey, goalsMet, isSuccessfulDay)
            opt isSuccessfulDay == true
                CEVAL->>ESTK: incrementSuccessfulDay(weekId)
            end
        end
    end
```

> **D2.1** is enforced structurally: the only inbound boundary is `Day-Close Trigger`; the controller has
> no mid-day entry point. `isSuccessfulDay` (= ≥1 daily goal met) is computed by the controller across
> goals and persisted on `DailyResult`.

**Backward trace — UC-D2**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| evaluateDay | `DailyEvaluationController` | D2 basic (after day-close) / D2.1 | `«C» DailyEvaluationController` + `«B» Day-Close Trigger` |
| listActive / isEnrolledOn | `Enrollment` | D2 (scope per participant) / D2.2 | `«E» Enrollment` |
| dailyGoals | `Goal` | D2 (read threshold) | `«E» Goal` |
| valuesForDay | `Activity` | D2 (read metric) | `«E» Activity` |
| create / createEmpty | `DailyResult` | D2 (mark successful-day) / D2.2 (empty prior days) | `«E» DailyResult` |
| incrementSuccessfulDay | `Streak` | D2 (feed streak) | `«E» Streak` |

---

## UC-D3 — Compute Weekly Score 🟢 P1

**Basic course**: a `Goal-Met Event` (raised by D2's evaluation) drives a dynamic recompute → controller
sums each goal's weighted contribution from the `ScoringPlan` / `ScoreComponent`, clamps to the 100-cap,
and writes `WeeklyScore`.
**Alternates**: D3.1 no goals met → score 0; D3.2 the 100-cap is never exceeded (cap invariant).

```mermaid
sequenceDiagram
    autonumber
    participant BEVT as «B» Goal-Met Event
    participant CWS as «C» WeeklyScoreController
    participant ESP as «E» ScoringPlan
    participant ESC as «E» ScoreComponent
    participant EGOAL as «E» Goal
    participant EDR as «E» DailyResult
    participant EWS as «E» WeeklyScore

    BEVT->>CWS: onGoalMet(enrollment, weekId, goalRef)
    CWS->>ESP: componentsFor(challenge)
    ESP->>ESC: weights()
    ESC-->>ESP: components[]
    ESP-->>CWS: scoreComponents[]

    loop per ScoreComponent
        CWS->>EGOAL: isMetThisWeek(goalRef, weekId)
        EGOAL->>EDR: successDays(goalRef, weekId)
        EDR-->>EGOAL: metState
        EGOAL-->>CWS: met?
        opt met
            CWS->>CWS: accumulate(weeklyAllocation)
        end
    end

    alt D3.1 none met
        CWS->>EWS: setScore(weekId, 0)
    else basic course
        CWS->>CWS: total = sum(allocations)
        CWS->>EWS: setScore(weekId, clamp(total, 0, 100))  %% D3.2 cap invariant
    end
```

> **D3.2** the cap (`clamp(..,0,100)`) is controller logic — no single entity owns it — but the clamped
> value is written to `WeeklyScore.scoreValue`. The `Goal-Met Event` boundary is raised by UC-D2's
> controller, not a human actor (Package D is system-driven).

**Backward trace — UC-D3**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| onGoalMet | `WeeklyScoreController` | D3 basic (dynamic update) | `«C» WeeklyScoreController` + `«B» Goal-Met Event` |
| componentsFor / weights | `ScoringPlan` / `ScoreComponent` | D3 (weighted contribution) | `«E» ScoringPlan`, `«E» ScoreComponent` |
| isMetThisWeek / successDays | `Goal` / `DailyResult` | D3 (per-goal contribution) | `«E» Goal`, `«E» DailyResult` |
| accumulate / total / clamp | `WeeklyScoreController` | D3 (sum) / D3.2 (cap) | `«C» WeeklyScoreController` |
| setScore | `WeeklyScore` | D3 / D3.1 (zero) / D3.2 (≤100) | `«E» WeeklyScore` |

---

## UC-D4 — Award Streak / Consistency Bonus 🟢 P1

**Basic course**: within-week (Streak-Update) and at week-close (Clock), the controller counts
successful days (cap 7), resolves the tier (Bronze 4/7, Silver 6/7, Gold 7/7), and folds the configured
consistency bonus into the `WeeklyScore` via the `isConsistencyBonus` `ScoreComponent`.
**Alternates**: D4.1 bonus is embedded inside the 100 total; D4.2 streak resets each week — no carryover.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock / Scheduler 🟢
    participant BSTK as «B» Streak-Update / Week-Close Trigger
    participant CBON as «C» ConsistencyBonusController
    participant EDR as «E» DailyResult
    participant ESTK as «E» Streak
    participant ESC as «E» ScoreComponent
    participant EWS as «E» WeeklyScore

    CLK->>BSTK: streakUpdate(weekId) / weekClose(weekId)
    BSTK->>CBON: recomputeBonus(enrollment, weekId)

    alt D4.2 new weekId
        CBON->>ESTK: reset(weekId)  %% successfulDays -> 0, no carryover
    end

    CBON->>EDR: countSuccessfulDays(enrollment, weekId)
    EDR-->>CBON: days (0..7, cap 7)
    CBON->>ESTK: setSuccessfulDays(weekId, days)
    CBON->>CBON: tier = resolveTier(days)  %% 4/7 Bronze · 6/7 Silver · 7/7 Gold
    CBON->>ESTK: setTier(weekId, tier)
    CBON->>ESC: bonusAllocation(tier)  %% isConsistencyBonus_flag
    ESC-->>CBON: bonusPoints
    CBON->>EWS: applyConsistencyBonus(weekId, bonusPoints)  %% D4.1 embedded in 100, clamp <=100
```

> **D4.1** the bonus is delivered through the `isConsistencyBonus_flag` `ScoreComponent`, so
> `WeeklyScore.applyConsistencyBonus` keeps the total ≤100 (same cap invariant as D3.2).
> **D4.2** `Streak.reset` zeroes `successfulDays` on each new `weekId` (`resetsWeekly`).

**Backward trace — UC-D4**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| recomputeBonus | `ConsistencyBonusController` | D4 basic | `«C» ConsistencyBonusController` + `«B» Streak-Update / Week-Close Trigger` |
| countSuccessfulDays | `DailyResult` | D4 (count successful days) | `«E» DailyResult` |
| reset / setSuccessfulDays / setTier | `Streak` | D4 (write tier/days) / D4.2 (reset) | `«E» Streak` |
| resolveTier | `ConsistencyBonusController` | D4 (resolve tier) | `«C» ConsistencyBonusController` |
| bonusAllocation | `ScoreComponent` | D4 (configured bonus weight) | `«E» ScoreComponent` |
| applyConsistencyBonus | `WeeklyScore` | D4.1 (embedded in 100) | `«E» WeeklyScore` |

---

## UC-D5 — Finalize Weekly Score 🟢 P1

**Basic course**: at week-close the Clock fires → controller finalizes `WeeklyScore` (sets
`finalized_flag` + `finalizedTimestamp`), locks it immutable with a traceability link to the day data,
and emits the downstream triggers: reward-point accrual (G1), weekly summary (H4), and Title progression
(D8 🟡).
**Alternates**: D5.1 late data cannot change a finalized score; D5.2 a partial week is extrapolated to /100
before lock.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock / Scheduler 🟢
    participant BWC as «B» Week-Close Trigger
    participant CFIN as «C» WeeklyFinalizationController
    participant EWS as «E» WeeklyScore
    participant EDR as «E» DailyResult
    participant EENR as «E» Enrollment
    participant CG1 as «C» RewardAccrualController (G1)
    participant CH4 as «C» WeeklySummaryController (H4)
    participant CD8 as «C» TitleProgressionController (D8 🟡)

    CLK->>BWC: weekClose(weekId)
    BWC->>CFIN: finalizeWeek(weekId)
    CFIN->>EENR: scopeEnrollments(weekId)
    EENR-->>CFIN: enrollments[]

    loop per enrollment
        alt D5.1 already finalized
            CFIN->>EWS: isFinalized(weekId)
            EWS-->>CFIN: true
            Note over CFIN,EWS: late Activity/IngestionLog ignored for score
        else basic / D5.2 partial week
            opt D5.2 partial week
                CFIN->>EWS: extrapolateToHundred(weekId, daysElapsed)
            end
            CFIN->>EDR: traceabilityRefs(weekId)
            EDR-->>CFIN: dailyResultRefs[]
            CFIN->>EWS: finalize(weekId, finalizedTimestamp, dailyResultRefs)
            EWS-->>CFIN: finalized
            CFIN->>CG1: onWeeklyFinalized(weekId)   %% reward accrual, Package G
            CFIN->>CH4: onWeeklyFinalized(weekId)   %% weekly summary, Package H
            CFIN->>CD8: onWeeklyFinalized(weekId)   %% Title progression 🟡 (counters written P1)
        end
    end
```

> **D5.1** `WeeklyScore.finalize` is idempotent: once `finalized_flag=true` the controller refuses
> mutation. Downstream controllers (G1/H4/D8) are collaborators owned by other packages — shown here only
> to record the trigger edges; their internals are not re-detailed in Package D.

**Backward trace — UC-D5**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| finalizeWeek | `WeeklyFinalizationController` | D5 basic | `«C» WeeklyFinalizationController` + `«B» Week-Close Trigger` |
| scopeEnrollments | `Enrollment` | D5 (scope) | `«E» Enrollment` |
| isFinalized | `WeeklyScore` | D5.1 (no late change) | `«E» WeeklyScore` |
| extrapolateToHundred | `WeeklyScore` | D5.2 (partial week /100) | `«E» WeeklyScore` |
| traceabilityRefs | `DailyResult` | D5 (traceable to goal data) | `«E» DailyResult` |
| finalize | `WeeklyScore` | D5 (finalize + lock immutable) | `«E» WeeklyScore` |
| onWeeklyFinalized ×3 | `RewardAccrualController` / `WeeklySummaryController` / `TitleProgressionController` | D5 (emit downstream triggers G1/H4/D8) | `«C» CG1`, `«C» CH4`, `«C» CD8 🟡` |

---

## UC-D6 — Compute Final Wellness Score & Tie-Break 🟢 P1

**Basic course**: at challenge-end the Clock fires → `FinalScoreController` averages the completed,
finalized weekly scores (equal weight; late enrollment averages from its enrollment week), writes and
locks `WellnessScore`; then `TieBreakController` orders competitors into the finalized `Ranking`, applying
the `ScoringPlan.tieBreakRules` (more weeks above threshold; then lower variance).
**Alternates**: D6.1 no updates after finalization; D6.2 a membership change must not retroactively alter
finalized weekly scores.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock / Scheduler 🟢
    participant BCE as «B» Challenge-End Trigger
    participant CFS as «C» FinalScoreController
    participant CTB as «C» TieBreakController
    participant EENR as «E» Enrollment
    participant EWS as «E» WeeklyScore
    participant EWELL as «E» WellnessScore
    participant ESP as «E» ScoringPlan
    participant ERANK as «E» Ranking

    CLK->>BCE: challengeEnd(challengeRef)
    BCE->>CFS: computeFinal(challengeRef)
    CFS->>EENR: participants(challengeRef)
    EENR-->>CFS: enrollments[]

    loop per enrollment
        CFS->>EWS: completedWeeks(enrollment)  %% finalized only, from enrollment week
        EWS-->>CFS: weeklyScores[]
        CFS->>CFS: avg = average(weeklyScores)  %% equal weight
        CFS->>EWELL: setValue(enrollment, avg)
        CFS->>EWELL: lock(enrollment)  %% D6.1 no further updates
    end

    CFS->>CTB: finalizeRanking(challengeRef)
    CTB->>ESP: tieBreakRules(challengeRef)
    ESP-->>CTB: rules
    CTB->>EWELL: lockedScores(challengeRef)
    EWELL-->>CTB: scores[]
    CTB->>CTB: order = applyTieBreak(scores, rules)  %% weeks>threshold, then lower variance
    CTB->>ERANK: persist(challengeRef, orderedEntries)

    Note over CFS,EWS: D6.2 membership change never recomputes finalized WeeklyScore
```

> `Ranking` is the **scoring-side** finalized order; the Package-E `Leaderboard` later *reflects* it as a
> read-only view. Averaging and tie-break ordering are controller logic (cross-entity), but their results
> are persisted to `WellnessScore` and the new `Ranking` entity.

**Backward trace — UC-D6**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| computeFinal / average | `FinalScoreController` | D6 basic (average completed weeks) | `«C» FinalScoreController` + `«B» Challenge-End Trigger` |
| participants | `Enrollment` | D6 (scope; from enrollment week) | `«E» Enrollment` |
| completedWeeks | `WeeklyScore` | D6 (read finalized weeks) / D6.2 (never recompute) | `«E» WeeklyScore` |
| setValue / lock / lockedScores | `WellnessScore` | D6 (write+lock) / D6.1 (no updates) | `«E» WellnessScore` |
| finalizeRanking / applyTieBreak | `TieBreakController` | D6 (finalize rankings + tie-break) | `«C» TieBreakController` |
| tieBreakRules | `ScoringPlan` | D6 (tie-break rules) | `«E» ScoringPlan` |
| persist | `Ranking` | D6 (finalized ordered result) | `«E» Ranking (new)` |

---

## UC-D7 — Award Badge 🟢 P1

**Basic course**: a `Badge-Trigger Event` (raised by D2/D3/D4/D5 evaluations or a participation event)
arrives → controller evaluates the trigger against the `Badge` template, awards or advances the
`BadgeAward`, and attaches it to the `Member`; in-progress badges are tracked with a percent.
**Alternates**: D7.1 tiered advance (bump tier when a higher threshold is crossed); D7.2 team/district
badge categories deferred 🟡🔵; D7.3 badges persist across challenges (attach to `Member`, not `Enrollment`).

```mermaid
sequenceDiagram
    autonumber
    participant BBT as «B» Badge-Trigger Event
    participant CBAD as «C» BadgeAwardController
    participant EBADGE as «E» Badge
    participant EAWARD as «E» BadgeAward
    participant EMEM as «E» Member

    BBT->>CBAD: onTrigger(memberRef, triggerType, metricSnapshot)
    CBAD->>EBADGE: matching(triggerType)
    EBADGE-->>CBAD: badges[]

    loop per matching Badge
        CBAD->>EAWARD: existing(memberRef, badgeId)
        EAWARD-->>CBAD: award?
        alt threshold fully met
            alt D7.1 tiered & higher tier crossed
                CBAD->>EAWARD: advanceTier(memberRef, badgeId, newTier)
            else first award
                CBAD->>EAWARD: create(memberRef, badgeId, earnedDate, tierLevel)
                CBAD->>EMEM: attach(award)   %% D7.3 persists across challenges
            end
        else partial progress
            CBAD->>EAWARD: updateProgress(memberRef, badgeId, inProgressPercent)
        end
    end

    Note over CBAD,EBADGE: D7.2 team/district categories deferred 🟡🔵 (Badge.category supports them, award path needs Team/District context)
```

> **D7.3** `BadgeAward` attaches to `Member` (not `Enrollment`), so badges persist across challenges.
> **D7.2** is structurally present in `Badge.category` but the award path for team/district context is out
> of Phase-1 scope.

**Backward trace — UC-D7**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| onTrigger | `BadgeAwardController` | D7 basic (evaluate trigger) | `«C» BadgeAwardController` + `«B» Badge-Trigger Event` |
| matching | `Badge` | D7 (template + triggerType) | `«E» Badge` |
| existing / create / advanceTier / updateProgress | `BadgeAward` | D7 (award) / D7.1 (tiered advance) / D7 (in-progress) | `«E» BadgeAward` |
| attach | `Member` | D7.3 (persist across challenges) | `«E» Member` |

---

## UC-D8 — Award / Advance Title 🟡 P2 (deferred — modelled for traceability)

**Basic course**: on a Weekly-Finalized event (from D5), the controller increments the lifetime
`MemberProgression` counters (`totalCompletedWeeks`, and `totalPerfectWeeks` when the week was perfect),
then advances `Title` to the highest unlocked level per thresholds.
**Alternates**: D8.1 disenroll before finalization → that week is not counted; D8.2 counters never change
retroactively.

> **P1 note**: the **counters** are written by Phase-1 scoring (forward-traceability); the **Title**
> read-out is the P2 user-facing feature — hence the `🟡` lifelines/messages below.

```mermaid
sequenceDiagram
    autonumber
    participant BWF as «B» Weekly-Finalized Event (from D5)
    participant CTIT as «C» TitleProgressionController 🟡
    participant EWS as «E» WeeklyScore
    participant EMP as «E» MemberProgression
    participant ETITLE as «E» Title 🟡

    BWF->>CTIT: onWeeklyFinalized(memberRef, weekId)
    alt D8.1 disenrolled before finalization
        CTIT->>EWS: wasCountedAtFinalization(weekId)
        EWS-->>CTIT: false
        Note over CTIT,EWS: week not counted, no counter change
    else basic course
        CTIT->>EWS: isPerfectWeek(weekId)
        EWS-->>CTIT: perfect?
        CTIT->>EMP: incrementCompletedWeeks()   %% P1 counter (written early)
        opt perfect
            CTIT->>EMP: incrementPerfectWeeks()  %% P1 counter
        end
        CTIT->>ETITLE: highestUnlocked(completedWeeks, perfectWeeks) 🟡
        ETITLE-->>CTIT: title 🟡
        CTIT->>EMP: setCurrentTitle(title) 🟡    %% D8.2 monotonic, never retroactive
    end
```

**Backward trace — UC-D8 🟡**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| onWeeklyFinalized | `TitleProgressionController 🟡` | D8 basic | `«C» TitleProgressionController 🟡` + `«B» Weekly-Finalized Event` |
| wasCountedAtFinalization / isPerfectWeek | `WeeklyScore` | D8.1 (disenroll) / D8 (perfect-week) | `«E» WeeklyScore` |
| incrementCompletedWeeks / incrementPerfectWeeks / setCurrentTitle | `MemberProgression` | D8 (counters P1) / D8.2 (no retroactive) | `«E» MemberProgression` |
| highestUnlocked | `Title 🟡` | D8 (advance highest unlocked) | `«E» Title 🟡` |

---

## UC-D9 — Aggregate Team Score 🟡 P2 (deferred — modelled for traceability)

**Basic course**: on a Team-Score Recalc event, the controller averages member `WellnessScore`s, writes
the team average (materialised as a `WellnessScore` via the existing `Team→WellnessScore` association),
and updates the team's place in `Ranking`.
**Alternate**: D9.1 member add/remove → average recalculated *forward* only.

```mermaid
sequenceDiagram
    autonumber
    participant BTE as «B» Team-Score Recalc Event
    participant CTS as «C» TeamScoreController 🟡
    participant ETEAM as «E» Team 🟡
    participant EWELL as «E» WellnessScore
    participant ERANK as «E» Ranking

    BTE->>CTS: recalcTeam(teamRef)
    CTS->>ETEAM: members(teamRef) 🟡
    ETEAM-->>CTS: members[]
    CTS->>EWELL: scoresFor(members)
    EWELL-->>CTS: memberScores[]
    CTS->>CTS: teamAvg = average(memberScores)  %% D9.1 forward-only
    CTS->>EWELL: setTeamValue(teamRef, teamAvg) 🟡  %% Team.teamScore_avg materialised
    CTS->>ERANK: reorderTeams(challengeRef)
```

> `TeamScore` reuses `Team.teamScore_avg` (a `WellnessScore` via `Team→WellnessScore`) — **no new class**.

**Backward trace — UC-D9 🟡**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| recalcTeam / teamAvg | `TeamScoreController 🟡` | D9 basic / D9.1 (forward recalc) | `«C» TeamScoreController 🟡` + `«B» Team-Score Recalc Event` |
| members | `Team 🟡` | D9 (team membership) | `«E» Team 🟡` |
| scoresFor / setTeamValue | `WellnessScore` | D9 (average of member scores) | `«E» WellnessScore` |
| reorderTeams | `Ranking` | D9 (teams ranked) | `«E» Ranking (new)` |

---

## UC-D10 — Aggregate District Score 🔵 P3 (deferred — modelled for traceability)

**Basic course**: on a District-Score Recalc event, the controller averages participating users'
`WellnessScore`s, writes the district average (materialised as a `WellnessScore` via
`District→WellnessScore`), and updates the district's place in `Ranking`.
**Alternate**: D10.1 a user cannot change district mid-challenge.

```mermaid
sequenceDiagram
    autonumber
    participant BDE as «B» District-Score Recalc Event
    participant CDS as «C» DistrictScoreController 🔵
    participant EDIST as «E» District 🔵
    participant EWELL as «E» WellnessScore
    participant ERANK as «E» Ranking

    BDE->>CDS: recalcDistrict(districtRef)
    CDS->>EDIST: participants(districtRef) 🔵
    EDIST-->>CDS: enrollments[]
    Note over CDS,EDIST: D10.1 district membership frozen for the challenge
    CDS->>EWELL: scoresFor(enrollments)
    EWELL-->>CDS: scores[]
    CDS->>CDS: districtAvg = average(scores)
    CDS->>EWELL: setDistrictValue(districtRef, districtAvg) 🔵  %% District.districtScore_avg materialised
    CDS->>ERANK: reorderDistricts(challengeRef)
```

> `DistrictScore` reuses `District.districtScore_avg` (a `WellnessScore` via `District→WellnessScore`) — **no new class**.

**Backward trace — UC-D10 🔵**

| # | Message → owner | Use-case course | Robustness object |
|---|-----------------|-----------------|-------------------|
| recalcDistrict / districtAvg | `DistrictScoreController 🔵` | D10 basic | `«C» DistrictScoreController 🔵` + `«B» District-Score Recalc Event` |
| participants | `District 🔵` | D10 (one district per user) / D10.1 (frozen) | `«E» District 🔵` |
| scoresFor / setDistrictValue | `WellnessScore` | D10 (average of user scores) | `«E» WellnessScore` |
| reorderDistricts | `Ranking` | D10 (districts ranked) | `«E» Ranking (new)` |

---

## Operation Allocation Summary (forward link → Step 4 Design)

Each message above is now a method on the entity that owns the data. These are the operations the
domain classes (`02-domain-model.md`) must expose at design time:

| Entity | Allocated operations (from this step) | From UCs |
|--------|---------------------------------------|----------|
| `Goal` | resolveWindow, isWithinLateSyncLimit, dailyGoals, isMetThisWeek | D1, D2, D3 |
| `Activity` | findInWindow, create, valuesForDay | D1, D2 |
| `IngestionLog` (new) | record | D1 |
| `Enrollment` | listActive, isEnrolledOn, scopeEnrollments, participants | D2, D5, D6 |
| `DailyResult` | create, createEmpty, successDays, countSuccessfulDays, traceabilityRefs | D2, D3, D4, D5 |
| `Streak` | incrementSuccessfulDay, reset, setSuccessfulDays, setTier | D2, D4 |
| `ScoringPlan` | componentsFor, tieBreakRules | D3, D6 |
| `ScoreComponent` | weights, bonusAllocation | D3, D4 |
| `WeeklyScore` | setScore, applyConsistencyBonus, isFinalized, extrapolateToHundred, finalize, completedWeeks, isPerfectWeek, wasCountedAtFinalization | D3, D4, D5, D6, D8 |
| `WellnessScore` | setValue, lock, lockedScores, scoresFor, setTeamValue 🟡, setDistrictValue 🔵 | D6, D9, D10 |
| `Ranking` (new) | persist, reorderTeams 🟡, reorderDistricts 🔵 | D6, D9, D10 |
| `Badge` | matching | D7 |
| `BadgeAward` | existing, create, advanceTier, updateProgress | D7 |
| `Member` | attach (badge) | D7 |
| `MemberProgression` | incrementCompletedWeeks, incrementPerfectWeeks, setCurrentTitle 🟡 | D8 |
| `Title 🟡` | highestUnlocked | D8 |
| `Team 🟡` | members | D9 |
| `District 🔵` | participants | D10 |

**Controller-resident logic** (cross-entity, not owned by any single entity): cap-clamp (D3.2/D4.1),
weekly averaging (D6), tie-break ordering (D6), tier resolution (D4), team/district averaging (D9/D10).
These stay on their controllers per Rosenberg's allocation rule and become application-layer services in
Step 4.
