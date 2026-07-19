# Solution Architecture (C4 container/component) — draw.io diagram-as-code

> **Deliverable:** `solution-architecture.drawio` (open/edit in https://app.diagrams.net).
> Source = `gen_solution_drawio.py` (the diagram-as-code). Template style: banded layered architecture
> with trust-boundary zones, nested service containers, typed connectors + legend.

## Why draw.io (and the layout guarantee)
The hard requirement — connectors must be **orthogonal (angled, never diagonal)**, **never overlap an
element**, and **never trunk** (no two lines on the same row/column) — rules out Mermaid / PlantUML-C4 /
D2-ELK (all trunk and cross boxes). draw.io edges support explicit **`exitX/entryX` anchors**, so
connectors fan to distinct points *and* stay orthogonal. An **A\* obstacle-avoiding router** (in the
generator) computes the waypoints through band-gaps and side-gutters; the build verifies **0 box
crossings, 0 diagonals** across all 33 connectors.

## Bands (top → down) — 11 trust/security zones
1. **Client Surfaces** — Sahatna Citizen App (Challenges · Rewards/Wallet · Marketplace) · RTL.
2. **API Gateway — North** — Azure APIM (citizen) + **UAE Pass IdP** (federation, mints platform JWT).
3. **BFF Layer** — Member / Admin-Partner BFF (JWT validation · idempotency relay).
4. **Integration Layer — South** — Azure APIM (sync) + **Event Hub** (async, Kafka+Lenses spine) +
   **Microsoft Entra IdP** (workforce/service identity).
5. **Gamification Platform — Core Engine** — Enrolment/Eligibility, Cohort, Challenge, Verification,
   Scoring, Engagement + Eligibility-Resolver saga + Malaffi Adapter.
6. **Wallet & Marketplace Services** — Wallet ledger, Marketplace/Voucher, Partner/Settlement, Fraud +
   Redemption Orchestrator (saga) + Partner Adapter Framework.
7. **Persistence** — Wallet / Engine / Marketplace stores + Azure Key Vault (column-level KMS).
8. **Partner Trust Boundary** — mTLS / OAuth2 · idempotent · uncertain → manual reconcile.
9. **External Partner APIs** — Malaffi HIE, Reward Providers (YouGotaGift / aggregators), DoH ESB.
10. **Platform Services** — FRAUD-SVC, NUDGE-SVC, CONS-SVC, ID-SVC, DATA-SVC (Event-Hub consumers).
11. **Cross-cutting** — Secrets (Key Vault + ESO), GitOps (KubeVela+Crossplane+ArgoCD), Observability.

## Connector legend (typed)
| Style | Meaning |
|---|---|
| solid black | Synchronous HTTPS (internal request path + persistence) |
| dashed grey | Async / event publish–consume (via Event Hub) |
| solid red (2px) | Cross trust boundary (partner / settlement) |
| dotted purple | Identity · consent · read-secret |

## North–south request path
`Client → APIM (UAE Pass) → BFF → APIM (Entra) → Gamification Engine`, with the **Event Hub** in the
same south integration band carrying the async spine; partner/HIE/settlement calls cross the **Partner
Trust Boundary** (red). To regenerate after edits: `python3 gen_solution_drawio.py`.
