# ArchiMate 3.1 — Reference Vocabulary for the Wellness Analysis

> Source: `ArchiMate Framework Cheat Sheet v3.1 (1) (1).pdf` (The Open Group).
> This pins the element + relationship vocabulary every later step must conform to, so the model is
> standards-correct and tool-portable (Archi / BiZZdesign).

## Layers × Aspects (the framework grid)

Aspects (columns): **Passive Structure** (what behaviour acts on) · **Behaviour** (what happens) ·
**Active Structure** (who/what acts) · **Motivation** (why).

| Layer | Passive | Behaviour | Active Structure |
|---|---|---|---|
| **Strategy** | — | Capability, Course of Action, Value Stream | Resource |
| **Business** | Representation, Contract, Business Object, Product | Service, Process, Function, Interaction, Event | Actor, Role, Collaboration, Interface |
| **Application** | Data Object | Service, Process, Function, Interaction, Event | Component, Collaboration, Interface |
| **Technology** | Artifact | Service, Process, Function, Interaction, Event | Node, Device, System Software, Collaboration, Interface, Path, Communication Network |
| **Physical** | Material | — | Equipment, Facility, Distribution Network |
| **Impl. & Migration** | Gap, Deliverable | Work Package, Event | — |
| **Motivation** | Stakeholder, Driver, Assessment, Value, Meaning, Goal, Outcome, Principle, **Requirement**, **Constraint** | | |
| **Composite** | Product, Plateau, Location, Group | | |

## Relationships (and when to use which)

**Structural** (strongest → weakest cohesion):
- **Composition** ◆── — whole-part, part cannot exist without whole (Challenge ◆ ScoringPlan).
- **Aggregation** ◇── — grouping, parts exist independently (Segment ◇ Members).
- **Assignment** ●──▶ — active element performs behaviour / role (ACTV-SVC ● Activity-Verification function; Actor ● Role).
- **Realisation** ┈┈▷ — more-concrete realises more-abstract (App Service realises Business Service; Process realises Service).

**Dependency**:
- **Serving** ──▶ — element provides functionality to another (FRAUD-SVC serves WALLET-SVC).
- **Access** ┈┈┈ — behaviour reads/writes a passive object (Scoring kernel accesses ScoringPlan).
- **Influence** ┈┈▷ (+/−) — a motivation element affects another (Constraint influences Requirement/Goal).
- **Association** ─── — generic, unspecified relationship.

**Dynamic**:
- **Trigger** ──▶ (solid) — causal/temporal flow of control (`activity.verified` triggers Goal evaluation).
- **Flow** ┈┈▶ (dashed) — transfer of value/info/money (Points flow Wallet→Redemption).

**Other / Connectors**: **Specialisation** ──▷ (is-a); **Junctions** AND ● / OR ○ to split-join relationships.

## Generic meta-model (drives correctness)

`Service` (external behaviour) is realised by `Process/Function` (internal behaviour), performed via
`Assignment` by an `Active Structure` element, exposed through an `Interface`, acting on `Passive
Structure` via `Access`. Events trigger behaviour. This shape is identical across Business / Application
/ Technology layers — which is exactly what lets us trace a Business Service down to an OAM component.

## How our catalogue binds to this

- **RULE-\*** → Motivation layer **Constraint** (a few are Driver/Assessment), linked by **Influence**
  to the **Requirement** (BR-\*) / **Business Service** / **Business Object** they govern.
- **BR-\*** tagged "Business Service/Process/Function/Interaction/Event" → Business **Behaviour**.
- ABBs (CHAL-SVC, WALLET-SVC, …) → Business **Functions/Services** in Step 2, then **Application
  Components** in Step 3 (Realisation across the Business→Application seam).
- The platform-native realisation (Step 4): each Application Component → an **OAM component**
  (`webservice`, `realtime-platform`, `analytics-platform`, `postgresql`, …) on the Technology layer.

## Next steps in this analysis

1. ✅ **Step 1** — extract business requirements + rules (`00-business-requirements-and-rules.md`).
2. **Step 2** — Motivation + Business layer model: Stakeholders/Drivers/Goals → Requirements (BR) ←
   Constraints (RULE); Business Services/Processes/Objects/Events for the 18 ABBs + Phases A–D.
3. **Step 3** — Application layer: Components realising Business Functions; App Services + Data Objects;
   the event spine; the OLAP/OLTP seam as an explicit boundary.
4. **Step 4** — Technology realisation mapped to this platform's OAM capabilities (the wellness-game OAM).
