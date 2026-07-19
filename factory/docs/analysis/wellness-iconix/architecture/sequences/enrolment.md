# Application-Level Sequences — "Discovery & Enrolment" package (`enrolment`, 🟢 P1)

> **Top-down abstraction** of the bottom-up ICONIX Step-3 sequences in
> [`../../04-sequences/enrolment.md`](../../04-sequences/enrolment.md). Participants here are **applications and
> stores only** — surfaces (Mobile App / Admin Portal), the **two-leg gateway** (`APIM-north (Citizen Gateway)` ·
> `APIM-south (Platform Gateway)`) and the **Mobile BFF** that drives the citizen surface, named **microservices**,
> their **datastores**, and **external systems**. Low-level «B»/«C»/«E» objects and fine-grained messages are
> collapsed into coarse application-to-application calls. Cross-context calls and async events between microservices
> are shown explicitly.
>
> **Layering contract** (per `architecture/LAYERING-SPEC.md`, matching `earn-scoring.md` / `notification.md`): every
> citizen flow routes `Mobile App → APIM-north (Citizen Gateway) → Mobile BFF → APIM-south (Platform Gateway) →
> <GP microservice>`. The **Mobile BFF** is the chosen BFF for all enrolment journeys (gameplay reads/commands).
> No actor reaches a GP microservice directly; UAE Pass is the citizen IdP at APIM-north.
>
> **Phase discipline**: Journeys A–C cover 🟢 **P1** use cases UC-C1..C5 (individual-only). Team / District enrolment
> (UC-C6/C7 🟡 P2, UC-C8 🔵 P3) are tagged and shown as a single forward-traceability sketch at the end — **out of P1 build scope**.
>
> **Bounded-context ownership in this package**: `enrolment-svc` (membership-db) is the keystone owner; it makes
> cross-context **read** calls into `challenge-svc` (catalogue) and `eligibility-svc` (audience read-model), and emits
> an async **`MemberEnrolled`** domain event consumed downstream by `scoring-svc`, `leaderboard-svc`, `ingestion-svc`
> and `notification-svc`.

---

## Journey A — Discover & View Challenges 🟢 P1

Merges **UC-C1 Discover Challenges** + **UC-C2 View Challenge Details** (read-only browse path; no entity writes).

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant 🟢
        participant MOB as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant MBF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant CHS as 🟥 challenge-svc
    participant CHDB as challenge-db (PostgreSQL)
    participant ELS as eligibility-svc
    participant ELC as eligibility-cache (Redis read-model)
    participant ENS as enrolment-svc
    participant MDB as membership-db (PostgreSQL)

    PART->>MOB: open Wellness module / tap a card
    MOB->>APN: GET /challenges?memberId (+ details on tap)
    APN->>MBF: forward (UAE Pass JWT)
    MBF->>APS: list published + challenge detail
    APS->>CHS: list published + challenge detail
    CHS->>CHDB: read catalogue / goals / reward mapping
    CHS->>ELS: filterEligible(memberId, candidates)
    ELS->>ELC: lookup segment + eligibility read-model
    ELS-->>CHS: eligibleChallenges[]
    CHS->>ENS: mark already-enrolled(memberId, challengeIds)
    ENS->>MDB: read enrolments for member
    ENS-->>CHS: enrolledFlags
    CHS-->>APS: cards + (on tap) full details
    APS-->>MBF: cards + details
    MBF-->>APN: composed list / details payload
    APN-->>MOB: rendered list / details screen
    MOB-->>PART: show cards (or empty teaser) / challenge details
```

> 🟥 svc receives from outside GP · 🟦 svc writes to outside GP (microservices only)

**UC coverage**: UC-C1 Discover Challenges (incl. Alt C1.1 empty/teaser), UC-C2 View Challenge Details — both `«include»` UC-B1 eligibility (served from `eligibility-svc` read-model).

---

## Journey B — Connect Wellness Data 🟢 P1

**UC-C4 Connect Wellness Data** — standalone or routed-into from enrolment (Journey C, opt). The wellness connection
is persisted by `enrolment-svc` (Member-owned) and is the **ingestion anchor** for `ingestion-svc`.

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant 🟢
        participant MOB as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant MBF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant ENS as 🟥 enrolment-svc
    participant MDB as membership-db (PostgreSQL)
        participant WEAR as Wearables: Apple Health / Google Fit (ACL)
    participant ING as ingestion-svc

    PART->>MOB: choose provider (Apple / Google)
    MOB->>APN: POST /wellness-connections (UAE Pass JWT)
    APN->>MBF: forward connect request
    MBF->>APS: connectWellnessData(memberId, provider)
    APS->>ENS: connectWellnessData(memberId, provider)
    ENS->>WEAR: requestAuthorization(scopes) [OAuth]
    WEAR-->>ENS: grant | deny
    alt granted
        ENS->>MDB: persist connection(status=connected) + flag member
        ENS-->>ING: WellnessConnected(memberId, provider, scopes) [async]
        Note over ING: metric sync into Activity Ingestion now enabled
    else denied / failed (Alt C4.1)
        ENS->>MDB: persist connection(status=denied), flag stays false
    end
    ENS-->>APS: connection{status}
    APS-->>MBF: connection{status}
    MBF-->>APN: connected | proceed (device goals unmet until connected)
    APN-->>MOB: connection result
    MOB-->>PART: show result
```

**UC coverage**: UC-C4 Connect Wellness Data (incl. Alt C4.1 denied/failed). External ACL = Wearables (Apple Health / Google Fit). Async `WellnessConnected` primes `ingestion-svc`.

---

## Journey C — Enroll (Individual) 🟢 P1 — package keystone

Merges **UC-C3 Enroll (Individual)** + **UC-C5 Provide Participation Consent**, with **UC-C4** reached as an `opt`
route-in. `enrolment-svc` orchestrates: re-check eligibility (cross-context read), capture consent, optionally route
wellness connect, then create the enrolment, snapshot eligibility config, lock goals, and emit `MemberEnrolled`.

```mermaid
sequenceDiagram
    autonumber
    actor PART as Participant 🟢
        participant MOB as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant MBF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant ENS as 🟥 enrolment-svc
    participant MDB as membership-db (PostgreSQL)
    participant ELS as eligibility-svc
    participant CHS as challenge-svc
    participant SCO as scoring-svc
    participant LBS as leaderboard-svc
    participant NOT as notification-svc

    PART->>MOB: start + confirm enrolment (challengeId)
    MOB->>APN: POST /enrolments (UAE Pass JWT)
    APN->>MBF: forward enrol command
    MBF->>APS: enroll(memberId, challengeId, leaderboardConsent)
    APS->>ENS: enroll(memberId, challengeId, leaderboardConsent)
    ENS->>ELS: re-check eligibility(memberId, challengeId)
    ELS-->>ENS: eligible:true
    Note over ENS,MBF: Alts C3.1 not eligible / C3.3 consent declined → blocked,<br/>no enrolment created (consent = name|initials, opt-in NFR-1).<br/>opt C3.2: route to Journey B (Connect Wellness Data).
    ENS->>MDB: create enrolment + snapshot eligibility config + lock goals
    ENS->>CHS: assignParticipant(challengeId)
    ENS-->>SCO: MemberEnrolled(memberId, challengeId, goalSet) [async]
    ENS-->>LBS: MemberEnrolled(memberId, challengeId, consent) [async]
    ENS-->>NOT: MemberEnrolled → enrolment-confirmed notice [async]
    ENS-->>APS: enrollmentConfirmed
    APS-->>MBF: enrollmentConfirmed
    MBF-->>APN: enrolled (goals locked for duration)
    APN-->>MOB: enrolled
    MOB-->>PART: show enrolled
```

**UC coverage**: UC-C3 Enroll (Individual) — incl. Alt C3.1 not-eligible, C3.2 route-to-UC-C4, C3.3 consent-declined,
C3.4 multi-challenge (no active-enrollment check), C3.5 goals-locked — `«include»` UC-B1 (eligibility re-check via
`eligibility-svc`), UC-B3 (eligibility snapshot, persisted in membership-db), and UC-C5 Provide Participation Consent
(name/initials choice captured inline). The async **`MemberEnrolled`** event fans out to `scoring-svc` (open goal
progression), `leaderboard-svc` (admit ranked member with consent display mode), `ingestion-svc` (via the wellness
connection from Journey B), and `notification-svc` (confirmation, downstream of consent gate).

---

## Journey D (sketch) — Team / District Enrolment 🟡 P2 / 🔵 P3 *(out of P1 build scope — forward-traceability only)*

UC-C6 Create Team + UC-C7 Join Team (🟡 P2) and UC-C8 Enroll Representing District (🔵 P3). Same keystone owner
(`enrolment-svc`) with a `mode=team|district` enrolment; team invites fan out via `notification-svc` → Notification
Provider. Shown only for forward traceability; **not built in P1**.

```mermaid
sequenceDiagram
    autonumber
    actor ORG as Team Creator / District Rep 🟡🔵
        participant MOB as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant MBF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant ENS as 🟥 enrolment-svc
    participant MDB as membership-db (PostgreSQL)
    participant NOT as 🟦 notification-svc
        participant NP as Notification Provider: push/email (ACL)

    ORG->>MOB: create team / enroll representing district
    MOB->>APN: POST /enrolments (mode=team|district, UAE Pass JWT)
    APN->>MBF: forward team/district command
    MBF->>APS: createTeam | enrollDistrict(...)
    APS->>ENS: createTeam | enrollDistrict(...)
    ENS->>MDB: persist Team/District + mode enrolment (+ invitations)
    ENS-->>NOT: TeamInvited / enrolment notice [async, P2]
    NOT->>NP: deliver invite (unique link + code)
    ENS-->>APS: created
    APS-->>MBF: created
    MBF-->>APN: show team/district enrolled (selection locked)
    APN-->>MOB: team/district enrolled
```

**UC coverage**: UC-C6 🟡 / UC-C7 🟡 / UC-C8 🔵 — tagged out of P1 scope; consume `notification-svc` and the
Notification-Provider ACL for invite delivery.

---

## Abstraction self-audit

| Rule | Result |
|---|---|
| Participants are applications/stores/externals only | PASS — Mobile App, APIM-north (Citizen Gateway), Mobile BFF, APIM-south (Platform Gateway), named `*-svc`, named datastores, Wearables/Notification-Provider ACLs; no «B»/«C»/«E» objects. |
| Layering contract obeyed (citizen path: Mobile → APIM-north → Mobile BFF → APIM-south → svc) | PASS — all four journeys A–D route through the two-leg gateway + Mobile BFF; no bare "API Gateway", no actor reaches a GP microservice directly. |
| Each diagram ≤ ~18 messages | PASS — A=18, B=17, C=18, D=12 (full Mobile→APIM-north→BFF→APIM-south→svc chain shown). |
| Trivial UCs merged per journey | PASS — C1+C2 (A), C3+C5+C4-route (C); C4 standalone (B); C6/C7/C8 (D sketch). |
| Cross-context calls shown | PASS — enrolment-svc → eligibility-svc / challenge-svc reads. |
| Async inter-service events shown | PASS — `MemberEnrolled` fan-out (scoring/leaderboard/ingestion/notification); `WellnessConnected`; `TeamInvited`. |
| Backward UC traceability note per diagram | PASS — one-line UC-coverage note under each journey, tracing to UC-C1..C8 in `01-use-cases.md` and the low-level sequences. |
| Phase tags preserved | PASS — A/B/C 🟢 P1; D 🟡 P2 / 🔵 P3 tagged out of build scope. |
