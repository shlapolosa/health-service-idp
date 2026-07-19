# Business Phase — Capability Realization (step 3a)

> **Deliverable:** `business-capability-realization.archimate.xml` — ArchiMate Model Exchange 3.0,
> well-formed. View: **Capability Realization** (mirrors the reference pattern).
> **Scope (deliberately narrow, expands next):** only the **business behaviour that realizes the
> capabilities** — the Business Services that realize each Capability, and the Business Functions
> (the document's ABBs) that realize those services.

## The realization chain

```
Strategy:   Capability
                ▲ realization   (one capability realized by ONE OR MORE services)
Business:   Business Service(s)       ← externally-visible service(s) offered to Member/Partner/DoH
                ▲ realization
Business:   Business Function(s)      ← internal capability behaviour (the ABBs)
```

A capability is realized by **one or more** Business Services (not 1:1); each service is realized by
its specific Business Function(s). **12 capabilities → 27 services → 30 functions.** Capability IDs
are the **same** as the Strategy model (`cap1…cap12`), so the two models merge into one coherent
picture (Strategy → Business) when we assemble the full layered view.

## Capability → Business Services → Business Functions (the ABBs)

| Capability | Business Services (each realizes the capability) | Functions realizing each service |
|---|---|---|
| Cohort Identification & Segmentation | Cohort Definition · Segment Publication | Cohort Analysis · Segment Publication |
| Challenge Lifecycle Management | Challenge Authoring · Challenge Presentation · Challenge Conclusion | Challenge Management · Presentation · Programme Conclusion |
| Wellness Scoring & Recognition | Daily Scoring · Weekly Aggregation · Recognition & Titles | Wellness Scoring + Goal Mgmt · Score Aggregation · Streak + Badge + Title & Progression |
| Activity & Clinical Verification | Activity Verification · Clinical Verification | Activity Verification · Clinical Verification |
| Reward Points & Wallet | Wallet Balance · Points Crediting · Point Reservation | Reward Points Wallet · Points Crediting · Reservation |
| Marketplace & Redemption | Catalogue Browse · Reward Redemption · Voucher Issuance | Catalogue Mgmt · Reward Marketplace · Voucher Mgmt |
| Partner Lifecycle & Settlement | Partner Onboarding · Catalogue Management · Settlement | Partner Lifecycle Mgmt · Partner Catalogue Mgmt · Settlement |
| Engagement & Nudging | Engagement & Nudge | Engagement & Nudge (NUDGE) |
| Consent, Identity & Compliance | Consent Management · Identity & Authentication | Consent Management · Identity & Authentication |
| Fraud & Integrity | Integrity Check | Fraud & Integrity (FRAUD) |
| Integration & Interoperability | Event Streaming · Partner / Data Integration | Event & Integration Mgmt · Integration |
| Analytics & Insight | Analytics · Reporting | Data Management · Reporting |

**12 capabilities → 27 services → 30 functions.** The functions cover all **17 ABBs** plus Cohort
Analysis/Segment Publication (Phase A), Presentation & Conclusion (Phases C/8), Score Aggregation,
Points Crediting & Reservation, Catalogue & Voucher Mgmt, and Partner Lifecycle/Settlement (Part 5) —
every capability realized, every ABB placed. Each capability with multiple services shows those
services side-by-side in its column, each centred over its realizing function(s).

## Layout

Three aligned swimlanes, columns one-per-capability (mirrors the reference's Capability-Realization
pattern): **Strategy · Capabilities** (tan) on top, **Capability Realization · Business Services**
(yellow) beneath each capability, **Behaviour · Business Functions** (yellow) at the bottom.
Realization arrows run straight up each column; connectors are right-angled (bendpoints).

## Deferred to the next expansion (when we "expand shortly")

- **Business Roles / Actors** (Structure) performing the functions (assignment), and **Resources**
  realized by business actors/objects.
- **Business Processes** (the member/partner journeys: enrol → earn → redeem → settle), **Business
  Objects / Events**, **Products**, **Contracts**.
- The **Application layer** (Application Components/Services realizing the business functions) and its
  realization onto this platform's **OAM components** (webservice / realtime-platform / analytics-
  platform / postgresql …) — Phases 4–5.
