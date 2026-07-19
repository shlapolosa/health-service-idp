# ICONIX Step 3 — Sequence Diagrams: Package H — Notification & Nudges (`notification`)

**Process**: ICONIX (Rosenberg) — use-case-driven, milestone-driven. This is the **Step-3**
deliverable for the cross-cutting (`⚪ XC`) Notification package, realizing the **robustness diagrams**
in `03-robustness/notification.md` against the **domain model** in `02-domain-model.md`.

**How to read these**: each robustness **control** node (`«C»` verb) becomes one or more **messages**.
Per Rosenberg's allocation rule, each operation is allocated to the **entity that owns the data** it
reads/writes — so `read consent` lives on `NotificationConsent`, `assemble summary` reads `WeeklyScore`,
etc. Controllers orchestrate; entities answer. The **Basic Course** is the main top-to-bottom flow;
**Alternate Courses** are `alt` / `opt` fragments.

**Phase scope**: All four UCs are `🟢 P1` (cross-cutting). Phase-2/3 fan-out (team-add notifications,
district announcements, title-unlock nudges) is **out of build scope** and tagged inline where it touches
a message.

**New entities consumed** (back-ported from Step-2 robustness — must exist in `02-domain-model.md`):
`NotificationConsent` (N1), `NotificationType` (N2), `NotificationMessage` (N3), `NudgeSegment` (N4).

**Shared convergence point**: `NotificationDispatcher` is modelled **once** below and reused (by
reference) in H2/H3/H4 — the single place the consent gate (NFR-1) and the by-name rule are enforced.

---

## Shared sub-flow — `NotificationDispatcher.dispatch(...)` (the consent + by-name gate)

Funnelled through by **UC-H2, UC-H3, UC-H4**. Modelled once; each send-UC below `ref`s it.

```mermaid
sequenceDiagram
    autonumber
    participant DISP as «C» NotificationDispatcher
    participant CONSENT as «E» NotificationConsent (N1)
    participant MEMBER as «E» Member
    participant MSG as «E» NotificationMessage (N3)
    participant SEND as «C» send via provider
    participant NAPI as «B» Sahatna Notifications API
    participant GW as Notification Provider

    Note over DISP: dispatch(member, challenge, type, payload)
    Note over NAPI: Sahatna Notifications API (BFF) owns outbound delivery, push/email/in-app, consent-gated

    DISP->>CONSENT: getConsent(memberRef)
    CONSENT-->>DISP: {pushEnabled, emailEnabled, emailOnFile}

    alt H2.x/H3.x/H4.x — no consent on requested channel
        DISP->>MSG: recordSuppressed(member, type, reason="no-consent")
        Note right of MSG: NFR-1 honoured — nothing sent
    else consent present on ≥1 channel
        DISP->>MEMBER: getDisplayName(memberRef)
        MEMBER-->>DISP: displayName / initials
        DISP->>DISP: personalize(payload, displayName)  %% "address by name"
        DISP->>DISP: selectChannels(push?/email?)  %% push always, email only if emailEnabled && emailOnFile
        DISP->>MSG: create(member, challenge, type, body_personalized, deepLink, channel)
        MSG-->>DISP: messageId
        DISP->>SEND: send(messageId, channel)
        SEND->>NAPI: deliver(personalizedBody, deepLink, channel)
        NAPI->>GW: push/email outbound
        GW-->>NAPI: providerStatus
        NAPI-->>SEND: deliveryStatus
        SEND->>MSG: updateStatus(messageId, deliveryStatus)
    end
```

**Backward traceability (this sub-flow):**
- `getConsent` ⇐ robustness `C_DISP — gate consent`, UC-H1's persisted `NotificationConsent` (N1).
- `personalize` ⇐ `C_DISP — personalize` ("address by name", NFR-1 / §Communication Enablement).
- `recordSuppressed` / `create` / `updateStatus` ⇐ `E_MSG NotificationMessage` (N3) audit-trail requirement.
- `send` → `deliver` ⇐ `C_SEND` → `«B» Sahatna Notifications API` (BFF, owns outbound delivery, E4) →
  **Notification Provider** actor. The `«B» Notification Provider Gateway` robustness node is realized
  by the `Sahatna Notifications API` outbound surface.

---

## UC-H1 — Manage Notification Consent 🟢 P1
*Realizes P1-11, NFR-1, §Communication Enablement · Actor: **Participant***
*Robustness source: `03-robustness/notification.md` UC-H1.*

**Basic Course**: Participant opens settings → controller loads current consent → Participant toggles
push/email → controller validates email-on-file → consent persisted.

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant
    participant SET as «B» Notification Settings Screen
    participant CC as «C» ConsentController
    participant CONSENT as «E» NotificationConsent (N1)
    participant MEMBER as «E» Member

    PART->>SET: open()
    SET->>CC: loadConsent(memberRef)
    CC->>CONSENT: getOrInit(memberRef)
    CONSENT-->>CC: {pushEnabled, emailEnabled, emailOnFile, lastUpdated}
    CC->>MEMBER: getEmailOnFile(memberRef)
    MEMBER-->>CC: email?  (boolean)
    CC-->>SET: render(currentConsent, emailAvailable)
    SET-->>PART: show toggles

    PART->>SET: setConsent(push, email)
    SET->>CC: saveConsent(memberRef, push, email)

    CC->>MEMBER: getEmailOnFile(memberRef)
    MEMBER-->>CC: hasEmail (boolean)

    alt H1.2 — email toggled on but no email on file
        CC->>CONSENT: update(pushEnabled=push, emailEnabled=false, emailOnFile=false)
        CONSENT-->>CC: saved
        CC-->>SET: warn("email channel unavailable — no address on file")
    else email on file (or email left off)
        CC->>CONSENT: update(pushEnabled=push, emailEnabled=email, emailOnFile=hasEmail)
        CONSENT-->>CC: saved
        CC-->>SET: confirm()
    end
    SET-->>PART: updated state

    opt H1.1 — participant disables all channels
        Note over CONSENT: pushEnabled=false, emailEnabled=false<br/>→ becomes the gate-state every send-UC reads via getConsent()
    end
```

**Backward traceability (UC-H1):**
- `loadConsent` / `getOrInit` ⇐ `C_LOAD` + `E_CONSENT` (N1).
- `getEmailOnFile` ⇐ `C_LOAD`/`C_VALID` reading `E_Member`.
- `saveConsent` / `update` ⇐ `C_SAVE` + `E_CONSENT` (N1).
- `validate email-on-file` ⇐ `C_VALID`; H1.2 sets `emailOnFile=false` (alt-course object).
- H1.1 all-off ⇐ robustness note "gate-state every other UC reads".

---

## UC-H2 — Send Challenge-Lifecycle Notification 🟢 P1
*Realizes P1-11, P1-12, §Nudges, §Challenge Conclusion · Triggered by UC-A7 / UC-I1 / UC-I3 via Clock.*
*Robustness source: `03-robustness/notification.md` UC-H2.*

**Basic Course**: Clock fires a lifecycle event (initiation / mid / end / winners) → controller maps
event → enabled `NotificationType` → resolves recipient set from `Enrollment` (+ `WinnersList` for the
winners event) → for each recipient funnels through the shared `NotificationDispatcher`.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock/Scheduler
    participant EVT as «B» Lifecycle-Event API
    participant LNC as «C» LifecycleNotificationController
    participant CHAL as «E» Challenge
    participant TYPE as «E» NotificationType (N2)
    participant ENR as «E» Enrollment
    participant WIN as «E» WinnersList
    participant DISP as «C» NotificationDispatcher
    actor PART as Participant
    participant PAGE as «B» Deep-Linked Page

    CLK->>EVT: lifecycleEvent(challengeRef, eventKind)
    EVT->>LNC: onLifecycleEvent(challengeRef, eventKind)

    LNC->>CHAL: getChallenge(challengeRef)
    CHAL-->>LNC: challenge
    LNC->>TYPE: getTypeFor(challengeRef, eventKind)
    TYPE-->>LNC: {typeKey, enabledForChallenge_flag, channel, deepLinkTarget, templateRef}

    alt H2.1 — type disabled for this challenge
        Note over LNC: enabledForChallenge_flag == false<br/>→ no recipients, no message, return
    else type enabled
        LNC->>ENR: listActiveEnrollments(challengeRef)
        ENR-->>LNC: members[]

        opt eventKind == winners
            LNC->>WIN: getWinners(challengeRef)
            WIN-->>LNC: winnerMembers[]
            Note over LNC: recipient set narrowed to winners
        end

        loop each recipient member
            LNC->>DISP: dispatch(member, challenge, type, payload{deepLinkTarget})
            Note right of DISP: ref → shared dispatch() sub-flow<br/>(consent gate + personalize + send + record)
        end
    end

    opt H2.tap — participant taps delivered push
        PART->>PAGE: tap(deepLink)
        PAGE->>LNC: openTarget(deepLinkTarget)
        Note over PAGE: routes to registration / conclusion / winners page
    end

    Note over LNC: P2/P3 — team-add & district-announcement<br/>lifecycle events: OUT OF BUILD SCOPE
```

**Backward traceability (UC-H2):**
- `onLifecycleEvent` ⇐ `C_LIFE map lifecycle event → enabled type`, from `B_EVT` ← Clock.
- `getChallenge` / `getTypeFor` ⇐ `C_LIFE` reading `E_CHAL` + `E_TYPE` (N2).
- `listActiveEnrollments` ⇐ `C_RECIP resolve recipient set` reading `E_ENR` (+ `E_MEMBER`).
- `getWinners` ⇐ `C_RECIP` reading `E_WIN WinnersList` (winners event only).
- `dispatch(...)` ⇐ `C_DISP` + `C_SEND` → shared sub-flow (writes `E_MSG` N3, reads `E_CONSENT` N1).
- H2.1 disabled-type alt ⇐ robustness alt-course `C_LIFE` reads `enabledForChallenge_flag`.
- tap → `openTarget` ⇐ `B_PAGE` re-entering via `C_LIFE`'s deep-link target.

---

## UC-H3 — Send Progress Nudge 🟢 P1
*Realizes P1-11, §Nudges (Challenge progress) · Clock weekly cadence + 3-days-in reminder · push-only.*
*Robustness source: `03-robustness/notification.md` UC-H3.*

**Basic Course**: Clock fires the nudge schedule → controller evaluates each participant's goal status
from `WeeklyScore`/`DailyResult`/`Goal` → resolves the `NudgeSegment` (missing-goal vs all-met) →
picks the matching `NotificationType` → dispatches (push channel) via the shared dispatcher.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock/Scheduler
    participant SCHED as «B» Nudge-Schedule API
    participant PNC as «C» ProgressNudgeController
    participant ENR as «E» Enrollment
    participant WS as «E» WeeklyScore
    participant DR as «E» DailyResult
    participant GOAL as «E» Goal
    participant SEG as «E» NudgeSegment (N4)
    participant TYPE as «E» NotificationType (N2)
    participant DISP as «C» NotificationDispatcher

    CLK->>SCHED: nudgeTick(challengeRef, cadence)
    SCHED->>PNC: onNudgeTick(challengeRef, cadence)

    PNC->>ENR: listActiveEnrollments(challengeRef)
    ENR-->>PNC: enrollments[]

    loop each enrollment
        PNC->>WS: getCurrentWeek(enrollment)
        WS-->>PNC: weeklyScore
        PNC->>DR: getDailyResults(enrollment, weekRef)
        DR-->>PNC: dailyResults[]
        PNC->>GOAL: getAssignedGoals(enrollment)
        GOAL-->>PNC: goals[]
        PNC->>SEG: classify(enrollment, goals, dailyResults)
        SEG-->>PNC: segmentKey  %% missing-goal | on-track | all-met

        alt H3.1a — segment == missing-goal (3 days in, goals unmet)
            PNC->>TYPE: getType(segmentKey="missing-goal")
            TYPE-->>PNC: missingGoalReminder
            PNC->>DISP: dispatch(member, challenge, missingGoalReminder, payload, channel=push)
        else H3.1b — segment == all-met
            PNC->>TYPE: getType(segmentKey="all-met")
            TYPE-->>PNC: upholdPerformance
            PNC->>DISP: dispatch(member, challenge, upholdPerformance, payload, channel=push)
        else cadence == week-start / week-end
            PNC->>TYPE: getType(cadenceKey)  %% week-plan | week-review
            TYPE-->>PNC: cadenceNudge
            PNC->>DISP: dispatch(member, challenge, cadenceNudge, payload, channel=push)
        end
        Note right of DISP: ref → shared dispatch() sub-flow (push-only here)
    end

    Note over PNC: P2/P3 — team-progress & district nudges: OUT OF BUILD SCOPE
```

**Backward traceability (UC-H3):**
- `onNudgeTick` ⇐ `C_EVAL evaluate goal status`, from `B_SCHED` ← Clock.
- `getCurrentWeek` / `getDailyResults` / `getAssignedGoals` ⇐ `C_EVAL` reading `E_WS`, `E_DR`, `E_GOAL`.
- `classify` ⇐ `C_SEG resolve NudgeSegment` writing/deriving `E_SEG NudgeSegment` (N4).
- `getType(segmentKey/cadenceKey)` ⇐ `C_PICK pick nudge` reading `E_TYPE` (N2).
- `dispatch(...)` ⇐ `C_DISP` + `C_SEND` → shared sub-flow (push channel).
- H3.1 missing-goal vs uphold alt ⇐ robustness alt-course `C_EVAL → C_SEG → C_PICK`.

---

## UC-H4 — Send Weekly Summary 🟢 P1
*Realizes P1-6, §Nudges · Trigger: **UC-D5 Finalize Weekly Score** (← Clock at week-close).*
*Robustness source: `03-robustness/notification.md` UC-H4.*

**Basic Course**: UC-D5 finalizes the week and fires the trigger → controller assembles each member's
summary (goals met, score, and — if the points feature is on — points earned) from `WeeklyScore` /
`DailyResult` / `Wallet` / `PointTransaction` → dispatches the weekly-summary message.

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock/Scheduler
    participant FIN as «B» Week-Finalized Trigger API
    participant WSC as «C» WeeklySummaryController
    participant ENR as «E» Enrollment
    participant CHAL as «E» Challenge
    participant WS as «E» WeeklyScore
    participant DR as «E» DailyResult
    participant WALLET as «E» Wallet
    participant TXN as «E» PointTransaction
    participant TYPE as «E» NotificationType (N2)
    participant DISP as «C» NotificationDispatcher

    CLK->>FIN: weekFinalized(challengeRef, weekRef)  %% from UC-D5
    FIN->>WSC: onWeekFinalized(challengeRef, weekRef)

    WSC->>ENR: listActiveEnrollments(challengeRef)
    ENR-->>WSC: enrollments[]
    WSC->>CHAL: getPointsFeatureFlag(challengeRef)
    CHAL-->>WSC: pointsFeatureFlag

    loop each enrollment
        WSC->>WS: getFinalizedWeek(enrollment, weekRef)
        WS-->>WSC: {scoreValue, componentBreakdown}
        WSC->>DR: getGoalsMet(enrollment, weekRef)
        DR-->>WSC: goalsMetCount

        alt G1.4 — pointsFeatureFlag == on
            WSC->>WALLET: getWallet(memberRef)
            WALLET-->>WSC: wallet
            WSC->>TXN: getWeekCredit(walletId, weekRef)
            TXN-->>WSC: pointsEarned
            Note over WSC: summary = {goalsMet, score, points}
        else points feature off
            Note over WSC: summary = {goalsMet, score}  %% points line omitted
        end

        WSC->>TYPE: getType("weekly-summary")
        TYPE-->>WSC: weeklySummaryType
        WSC->>DISP: dispatch(member, challenge, weeklySummaryType, summaryPayload)
        Note right of DISP: ref → shared dispatch() sub-flow
    end

    Note over WSC: P2/P3 — team & district weekly roll-up summaries: OUT OF BUILD SCOPE
```

**Backward traceability (UC-H4):**
- `onWeekFinalized` ⇐ `C_ASSEM assemble summary`, from `B_FIN` ← UC-D5 / Clock.
- `getFinalizedWeek` / `getGoalsMet` ⇐ `C_ASSEM` reading `E_WS WeeklyScore` + `E_DR DailyResult`.
- `getWallet` / `getWeekCredit` ⇐ `C_ASSEM` reading `E_WALLET` + `E_TXN` (points line).
- `getType("weekly-summary")` ⇐ `C_ASSEM` reading `E_TYPE` (N2).
- `dispatch(...)` ⇐ `C_DISP` + `C_SEND` → shared sub-flow.
- G1.4 points-flag alt ⇐ robustness alt-course `C_ASSEM` gates `Wallet`/`PointTransaction` reads on
  `Challenge.pointsFeatureFlag`.

---

## UC-H5 — Read In-App Notification Feed 🟢 P1  *(added in architecture enhancements — E4)*
*Realizes P1-11, §Communication Enablement (in-app feed) · Actor: **Participant***
*Robustness source: `03-robustness/notification.md` UC-H5.*

**Basic Course**: Participant opens the in-app feed → the `Sahatna Notifications API` (read-side, via
APIM-north) lists the member's notifications from the `NotificationMessage` log as `InAppFeedItem`
projections → Participant taps an item to mark it read and deep-link into the relevant page.

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant
    participant FEED as «B» In-App Feed Screen
    participant NAPI as «B» Sahatna Notifications API
    participant IFC as «C» InAppFeedController
    participant MSG as «E» NotificationMessage (N3)
    participant ITEM as «E» InAppFeedItem (N5)
    participant MEMBER as «E» Member

    PART->>FEED: open in-app feed
    FEED->>NAPI: GET feed (memberRef, via APIM-north)
    NAPI->>IFC: listFeed(memberRef)
    IFC->>MEMBER: resolve(memberRef)
    MEMBER-->>IFC: memberRef ok
    IFC->>MSG: listForMember(memberRef)
    MSG-->>IFC: messages[]
    IFC->>ITEM: project(messages[])
    ITEM-->>IFC: feedItems[]
    IFC-->>NAPI: feedItems[]
    NAPI-->>FEED: feed payload
    FEED-->>PART: render feed (read/unread)

    alt H5.1 — empty feed
        Note over IFC: no NotificationMessage for member, feed renders empty-state
    else H5.2 — participant taps a feed item
        PART->>FEED: tap(feedItemId)
        FEED->>NAPI: markRead(feedItemId), via APIM-north
        NAPI->>IFC: markRead(feedItemId)
        IFC->>ITEM: setReadStatus(feedItemId, read)
        ITEM-->>IFC: ok
        Note over FEED: deep-link routes to the item target, same routing as a tapped push UC-H2
    end
```

**Backward traceability (UC-H5):**
- `listFeed` / `listForMember` ⇐ `C_LIST list in-app feed` reading `E_MSG NotificationMessage` (N3).
- `project` ⇐ `C_LIST` deriving `E_FEED InAppFeedItem` (N5) read-model projection.
- `markRead` / `setReadStatus` ⇐ `C_READ mark item read` writing `E_FEED InAppFeedItem` (N5).
- `Sahatna Notifications API` boundary ⇐ E4 notifications-API read surface, `Mobile → APIM-north →
  Sahatna Notifications API`.

---

## Step-3 traceability & invariant check (per Rosenberg)

| Check | Status |
|------|--------|
| Every robustness `«C»` verb maps to ≥1 sequence message | ✅ load/save/validate (H1), map/resolve/dispatch/send (H2), evaluate/resolve-segment/pick/dispatch (H3), assemble/dispatch (H4) |
| Every operation allocated to the **entity that owns the data** | ✅ consent→NotificationConsent, name→Member, summary reads→WeeklyScore/DailyResult/Wallet/PointTransaction, type→NotificationType, audit→NotificationMessage |
| No sequence message references an orphan class | ✅ N1–N4 declared as participants; all reused entities exist in `02-domain-model.md` |
| Shared consent gate modelled once, reused | ✅ `NotificationDispatcher.dispatch(...)` sub-flow `ref`d by H2/H3/H4 |
| Basic course = main flow; alternates as alt/opt | ✅ H1.1/H1.2, H2.1/tap, H3.1, G1.4 all rendered as `alt`/`opt` fragments |
| Phase-2/3 fan-out tagged out of scope | ✅ team/district notes on H2/H3/H4 |
| Actors touch only boundary | ✅ Participant→Screen/Page/Feed, Clock→Event/Schedule/Trigger API, Provider→Sahatna Notifications API |
| E4 — Sahatna Notifications API owns outbound + exposes in-app feed read | ✅ dispatch sub-flow delivers via Sahatna Notifications API → Notification Provider, UC-H5 reads feed via Sahatna Notifications API (APIM-north) |

**Backward-traceability gap reminder (from Step-2):** entities **N1–N4** must be present in
`02-domain-model.md` for these sequence messages to be non-orphan. If not yet back-ported, add
`NotificationConsent`, `NotificationType`, `NotificationMessage`, `NudgeSegment` (all `[P1]`) before
sign-off.
