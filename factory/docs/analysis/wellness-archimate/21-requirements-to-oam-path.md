# Requirements → OAM — the full path we took

End-to-end methodology for the UAE wellness-gamification platform ("Sahatna Points", DoH-sponsored,
Malaffi HIE for clinical data), from raw requirements to a deployable OAM Application and an editable,
animated solution-architecture diagram. Each stage names its **input → method → output artifact**.

## Stage 0 — Source & extraction
- **In:** the raw brief (`wellness_doc.txt`).
- **Method:** extract every statement into stable IDs — **114 BRs + 139 RULEs**, with source-line
  provenance and ArchiMate-layer tags; 8 load-bearing invariants each cite specific RULE IDs.
- **Out:** the extraction (BR/RULE inventory) — the spine everything else traces back to.

## Stage 1 — Motivation & Strategy
- **In:** the BR/RULE inventory.
- **Method:** abstract slices into **requirements r1–r15**, **constraints c1–c10**, goals/outcomes, and
  **courses of action coa1–coa8**; map each requirement to a course of action.
- **Out:** `03-motivation-strategy-view.md` (+ `gen_motivation_strategy.py`).

## Stage 2 — Business layer (capabilities + processes)
- **In:** strategy.
- **Method:** **12 capabilities (cap1–cap12)** → 27 services → 30 functions; enumerate the business
  processes and their cooperation; capability-realization view.
- **Out:** `05-business-capability-realization.md`, `06-business-process-cooperation.md`.

## Stage 3 — Data ownership & actors
- **In:** business layer.
- **Method:** who owns what data, which actors act (Member, Admin, DoH, Partner, Clinical Team), the
  two Malaffi APIs (segment-metadata vs scoped membership), consent/notification ownership.
- **Out:** `07-data-ownership-and-actors.md`.

## Stage 4 — Application layer
- **In:** capabilities + processes.
- **Method:** business functions → **application components** (consolidating GOAL/STREAK/TITLE/BADGE →
  Scoring & Recognition, etc.); cooperation + eligibility views, laid out via the archimate-view engine.
- **Out:** `08-application-layer.md`, `09-application-landscape-design.md`, `application-layer.archimate.xml`.

## Stage 5 — Technology layer (ABB vs SBB)
- **In:** application components.
- **Method:** separate **Architecture Building Blocks** (capabilities the layers define) from **Solution
  Building Blocks** (the catalog ComponentDefinitions that realize them) — `auth0-idp` as the IdP SBB for
  UAE Pass/Entra, same `-conn` shape.
- **Out:** `11-technology-view.md` (+ the [[feedback-abb-not-sbb]] principle).

## Stage 6 — Solution architecture (C4)
- **In:** ABB→SBB mapping.
- **Method:** a **banded C4 container diagram** — full-width trust-zone bands (client · gateways · BFF ·
  engine · value · persistence · external · platform · cross-cutting), typed connectors.
- **Out:** `12-solution-architecture.md` + `solution-architecture.drawio` (`gen_solution_drawio.py`).

## Stage 7 — OAM Application (the deployable)
- **In:** the solution C4.
- **Method:** each SBB → a **real catalog ComponentDefinition** (`webservice`, `postgresql`,
  `realtime-platform`, `analytics-platform`, `realtime-service`, `graphql-gateway`, `auth0-idp`); bindings
  encode the architecture (`database:`, `realtime:`, `identity:`, `expose-api`, monorepo `repository:`).
- **Out:** `wellness-platform-oam.yaml` + `13-oam-application.md`.

## Stage 8 — Coverage & traceability (gap closure)
- **In:** the OAM vs every upstream layer.
- **Method:** a **1-by-1 replay** of the pipeline checking forward (nothing dropped) + backward (no
  orphans) at each transition. Found the single break at **Application→OAM**: 3 silent drops.
- **Fix:** added **`cohort-svc`** (local segmentation), **`verification-svc`** (verified-signal gate,
  inv-3), **`malaffi-adapter`** (segment-metadata + scoped membership) → closed the break.
- **Out:** `14-oam-coverage-analysis.md`, `15-process-review.md`, `16-traceability-matrix.md`.

## Stage 9 — Behaviour + terminology correction
- **In:** the corrected component set.
- **Method:** first an authoritative **terminology correction** (Feature vs Segment vs Cohort; clinical
  segments on Malaffi; challenge Definition + localized Content both owned by the Challenge service (no
  CMS); eligibility returns challenge_ids → Challenge service hydrates localized content; enrolment = a
  telemetry scoring subscription) — *before* touching artifacts. Then a
  **master journey** (lifecycle glued by frozen state + Event-Hub events) + **detailed runtime sequences**
  using only C4 components + actors (two-way audited). Later: notifications (Sahatna-owned, consent-gated),
  wearable telemetry (Health Connect SDK → Wearable Service → Event Hub).
- **Out:** `18-eligibility-terminology-analysis.md`, `17-behaviour-master-journey.md` (merged into)
  `19-behaviour-detailed-sequences.md`, `master-journey.mmd`.

## Stage 10 — Async eventing & B2B security
- **In:** the behaviour.
- **Method:** who owns the Event Hub (platform-owned spine), the B2B Entra construct (Sahatna app-reg →
  client-credentials → platform APIM token), per-topic publisher/subscriber table, `telemetry-ingest`.
- **Out:** `20-async-eventing-and-b2b-security.md` + topic set reflected into the OAM `event-spine`.

## Stage 11 — Visualization engineering (the diagram)
- **In:** the solution model (`c4-data.json`).
- **Method:** evolved the renderer for clarity — **banded barycenter layout + channel router** (side-gutter
  buses), **dotted system & trust boundaries**, **per-band security context**, **descriptions**, **animated
  async** (`flowAnimation`); empirically proved ELK/Graphviz can't do swimlanes via config; output as
  **editable draw.io** + animated SVG.
- **Out:** `solution-architecture-elk.drawio` / `.svg` / `-animated.svg` (`gen_band_svg.py`,
  `gen_band_drawio.py`); the reusable capabilities **ported into the `drawio-c4` skill** (banded mode).

## The through-line
Raw brief → IDs → r/c/coa → capabilities/processes → application components → ABB/SBB → C4 →
**OAM** (gap-closed, traceable) → behaviour (terminology-correct, audited) → async/B2B → an editable,
animated diagram. The OAM provisions the *runtime substrate*; the load-bearing **invariants** (frozen-on-
publish, verified-signal gate, financial-grade wallet, redemption/settlement discipline, residency/AML)
are **implementation + config obligations** carried in each service's `REQUIREMENTS.md`, not the manifest.
