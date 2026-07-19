# ICONIX Step 3 — Sequence Diagrams: Package I — Settlement / Conclusion (`settlement`)

**Process**: ICONIX (Rosenberg) — use-case-driven, milestone-driven. This is the **Step-3**
deliverable for the **Settlement / Conclusion** package (id `settlement`). Each use case from
[03-robustness/settlement.md](../03-robustness/settlement.md) is realized as a Mermaid `sequenceDiagram`.

**Method allocation rule (Rosenberg)**: the robustness `«C»` control verbs become **messages**, and
each operation is **allocated to the entity that owns the data it mutates/reads**. Controllers remain as
participants (they own orchestration), but data-touching behaviour is pushed onto the entity classes
from [02-domain-model.md](../02-domain-model.md) — so `WinnersList.confirm()`, not a free-floating verb.

**Traceability spine**: `use case ⇄ domain class ⇄ robustness object ⇄ sequence message`. Every
message below carries a **back-trace note** to its originating `«C»` node and UC.

**Phase scope**: All five UCs are `🟢 P1` (individual settlement). Team/District branches (I5.2, I5.3)
are shown as **tagged `opt` fragments**, modelled for forward-traceability only — **out of P1 build scope**.

**Participant legend**: `«B»` boundary · `«C»` controller · `«E»` entity. New entities introduced in
Step-2 and back-ported to the domain model: **WinnersList (N1)**, **WinnerAllocation (N2)**,
**ChallengeConclusion (N3)**.

**Convergence gate**: `WinnersList.confirm()` (UC-I2 `C_CONF`) is modelled once here and **referenced**
(precondition guard) by the UC-I3 and UC-I4 sequences — neither acts on a non-`Confirmed` list.

---

## UC-I1 — Conclude Challenge 🟢 P1

*Realizes P1-12, §Challenge Conclusion · Actor: **Clock/Scheduler** (end-event). Triggers UC-H2.*
*Precondition: UC-D6 has locked `WellnessScore`; UC-E1.2 has finalized `Leaderboard` (read-only).*

```mermaid
sequenceDiagram
    autonumber
    actor CLK as Clock/Scheduler
    participant B_END as «B» Challenge-End Trigger API
    participant CC as «C» ConclusionController
    participant E_CHAL as «E» Challenge
    participant E_CONCL as «E» ChallengeConclusion (N3)
    participant E_ENR as «E» Enrollment
    participant B_NOT as «B» Notification Trigger API (→ UC-H2)
    actor PART as Participant
    participant B_DET as «B» Challenge Details Screen

    Note over CLK,E_CHAL: Basic Course — end-event fires
    CLK->>B_END: endEventReached(challengeId)
    B_END->>CC: concludeChallenge(challengeId)
    CC->>E_CHAL: markCompleted()  %% C_CONCL — Challenge.status→Completed
    E_CHAL-->>CC: status=Completed
    CC->>E_CONCL: createDraft(challengeRef, state=UnderReview)  %% C_CONCL/C_REVIEW — N3 created draft
    E_CONCL-->>CC: conclusionId
    CC->>E_ENR: flagUnderReview()  %% C_REVIEW — participants see "under review"

    Note over CC,B_NOT: Fire conclusion-initiation trigger (hand-off to Package H)
    CC->>B_NOT: fireConclusionInit(challengeId)  %% C_FIRE → UC-H2 lifecycle trigger

    Note over PART,B_DET: Participant reads under-review state (boundary→control→entity, no shortcut)
    PART->>B_DET: open(challengeId)
    B_DET->>CC: getReviewState(challengeId)
    CC->>E_CONCL: readState()
    E_CONCL-->>CC: UnderReview
    CC-->>B_DET: "Data under review, winners announced shortly"
    B_DET-->>PART: render under-review banner
```

**Back-trace map (message ⇄ robustness `«C»` ⇄ UC)**:

| Message | Robustness control node | UC |
|---|---|---|
| `Challenge.markCompleted()` | `C_CONCL` (transition → Completed) | UC-I1 |
| `ChallengeConclusion.createDraft()` | `C_CONCL`+`C_REVIEW` (N3 draft, under-review) | UC-I1 |
| `Enrollment.flagUnderReview()` | `C_REVIEW` (set UI state) | UC-I1 |
| `fireConclusionInit()` | `C_FIRE` (notification trigger) | UC-I1 → UC-H2 |

**Alternate course**: none branching in I1. Precondition guard — if `WellnessScore.locked=false` or
`Leaderboard.finalized=false`, `concludeChallenge` aborts (data not settled); modelled as precondition,
not a recompute. Notification content lives in Package H (UC-H2).

---

## UC-I2 — Review & Confirm Winners 🟢 P1

*Realizes P1-12, P1-13, §Challenge Conclusion · Actor: **DoH Gamification Staff** (+ **ADHDS Operator**
for I2.1). Includes UC-J2 (retrieve computed winners). `WinnersList.confirm()` is the convergence gate.*

```mermaid
sequenceDiagram
    autonumber
    actor DOH as DoH Gamification Staff
    actor ADHDS as ADHDS Operator
    participant B_DASH as «B» Reporting Dashboard Screen
    participant B_REV as «B» Winners Review Screen
    participant B_ADJ as «B» Winners-Adjust API
    participant WRC as «C» WinnersReviewController
    participant E_WC as «E» WinningCriteria
    participant E_WS as «E» WellnessScore
    participant E_ENR as «E» Enrollment
    participant E_MBR as «E» Member
    participant E_WL as «E» WinnersList (N1)
    participant E_WA as «E» WinnerAllocation (N2)

    Note over DOH,E_WA: Basic Course — retrieve (← UC-J2) then build
    DOH->>B_DASH: openWinnersReview(challengeId)
    B_DASH->>WRC: retrieveComputedWinners(challengeId)  %% C_RETR (include UC-J2)
    WRC->>E_WC: getCriteria(challengeId)  %% C_RETR
    E_WC-->>WRC: criteria[]
    WRC->>E_WS: readFinalizedScores(challengeId)  %% C_RETR (read-only, never recompute)
    E_WS-->>WRC: scores[]
    WRC->>E_ENR: getRankedEnrollments(criteria, scores)  %% C_RETR
    E_ENR-->>WRC: rankedWinners[]

    WRC->>E_WL: create(challengeRef, status=Draft)  %% C_BUILD — N1 draft roster
    E_WL-->>WRC: winnersListId
    loop per ranked winner per criteria
        WRC->>E_WA: addAllocation(enrollmentRef, criteriaRef, rank, rewardType)  %% C_BUILD — N2 line item
        WRC->>E_MBR: resolveDisplay(memberRef)  %% C_BUILD (name/initials per consent)
    end
    WRC-->>B_REV: draft winners list

    Note over ADHDS,E_WL: Alternate I2.1 — list needs tweaks (ADHDS edits)
    opt I2.1 — adjust before confirmation
        ADHDS->>B_ADJ: editAllocation(allocationId, change)
        B_ADJ->>WRC: adjustWinnersList(allocationId, change)  %% C_ADJ
        WRC->>E_WA: updateAllocation(change)  %% C_ADJ — mutate N2 row
        WRC->>E_WL: markAdjusted()  %% C_ADJ — status Draft→Adjusted
    end

    Note over DOH,E_WL: Basic Course — confirmation gate (I2.2)
    DOH->>B_REV: confirm()
    B_REV->>WRC: confirmWinnersList(winnersListId)  %% C_CONF (THE GATE)
    WRC->>E_WL: confirm(confirmedBy=DoH)  %% C_CONF — status→Confirmed, stamp confirmedTimestamp
    E_WL-->>WRC: status=Confirmed
    WRC-->>B_REV: confirmed — announcement & distribution now unlocked
```

**Back-trace map (message ⇄ robustness `«C»` ⇄ UC)**:

| Message | Robustness control node | UC |
|---|---|---|
| `retrieveComputedWinners()` / `WinningCriteria.getCriteria()` / `WellnessScore.readFinalizedScores()` / `Enrollment.getRankedEnrollments()` | `C_RETR` (include point) | UC-I2 ⊃ UC-J2 |
| `WinnersList.create()` / `WinnerAllocation.addAllocation()` / `Member.resolveDisplay()` | `C_BUILD` | UC-I2 |
| `WinnerAllocation.updateAllocation()` / `WinnersList.markAdjusted()` | `C_ADJ` | UC-I2 / I2.1 |
| `WinnersList.confirm()` | `C_CONF` (gate) | UC-I2 / I2.2 |

**Alternate courses**: **I2.1** (`opt`) — only **ADHDS Operator** touches `B_ADJ`; mutates `N2`/`N1`
pre-confirmation. **I2.2** — `WinnersList.confirm()` sets `status=Confirmed`; this single message is the
**convergence gate** referenced by UC-I3 and UC-I4 below. `WellnessScore` is read-only — settlement
never recomputes scores.

---

## UC-I3 — Announce Winners & Publish Conclusion 🟢 P1

*Realizes P1-12, §Challenge Conclusion · Actor: **DoH Gamification Staff** / system. **Precondition:
UC-I2 `WinnersList.confirm()`**. Triggers UC-H2 won/not-won completion notifications.*

```mermaid
sequenceDiagram
    autonumber
    actor DOH as DoH Gamification Staff
    participant B_PUB as «B» Publish-Conclusion Action Screen
    participant AC as «C» AnnouncementController
    participant E_WL as «E» WinnersList (N1)
    participant E_CHAL as «E» Challenge
    participant E_LB as «E» Leaderboard
    participant E_WA as «E» WinnerAllocation (N2)
    participant E_CONCL as «E» ChallengeConclusion (N3)
    participant E_ENR as «E» Enrollment
    participant B_NOT as «B» Notification Trigger API (→ UC-H2)
    actor PART as Participant
    participant B_PAGE as «B» Challenge Details Page

    Note over DOH,E_WL: Basic Course — verify gate first (refuse non-Confirmed)
    DOH->>B_PUB: publish(challengeId)
    B_PUB->>AC: publishConclusion(challengeId)
    AC->>E_WL: isConfirmed()  %% C_GATE — convergence gate (UC-I2 C_CONF)
    E_WL-->>AC: status

    alt WinnersList.status == Confirmed
        AC->>E_CHAL: getOverallStats()  %% C_ASSEM
        E_CHAL-->>AC: stats
        AC->>E_LB: getFinalRankings()  %% C_ASSEM (read finalized leaderboard)
        E_LB-->>AC: rankings
        AC->>E_WA: getConfirmedWinners()  %% C_ASSEM (optional winners list, config-gated)
        E_WA-->>AC: winners[]
        AC->>E_CONCL: publish(stats, outcomes, nextStepsTeaser, winnersListRef)  %% C_PUB — N3 published
        E_CONCL-->>AC: publishedTimestamp

        Note over AC,B_NOT: Trigger completion notifications (branch won / not-won)
        loop per Enrollment
            AC->>E_ENR: isWinner(enrollmentRef)  %% C_NOTIFY branch test (appears in WinnerAllocation?)
            E_ENR-->>AC: won | notWon
            AC->>B_NOT: triggerCompletionNotice(enrollmentRef, won|notWon)  %% C_NOTIFY → UC-H2 deep-link
        end
        AC-->>B_PUB: published
    else not Confirmed
        AC-->>B_PUB: refuse — WinnersList not Confirmed
    end

    Note over PART,E_CONCL: Public details page re-reads published conclusion (no boundary→entity shortcut)
    PART->>B_PAGE: open(challengeId)
    B_PAGE->>AC: getPublishedConclusion(challengeId)  %% via C_ASSEM read path
    AC->>E_CONCL: read()
    E_CONCL-->>AC: conclusion(stats, outcomes, optional winners)
    AC-->>B_PAGE: render
    B_PAGE-->>PART: updated details page
```

**Back-trace map (message ⇄ robustness `«C»` ⇄ UC)**:

| Message | Robustness control node | UC |
|---|---|---|
| `WinnersList.isConfirmed()` | `C_GATE` (refuse non-Confirmed) | UC-I3 (gate ← UC-I2) |
| `Challenge.getOverallStats()` / `Leaderboard.getFinalRankings()` / `WinnerAllocation.getConfirmedWinners()` | `C_ASSEM` | UC-I3 |
| `ChallengeConclusion.publish()` | `C_PUB` | UC-I3 |
| `Enrollment.isWinner()` + `triggerCompletionNotice()` | `C_NOTIFY` (won/not-won branch) | UC-I3 → UC-H2 |
| `ChallengeConclusion.read()` (page re-read) | `C_ASSEM` read path | UC-I3 |

**Alternate courses**: `alt` on the **confirmation gate** — non-`Confirmed` list ⇒ `refuse` (back-ref to
UC-I2 invariant). `C_NOTIFY` **branches won vs not-won** per `Enrollment` membership in a
`WinnerAllocation`; both branches deep-link via Package H. Optional winners block on `B_PAGE` is
config-gated.

---

## UC-I4 — Distribute Rewards 🟢 P1

*Realizes §Reward Distribution · Actor: **DoH Gamification Staff** (offline) / system (points).
**Precondition: UC-I2 confirmation**. Triggers UC-H2 collection comms. Points leg reuses the
`Wallet`/`PointTransaction` fragment shared with UC-G1 (`sourceRef=winner-allocation`).*

```mermaid
sequenceDiagram
    autonumber
    actor DOH as DoH Gamification Staff
    participant B_DIST as «B» Reward Distribution Screen
    participant RDC as «C» RewardDistributionController
    participant E_WL as «E» WinnersList (N1)
    participant E_WA as «E» WinnerAllocation (N2)
    participant E_MBR as «E» Member
    participant B_CONTACT as «B» Winner Contact Detail View
    participant E_WALLET as «E» Wallet
    participant E_TXN as «E» PointTransaction
    participant E_ENR as «E» Enrollment
    participant B_NOT as «B» Notification Trigger API (→ UC-H2)

    Note over DOH,E_WA: Basic Course — load only the confirmed list
    DOH->>B_DIST: openDistribution(challengeId)
    B_DIST->>RDC: loadAllocations(challengeId)  %% C_LOAD
    RDC->>E_WL: isConfirmed()  %% C_LOAD refuses non-Confirmed (gate ← UC-I2)
    E_WL-->>RDC: Confirmed
    RDC->>E_WA: getPendingAllocations(winnersListId)  %% C_LOAD
    E_WA-->>RDC: allocations[]

    loop per WinnerAllocation
        RDC->>E_WA: rewardType()  %% C_ROUTE — offline / points / hybrid (I4.1)
        E_WA-->>RDC: type

        opt type includes OFFLINE
            RDC->>E_MBR: getContactDetails(memberRef)  %% C_OFFLINE
            E_MBR-->>RDC: email, phone
            RDC->>B_CONTACT: showContact(email, phone)  %% C_OFFLINE — surface to DoH
            B_CONTACT-->>DOH: winner contact details
            RDC->>E_WA: setFulfilment(contacted)  %% C_FULFIL
        end

        opt type includes POINTS  (gated by Challenge.pointsFeatureFlag)
            RDC->>E_WALLET: credit(allocatedPoints)  %% C_CREDIT — reuse G1 path
            RDC->>E_TXN: record(type=earn, sourceRef=winner-allocation)  %% C_CREDIT
            E_TXN-->>E_WALLET: balance updated
            RDC->>E_ENR: linkCredit(enrollmentRef, txnId)  %% C_CREDIT audit link
            RDC->>E_WA: setFulfilment(credited)  %% C_FULFIL
        end

        Note over RDC,B_NOT: I4.1 hybrid — BOTH opt fragments run for the same allocation
        RDC->>E_WA: setFulfilment(done)  %% C_FULFIL — idempotent terminal state
        RDC->>B_NOT: triggerCollectionComms(enrollmentRef)  %% C_COMMS → UC-H2
    end
    RDC-->>B_DIST: distribution complete
```

**Back-trace map (message ⇄ robustness `«C»` ⇄ UC)**:

| Message | Robustness control node | UC |
|---|---|---|
| `WinnersList.isConfirmed()` / `WinnerAllocation.getPendingAllocations()` | `C_LOAD` (gate ← UC-I2) | UC-I4 |
| `WinnerAllocation.rewardType()` | `C_ROUTE` (offline/points/hybrid) | UC-I4 / I4.1 |
| `Member.getContactDetails()` + `showContact()` | `C_OFFLINE` | UC-I4 |
| `Wallet.credit()` / `PointTransaction.record()` / `Enrollment.linkCredit()` | `C_CREDIT` (shared w/ UC-G1) | UC-I4 |
| `WinnerAllocation.setFulfilment()` | `C_FULFIL` (pending→contacted/credited→done) | UC-I4 |
| `triggerCollectionComms()` | `C_COMMS` | UC-I4 → UC-H2 |

**Alternate courses**: **I4.1 hybrid** — when `rewardType()` returns hybrid, **both** the OFFLINE and
POINTS `opt` fragments fire for one allocation. The POINTS leg is additionally gated by
`Challenge.pointsFeatureFlag` (off ⇒ skip points, offline still runs). `setFulfilment(done)` makes
distribution **idempotent and auditable**. `PointTransaction.record(sourceRef=winner-allocation)`
distinguishes this from the weekly-score credit but reuses the identical UC-G1 ledger fragment.

---

## UC-I5 — Disenroll / Leave Challenge 🟢 P1

*Realizes §Disenrollment · Actor: **Participant**. I5.1 no-rejoin P1; I5.2 team-freeze 🟡 P2;
I5.3 district-aggregation 🔵 P3 (out of build scope, tagged).*

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant
    participant B_DET as «B» Challenge Details Screen
    participant B_CONF as «B» Disenroll Confirm Dialog
    participant DC as «C» DisenrollmentController
    participant E_ENR as «E» Enrollment
    participant E_MBR as «E» Member
    participant E_LB as «E» Leaderboard
    participant E_LBE as «E» LeaderboardEntry
    participant E_WS as «E» WellnessScore

    Note over PART,B_CONF: Screen-to-screen navigation (not a boundary↔boundary data flow)
    PART->>B_DET: tapLeaveChallenge()
    B_DET->>B_CONF: open()
    PART->>B_CONF: confirmLeave()
    B_CONF->>DC: disenroll(memberRef, challengeId)

    Note over DC,E_ENR: Basic Course — confirm + set status Left
    DC->>E_ENR: confirmExit()  %% C_CONFIRM
    DC->>E_ENR: setLeft()  %% C_LEAVE — status→Left
    DC->>E_MBR: detachActive(challengeId)  %% C_LEAVE

    Note over DC,E_LBE: Remove from active ranking
    DC->>E_LB: removeEntry(enrollmentRef)  %% C_DERANK
    DC->>E_LBE: deactivate()  %% C_DERANK

    Note over DC,E_WS: Preserve archived history (read-only, not deleted)
    DC->>E_WS: preserveHistorical()  %% C_ARCH — historical contribution kept

    Note over DC,E_ENR: I5.1 — enforce no-rejoin (P1)
    DC->>E_ENR: markNoRejoin()  %% C_NOREJOIN — blocks later UC-C3 enroll for same Member+Challenge
    DC-->>B_CONF: left — cannot rejoin

    Note over DC,E_ENR: I5.2 team-member leave 🟡 P2 — OUT OF P1 BUILD SCOPE (forward-trace only)
    opt I5.2 — Team participation [P2]
        DC->>E_ENR: recomputeTeamComposition()  %% C_LEAVE branch (Team entity not in P1 set)
        Note right of E_ENR: freeze team score contribution
    end

    Note over DC,E_WS: I5.3 district participant leave 🔵 P3 — OUT OF P1 BUILD SCOPE (forward-trace only)
    opt I5.3 — District aggregation [P3]
        DC->>E_WS: removeFromDistrictAggregationForward()  %% C_LEAVE branch (District entity not in P1 set)
        Note right of E_WS: historical district contribution preserved
    end
```

**Back-trace map (message ⇄ robustness `«C»` ⇄ UC)**:

| Message | Robustness control node | UC | Phase |
|---|---|---|---|
| `Enrollment.confirmExit()` | `C_CONFIRM` | UC-I5 | 🟢 P1 |
| `Enrollment.setLeft()` / `Member.detachActive()` | `C_LEAVE` | UC-I5 | 🟢 P1 |
| `Leaderboard.removeEntry()` / `LeaderboardEntry.deactivate()` | `C_DERANK` | UC-I5 | 🟢 P1 |
| `WellnessScore.preserveHistorical()` | `C_ARCH` | UC-I5 | 🟢 P1 |
| `Enrollment.markNoRejoin()` | `C_NOREJOIN` | UC-I5 / I5.1 | 🟢 P1 |
| `Enrollment.recomputeTeamComposition()` | `C_LEAVE` (team branch) | UC-I5 / I5.2 | 🟡 P2 |
| `WellnessScore.removeFromDistrictAggregationForward()` | `C_LEAVE` (district branch) | UC-I5 / I5.3 | 🔵 P3 |

**Alternate courses**: **I5.1** (P1) — `Enrollment.markNoRejoin()` flags the enrollment so a later
**UC-C3** enroll attempt for the same Member+Challenge is blocked. **I5.2** (🟡 P2 `opt`) and **I5.3**
(🔵 P3 `opt`) branch off `C_LEAVE` but depend on Team/District entities **absent from the P1 build set** —
shown tagged, out-of-build-scope. `B_DET → B_CONF` is screen navigation (actor re-touches `B_CONF`).

---

## Step-3 invariant & traceability check

| Check | Status |
|---|---|
| Every `«C»` robustness verb realized as a sequence message | ✅ all of `C_CONCL`/`C_REVIEW`/`C_FIRE`, `C_RETR`/`C_BUILD`/`C_ADJ`/`C_CONF`, `C_GATE`/`C_ASSEM`/`C_PUB`/`C_NOTIFY`, `C_LOAD`/`C_ROUTE`/`C_OFFLINE`/`C_CREDIT`/`C_FULFIL`/`C_COMMS`, `C_CONFIRM`/`C_LEAVE`/`C_DERANK`/`C_ARCH`/`C_NOREJOIN` mapped |
| Each operation allocated to the owning entity | ✅ data-mutating methods sit on `Challenge`/`ChallengeConclusion`/`WinnersList`/`WinnerAllocation`/`Wallet`/`PointTransaction`/`Enrollment`/`Leaderboard`/`WellnessScore`/`Member` |
| Actors touch only boundary | ✅ Clock→`B_END`, Participant→`B_DET`/`B_PAGE`/`B_CONF`, DoH→`B_DASH`/`B_REV`/`B_PUB`/`B_DIST`, ADHDS→`B_ADJ` |
| Confirmation gate referenced once, reused by I3+I4 | ✅ `WinnersList.confirm()` (I2) ⇒ `isConfirmed()` guards I3 (`alt`) and I4 (`C_LOAD`) |
| Settlement never recomputes scores | ✅ `WellnessScore`/`Leaderboard` accessed via read methods (`readFinalizedScores`, `getFinalRankings`, `preserveHistorical`); only status flags + winner `PointTransaction` written |
| No message references an orphan class | ✅ N1/N2/N3 back-ported to `02-domain-model.md` precondition (Step-2 handoff); all participants exist in domain model |
| Basic Course = main flow, Alternate Courses = alt/opt | ✅ I2.1/I3-gate/I4.1-hybrid/I5.1-I5.3 modelled as `opt`/`alt`/`loop` fragments |

**Forward handoff (to Step 4 / design)**: each entity method above becomes a class operation; the
`WinnersList.confirm()` gate and the shared `Wallet.credit()`/`PointTransaction.record()` fragment
(UC-I4 ⇄ UC-G1) are reuse points to consolidate. Package-H notification triggers
(`fireConclusionInit`, `triggerCompletionNotice`, `triggerCollectionComms`) are the cross-package
seams to UC-H2.
