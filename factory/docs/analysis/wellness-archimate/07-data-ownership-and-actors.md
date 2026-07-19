# Data Ownership & Cross-Organisation Actors

> Captures the three-function / three-data-type model and the cohort/eligibility split.
> Reflected in the new view **"Data Ownership & Cohort / Eligibility Cooperation"** (3rd view in
> `business-process-cooperation.archimate.xml`) and wired into the Member Journey.

## Three Business Actors (active structure) — NOT functions

Sahatna, Malaffi and the Gamification Platform are organizations/systems that **perform** behaviour,
so they are **Business Actors**. The work each does is one or more **Business Functions** the actor is
*assigned to* (Actor ─Assignment→ Function ─Realization→ Service). **This complements views 05/06 — it
does not replace the platform's full scope.**

| Business Actor | Role in the architecture | Business Functions | Services it provides |
|---|---|---|---|
| **Sahatna** | **Mobile app — where end users interact**, *and* a data source. Surfaces the platform's services to members; streams telemetry; holds demographics. | Member Mobile Experience · Demographics & Profile · Telemetry Capture & Streaming | **Member App Service** (→ Member) · Demographic Data Service (→ Platform) · Telemetry Streaming Service (→ Platform) |
| **Gamification Platform** | **The engine — ALL challenge / gamification / scoring / wallet / marketplace / cohort (non-clinical) / eligibility (non-clinical) management.** | **13 functions:** Cohort Planning · Challenge Lifecycle Mgmt · Wellness Scoring & Recognition · Activity Verification · Reward Points & Wallet · Marketplace & Redemption · Partner Lifecycle & Settlement · Engagement & Nudging · Eligibility Evaluation · Consent & Identity · Fraud & Integrity · Analytics & Insight · Integration & Interoperability | The gamified-wellness services (Enrolment, Scoring, Reward Redemption, …) — full set realized in views **05/06**; here they are shown **served through the Sahatna app** |
| **Malaffi (HIE)** | Clinical-data authority + membership + clinical cohort/segmentation/eligibility. | Clinical Data Management · Membership Registry · Clinical Cohort, Segmentation & Eligibility | Membership & Eligibility Service (→ Platform) · Clinical Cohort & Segmentation Service (→ Platform) |

**Channel + engine pattern:** **Member → Sahatna (mobile app) → Gamification Platform (engine) → Malaffi (clinical HIE).**
The platform's member-facing services (Enrolment, Scoring, Reward Redemption) are **served through the
Sahatna app** (Service ─Serving→ Sahatna's *Member Mobile Experience*), which in turn serves the
Member. Only **clinical data** sits outside the platform — owned by Malaffi.

## Three data types (passive structure) — owned by their source

| Business Object | Examples | Owner (maintains it) |
|---|---|---|
| **Clinical Data** | diabetes, obesity, … | **Malaffi (HIE)** |
| **Demographic Data** | gender, nationality, age, … | **Sahatna** |
| **Telemetry** | steps, sleep, nutrition, VO2, … | **Sahatna** (streamed) |

Ownership is modelled as the owner's function **Access**-ing (writing) the object.

## The cohort / segmentation / eligibility split (key assertions)

1. **Sahatna → Gamification Platform (data feed):** Sahatna's *Demographic Data Service* and
   *Telemetry Streaming Service* **serve** the platform's **Cohort Planning** function. The platform
   **receives** demographic + telemetry data and **does cohort planning** on it.
2. **Malaffi also does cohort/segmentation/eligibility:** Malaffi owns clinical data and runs its own
   **Clinical Cohort, Segmentation & Eligibility** function — exposed as the *Clinical Cohort &
   Segmentation Service*, which also **serves** the platform's Cohort Planning (clinical cohorts).
3. **Platform queries membership/eligibility from Malaffi:** the platform's **Eligibility Evaluation**
   function consumes Malaffi's *Membership & Eligibility Service* (Serving) — i.e. the yes/no at
   enrolment, where it depends on clinical eligibility and HIE membership, is resolved by Malaffi.

So cohort/eligibility is **shared**: the platform plans cohorts on Sahatna's demographic+telemetry
data; Malaffi plans clinical cohorts and is the authority for membership + clinical eligibility.

## ArchiMate relationships used

- **Assignment** — Actor performs Function (Sahatna→Demographic&Telemetry Mgmt, Platform→Cohort
  Planning/Eligibility, Malaffi→Clinical Cohort…).
- **Realization** — Function realizes Service (the offered services above).
- **Serving** — provider Service serves consumer Function (Sahatna/Malaffi services → platform
  Cohort Planning / Eligibility Evaluation).
- **Access** — Function reads/writes a data object (owner writes; platform Cohort Planning reads
  demographic + telemetry).

## Impact on earlier deliverables

- **Member Journey (view 06):** the three data objects now appear in the passive lane; *Compute
  Features* / *Define Cohort* Access demographic, telemetry and (via Malaffi) clinical data; *Verify
  Activity* Accesses telemetry; *Evaluate Eligibility* is where the Malaffi membership/eligibility
  query lands.
- **Capability map (view 05):** the *Cohort Identification & Segmentation* capability is now
  understood as **shared** with Malaffi (clinical) — the platform owns demographic/telemetry cohorting;
  Malaffi owns clinical cohorting + the membership/eligibility authority.
- **Motivation (gaps #8/#9):** confirms the ADHICS special-category handling and data-residency /
  minimal-PII constraints — clinical data stays under Malaffi (HIE); the platform consumes a service,
  it does not own or copy clinical data.

## Enhancements — corrected terminology (supersedes the above where they differ; see `18-eligibility-terminology-analysis.md`)

**Two more actors at design-time** (beyond Sahatna / Platform / Malaffi):
- **DoH** — *defines the features* a cohort is built from. Not the platform.
- **Clinical Team** — *builds the clinical segment* (`segment_id` + membership) and **stores it on
  Malaffi**. The platform never holds clinical membership.

**Sahatna owns two things:** the **member channel/BFF** and the **demographic+telemetry data source**.
Challenge *content* is **no longer Sahatna's** — it moved to the Challenge service (see below); Sahatna
is now a **thin renderer** of platform-supplied localized content.

**Segment build + membership live with the data owner (by data type):**
| Segment type | Built by | stored | Membership at eligibility |
|---|---|---|---|
| **Clinical** | Clinical Team | **Malaffi (external)** | queried per-user (scoped) — never bulk-loaded |
| **Demographic / Telemetry** | **Platform (`cohort-svc`, local)** | **Platform (local)** | local check |

**Malaffi is two APIs, not one:** **Segment-metadata** (authoring, no membership) + **scoped
Membership-query** (eligibility — "of these active `segment_id`s, which is X in" — data minimisation, c9).

**Challenge has one owner:** the **Challenge service** owns both the **definition**
(`challenge_id↔segment_id↔ScoringPlan`, frozen) **and** the **localized content (AR/EN)** — no CMS.
Eligibility returns **`challenge_id`s**; the **Challenge service hydrates** them to *localized published*
content (`Accept-Language`) and the BFF returns them for Sahatna to render.

**Enrolment = a subscription:** the enrolment record (user × challenge) arms the platform to listen for
that user's telemetry and score it within that challenge; multiple concurrent.

**Corrects the table above:** "Membership & Eligibility Service" → the **two Malaffi APIs**; platform
**Cohort Planning** is **LOCAL** segmentation only (clinical cohorting is external); "Evaluate
Eligibility" → *platform returns challenge_ids → Challenge service hydrates localized content*.

## Enhancement — Notifications & consent propagation (Sahatna-owned delivery)
**Sahatna owns the end-user experience.** It exposes a **Notifications API** (a new C4 component
`Sahatna Notifications API`, in the Sahatna/BFF zone, fronted by APIM). The gamification platform never
delivers to the citizen directly:
- **`NUDGE-SVC` (platform)** has no channels of its own. On a notification-worthy event (streak-at-risk,
  points credited, voucher issued, redemption uncertain) it *composes* a request and **calls the Sahatna
  Notifications API via APIM**. Sahatna then owns the actual push/email/SMS/in-app delivery and its UX.
- **Consent propagates Sahatna → platform.** Notify-consent (and per-channel preferences) is captured at
  Sahatna (enrolment T&C / preferences) and **propagated down to `CONS-SVC`**. `NUDGE-SVC` **checks
  `CONS-SVC` before creating any notification** — no consent (or channel off) ⇒ suppressed, nothing sent.
- **Ownership:** delivery + channel state + citizen UX = **Sahatna**; notify-consent record (propagated)
  + the compose/consent-gate decision = **platform** (`CONS-SVC` + `NUDGE-SVC`). Direction: consent flows
  down, notifications flow back up through Sahatna. Behaviour captured in `19-...` §7 + §2b.
