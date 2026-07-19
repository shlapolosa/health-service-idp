# Session Journey — Ground-up ArchiMate analysis of the Wellness Gamification platform

> **Why we did this:** to reverse-engineer a complex solution document into a rigorous, layered
> architecture — and from that, distil the *reasoning discipline* that should refine the **dev-agent
> prompt** (how it goes from a REQUIREMENTS spec → architecture → OAM/code).

## What we built (all in `factory/docs/analysis/wellness-archimate/`)

| Phase | Artifact | Result |
|---|---|---|
| Extract | `00-business-requirements-and-rules.md` + partials | **114 business requirements + 139 rules**, 8 load-bearing invariants, each tagged with an ArchiMate type + source-line trace |
| Vocabulary | `01-archimate-reference.md` | pinned ArchiMate 3.1 element + relationship set |
| Decompose | `02-structural-elements.md` | S-V-O parse → **41 active / 78 behaviour / 63 passive** elements |
| Gaps | `04-gaps-and-recommendations.md` | **49 gaps** (parallel functional + NFR/compliance review); folded #4/#7/#8/#9 (AML/SVF, PDPL rights, ADHICS, data-residency) |
| Motivation/Strategy | `motivation-strategy.archimate.xml` (+ `03-…md`) | 99→102 elements, 154→160 rels; **lifted solution language out of the motivation layer** (e.g. "OLAP/OLTP seam (CDC+reverse-ETL)" → "Separate analytical insight from operational delivery") |
| Capability realization | `business-capability-realization.archimate.xml` (+ `05-…md`) | **12 capabilities → 27 services → 30 functions** (multi-service per capability) |
| Business process | `business-process-cooperation.archimate.xml` (+ `06-…md`) | 4 views: member journey, partner lifecycle, cross-org data cooperation, detailed platform flow; active/behaviour/passive separation, left-to-right value chains, business colours, staggered routing |
| Data ownership | `07-data-ownership-and-actors.md` | **3 actors** (Sahatna mobile app/channel, Gamification Platform engine, Malaffi HIE black box) × **3 data types** (demographic+telemetry = Sahatna, clinical = Malaffi); the local-vs-Malaffi eligibility branch rule |
| Application | `application-layer.archimate.xml` (+ `08-`,`09-…md`) | **6 views**, full ArchiMate symbol set (component/collaboration/interface/function/interaction/process/service/event/data object); **8/8 business functions covered**; eligibility view reworked clean (interfaces on consumption paths). *Still finishing layout on 5 views.* |

## What we learned (the reusable reasoning discipline)

1. **Layer top-down, abstract upward.** Requirements/Rules → Motivation (why) → Strategy (capabilities) →
   Business (services/functions/processes) → Application (components/services/interfaces/data) →
   Technology (OAM). Each layer is **technology-agnostic relative to the one below** — solution detail
   must not leak up (we repeatedly stripped CDC/Kafka/two-phase/idempotency from the business/motivation).
2. **Separate the three ArchiMate aspects everywhere** — Active structure (who: actors/roles/components),
   Behaviour (what: services/processes/functions/interactions/events), Passive (data: objects).
   Use the right relationship: Assignment (performs), Realization (concretises), Serving (offers to),
   Composition (whole-part), Access (read/write), Triggering (sequence), Flow (cross-boundary).
3. **Distinguish service vs function vs process vs interface.** Service = external offer; Function =
   capability grouping; Process = time-ordered flow; **Interface = the access point every cross-boundary
   call must go through.** Don't collapse them.
4. **System boundaries + data ownership are first-class.** Identify the actors/systems, who *owns* each
   data type, what's a black box (Malaffi: only its API + the answers behind it), and the exact
   integration rule (clinical → Malaffi; demographic/telemetry → local).
5. **Coverage is a checkable invariant.** Every capability → realized by ≥1 service; every business
   function → served by an application service realized by a component. We verified this programmatically
   (caught Programme Conclusion, Partner Lifecycle, and 3 seam-only functions and filled them).
6. **Gaps are found by adversarial parallel review**, not single-pass — functional and NFR/compliance
   reviewers in parallel surfaced 49 gaps a single read would miss.

## → For the dev-agent prompt

The dev-agent should not jump straight from a REQUIREMENTS.md to code. The discipline above is the
spec it should follow: **(a)** extract requirements + rules + invariants; **(b)** derive capabilities
and business services/functions; **(c)** identify system boundaries, data ownership, and external
black-box APIs; **(d)** define application components, the services they realize, the interfaces every
call goes through, and the data each ingests/produces; **(e)** map each component to an OAM component
type; **(f)** prove coverage (every requirement → capability → service → component) before emitting.
The OAM (`wellness-gamification-example.yaml`) is the Technology-layer realization of step (d–e).

## Open / next

- Finish the Application-layer layouts (5 views) — clean left-to-right layering, interfaces on every
  consumption path, staggered routing (eligibility view is the template).
- Phase 5 — **Technology**: realize the application components onto OAM component types
  (webservice / realtime-platform / analytics-platform / postgresql / realtime-service / auth0-idp /
  graphql-gateway).
- Then: turn this discipline into the refined dev-agent prompt.
