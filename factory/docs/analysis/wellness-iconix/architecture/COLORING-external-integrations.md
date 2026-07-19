# External-integration colour coding — architecture sequences

> In every `architecture/sequences/*.md`, mark the **GP microservices that are external integration points**
> with a colour chip on the participant label (`participant CH as 🟥 challenge-svc`). Chips go **only on
> microservices** — nothing else is chipped.

## GP system boundary (who is internal vs external)
- **INSIDE GP** (never chipped): `APIM-south` (Platform Gateway), all `*-svc` microservices, all datastores,
  `domain-event-log`, and `Admin Portal` (DoH/ADHDS back-office). The GP boundary = everything **beyond the BFF,
  up to (not including) the providers**.
- **OUTSIDE GP** (external; themselves never chipped): Sahatna **front-end** (`Mobile App`), Sahatna **backend**
  (the BFF components: `Mobile BFF`, `Content Renderer`, `Wearable Ingest`, `Sahatna Survey API`,
  `Sahatna Notifications API`), `APIM-north` (Citizen Gateway), and all **providers / sources**
  (`Malaffi`, `Reward Partners`, `Notification Provider`, `Citymoov`, `IFHAS`, `Sahatna Events`, `Health Connect SDK`).

## Chip rule (microservices only)
For each `*-svc` in a diagram, judged **per diagram**:
- **🟥 receives from external** — the svc handles a message that **originated OUTSIDE GP**: a citizen/app request
  that entered via APIM-south (origin = Mobile App / BFF), OR a direct push from a provider/source. The svc is the
  GP entry point for that external traffic. *(Admin Portal–originated messages are INTERNAL — they do NOT make a svc 🟥.)*
- **🟦 writes externally** — the svc **sends** a message to a participant OUTSIDE GP: a provider call
  (e.g. `eligibility-svc → Malaffi`, `rewards-svc → Reward Partners`, `settlement-svc → Malaffi`) or a delivery to a
  BFF (`notification-svc → Sahatna Notifications API`).
- **🟥🟦 both** if it does both (e.g. `eligibility-svc` receives discovery AND calls Malaffi).
- **No chip** if the svc only talks to other internal services / datastores / `domain-event-log` / Admin Portal
  (e.g. a purely internal or admin-only service like `reporting-svc`).

## Placement & hygiene
- Put the chip(s) immediately after `as ` in the microservice's `participant` declaration: `participant ELIG as 🟥🟦 eligibility-svc`.
- Do **not** chip APIM-south, datastores, event-log, Admin Portal, external participants, or actors.
- Legend under the first diagram: `> 🟥 svc receives from outside GP · 🟦 svc writes to outside GP (microservices only)`.
- Mermaid hygiene: no `;` in messages (use `,`); capital `Note`; balanced `alt/opt/loop … end`; no stray fences/tags.

## Example
```mermaid
sequenceDiagram
    actor U as Participant
    participant MA as Mobile App
    participant APS as APIM-south (Platform Gateway)
    participant ELIG as 🟥🟦 eligibility-svc
    participant ECACHE as eligibility-cache (Redis)
    participant MAL as Malaffi (clinical · ACL)

    U->>MA: open discovery
    MA->>APS: getEligibleChallenges (via APIM-north + BFF)
    APS->>ELIG: evaluateEligibility          %% external-origin request → ELIG is 🟥
    ELIG->>MAL: getScopedMembership(...)       %% writes to provider → ELIG is 🟦
    MAL-->>ELIG: clinical membership
    ELIG-->>MA: eligible challenges
