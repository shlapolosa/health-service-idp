# Async Eventing Ownership + B2B Security

## B2B security construct (sync, boundary-crossing)
Platform runs its own **Microsoft Entra** instance. It registers a **Sahatna identity** (app registration).
Sahatna holds `client_id` + `client_secret`, presents them to the **platform APIM** (OAuth2 **client-credentials**
flow) and receives an **access token**. Every Sahatna→platform *sync* call (eligibility, enrol, telemetry POST)
carries that token; APIM validates it (issuer = platform Entra, audience = platform API, app-role scoped). This is
the `idp_entra` south-gateway path. Symmetric for platform→Sahatna calls (notifications): the platform is a
registered client of Sahatna's Entra/APIM. **APIM + Entra secure the SYNC boundary only.**

## Who should own the Event Hub instance? → the PLATFORM (single instance)
The Event Hub (`eh_integration`, EVENT-SVC = Kafka + Lenses + schema registry) is the **gamification platform's
internal integration spine**. Ownership follows the **schema contract + retention + replay (inv-6)** — all platform
concerns. Every domain event's producer and consumer is a platform ABB; Sahatna is a UX/data-source *edge*, not a
domain participant. So:
- **One Event Hub, platform-owned.** It never spans the trust boundary.
- **Sahatna↔platform crossings stay SYNC** (APIM + the B2B token above), because APIM/Entra can't guard a raw
  Kafka socket. The spine stays internal → no external consumer groups, no shared schema governance.
- **Notifications go platform→Sahatna as a SYNC APIM call** (NUDGE-SVC → Sahatna Notifications API), deliberately
  NOT on the Event Hub — so Sahatna needs **no subscription** on the platform spine.
- **One inbound exception (only if the wearable firehose is too heavy for sync APIM):** a dedicated
  `telemetry.ingest` topic that Sahatna publishes to **directly**, authenticated with an **Entra workload/managed
  identity + topic-scoped ACL** (Event-Hub-native auth, NOT the APIM token). Even then the platform owns the topic,
  schema and retention; Sahatna is a least-privilege publisher to that **one** topic.

## Async paths — owner / publisher / subscriber
All internal paths run inside the platform trust zone (Istio mTLS + Event Hub ACLs); the B2B token is irrelevant
there — it only matters on the one boundary-crossing ingress row.

| Async path (topic / event) | Event Hub owner | Publisher | Subscriber(s) |
|---|---|---|---|
| `telemetry.ingest` (raw activity, **boundary-crossing**) | Platform | **Sahatna** (Entra MI, topic-scoped) — *or* Verification after a sync APIM POST | Verification |
| `activity.verified` | Platform | Verification | Scoring & Recognition · FRAUD-SVC (async anomaly) |
| `enrolment.created` | Platform | Enrolment & Eligibility | Verification (arm routing) · Scoring (init state) |
| `challenge.published` | Platform | Challenge | Eligibility Resolver (active bindings) · DATA-SVC |
| `challenge.withdrawn` | Platform | Enrolment & Eligibility | Scoring (void state) |
| `points.credited` | Platform | Wallet — Points Ledger | DATA-SVC · NUDGE-SVC (→ Sahatna notify) · live-board |
| `voucher.issued` | Platform | Redemption Orchestrator | DATA-SVC · NUDGE-SVC · FRAUD-SVC (async anomaly) |
| `redemption.uncertain` | Platform | Redemption Orchestrator | NUDGE-SVC · DATA-SVC (ops/reconcile) |
| `eligibility.resolved` | Platform | Eligibility Resolver | DATA-SVC (analytics) |
| `leaderboard` (Lenses roundtrip feature) | Platform | Scoring / Lenses SQL | live-board (realtime gateway → `/ws`) |
| `challenge.concluded` | Platform | Challenge | DATA-SVC · Partner & Settlement |
| `settlement.run` (scheduled, internal trigger) | Platform | Partner & Settlement | Partner & Settlement |
| **Notifications (NOT on Event Hub)** | — (sync APIM) | NUDGE-SVC (platform) | Sahatna Notifications API (sync, consent-gated) |

**Direction summary:** consent + telemetry flow Sahatna → platform; notifications flow platform → Sahatna; every
gamification domain event stays platform↔platform on the platform-owned spine.
