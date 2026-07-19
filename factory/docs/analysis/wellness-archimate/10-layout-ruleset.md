# ArchiMate View Layout — Consolidated Ruleset (engine spec)

> Single source of truth for the layout engine. Every view is produced by feeding (elements, types,
> nesting, relationships) to the engine; these rules are encoded as **placement logic + invariants**,
> not applied by hand per view. Derived from the canonical ArchiMate Layered View reference
> (`Image #19`) plus all feedback this session.

## A. Vertical order (top → down)

A1. **Architectural domain banding** — *only when a view spans >1 domain*, stack domains in framework
order, top→down: **Motivation → Strategy → Business → Application → Technology → Implementation**.
A single-domain view has **no** domain bands.

A2. **Aspect bands within a domain** — rank by ArchiMate **aspect**, not by specific element type.
Default top→down: **Active structure → Behaviour → Passive structure**, applied *in combination with*
A4 (a served element sits above its server). A4 is primary (dependency direction); the aspect order is
the tiebreak when no Serving/Realization constrains the pair.
- Active = component, actor, role, collaboration, interface, node.
- Behaviour = service, process, function, interaction, event, course-of-action.
- Passive = data object, business object, artifact, representation, contract.

A3. **Sub-order inside the Behaviour band:** *services above processes/functions* (a service is the
exposed offer; the process/function realizes it).

A4. **Serving/Realization precedence (overrides A2 for the involved pair).** A Serving or Realization
relationship must point **upward**: the *served / realized* element sits **above** the one that
serves / realizes it. This is what lifts an externally-served actor (e.g. *Customer*) to the very top
and pushes realizing components (e.g. *ERP*) to the bottom — reproducing the reference. Aspect bands
(A2) are the default/tiebreak; dependency direction wins when the two conflict.

A5. **Passive always bottom**; cross-boundary **Flow/Access** to data routes in **stacked channels
below the lowest element row** (labelled), never between the working rows.

## B. Horizontal order & alignment (left → right)

B1. Within a row, read **left → right** following **Triggering/Flow** order (the value chain);
fall back to declared order, then barycenter sweeps to cut crossings.
B2. **Column alignment = barycenter.** Place each element at the mean-x of the partner(s) it
serves/realizes (and vice-versa) so cross-layer connectors are short and vertical.
B3. **Multiple realizers/servers of one target:** spread the group horizontally around the target's x;
the router **fans** connectors to **distinct anchor offsets** along the shared edge (one-to-many is
mirrored). No two connectors share an anchor point.

## C. Spacing, sizing, minimum lengths

C1. **No overlaps**, ever (hard invariant H1).
C2. **Min inter-layer vertical gap** large enough that every cross-layer connector ≥ `MIN_CONN` (≈48px).
C3. **Min sibling horizontal gap** (`HGAP` ≈ 70px) so adjacent boxes and their labels never touch.
C4. **Min connector length** `MIN_CONN` ≈ 48px and **min stub** `MIN_STUB` ≈ 24px straight off each
endpoint before the first bend — connectors are never stubby/illegible. Gap rules win over B2 if
alignment would violate this.
C5. **Centred composition** with uniform outer `MARGIN` (≈60px); each row centred within the widest row.

## D. Containers & nesting

D1. **Composition/Aggregation/Assignment-to-grouping shown by NESTING**, not a drawn line
(actor/role/collaboration boxes enclose the behaviours assigned to them; sub-groups nest, e.g.
*Production Unit ⊃ Production ⊃ {planning, processing, packaging}*).
D2. A container sizes to fit its children (inner row + padding + caption strip) and occupies its
aspect/domain rank as one block.
D3. **Only leaf boxes are routing obstacles**; a connector may enter a container to reach a child but
must never cross a leaf box.

## E. Relationship routing

E1. **Orthogonal only** — horizontal/vertical segments ("angled"), never straight-diagonal.
E2. **Never cross an element** (hard invariant H2) — A* obstacle-avoiding router.
E3. **Triggering only between adjacent steps** in the flow (no jump-over a box); a black-box/external
system sits **off the flow line**, its calls routed under/around.
E4. Distinct lanes for parallel connectors (usage penalty) so lines don't overlap each other.
E5. Use the **correct relationship type**: Assignment (active *performs* behaviour / is deployed),
Realization (concretises), Serving (offers-to), Composition (nesting), Access (read/write data),
Triggering (sequence), Flow (cross-boundary transfer), Influence (+/−), Specialization.

## F. Semantic correctness (ArchiMate)

F1. Separate the three aspects; never collapse service ↔ function ↔ process ↔ interface.
F2. **Interface** = the access point every cross-boundary call goes through; distinguish **external**
(consumed outside the boundary) from **internal** interfaces.
F3. Standard layer colours: Business `#FFFFB5`, Application `#B5FFFF`, Technology `#C9E7B8`,
Strategy `#F5DEAA`, Motivation `#E6E6FA`, Physical `#C9E7B8`.

## G. Completeness & labels

G1. **A view must fully define its domain/solution** — e.g. an *Eligibility* view contains the entire
eligibility solution (actors, services, behaviour, interfaces, data, externals), not a fragment.
G2. **Every label always visible / unobstructed** — boxes sized to text; no connector or box covers a
label; relationship labels (trigger/serving/realization/data-name) placed on a clear segment.

## H. Hard invariants (build fails if violated)

- **H1** no two leaf boxes overlap.
- **H2** no routed connector segment crosses a leaf-box interior.
- **H3** every connector length ≥ `MIN_CONN`.
- **H4** every Serving/Realization points upward (target row above source row), unless explicitly
  exempted (e.g. a same-row peer serving).
- **H5** every element declared in the view is placed and every relationship is routed (no floaters,
  no missing edges) — and coverage holds (each behaviour realized, each service served).

## Open decision (flagged, default chosen)
A2 vs A4 can conflict for a *served active element* (an actor that only receives Serving). **Default:
A4 wins** — it floats to the top of its domain (matches the reference's *Customer*). Override per-view
if a different reading is wanted.
