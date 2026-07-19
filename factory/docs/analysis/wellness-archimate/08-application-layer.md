# Application Layer (Phase 4)

> **Deliverable:** `application-layer.archimate.xml` — ArchiMate Model Exchange 3.0, well-formed,
> **2 views**. Colours: **Application = cyan** (`#B5FFFF`), Business = yellow. OAM component-type
> mapping is **deferred to the Technology phase** (per decision). Business-function IDs (`fn_p1…fn_p13`)
> match the business model so the layers merge.

**Model:** 16 Application Components · 14 Application Services · 22 Data Objects · 13 Business
Functions (for the seam) · 72 relationships (Realization 14, Serving 33, Access 25 with Read/Write).

## View 1 — Application Cooperation

Three lanes: **Application Services** (top, offered APIs) · **Application Components** (middle, the
microservices) · **Data Objects** (bottom, Read/Write access). Plus the curated inter-component
**serving** dependencies and the external systems.

**Application Components (the microservices):**

| Component | Application Service | Realizes business function |
|---|---|---|
| Cohort & Segmentation Service | Cohort & Segmentation API | Cohort Planning |
| Challenge Service | Challenge Management API | Challenge Lifecycle Mgmt |
| Enrolment & Eligibility Service | Enrolment API | Eligibility Evaluation |
| Scoring & Recognition Service | Scoring & Recognition API | Wellness Scoring & Recognition |
| Verification Service | Verification API | Activity Verification |
| Wallet Service | Wallet API | Reward Points & Wallet |
| Marketplace & Voucher Service | Redemption API | Marketplace & Redemption |
| Partner & Settlement Service | Partner API | Partner Lifecycle & Settlement |
| Engagement Service | Engagement API | Engagement & Nudging |
| Consent & Identity Service | Consent & Identity API | Consent & Identity |
| Fraud & Integrity Service | Integrity API | Fraud & Integrity |
| Analytics & Reporting Service | Analytics API | Analytics & Insight |
| Event Hub | Event Streaming API | Integration & Interoperability |
| Member Gateway (BFF / Realtime) | Member Experience API | (member-facing aggregation) |
| **Sahatna Mobile App** *(external)* | — | data source + member channel |
| **Malaffi HIE System** *(external)* | — | clinical data + membership/eligibility |

**Key serving dependencies (the data-plane wiring):** Event Hub → Scoring/Wallet/Engagement/Analytics/
Gateway (async spine) · Fraud → Wallet/Marketplace (inline integrity) · Wallet → Marketplace · Verification
→ Scoring · Analytics → Cohort · Consent → Gateway · Challenge → Enrolment → Scoring → Wallet · Gateway →
Sahatna app → Member · Sahatna → Cohort/Verification (demographic + telemetry) · Malaffi → Enrolment/Cohort
(membership + clinical). Each component **Access**es its Data Objects (Read inputs / Write outputs).

## View 2 — Application → Business Realization Seam

A clean 3-lane, column-aligned seam (the chain we agreed):

```
Business Functions   (engine behaviour)        ← serving ←  Application Services (offered)  ← realization ←  Application Components (microservices)
Cohort Planning                                   Cohort & Segmentation API                    Cohort & Segmentation Service
Challenge Lifecycle Mgmt                          Challenge Management API                     Challenge Service
Eligibility Evaluation                            Enrolment API                               Enrolment & Eligibility Service
…                                                 …                                           …
```

Each Application Component **realizes** its Application Service, which **serves** the Business Function
it implements — so the application layer plugs straight into the business model (and the capability
chain above it: Capability ← Business Service ← Business Function ← **Application Service ← Component**).

## What's deferred (Technology phase / Phase 5)

- **OAM component-type mapping** — each Application Component → its platform component type
  (`webservice` for the microservices · `realtime-platform` for the Event Hub · `analytics-platform`
  for Analytics/Cohort · `postgresql` for the data stores · `realtime-service` for the Member Gateway
  `/ws` · `auth0-idp` for Identity · `graphql-gateway` for the BFF) — modelled as **Technology Nodes /
  Artifacts** realizing these Application Components, tying the whole ArchiMate analysis to the
  `wellness-gamification-example.yaml` OAM.
- Deployment (Nodes, Communication Networks), and the external integrations (Sahatna app platform,
  Malaffi HIE endpoints).
