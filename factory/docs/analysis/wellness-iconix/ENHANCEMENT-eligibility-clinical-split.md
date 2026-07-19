# Enhancement — Eligibility: separate Clinical (Malaffi) vs Local eligibility

> Fixes a real gap: runtime eligibility currently reads **all** attributes (incl. `conditions`/PoD) from the
> **local** Member profile (membership-db) and never queries Malaffi — inconsistent with the C4 (`eligibility-svc →
> Malaffi` ACL edge), the use cases (Malaffi = source of conditions/PoD), and the agreed model (clinical membership
> **stays on Malaffi**, queried per-user; "conditions" is dual-source). Apply across domain + robustness + both
> sequence levels. Naming must match the C4. **Mermaid hygiene:** no `;` in messages (use `,`), capital `Note`,
> balanced `alt/opt/loop … end`, no stray fences/tags.

## Domain (`02-domain-model.md`)
- Make `Segment` abstract; add two specializations (tag "(added in eligibility clinical-split)"):
  - **`LocalSegment`** — demographic (age/gender/district) + telemetry/local accessibility. Membership evaluated
    against the platform `Member` profile (membership-db).
  - **`ClinicalSegment`** — conditions / PoD(accessibility). Membership **lives on Malaffi**; resolved per-user via a
    **scoped membership query** (ACL, no bulk copy). Author-time it is validated via Malaffi segment *metadata* (E1).
- `EligibilitySnapshot` gains a frozen field: the **point-in-time clinical-membership result** (so locked eligibility
  is independent of later Malaffi changes). Relate `EligibilitySnapshot → ClinicalSegment` (frozen membership).

## Eligibility evaluation (control logic — robustness + sequences)
- `EligibilityEvaluator` **branches** per the candidate rule's required segments:
  - **Local segments** → match against the member profile read from `enrolment-svc`/`membership-db`.
  - **Clinical segments** → `eligibility-svc` calls **Malaffi via an anti-corruption layer** (`MalaffiAdapter` /
    ACL): `getScopedMembership(memberId, clinicalSegmentIds)` — scoped to the active clinical segment ids only
    (data minimisation), **no membership is copied/stored** locally.
  - Eligible **iff** the member matches **all** required LOCAL segments (profile) **AND** all required CLINICAL
    segments (Malaffi membership), plus whitelist gating (UC-B2).
- Robustness: add boundary→control→entity for the clinical path — control `ClinicalMembershipResolver` (+ the
  `MalaffiAdapter` ACL boundary to the external Malaffi actor); entity `ClinicalSegment`/`LocalSegment`.

## Snapshot freeze (the snapshot rationale)
- At enrollment (UC-B3), `snapshotEligibility` **re-queries Malaffi scoped membership** for the challenge's clinical
  segments and **freezes the result inside the immutable `EligibilitySnapshot`** alongside the local match — so a
  participant's eligibility is pinned point-in-time and unaffected by later Malaffi/profile changes. This is a
  concrete reason the snapshot exists.

## Files to edit
- `02-domain-model.md` (Segment split + snapshot frozen clinical field)
- `03-robustness/eligibility.md` (clinical branch: MalaffiAdapter boundary, ClinicalMembershipResolver control, ClinicalSegment/LocalSegment entities)
- `04-sequences/eligibility.md` (low-level: clinical-membership query branch + snapshot freezes clinical membership)
- `architecture/sequences/eligibility.md` (high-level: add `Malaffi (clinical · scoped membership ACL)` participant;
  clinical branch on discovery + snapshot; **fix the header note** that currently claims "no external-ACL legs" —
  eligibility now has a clinical ACL leg to Malaffi; update the cross-context summary table)
- `02-logic-bounded-contexts.md` (C2 eligibility-svc: note the Malaffi ACL / scoped-membership runtime query)

## Naming (match C4 `solution-c4.drawio`)
`eligibility-svc`, `Malaffi` (external, clinical · scoped membership, ACL), `eligibility-cache`, `membership-db`,
`challenge-svc`/`challenge-db`, `enrolment-svc`, `domain-event-log`. Keep all existing journeys, UC traces and the
B1.1 / B3.1 create-only guards.
