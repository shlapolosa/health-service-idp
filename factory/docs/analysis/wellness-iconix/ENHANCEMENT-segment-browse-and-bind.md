# Enhancement — Segment browse-and-bind at authoring (segmentation is a separate concern)

> Cohort identification, segmentation and membership resolution happen **separately from challenge authoring**.
> So the authoring admin cannot "send criteria to validate" — they **browse the segment catalogue and manually
> bind** the correct segment(s). Apply across challenge-authoring (both sequence levels), robustness, the domain
> model and the logic contexts. Naming matches the C4 and the Malaffi OpenAPI (`architecture/malaffi-api.openapi.yaml`).
> **Mermaid hygiene:** no `;` in messages (use `,`); capital `Note`; balanced `alt/opt/loop … end`; no stray fences/tags.
> **Preserve the existing chips** (`challenge-svc` 🟥, `eligibility-svc` 🟦) — do not strip or move them.

## The corrected author-time interaction (replaces `validateClinicalSegment(conditions)`)
1. **Segmentation is upstream & separate.** Clinical segments are defined/maintained on **Malaffi** (clinical team);
   local segments in a **platform local-segment store**. Built ahead of, and independently from, any challenge.
2. At the audience step the admin asks `eligibility-svc` (which owns the Malaffi ACL + local-segment store) to
   **`listSegments()`** → returns the **catalogue of segment descriptions** (`segmentId`, name, description,
   type = clinical|local) — **metadata only, no membership** (ACL → Malaffi `GET /clinical-segments`).
3. The admin **browses and manually selects** the segment(s) matching the intended audience and **binds** them.
4. `challenge-svc` stores **`segmentId` references** on the `EligibilityRule` — **not raw criteria**.
5. Validity is **implicit** (you can only bind from the live catalogue) — drop the separate "validate" call.
6. **Publish-time existence re-check** (Journey 3): `getSegment(id)` (ACL → Malaffi `GET /clinical-segments/{segmentId}`)
   to catch a segment retired between authoring and go-live; fail/flag publish if a bound segment is gone.
7. Runtime unchanged: membership resolved separately — local → profile, clinical → Malaffi
   `getScopedMembership(memberId, segmentIds)` (ACL → `POST /clinical-segment-membership/resolve`), frozen in the snapshot.

## Files to edit
- `architecture/sequences/challenge-authoring.md` — Journey 2: replace the `alt audience targets clinical conditions /
  validateClinicalSegment` block with a **browse-and-bind** exchange: `challenge-svc → eligibility-svc.listSegments()`,
  `eligibility-svc → Malaffi GET /clinical-segments` (clinical) + local store (local), catalogue back to the admin,
  admin selects, `challenge-svc` writes bound `segmentId` refs into the EligibilityRule. Journey 3: add a
  publish-time `getSegment(id)` existence re-check before go-live. Keep chips + layering intact.
- `04-sequences/challenge-authoring.md` — same at boundary/control/entity granularity (SegmentCatalogBrowser screen,
  controllers list/select/bind, EligibilityRule references Segment by id).
- `03-robustness/challenge-authoring.md` — add boundary **Segment Catalogue Browser** (admin), control
  **SegmentCatalogProvider** (lists via ACL) + **SegmentBindingController** (binds chosen ids); entity = `Segment`
  **referenced by id** (sourced externally), not authored here. Drop the `ClinicalSegmentValidator` (validation now implicit);
  add a `SegmentExistenceChecker` used at publish.
- `02-domain-model.md` — `Segment` (with `LocalSegment`/`ClinicalSegment`) is **owned by the segmentation concern, not
  `challenge-svc`**; `Challenge`/`EligibilityRule` holds a **reference (`segmentId`)**, not the criteria. Re-tag accordingly
  "(updated: segment referenced, segmentation is separate)". Keep existing classes.
- `architecture/02-logic-bounded-contexts.md` — C1 `challenge-svc`: Segment is **referenced not owned**; author-time =
  **browse `listSegments()` + bind**, not validate; publish-time existence re-check. Add a short **"Cohort & Segmentation
  (upstream / external)"** note: clinical segments + membership live on Malaffi; local segments in a platform local-segment
  store; cohort identification + membership resolution are a separate concern that authoring only **consumes**.

## ACL ↔ Malaffi mapping (DDD anti-corruption layer; ACL keeps GP vocabulary)
| GP ACL method | Malaffi operation (OpenAPI) |
|---|---|
| `listSegments()` | `GET /clinical-segments` (`listClinicalSegments`) |
| `getSegment(id)` | `GET /clinical-segments/{segmentId}` (`getClinicalSegment`) |
| `getScopedMembership(memberId, segmentIds)` | `POST /clinical-segment-membership/resolve` (`resolveClinicalMembership`) |
