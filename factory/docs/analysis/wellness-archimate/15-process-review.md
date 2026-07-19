# Process Review — Requirements → OAM (end-to-end, detailed)

> A critical retrospective of the method we used to take a solution document all the way to a deployable
> OAM Application, what each step produced, the decisions/corrections that shaped the method, and an
> honest assessment of where the process is strong, where it leaks, and what to change.

---

## 1. The pipeline (what we actually did, in order)

| # | Phase | Input | Method | Output artifact(s) | Load-bearing decision/correction |
|---|---|---|---|---|---|
| 1 | **Extract** | `wellness…docx` | python-docx pull → parallel sub-agents catalogue every requirement/rule with a source-line trace, tag each with an ArchiMate type | `00-business-requirements-and-rules.md` (+ partials): **114 BRs, 139 rules, 8 invariants** | Treat the 8 *load-bearing invariants* as the spine — everything downstream traces to them |
| 2 | **Vocabulary** | ArchiMate 3.1 cheat-sheet | pin the element + relationship set so later layers are consistent | `01-archimate-reference.md` | Relationship semantics fixed up front (Assignment/Realization/Serving/Access/Triggering/Composition) |
| 3 | **Decompose** | the catalogue | subject–verb–object parse of every sentence → active / behaviour / passive | `02-structural-elements.md`: **41 active / 78 behaviour / 63 passive** | The 3-aspect split is the unit of all later modelling |
| 4 | **Gaps (adversarial)** | catalogue | two parallel reviewers — functional + NFR/compliance | `04-gaps-and-recommendations.md`: **49 gaps** | Folded #4/#7/#8/#9 (AML/SVF, PDPL rights, ADHICS, residency) back into the model |
| 5 | **Motivation + Strategy** | catalogue + gaps | model Goals/Outcomes/Requirements/Constraints/Principles + Capabilities/CoA/Resources/ValueStream; lay out via the engine | `motivation-strategy.archimate.xml`, `03-…md` | **Correction: solution leakage** — "OLAP/OLTP seam (CDC+reverse-ETL)" rephrased to "Separate analytical insight from operational delivery". Courses of Action wired to the Requirements/Capabilities they realize |
| 6 | **Business — Capability Realization** | strategy capabilities | Capability → Service → Function (multi-service per capability) | `business-capability-realization.archimate.xml`, `05-…md`: **12 caps → 27 svcs → 30 fns** | Distinguish *service vs function* explicitly |
| 7 | **Business — Process Cooperation** | functions | value-chain views, active/behaviour/passive lanes, left-to-right | `business-process-cooperation.archimate.xml`, `06-…md` | **Correction: Assignment, not composition** for role→process; composition shown by *nesting*; business colour discipline |
| 8 | **Data ownership** | the doc | 3 actors × 3 data types + the local-vs-Malaffi branch rule | `07-data-ownership-and-actors.md` | Malaffi = black box (API only); demographic/telemetry = Sahatna; clinical = Malaffi |
| 9 | **Application** | business + data | 6 views (cooperation, eligibility, earn&redeem, partner, authoring, seam), full symbol set, system boundaries, interfaces on every call path | `application-layer.archimate.xml`, `08/09-…md` | **8/8 business functions covered** (verified programmatically); interface-on-consumption-path rule |
| 10 | **Layout engine** | messy views | consolidate hand-fixes into a ruleset → build an engine → run views through it | `10-layout-ruleset.md`, `~/.claude/skills/archimate-view/` (engine + skill), `archi_layout.py` | Layout as **invariants H1–H5** (no overlap / no edge-over-element / min length / serving-up / no shared lane) — build fails if violated |
| 11 | **Technology** | application | ABB (architecture) then SBB (solution realization) | `technology-layer.archimate.xml`, `11-…md` | **Correction: ABB not SBB** — first draft named products/OAM types as the architecture; redone as product-agnostic ABBs + a separate SBB-realizes-ABB view (TOGAF) |
| 12 | **Solution (C4)** | SBBs | banded trust-zone draw.io diagram-as-code, junctions, A* orthogonal router | `solution-architecture.drawio`, `gen_solution_drawio.py`, `12-…md` | Routing as invariants: orthogonal, no box-crossing, no trunk, vertical-stub rule, symmetric junction combs |
| 13 | **OAM** | solution SBBs | one OAM Application referencing real catalog CDs | `wellness-platform-oam.yaml`, `13-…md`: **17 components / 7 types** | `auth0-idp` as the *equivalent* for UAE Pass + Entra (ABB→SBB swap-without-rewiring) |
| 14 | **Coverage** | OAM vs motivation/business | trace every goal/outcome/requirement/CoA/invariant to a component | `14-oam-coverage-analysis.md` | **Found 3 missing components** (cohort, verification, malaffi) + a class of invariants OAM can't express |

---

## 2. The discipline that emerged (the reusable method)

1. **Layer top-down, abstract upward.** Each layer is technology-agnostic relative to the one below;
   solution detail must not leak up (we stripped it repeatedly — steps 5, 11).
2. **Three aspects, right relationship.** Active/behaviour/passive everywhere; Assignment performs,
   Realization concretises, Serving offers, Composition = nesting, Access read/writes, Triggering
   sequences.
3. **Distinguish service / function / process / interface.** A service is the offer; a function groups
   capability; a process is time-ordered; an interface is the access point every cross-boundary call
   goes through.
4. **ABB before SBB** (TOGAF). The architecture states *what capability* is required; the product/OAM
   type is the *solution* that realizes it, in a separate view. Products swap without rewiring.
5. **Coverage is a checkable invariant.** Every capability realized by ≥1 service; every business
   function served by a component; every requirement traceable to a component.
6. **Make the artifact self-checking.** Layout (H1–H5) and coverage both gated programmatically rather
   than eyeballed.
7. **Gaps come from adversarial parallel review**, not a single pass.

---

## 3. The traceability chain (one example, end-to-end)
`RULE-110/103 "only validated activity scores"` → **inv #3 verified-signal gate** → driver/assessment →
**Goal g3 reproducible scoring** + **Outcome o7** → **Requirement r3** → **CoA coa6 inline fraud+verify** →
**Capability cap4 Activity & Clinical Verification** → Business *Verification Service* / *Activity
Verification* function → Application *Verification Service* component (authoring·verification view) →
Technology ABB *Container Workload Runtime* (+ Event Streaming) → SBB *Knative + webservice* →
**OAM: `verification-svc`** … **which is MISSING** (caught at step 14).

That single broken link is the most important output of the whole exercise: the chain is only as good
as its weakest trace, and the method *found* the break — but only at the end (see §5).

---

## 4. What worked (strengths)

- **Top-down, technology-agnostic layering held.** Every time solution detail crept up, the layer
  discipline caught it (motivation rephrase; ABB/SBB redo). The upper layers are genuinely
  implementation-independent.
- **Self-checking artifacts.** Layout H1–H5 and the 8/8 application coverage check turned "looks right"
  into "provably right / build fails". This is the single biggest quality lever.
- **Adversarial gap analysis** (parallel functional + compliance) surfaced 49 gaps a single read misses.
- **Honest coverage verdict.** The process did not hand-wave OAM coverage — it found and named the
  missing cohort/verification/malaffi components and the invariants OAM can't express.
- **Reusable tooling fell out of the work.** The `archimate-view` engine/skill and the draw.io generator
  are now general assets, not one-offs.
- **ABB/SBB separation paid off concretely** — the UAE-Pass/Entra → auth0-idp swap is one line, every
  other binding unchanged.

## 5. Where it leaked (weaknesses / risks — empirical)

1. **Coverage was checked at the *end*, not continuously.** The OAM dropped Cohort & Verification and
   nobody noticed until step 14. A traceability matrix maintained *from step 1*, re-checked at every
   layer transition, would have flagged it the moment the OAM was authored. **This is the top fix.**
2. **The hardest, most important content — the 8 behaviour invariants — does not propagate past
   Technology.** They are stated beautifully in steps 1/5 and then *cannot* be expressed in OAM. The
   process produced them but left no mechanism to carry them into code/config as acceptance criteria.
   They are exactly what gets lost in "throw it over the wall to the developer."
3. **Disproportionate effort on diagram aesthetics.** Many turns went to layout/routing polish
   (trunking, junctions, edge-hugging). It produced a genuinely reusable engine — but the *architecture*
   substance (e.g. the missing components) got less scrutiny than the pixels. Self-checking layout should
   have been built once, early, then left alone.
4. **Extraction fidelity is unverified.** The motivation/business element lists are my interpretation of
   the docx + sub-agent extraction. There is no round-trip check that the model faithfully represents the
   source (e.g. no "every RULE-xxx appears in ≥1 element" assertion).
5. **Two application views (Cooperation, Earn&Redeem) never reached clean.** Accepted as "dense by
   nature", but it means the engine doesn't yet handle containment-overview and branching-flow views —
   a known limitation, not a solved problem.
6. **Single-threaded human-in-the-loop.** Each correction (leakage, Assignment, ABB/SBB, layout) came
   from the user catching it. The process has no *automated* guard for "is this solution leakage?" or
   "is this an ABB or an SBB?" — those are still taste/expertise calls.

## 6. What to change (and feed into the dev-agent)

1. **Make coverage a continuous invariant.** A live `traceability.md`/matrix from step 1: requirement →
   invariant → goal/outcome → CoA → capability → business service/function → app component → tech ABB →
   SBB → OAM component. Re-run the completeness check at **every** layer boundary; fail loudly on a break.
2. **Carry invariants as acceptance criteria, not prose.** Each of the 8 invariants becomes an explicit,
   testable line in the `REQUIREMENTS.md` that travels into the service monorepo (the platform already
   supports this via SPEC-1). The OAM provisions structure; this file provisions *behaviour*.
3. **Separate the two deliverables explicitly per service:** (a) the OAM/structure, (b) the
   behaviour-invariant checklist + config (retention, residency, AML thresholds, reservation/holdback
   numbers). The dev-agent owns (b); the platform won't enforce it.
4. **Encode the upper-layer guards.** "No solution leakage", "ABB before SBB", "Assignment not
   composition", "coverage holds" become *gates* the agent self-checks, mirroring how layout became H1–H5.
5. **Build the self-checking layout once, early.** The `archimate-view` engine now exists; use it from
   the first diagram so aesthetics never again consume the substantive review budget.
6. **Add an extraction round-trip check.** Assert every source RULE/BR id is referenced by ≥1 model
   element; report orphans both ways.

## 7. One-line verdict
The method is **sound and, crucially, self-correcting** — its best feature is that it *finds its own
gaps* (49 in review, 3 missing components, the un-enforceable invariants). Its weakness is **timing and
propagation**: coverage was verified too late, and the behaviour invariants — the part the platform can't
enforce and the part that matters most — currently die at the Technology layer instead of travelling into
the code. Fixing *those two things* (continuous traceability + invariants-as-acceptance-criteria) is the
core of the refined dev-agent brief this whole exercise was building toward.
