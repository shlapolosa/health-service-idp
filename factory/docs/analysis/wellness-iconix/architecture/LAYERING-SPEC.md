# Layering & System-Boundary Spec (authoritative placement frame)

> The components surfaced by the architecture workflow (`01-interface-layer.md`, `02-logic-bounded-contexts.md`,
> `03-datastores.md`, `sequences/*.md`) are placed into the **four system boundaries / layers** below, then
> visualised with **/drawio-c4** (banded C4). This file is the authoritative placement frame.

## Architectural principle
- **Event-driven first.** Cross-boundary and cross-context interactions default to **asynchronous events**.
- **Sync only where inherently synchronous** (e.g. login/identity, eligibility read before enrol, redeem
  confirmation, marketplace browse). Mark each high-level edge **async (event)** vs **sync** explicitly.
- **Layered architecture** — strict top→down; a layer talks only to the seam directly below it.

## The four system boundaries (top → bottom)

### 1. Sahatna Mobile Application  *(client / presentation surface)*
- The citizen-facing **Participant** app.
- **North integration seam:** **Azure APIM** (gateway) + **UAE Pass** as the citizen **IdP** (OIDC → platform JWT).
- Talks **only** to the BFF layer (via APIM). No direct GP or 3rd-party access.

### 2. BFF Layer  *(presentation-driving / backend-for-frontend)*
- **Drives the presentation** for the mobile app (composition, localization, session, fan-out).
- **South integration seam → GP:** **B2B integration using Microsoft Entra ID** (OAuth2 client-creds / app
  registration) **+ APIM** (per-product). This is the trust boundary between Sahatna and the Gamification Platform.
- Holds **no authoritative business data** — it orchestrates calls/events into GP.

### 3. Gamification Platform (GP)  *(where data + logic live)*
- The **second system**: the bounded-context microservices (from `02-…`), their datastores (from `03-…`),
  and the **event backbone** (the platform's preferred async spine).
- Also hosts the **Admin Portal** (DoH Gamification staff + ADHDS operator) for management/authoring/reporting —
  an internal surface inside the GP boundary (workforce SSO via Entra, no public ingress).
- Integrates **down** to 3rd-party providers (mostly via API, behind anti-corruption layers).

### 4. 3rd-Party Providers  *(external, bottom layer)*
- **Malaffi** — clinical segmentation / scoped membership (eligibility). API integration, ACL.
- **Marketplace / reward providers** — voucher issue/redeem, partner reward submission. API integration.
- Plus: wearable/health data source, push/email notification provider.
- **Outside the platform trust zone**; reached primarily via API (some event ingest, e.g. wearables/telemetry).

## Seam summary (for the C4 edges)
| Seam | Mechanism | Default style |
|---|---|---|
| Mobile → BFF | APIM + UAE Pass JWT | sync (identity) + async where possible |
| BFF → GP | **Entra ID (B2B) + APIM**, per-product | event-first; sync for reads/confirmations |
| GP intra (context ↔ context) | **event backbone** | async (event) |
| GP → 3rd-party | API integration + ACL | sync (Malaffi eligibility, redeem) / async (telemetry ingest) |

## /drawio-c4 banded mapping (visualisation plan)
Bands top→down, with trust-boundary strips at the two integration seams:
1. **Sahatna Mobile** band → `trust_boundary("APIM · UAE Pass (citizen OIDC)")`
2. **BFF Layer** band → `trust_boundary("B2B · Entra ID + APIM")`
3. **Gamification Platform** — `system(...)` dotted boundary enclosing: API Gateway (south), the microservices
   (one component per bounded context), the **event backbone**, datastores, and **Admin Portal**.
4. **3rd-Party Providers** band → `trust_boundary("PARTNER TRUST BOUNDARY · API / ACL")` → Malaffi, marketplace,
   wearables, notification provider.
- Edge kinds: `sync` (solid), `async` (dashed + flowAnimation = the event-first default), `xtrust` (to 3rd parties),
  `identity` (UAE Pass / Entra).
- Output → `architecture/solution-c4.drawio`, invariant-checked (no overlaps / box-crossings / diagonals).

## Sequence layering contract (MANDATORY for every `architecture/sequences/*.md`)
Every high-level sequence MUST route through the layers by **originator** — no actor may reach a GP microservice
directly. Reference pattern already in-repo: `earn-scoring.md`, `notification.md` (APIM-north · BFF · APIM-south).

1. **Citizen / mobile-originated** flow:
   `Mobile App → APIM-north (Citizen Gateway) → <BFF> → APIM-south (Platform Gateway) → <GP microservice> → (<datastore> | domain-event-log | external via ACL)`
   - `<BFF>` chosen by concern: **Mobile BFF** (gameplay reads/commands) · **Content Renderer** (published content) ·
     **Wearable Ingest** (telemetry stream) · **Sahatna Survey API** (survey info + responses) · **Sahatna Notifications API** (in-app feed).
   - Login/identity: **UAE Pass** at APIM-north.
2. **Admin / staff (DoH · ADHDS)** flow:
   `Admin Portal → APIM-south (Platform Gateway) → <GP microservice>` — **NO BFF, NO north gateway** (Admin Portal is
   inside the GP boundary; workforce **Entra** SSO).
3. **Scheduler / time-actor & internal**: `Scheduler → <GP microservice>` directly; microservice ↔ microservice via
   **`domain-event-log`** (async, event-first); microservice → its **own datastore** (sync).
4. **External**: `<GP microservice> → 3rd-party` via ACL (Malaffi, Reward Partners, IFHAS, Sahatna Events, Notification Provider).
- **Wearable + survey-response** ride the citizen path as **async streams** to `ingestion-svc`.
- Use these exact participant names (match `solution-c4.drawio`): `Mobile App`, `APIM-north (Citizen Gateway)`,
  `APIM-south (Platform Gateway)`, the BFF names above, microservice names (`challenge-svc`…), datastores,
  `domain-event-log`, `Malaffi`, etc. The single generic `API Gateway` participant is **wrong** — split it into the
  correct leg(s) per originator.

## Next steps (after the architecture workflow lands)
1. Write `architecture/04-layered-system-view.md` — place every component from `01/02/03` into one of the four
   boundaries + its layer, tagging each integration edge async-event vs sync.
2. Generate the banded C4 via /drawio-c4 → `architecture/solution-c4.drawio`.
