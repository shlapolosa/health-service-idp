# 04 — Layered System View (component placement into the four boundaries)

> Places every high-level component from `01-interface-layer.md`, `02-logic-bounded-contexts.md`, `03-datastores.md`
> into the four system boundaries from `LAYERING-SPEC.md`, then tags each integration seam **async (event-first)** vs
> **sync (inherently synchronous)**. Visualised by `solution-c4.drawio` (built with /drawio-c4).

## Boundary 1 — Sahatna Mobile Application *(client / presentation surface)*
The 25 Mobile boundary objects collapse into 6 feature surfaces of the **Sahatna Participant App**:
| Surface | Screens (from 01) |
|---|---|
| Discover & Enrol | Challenge Discovery/Details, Enrollment Wizard, Consent Dialog, Wellness-Data Connect, Confirmation |
| Progress & Streaks | Weekly Progress, Streak Builder |
| Recognition & Share | Badge Collection, OS Share Sheet, Event Detail, Screening Status |
| Leaderboard / Track | Individual Leaderboard |
| Wallet & Marketplace | Wallet, Marketplace Catalog, Reward Detail + Redeem, My Rewards |
| Settings | Notification Settings |
| **Health Connect SDK** | on-device wearable/health telemetry source (Apple Health / Google Fit) — **streamed** from the app to the platform (not a screen) |
| **Surveys / Check-ins** | fetches **survey info** from the Sahatna Survey API; submits **survey responses** (streamed like telemetry) |

> **Frontend-stream inputs (wearables + surveys):** both wearable/health metrics (read on-device by the **Health Connect SDK**) and **survey responses** (self-reported check-ins) are **streamed from the frontend through all integration legs** — `Mobile App → APIM (north) → BFF (Wearable Ingest / Survey API) → APIM (south) → ingestion-svc` — as an **async** stream. There is **no server-side pull** from a wearables cloud; survey **info** is served read-side by the **Sahatna Survey API**.

**North seam → BFF:** `Azure APIM (Citizen Gateway)` + `UAE Pass` (OIDC → platform JWT). **sync** (identity/session); wearable telemetry rides this seam **async**.

## Boundary 2 — BFF Layer *(presentation-driving; no authoritative data)*
Introduced per the layering spec (Sahatna server-side). Drives the mobile experience and does **B2B into GP**:
| BFF component | Role |
|---|---|
| Mobile BFF (gameplay) | composition · session · fan-out to GP · localization shaping |
| Content Renderer | renders localized (AR/EN) published challenge content |
| Sahatna Notifications API | **Sahatna owns delivery** — push/email/in-app, consent-gated; also **exposes the notifications API** (in-app feed) to the app |
| Wearable Ingest Service | receives the **streamed** Health Connect SDK telemetry from the app (via north APIM) and relays it through the B2B seam to `ingestion-svc` |
| Sahatna Survey API | **exposes survey info** (definitions/questions) to the app, and **ingests survey responses** — which follow the **same frontend-stream path as wearable data** (north APIM → BFF → south APIM → `ingestion-svc`) |

**South seam → GP:** `Platform APIM` + `Microsoft Entra ID` (B2B OAuth2 client-creds, per-product). **event-first**, **sync** for reads/confirmations.

## Boundary 3 — Gamification Platform (GP) *(data + logic live here)*
### 3a. Admin Portal *(inside GP; workforce SSO via Entra, no public ingress)* — the 15 Admin objects:
- **Authoring & Config Console** — Request Form, Request Review, Config Console, Goal-Set, Winning-Criteria, Details-under-review, Catalog Admin, Reward Submission Form
- **Governance Console** — Governance/Archive, Disenroll Confirm
- **Reporting & Conclusion Console** — Challenge Dashboard, Winners List Review, Publish-Conclusion, Reward Distribution + Winner Contact

### 3b. Microservices (11 bounded contexts) + datastore (database-per-service):
| Microservice | Bounded context | Datastore(s) | Phase |
|---|---|---|---|
| challenge-svc | Challenge Authoring & Lifecycle | challenge-db (PostgreSQL) + challenge-content-store (object bucket) | P1 |
| eligibility-svc | Eligibility & Audience | eligibility-cache (Redis read-model) | P1 |
| enrolment-svc | Enrolment & Membership | membership-db (PostgreSQL) | P1 (Team P2/District P3) |
| ingestion-svc | Activity Ingestion | activity-log (append-only / time-series) | P1 |
| scoring-svc | Scoring & Progression | scoring-db (PostgreSQL) | P1 (Title P2) |
| leaderboard-svc | Leaderboard & Ranking | leaderboard-cache (Redis sorted-set) + leaderboard-snapshots | P1 |
| recognition-svc | Recognition & Engagement | recognition-db + sharecard-store (object) | P1 (Quest P2) |
| rewards-svc | Rewards, Wallet & Marketplace | points-ledger (append-only) + marketplace-db + reward-image-store (object) | P1 |
| settlement-svc | Settlement & Conclusion | settlement-db (PostgreSQL) | P1 |
| notification-svc | Notification | notification-db (PostgreSQL) | P1 |
| reporting-svc | Reporting & Analytics | analytics-db (OLAP read-model) | P1 |

### 3c. Event backbone — `domain-event-log` (the async spine; **event-first** default for all intra-GP context↔context).
Events: Goal-Met · Streak-Update · Badge-Trigger · Weekly-Finalized · Score-Recalc · Activity-Verified · Points-Credited · Voucher-Issued.

## Boundary 4 — 3rd-Party Providers *(external, bottom; API + ACL)*
| Provider | Integration | Style |
|---|---|---|
| Malaffi / DoH-ADHDS | clinical segmentation · manual reward-image intake · winner-confirm gate (ACL) | **sync** (eligibility read) + offline (image) |
| Wearables (Apple Health / Google Fit) | **on-device source only** — read by the Health Connect SDK in the app, then **streamed via the frontend** (north→BFF→south→ingestion-svc). **Not** a server-side provider integration. | **async** stream |
| IFHAS Screening Module | screening events → Ingestion | **async (event)** |
| Sahatna Events | event sign-up/check-in bonus points | **async (event)** |
| Notification Provider (push/email) | delivery, downstream of consent gate | **sync** dispatch |
| Reward Partners | partner reward + image submission · voucher issue/redeem | **sync** (redeem) + offline (submit) |
| Citymoov 🟡 P2 | quest completion points | async |

## Seam tagging summary
- **Mobile ↔ BFF:** sync (identity/session via APIM+UAE Pass).
- **BFF ↔ GP:** event-first; sync only for reads (eligibility, marketplace browse) + confirmations (redeem).
- **GP context ↔ context:** **async via `domain-event-log`** (event-first).
- **GP ↔ datastore:** sync (each context owns its store).
- **GP ↔ 3rd-party:** ACL; sync for Malaffi eligibility + redeem; async for telemetry/screening/event ingest.
