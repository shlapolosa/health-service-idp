# Application Landscape — Design (elements & relationships first)

> Goal: a rich, ArchiMate-correct application architecture showing **system boundaries**, the apps and
> functions inside them, the **interfaces** they expose/consume, the **services** they offer, the
> **collaborations / interactions** across boundaries, the **data** they ingest/output, and how they
> **realize/serve** the business layer. This document fixes the design; the view is generated after sign-off.

## 1. System boundaries (4) — modelled as Application Collaborations

| Boundary | What it is | Modelled as | Black box? |
|---|---|---|---|
| **Sahatna** | Member channel: mobile frontend + API Gateway + BFFs | Application Collaboration (contains components) | No — we own the channel components |
| **Gamification Platform** | The engine: challenge/scoring/wallet/marketplace + eligibility + integration | Application Collaboration (contains the microservices) | No — full internal detail |
| **Malaffi (HIE)** | Clinical-data exchange | **Application Component (black box)** exposing one **Application Interface** | **Yes** — only its API + the services behind it are visible |
| **External Reward Providers** | Voucher/redemption providers (incl. aggregators) | Application Component(s) exposing a redemption **Application Interface** | Yes — only their API |

## 2. Components, interfaces, functions, services per boundary

### Sahatna (channel) — Application Collaboration
- **Components:** Mobile App · API Gateway · Member BFF · Challenge BFF · Rewards BFF
- **Interfaces:** *Sahatna App UI* (to Member, the device) · *Sahatna Gateway API* (north-bound to platform)
- **Functions:** Presentation & Aggregation · Session/Token handling
- **Service:** *Member App Service* (serves the Member)

### Gamification Platform (engine) — Application Collaboration
- **Components (microservices):** Cohort & Segmentation · Challenge · **Enrolment & Eligibility** · Scoring & Recognition · Verification · Wallet · Marketplace & Voucher · Partner & Settlement · Engagement · Consent & Identity · Fraud & Integrity · Analytics & Reporting · Event Hub
- **Interfaces:** *Platform Public API* (consumed by Sahatna BFFs) · *Malaffi Adapter Interface* (consumes Malaffi API) · *Provider Adapter Interface* (consumes provider APIs) · *Event Streaming Interface*
- **Functions (internal, examples):** **Eligibility Resolution** · **Local Membership Check** · Cohort Matching · Daily/Weekly Scoring · Reservation & Crediting · Redemption Orchestration · Fraud Check · Event Publish/Subscribe
- **Services:** *Eligibility Service* · *Challenge Service* · *Scoring Service* · *Wallet Service* · *Redemption Service* · *Engagement Service* · *Consent & Identity Service* · *Analytics Service* · *Event Streaming Service*

### Malaffi (HIE) — black-box Application Component
- **Interface:** *Malaffi API* (Application Interface)
- **Services (behind the interface):** *Membership & Eligibility Service* (is the user a member / clinically eligible?) · *Clinical Cohort & Segmentation Service*
- We model **only** the interface + these two services; no internals.

### External Reward Providers — black-box Application Component(s)
- **Interface:** *Provider Redemption API*
- **Service:** *Voucher Redemption Service*

## 3. The login → eligibility → presentation flow  *(your key requirement)*

Modelled as an **Application Process** *"Login & Challenge Presentation"* plus an **Application
Interaction** *"Determine Eligible Challenges"* performed by an **Application Collaboration**
(Enrolment & Eligibility ⊗ Cohort & Segmentation ⊗ Malaffi):

```
Member ─uses→ Sahatna App UI
   │  (Application Event) ▶ User Logged In
   ▼
Sahatna Member BFF ─request via Sahatna Gateway API→ Platform Public API
   ▼
Enrolment & Eligibility component ─performs→ Eligibility Resolution (Application Function)
   1. read ACTIVE Challenge(s)               (Access read: Challenge Data)
   2. for each challenge, branch by type:
        • demographic OR telemetry → Local Membership Check          (Access read: Segment Data — held locally)
        • clinical                 → call Malaffi API → Membership & Eligibility Service   (Serving across boundary)
        • combination              → BOTH of the above
   3. compose result                          (Access write: Eligibility Result)
   ▼  (Application Event) ▶ Eligibility Resolved
Platform Eligibility Service ─serves→ Sahatna Challenge BFF ─→ Mobile App
   ▼
Member sees a mix of clinical / demographic / telemetry (and combination) challenges
```

**The branch rule (your statement) encoded:** *check current challenges → if demographic or telemetry-
based, check locally whether the user is a member; otherwise (clinical) ask Malaffi.* Combination
challenges check both. This is an **Application Interaction** because it's the *collective* behaviour of
platform components + the external Malaffi service.

## 4. Other key behaviours

- **Application Process "Earn"**: Verification → Scoring → Wallet crediting (Event Hub triggers between).
- **Application Process "Redeem"** + **Application Interaction "Fulfil Redemption"** (Marketplace ⊗ Wallet ⊗
  Fraud ⊗ External Provider): reserve points → fraud check → call *Provider Redemption API* → issue voucher.
- **Application Events:** User Logged In · Eligibility Resolved · Activity Verified · Points Credited ·
  Voucher Issued · Challenge Published.

## 5. Data Objects — ingested vs produced (Access Read/Write, Flow across boundaries)

| Data Object | Ingested from | Produced/owned by |
|---|---|---|
| Demographic Data | Sahatna (profile) | held locally in Platform (Cohort store) |
| Telemetry Data | Sahatna (device/wearables) | Platform (Verification, Cohort) |
| Clinical Membership / Eligibility | **Malaffi API** | Malaffi (we only read) |
| Segment / Local Membership | — | Platform (Cohort & Segmentation) |
| Challenge Data · Eligibility Result · Score · Wallet Ledger · Redemption · Voucher | — | Platform components |

Cross-boundary data movement (Sahatna→Platform, Malaffi→Platform, Platform→Provider) is modelled with
**Flow** relationships; within-component reads/writes with **Access (Read/Write)**.

## 6. Realization / serving up to the Business layer

Each Platform **Application Service** ─serving→ its **Business Function** (the seam): e.g. *Eligibility
Service* → *Eligibility Evaluation*; *Scoring Service* → *Wellness Scoring & Recognition*; *Redemption
Service* → *Marketplace & Redemption*. Application **Components** ─realize→ their Application Services.
The *Member App Service* (Sahatna) ─serves→ the **Member** (Business Role).

## 7. ArchiMate symbol coverage (all application-layer concepts present)

| Symbol | Where it appears |
|---|---|
| **Application Component** | Sahatna apps · 13 platform microservices · Malaffi · Providers |
| **Application Collaboration** | Sahatna · Gamification Platform · Eligibility-Determination · Redemption |
| **Application Interface** | Sahatna App UI · Sahatna Gateway API · Platform Public API · Malaffi API · Provider Redemption API · Event Streaming Interface |
| **Application Function** | Eligibility Resolution · Local Membership Check · Cohort Matching · Scoring · Reservation/Crediting · Redemption Orchestration · Fraud Check · Event Pub/Sub |
| **Application Interaction** | Determine Eligible Challenges · Fulfil Redemption |
| **Application Process** | Login & Challenge Presentation · Earn · Redeem |
| **Application Service** | Eligibility · Challenge · Scoring · Wallet · Redemption · Member App · Malaffi Membership & Eligibility · Provider Redemption · Event Streaming |
| **Application Event** | User Logged In · Eligibility Resolved · Activity Verified · Points Credited · Voucher Issued |
| **Data Object** | Demographic · Telemetry · Clinical · Segment · Challenge · Eligibility Result · Score · Wallet · Redemption · Voucher |
| **Relationships** | Composition (collab ⊃ component) · Assignment (component → function/interface) · Realization (component/function → service) · Serving (service/interface → consumer; service → business function) · Access (function → data, Read/Write) · Triggering (process flow) · Flow (cross-boundary data) · Aggregation (collaboration) |

## 8. Proposed views (once design is signed off)

1. **Application Cooperation (Overview-style, left→right)** — the 4 system boundaries as nested
   collaborations; components inside; interfaces on the boundaries; the flows between Sahatna → Platform
   → Malaffi/Providers; data objects below. Visual emphasis like `overview.png`.
2. **Eligibility Determination** — a focused interaction view of the login→eligibility flow (the branch
   rule), with the collaboration, interaction, interfaces, services, events and data.
3. **Application → Business Realization seam** — services serving business functions (refined from the
   current seam view).

---
**Open question for sign-off:** does Sahatna hold the demographic/telemetry data and *push* it to the
platform, or does the platform pull/store it? The design above assumes the platform **stores a local
copy** (so demographic/telemetry membership is a *local* check) and Malaffi stays the *remote* clinical
authority — matching your branch rule. Confirm or correct, plus any element renames, and I'll generate
the views.
