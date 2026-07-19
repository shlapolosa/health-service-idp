# Business Phase — Process Cooperation (step 3b)

> **Deliverable:** `business-process-cooperation.archimate.xml` — ArchiMate Model Exchange 3.0,
> well-formed, **2 views**, left-to-right **value-chain / Overview** layout (the Image #9 pattern),
> business layer only. Processes taken from the document's BPMN — **Part 0** (member) and **Part 5**
> (partner). **87 elements** · **137 relationships**.

## ArchiMate rules applied (confirmed)

Four labelled lanes, top→bottom, all left-to-right:

1. **Business Roles / Actors — ACTIVE STRUCTURE.** Roles are drawn **separately** (not containing
   processes). A role relates to behaviour by **Assignment** (*performs*), **never Composition** —
   so nesting a process inside a role would be wrong; we use explicit Assignment arrows instead.
2. **Business Services — BEHAVIOUR (external).** A **Business Service** is externally-visible
   behaviour offered to a consumer (rounded shape). Each phase process **realizes** its service, and
   the service **serves** the consuming role (Member / Programme Admin / DoH / Partner).
3. **Business Processes — BEHAVIOUR (internal flow).** A phase is a **composite Business Process
   composed of** its step sub-processes (**Composition** — processes *can* compose other processes),
   and composites + steps flow left-to-right via **Triggering**, like *Production* containing
   *planning → processing → packaging*.
4. **Business Objects — PASSIVE STRUCTURE.** Bottom lane; processes **Access** (read/write) them.

**Business Service vs Business Function (the distinction you asked for):** a *Service* is **external**
(what is offered) — shown here; a *Function* is **internal behaviour grouped by capability** — shown
in the **Capability-Realization view (`05`)**. The *same* behaviour is grouped **either** by flow
(Processes, this view) **or** by capability (Functions, view 05) — never both on one element. So the
two views together give Services (offered) ← realized by Functions (capability) **and** ← realized by
Processes (flow).

Relationship counts: Composition 47 (phase→step) · Triggering 45 (sequence) · Access 25 (object I/O)
· Assignment 19 (role→phase, supporting actor→step) · Realization 11 (process→service) · Serving 11
(service→consumer). Connectors are right-angled; spacing is generous (step gap 66 px, phase gap 86 px).

## View 1 — Member Journey: "Cohort to Reward" (now includes Rewards/Redemption)

Owner roles (containers), left-to-right, each holding a composite phase:

| Owner role (active) | Composite phase (behaviour) | Steps |
|---|---|---|
| Analytics & Data Team | **Cohort Identification** | Compute Features → Define Cohort → Publish Segment |
| Programme Administration | **Challenge Creation** | Author Challenge → Bind Eligibility → Author Presentation → Publish & Present |
| **Member / Citizen** | **Enrolment** | Enrol → Evaluate Eligibility → Accept T&C → Confirm |
| **Member / Citizen** | **Earning Loop** | Capture Activity → Verify Activity → Score Daily Goals → Apply Recognition → Aggregate Weekly → Credit Points |
| **Member / Citizen** | **Rewards & Redemption** *(new)* | Browse Rewards → Reserve Points → Redeem with Partner → Receive Voucher |
| Department of Health | **Conclusion** | Conclude Challenge → Hand Winners & Prizes |

Supporting actors (top lane): CMS Author → *Author Presentation*; Verification Authority → *Verify
Activity*. Passive (bottom): Segment · Challenge Contract · ScoringPlan · Enrolment · Verified
Activity · Weekly Score · Wallet · **Reward Catalogue** · **Voucher** · Title/Badge.

## View 2 — Partner Lifecycle (Part 5)

| Owner role (active) | Composite phase (behaviour) | Steps |
|---|---|---|
| Partner Onboarding (Admin) | **Onboarding & KYB** | Submit Application → KYB Due Diligence → Approval Decision |
| Marketplace Operations | **Contracting & Catalogue** | Provision Sandbox Creds → Push Catalogue → Validate Items → Index → Release Prod Creds |
| Redemption Ops | **Member Redemption** | Browse & Select → Reserve Points (5-min) → Call Partner API (10s) → Commit Debit & Voucher → Notify |
| Finance & Settlement | **Settlement** | Aggregate → Reconcile → Generate VAT Invoice → Route Payment → Release 5% Holdback |
| Partner Exit (Admin) | **Offboarding & Exit** | Offboarding Decision → 30-day Warning → Revoke & Depublish → 90-day Wind-down → Final Settlement → Retain Data / Mask PII |

Supporting actors: Partner → *Submit Application / Push Catalogue*; Member → *Browse & Select*;
Wallet/Finance → *Reserve / Commit*; Fraud & Compliance → *Call Partner API*. Passive: KYB Record ·
Contract · Catalogue · Reservation · Redemption · Voucher · Settlement/Invoice.

## Colours

All business-layer elements use the standard ArchiMate **business yellow** (`#FFFFB5`); element
**shape** distinguishes role / process / object — colour does not.

## Next expansion options

- Add **Products** (the challenge offered to members; the reward catalogue as a partner product) and
  **Contracts**, plus **Business Events** on the trigger flow if you want explicit start/end markers.
- Decompose any single step (e.g. *Redeem with Partner*) into its own detailed sub-process view.
- Proceed to the **Application layer** (Application Components/Services serving these processes) →
  realization onto the platform's **OAM components** (Phases 4–5).
