# OAM Application — the deployable (final layer)

> **Deliverable:** `wellness-platform-oam.yaml` — a single OAM `Application` that realizes the whole
> solution (the `solution-architecture.drawio` value path) using **real catalog ComponentDefinitions**.
> 17 components, 7 distinct types, all present in
> `factory/production-lines/traditional-cloud/adapters/catalog/`. `kubectl apply` (or `app.submit`) deploys it.

## Solution component → OAM component type
| Solution (SBB) | OAM type | OAM components |
|---|---|---|
| Microservices (engine, wallet, market) | **webservice** | enrolment-eligibility · challenge-svc · scoring-svc · consent-svc · wallet-svc · marketplace-svc · partner-settlement-svc · fraud-svc · engagement-svc |
| Data stores | **postgresql** | wallet-db · engine-db · market-db |
| Event Hub (async spine) | **realtime-platform** | event-spine (topics: activity/wallet/voucher/redemption/eligibility/leaderboard) |
| DATA-SVC (OLAP) | **analytics-platform** | analytics (Snowflake warehouse + roundtrip on the spine) |
| Member live board (/ws) | **realtime-service** | live-board (role: gateway, consumes: leaderboard) |
| BFF federation | **graphql-gateway** | member-bff (autoSchema) |
| Identity | **auth0-idp** | wellness-identity |

## The IdP equivalence (your note)
The diagram shows **UAE Pass** (citizen federation, north gateway) and **Microsoft Entra**
(workforce/service identity, south gateway). The platform catalog ships neither, so the OAM uses the
platform's identity SBB **`auth0-idp`** as the equivalent: it emits the `<name>-conn` secret
(`AUTH0_*` / `JWT_ISSUER_URI`) that webservices bind via `identity:`, and APIM validates the minted JWT.
On UAE infrastructure you swap `auth0-idp` for a UAE-Pass-federation + Entra connector that emits the
**same `-conn` shape** — every other line of the OAM is unchanged. That swap-without-rewiring is exactly
the **ABB→SBB** separation from the Technology layer ([[feedback-abb-not-sbb]]).

## How the bindings encode the architecture
- **Persistence:** `database: <db-component>` → injects `<db>-conn` (PG_*) into the service.
- **Async spine:** `realtime: event-spine` → injects `event-spine-conn` (KAFKA_*/TOPIC_*) — this is the
  Event Hub integration layer; analytics + live-board reuse the same spine by name.
- **Identity:** `identity: wellness-identity` → injects auth0 `-conn`; the north/south APIM validate it.
- **North federation:** `enableGraphQLFederation: true` on the public services → `member-bff`
  (graphql-gateway) auto-discovers + federates them.
- **South APIM:** the `expose-api` trait publishes each public service to APIM (per-OAM product).
- **Monorepo:** every webservice carries `repository: wellness-platform` → one source + gitops repo
  (UNIFY-1), the services fan out from it.

## Status vs the live demo
The catalog ships a 4-component demo (`examples/wellness-gamification-example.yaml`); this is the **full
17-component** realization. To deploy: `app.submit` it (or `vela up -f wellness-platform-oam.yaml`). The
data-plane contract tests (HARD-4) then verify each component type end-to-end.

---
This closes the five-layer analysis: **Motivation/Strategy → Business (capability + process) →
Application → Technology (ABB + SBB) → Solution (C4 draw.io) → OAM (this file).**


---
**Update:** OAM is now **20 components** — added `cohort-svc` (local segmentation), `verification-svc`
(verified-signal gate), `malaffi-adapter` (segment-metadata + scoped membership). See `18-...` for the
corrected terminology (DoH features · Clinical-Team clinical segments on Malaffi · challenge definition +
localized content owned by the Challenge service, no CMS · eligibility returns challenge_ids → Challenge
service hydrates localized content · enrolment = scoring subscription). **NOTE:** `cms-service` is removed —
challenge content + survey questionnaires move into `challenge-svc`; recount components and regenerate OAM.
