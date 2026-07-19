# Eligibility & Cohort — Terminology Analysis (pre-change)

> **UPDATE (CMS removed):** challenge *content* is no longer owned by a Sahatna CMS. The **Challenge
> service owns both the definition AND the localized content (AR/EN)**; it hydrates eligible
> `challenge_id`s to *localized published* content, and **Sahatna is a thin renderer**. Where the text
> below says "Sahatna CMS / Sahatna backend (CMS)", read "**Challenge service**". Steps 4 & 7 and the
> glossary are amended accordingly.

> Analysing the refined flow before touching any diagram. The key insight: **segment definition +
> membership live with the OWNER of the source data** (Clinical Team / Malaffi for clinical;
> the platform locally for demographic/telemetry), and **a challenge has two halves with two owners** —
> the *definition* (platform) and the *content* (Sahatna CMS). Several of our current labels are
> imprecise; corrected glossary + discrepancies below.

## 1. The corrected flow (stages, precise terms)
1. **Define features** — **DoH** defines the *features* a cohort is built from (clinical signals,
   demographic attributes, telemetry metrics).
2. **Build segment** —
   - *clinical*: the **Clinical Team** builds the **segment** and stores `segment_id` + **membership**
     **on the Malaffi/HIE side**. The platform never holds clinical membership.
   - *demographic / telemetry*: the **platform** builds + stores the segment **locally** (from
     Sahatna-ingested data).
3. **Author challenge** — **Admin** binds `challenge_id → segment_id` and attaches the **ScoringPlan /
   goals**. Needs **segment metadata** (a *different* Malaffi API) — **not membership** at this point.
4. **Publish** — Admin publishes the challenge in the admin portal; the **Challenge service freezes the
   definition AND the localized content (AR/EN)** together at a version. No CMS.
5. **Eligibility (login)** — **Sahatna** asks the **Gamification Platform**: "return the `challenge_id`s
   this user is eligible for."
6. **Membership query** — Platform asks **Malaffi** (the *membership* API): "which **segments** is user X
   a member of?" → `segment_id`s. Platform **maps segments → challenges** via its bindings → returns
   `challenge_id`s.
7. **Hydrate** — the **Challenge service** returns the **localized published** challenge *content* for
   those ids (`Accept-Language`, filtering to published); the BFF passes them to Sahatna to render.
8. **Enrol** — creates an **enrolment record** in the platform (user × challenge): it tells the platform
   to **listen for that user's telemetry and score it within that challenge**. A user may hold **multiple
   concurrent enrolments**.
9. **Demographic / telemetry path** — same shape, but membership build + query are **local** (no Malaffi).

## 2. Corrected glossary (the agreed vocabulary)
| Term | Meaning | Owner |
|---|---|---|
| **Feature** | a measurable criterion a cohort is built from | **DoH** defines |
| **Cohort** | the conceptual target population (a combination of features) | DoH/clinical intent |
| **Segment** | the *realised* cohort: `segment_id` + **membership** (resolved members) | **Clinical Team (Malaffi)** for clinical · **Platform (local)** for demographic/telemetry |
| **Segment metadata** | the segment's descriptor *without* membership (used to author) | Malaffi (clinical) / Platform (local) |
| **Membership** | the set of users in a segment (special-category if clinical, c9) | Malaffi (clinical, queried per-user) / Platform (local) |
| **Challenge — definition** | `challenge_id` ↔ `segment_id` + **ScoringPlan** + lifecycle/rules; frozen on publish | **Platform** |
| **Challenge — localized content** | presentation the member sees (copy, imagery, T&Cs), per locale (AR/EN) | **Challenge service** (rendered by Sahatna) |
| **ScoringPlan** | versioned scoring/goal definition bound into the challenge | Platform |
| **Eligibility** | for a user: which `challenge_id`s apply = (segments user is in) ▷ mapped via bindings | Platform resolves |
| **Enrolment record** | (user × challenge) subscription that scopes telemetry scoring to that challenge | Platform |

## 3. Where our current model's terminology is WRONG / imprecise
| # | Current model says | Correction |
|---|---|---|
| a | "Cohort Identification → **Compute Features**" (platform) | Feature **definition** is **DoH's**; the platform doesn't author features. Rename → *Define Features (DoH)*. |
| b | "**Cohort & Segmentation Service**" wholly in the platform | **Clinical** segment build + membership live with the **Clinical Team on Malaffi**; the platform builds **only local** (demographic/telemetry) segments. Split the capability by data type. |
| c | "Challenge → **bind eligibility**" | Precisely: **bind `challenge_id → segment_id`** + ScoringPlan; uses **segment metadata** (not membership). |
| d | "Challenge Service: authoring → **publish → present**" (platform owns presentation) | Platform owns the **definition**; **Sahatna CMS owns the content/presentation**. "Publish" = (platform freeze definition) + (Sahatna publish CMS). |
| e | Eligibility = platform "**compose & present** the eligible challenge list" | Platform returns **`challenge_id`s only**; **Sahatna CMS hydrates** to published content. Two responsibilities, two owners. |
| f | One Malaffi "**Membership & Eligibility Service**" | **Two** Malaffi APIs: **Segment-metadata** (authoring) + **Membership-query** (eligibility). (Plus a clinical-signal/verification API — separate concern.) |
| g | "Enrol · accept T&C · confirm" | The load-bearing semantic is the **enrolment record = a telemetry scoring subscription** scoped to (user, challenge); multiple concurrent. |
| h | Eligibility branch = "local membership check **else** Malaffi" | Correct, but: *clinical membership is never bulk-loaded* — it is **queried per-user** at eligibility; only **demographic/telemetry** membership is local/bulk. |

## 4. "Can the membership query be enhanced?" — yes
The naïve call "Malaffi, return **all** segments this user is a member of" **over-shares** clinical group
memberships to the platform (special-category data, c9; minimisation principle).

**Recommended enhancement — scoped membership query.** The platform already knows the set of `segment_id`s
that have **active, published challenges** (its bindings). So it asks Malaffi the *narrow* question:
> "Of `[segment_id S1 … Sn]`, which is user X a member of?"
returning only the intersection. Benefits: **data minimisation** (platform learns only memberships
relevant to active challenges), smaller payload, a clear **consent scope**, and it stays a clean per-user
call. This requires no new platform state — it already holds the active-challenge segment index.

Secondary (defer / optional): per-user membership **cache with short TTL** + Malaffi membership-change
**events** to invalidate (careful — eligibility sits on a money/credit path, so freshness matters);
**consent check** before any clinical membership query.

## 5. Actors & ownership the corrected flow surfaces (new/clarified)
- **DoH** — *feature definer* at design-time (was only modelled as sponsor / winner hand-off).
- **Clinical Team** — *clinical segment builder*, operating on the **Malaffi/HIE** side (new role).
- **Sahatna backend (CMS)** — *challenge content owner* (distinct from the Sahatna app/BFF).
- **Malaffi** — splits into **Segment-metadata API** + **Membership-query API** (+ clinical-signal API).
- **Gamification Platform** — owns the **Challenge Definition** (binding store `challenge_id↔segment_id↔ScoringPlan`), the **Enrolment/Subscription** records, and the **local** demographic/telemetry segments.

## 6. Net effect on the model (for confirmation, before I change anything)
- The eligibility view's single "Malaffi API / Membership & Eligibility Service" → **two interfaces**
  (segment-metadata + scoped-membership), and add a **clinical-signal** one if we model verification.
- The "Cohort & Segmentation" capability splits into **clinical (external, Malaffi/Clinical-Team)** vs
  **local (platform `cohort-svc`)** — and the missing `cohort-svc` from the traceability gap is now
  precisely scoped to the **local** path only.
- "Challenge" splits into **platform definition** vs **Sahatna CMS content** — the eligibility sequence
  becomes *platform returns ids → Sahatna CMS hydrates*.
- Enrolment is modelled as a **subscription** that arms telemetry scoring.

**Confirm the glossary in §2 and the corrections in §3**, and (a) whether to adopt the **scoped membership
query** (§4) as the design — then I'll fold it into the master journey and build the detailed
*Eligibility Determination* and *Challenge Authoring* runtime sequences with the corrected terminology.
