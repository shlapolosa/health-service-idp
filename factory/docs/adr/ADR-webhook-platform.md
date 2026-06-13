# ADR: WEBHOOK-PLATFORM — Reuse Svix (MIT) as the outbound webhook engine, not build/Convoy (#WH-1)

- Status: Proposed
- Date: 2026-06-13
- Decision drivers: the standing **reuse > repurpose > create** principle; HARD-3
  (no `:latest`); additive/non-breaking; the registration UI MUST be externally
  reachable with zero platform-team involvement.

## Context

The platform emits events today (Kafka topics: `sensor_agg`, lifecycle events). We
need EXTERNAL third parties to self-register an HTTPS endpoint + signing key and
reliably receive those events: signed payloads, retries with backoff, delivery logs,
and a **self-service UI exposed externally** so consumers manage their own
endpoints/keys.

Per the principle, before creating a webhook engine we must exhaust REUSE. Three
candidates were evaluated.

## Options

| Dimension | **Svix (svix/svix-server)** | Convoy (frain-dev/convoy) | Build (realtime-transport variant) |
|---|---|---|---|
| License | **MIT** — portal, retries, signing all free | **Elastic License v2** — some features gated | n/a (our code) |
| Self-service UI out of the box | **App Portal** — magic-link iframe, no consumer account needed | Customer dashboard iframe (also good) | None — we build it |
| Container image | `svix/svix-server:v1.69.0` (pinned) | `getconvoy/convoy` (Elastic-licensed) | our image |
| Helm chart | docker-compose reference; chartable | `convoy` Helm chart 3.7.x exists | n/a |
| Deps | Postgres + Redis | Postgres + Redis | Postgres + Redis (we'd add) |
| Signing | HMAC-signed payloads | HMAC payload signing | we implement |
| Retries/backoff | automatic exp-backoff | constant + exp-backoff w/ jitter | we implement |
| Magic-link/short-session portal | **yes, MIT** (no account for consumer) | dashboard (auth model heavier) | we build |
| Fit to platform shape | identical to realtime-platform CD (engine+pg+redis+VS) | identical | reuses transport wheel but no UI |

Sources: svix.com/open-source-webhook-service, github.com/svix/svix-webhooks (MIT),
hub.docker.com/r/svix/svix-server (v1.69.0), svix.com/application-portal (magic links);
github.com/frain-dev/convoy + convoy/LICENSE (Elastic License v2),
docs.getconvoy.io (dashboard iframe), artifacthub.io/packages/helm/convoy.

## Decision

**Reuse Svix (`svix/svix-server:v1.69.0`, MIT) as the engine.** Wrap it in a
`webhook-platform` ComponentDefinition that mirrors the realtime-platform shape
exactly (one OAM Component → a namespace of engine+Postgres+Redis+Secrets+Istio
Gateway/VirtualService + a `<name>-conn` secret). The Kafka→engine bridge is a
**realtime-service in a new `role: webhook`** — repurposing the existing
realtime-transport wheel (add a webhook sink) rather than introducing a new framework.

### Why NOT build

A hand-rolled engine would re-implement signing, exponential-backoff retries,
delivery logs, idempotency, AND a magic-link self-service portal — months of work
duplicating mature MIT code. Violates reuse-first.

### Why NOT Convoy

Convoy's dashboard is excellent, but its **Elastic License v2** gates features and
adds redistribution friction for a platform that bakes the engine into every consumer
namespace. Svix is unambiguously **MIT** with the portal/retries NOT gated, so it is
the lower-risk reuse. (Convoy remains a viable swap if a gated feature is never
needed — same CD shape would apply.)

### Why repurpose realtime-transport for the bridge (not a new service)

The bridge is "consume CONSUME_* topics → forward each message to an HTTP API" — that
is exactly the processor role minus the produce-back, plus an HTTP sink. The
realtime-transport wheel already does Kafka consume + role dispatch; adding a
`webhook` sink is additive. A whole new microservice/framework would duplicate the
consume machinery.

## Consequences

- New CD `webhook-platform` + skeleton composition `webhook-platform-claim-composition.yaml`
  (same provider-kubernetes Object wrapping + RT-COMPOSITION-V2 cluster-scoped lesson).
- New `role: webhook` on realtime-service (follow-up: transport-wheel webhook sink).
- The App Portal is externally exposed on its own Istio host
  `<name>-webhook-portal.<lbHost>` — explicit, non-breaking.
- Admin token is a RUNTIME `<name>-svix-credentials` secret (minted by an init Job);
  never committed. `<name>-conn` references it by name only.
- The registration/ingest REST API can ALSO be published through APIM via expose-api
  for programmatic registration (additive to the portal).

## Compliance with reuse>repurpose>create

REUSE Svix engine + App Portal (MIT). REPURPOSE realtime-platform CD shape +
realtime-transport wheel (webhook sink + role). CREATE only the thin CD/composition
glue + the sink function. Justified above.
