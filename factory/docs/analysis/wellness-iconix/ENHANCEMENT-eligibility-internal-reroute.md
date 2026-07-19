# Enhancement — Eligibility is internal (supporting read-model); discovery is published by Challenge

> Per the DDD aggregate analysis (`architecture/DDD-aggregate-analysis.md`): `eligibility-svc` owns **no aggregate** —
> `CohortScope` is a rebuildable **read model**, and its output is *a filtered view of Challenge*. It is therefore a
> **supporting service (read model + Malaffi clinical ACL)** with **no external surface**. Re-route so the citizen
> never calls it directly. Apply across the eligibility sequences (both levels), robustness, the logic context, and the C4.
> **Mermaid hygiene:** no `;` in messages (use `,`); capital `Note`; balanced `alt/opt/loop … end`; no stray fences/tags.
> Do **not** hand-edit participant chips — they are recomputed deterministically after this change.

## The re-route
- **Discovery — "get challenges" — front door = `challenge-svc`.** The citizen path becomes
  `Mobile App → APIM-north → Mobile BFF → APIM-south → **challenge-svc** (getEligibleChallenges) → (internal) **eligibility-svc**.resolveVisibility()`
  which consults the local-segment store + **Malaffi clinical ACL**, returns the visible set to `challenge-svc`, and
  `challenge-svc` returns the filtered challenges to the app. **`eligibility-svc` has NO inbound from APIM-south.**
- **Snapshot at enrolment — front door = `enrolment-svc`** (already internal): `enrolment-svc → eligibility-svc.snapshotEligibility()`
  → Malaffi scoped membership, frozen in the EligibilitySnapshot. Keep as-is.
- Keep the clinical-vs-local split, the Malaffi scoped-membership query, the snapshot clinical-freeze, and the
  B1.1 (create-only visible set) / B3.1 (immutable snapshot) guards intact — only the **entry point** changes.

## Files & edits
- `architecture/sequences/eligibility.md` — **Journey 1 (Discovery):** insert `challenge-svc` as the front door between
  `APIM-south` and `eligibility-svc` (`APS → challenge-svc → eligibility-svc`); eligibility-svc no longer receives from
  APIM-south; challenge-svc returns the filtered challenges back out. **Journey 2 (Snapshot):** unchanged (already
  `enrolment-svc → eligibility-svc`). **Header + cross-context summary:** state eligibility-svc is an **internal supporting
  service (read-model + Malaffi ACL), not a citizen front door**; discovery is **published by Challenge**.
- `04-sequences/eligibility.md` — reflect that the discovery **entry boundary belongs to Challenge** (a get-challenges
  endpoint); `EligibilityEvaluator` is invoked **internally** by the Challenge discovery controller, not via a directly-
  exposed Eligibility API. Snapshot path unchanged.
- `03-robustness/eligibility.md` — the discovery boundary is a **Challenge discovery** boundary (not an Eligibility API
  exposed to the actor); eligibility resolution objects are **internal controls** reached from Challenge. Keep the clinical
  branch (MalaffiAdapter ACL, ClinicalMembershipResolver) — only re-home the entry.
- `architecture/02-logic-bounded-contexts.md` — **C2 Eligibility & Audience:** re-label as a **Supporting service
  (read model + Malaffi ACL) — NOT externally exposed**. Published use cases: **none external**; consumed internally by
  **Challenge** (discovery) and **Enrolment** (snapshot). Note CohortScope is a projection (no SoR). Add a one-line
  "exposure" note: read models are consulted internally and surfaced through the owning context's contract.

## Resulting chips (recomputed deterministically, do not hand-edit)
- Discovery: `challenge-svc` **🟥** (now receives the citizen request from APIM-south); `eligibility-svc` **🟦** (inbound is a
  peer call from challenge-svc → no red; still calls Malaffi → blue).
- Snapshot: `enrolment-svc` **🟥**; `eligibility-svc` **🟦**.
- Net: `eligibility-svc` is **🟦-only everywhere** (never a front door).

## C4 (`solution-c4.drawio`) — handled separately
Replace the `APIM-south → eligibility-svc` edge with `challenge-svc → eligibility-svc` (discovery, internal); add
`enrolment-svc → eligibility-svc` (snapshot, internal); keep `eligibility-svc → Malaffi` (ACL).
