# DAPR-SPIKE (#157) — Should we adopt Dapr in this OAM-driven platform?

**Status:** Investigation / decision-ready
**Date:** 2026-06-07
**Author:** spike agent
**Branch:** `worktree-agent-ae9d4f6751e575cdd`

---

## TL;DR Verdict (one paragraph)

**SKIP Dapr as a general runtime; consider it LATER only as a narrow pub/sub
abstraction for RT-1, and even there it is dominated by the simpler
incumbent.** Dapr's value proposition is "fewer client libraries, talk HTTP/gRPC
to a sidecar." But this platform already solves the *binding* problem
declaratively via the BIND-1 `<comp>-conn` Secret contract + `envFrom`, and
solves *eventing/state* via Crossplane-provisioned Kafka/Redis with normalized
secrets. The thing Dapr would let us delete (a few client libs) is small; the
thing it adds is large and recurring: **a third sidecar (daprd) on top of
Knative's queue-proxy and Istio's istio-proxy, on a deliberately cost-tight
3-node / 10-vCPU-quota AKS cluster, plus a control plane (placement,
sidecar-injector, operator, sentry) to install, secure per-vcluster-tenant, and
keep upgraded.** That breaks the platform's "maintainability first — every
adoption must state what it DELETES" doctrine: Dapr is net-additive. The
Knative scale-to-zero cold-start penalty (daprd must start + connect to the
control plane on every 0→1) is the decisive feasibility killer for the default
webservice path. **Recommendation: reject for the webservice runtime; revisit
pub/sub-only for RT-1 *if and only if* RT-1's own evaluation shows the Lenses +
Crossplane-Kafka path is insufficient — which current evidence does not show.**

---

## Knative-coexistence verdict (the critical feasibility question)

**Verdict: NOT viable for the default scale-to-zero webservice path; only
marginally viable for always-on (min-scale ≥ 1) realtime workloads — and even
then it triples sidecar overhead.**

Evidence:

1. **Three sidecars per pod.** Every webservice pod on this platform already
   runs the app container + Knative **queue-proxy** + Istio **istio-proxy**
   (mesh is on, Istio 1.27, Knative Serving v1.22). Dapr adds **daprd** as a
   fourth container. On a cluster intentionally capped at **3 nodes / 6 vCPU
   used of a 10-vCPU regional quota** (see memory `cluster-sizing-default-3`),
   per-pod sidecar bloat is the binding constraint, not a rounding error. Dapr's
   own perf guidance cites the sidecar at ~0.48 vCPU + ~23 MB per 1000 req/s,
   but real-world reports show daprd resident at **hundreds of MiB** (one cited
   case: 661 MiB sidecar vs 89 MiB app). Multiply across every revision pod and
   the 4-vCPU headroom evaporates.

2. **Cold-start tax defeats scale-to-zero.** Knative's whole cost story here is
   scale-to-zero. On every 0→1, the pod must now also cold-start daprd, which
   must dial the Dapr control plane (placement/sentry) and load components
   before the app is "ready." This adds latency to exactly the path Knative
   optimizes and partially negates the cost benefit (you keep more warm
   capacity to hide it). KEDA/Knative + Dapr scale-to-zero is *documented as
   possible* but is an event-consumer pattern, not the synchronous-request
   webservice pattern we run.

3. **Port-conflict friction is real and unowned.** Dapr+Knative coexistence is
   tracked in `dapr/dapr#3067` — still labeled **P2 / kind/documentation /
   good-first-issue**, i.e. it works only with careful manual port wiring
   (Knative reserves queue-proxy ports 8012/8022; Dapr's app-port/http-port/
   metrics-port must be steered clear; see `knative/serving#2761`). It is not a
   first-class, supported integration. Baking that fragility into a CUE template
   that must render zero-touch for *every* service is a maintenance liability.

4. **AKS Dapr extension exists** (managed control-plane install), which lowers
   the *install* cost — but it does nothing about per-pod sidecar count, the
   cold-start tax, or the vcluster-tenant scoping of the injector.

**Conclusion:** Dapr can technically run beside Knative+Istio, but on *this*
cost-minimized substrate the coexistence cost is paid on every pod, every
scale-up, forever, for a benefit (thinner client libs) that the binding
contract already mostly delivers without a sidecar.

---

## Capability-by-capability verdict table

| Capability | Incumbent today | Dapr alternative | What Dapr DELETES | What Dapr ADDS | Verdict |
|---|---|---|---|---|---|
| **pub/sub** | `kafka` CD (Crossplane Helm) + `<name>-kafka-secret` / realtime CD; client libs `aiokafka` (py), `spring-kafka` (java); RT-1 plans Lenses-mediated Kafka | Dapr pubsub component over Kafka; app does HTTP/gRPC POST to sidecar `/v1.0/publish/...` and subscribes via declarative routes | the broker client libs in both templates; topic plumbing code | daprd sidecar on producer AND consumer pods; a Dapr `Component` CR per topic-binding; loss of Kafka-native features (headers, exactly-once, Lenses SQL governance) behind Dapr's lowest-common-denominator API | **LATER (RT-1 only)** — only if RT-1 finds Lenses+native-Kafka insufficient; otherwise SKIP |
| **service invocation** | Knative routing + Istio mesh (mTLS, retries, telemetry already) | Dapr service-invocation (`/v1.0/invoke/...`) with built-in mTLS/retry | nothing we don't already have | a *competing* mesh layer → 3rd sidecar; double mTLS; split observability between Istio and Dapr | **SKIP** — direct overlap/conflict with Istio; pure duplication |
| **state store** | `redis` CD → `<comp>-conn` Secret (`REDIS_*`/`REDIS_URL`/`CACHE_URL`), `envFrom`; py cache-aside + java lettuce | Dapr state API (`/v1.0/state/...`) over Redis | redis client lib usage in templates | daprd sidecar; a Dapr `Component` CR; weaker semantics than direct Redis (no native pipelines/Lua) | **SKIP** — binding contract already makes this one `envFrom` line |
| **secrets API** | ESO-synced `<comp>-conn` Secrets (`AUTH0_*`, `DB_*`) consumed via `envFrom`; Auth0/KeyVault wired by recipes | Dapr secrets API (`/v1.0/secrets/...`) | nothing — ESO already centralizes secret sync | runtime dependency on daprd for secret reads (vs env at boot); a Dapr secretstore `Component` | **SKIP** — env-at-boot via ESO is simpler and 12-factor-correct |
| **bindings (cron/http)** | K8s Jobs / CronJobs; Argo Events sensors | Dapr input/output bindings (cron, http, etc.) | a few Job/CronJob manifests | daprd on the bound pod; binding `Component` CRs | **SKIP** — Jobs/Argo Events already cover this with no sidecar |
| **Dapr Workflow** | Argo WFT path is being **retired** (W7 demotes oam-driven-contract); orchestration moving to app.submit + ArgoCD | Dapr Workflow (durable, code-defined) | n/a (the WFT path is already leaving) | a workflow runtime + placement dependency; couples business workflow to daprd availability | **SKIP** — no live consumer; would re-introduce a runtime we are removing |

---

## Interaction with RT-1 (parallel realtime workstream)

RT-1 is standing up Lenses-mediated Kafka + the existing `realtime-platform` CD
(which already renders Kafka, MQTT/Mosquitto, Lenses HQ+Agent, Metabase,
Postgres, and the normalized `<name>-kafka-secret` / `-mqtt-secret` / `-db-secret`).
The realtime webservice template already auto-`envFrom`s those secrets and
injects `KAFKA_BOOTSTRAP_SERVERS`, `MQTT_HOST`, etc.

**Could Dapr pubsub be RT-1's API?** In principle yes — a Dapr pubsub
`Component` CR could be *rendered by the realtime CD* (the same way it renders
the `-conn` secrets), giving app code a broker-agnostic publish/subscribe
surface. That is the one place Dapr has genuine architectural synergy with this
platform's "CD renders the binding" pattern.

**But it is dominated by the incumbent for RT-1's actual goals:**
- RT-1's value is **Lenses stream-processing/SQL governance** over Kafka. Dapr's
  pubsub API is a thin lowest-common-denominator that **hides** Kafka semantics
  (custom headers, partitions, consumer-group control, exactly-once) — the very
  things a streaming platform needs. You'd be abstracting away the product
  you're adopting.
- RT-1 realtime services run **min-scale ≥ 1** (WebSocket fan-out, Kafka
  consumers) so the scale-to-zero cold-start objection is weaker *there* — this
  is the only context where Dapr is even arguably feasible. But "feasible" still
  means a 3rd sidecar per realtime pod on the tight cluster.

**Recommendation for RT-1:** ship RT-1 on the existing realtime CD +
native-Kafka clients + Lenses. **Keep Dapr pubsub explicitly out of RT-1 scope.**
Only re-open this if RT-1 surfaces a concrete need for *broker portability*
(e.g. swapping Kafka for Azure Service Bus per-tenant) — that is the single
requirement that would justify the Dapr pubsub abstraction, and it is not on
RT-1's roadmap today.

---

## IF we adopted anyway — the thin-slice (for completeness; NOT recommended)

If a future broker-portability requirement forces the issue, the *least-bad*
adoption path that preserves zero-touch:

1. **Pub/sub only.** Never enable Dapr service-invocation, state, or secrets
   (those overlap Istio/Redis-conn/ESO and add nothing).
2. **Components rendered by the realtime CD.** The `realtime-platform` CD emits
   the Dapr pubsub `Component` CR alongside its existing `-kafka-secret`, scoped
   to the app via `scopes:`. No human authors Dapr YAML — the CD does, exactly
   like the binding contract. This is the synergy point.
3. **Sidecar via a webservice CD parameter, default OFF.** Add an optional
   `dapr: <app-id>` parameter to `webservice-shape` (mirroring the existing
   `realtime:` parameter pattern). When set, the CUE template injects the
   `dapr.io/enabled`, `dapr.io/app-id`, `dapr.io/app-port`, and a *pinned*
   `dapr.io/metrics-port` (steered clear of Knative's reserved 8012/8022) plus
   `dapr.io/sidecar-memory-limit` + `GOMEMLIMIT` to cap the footprint. Default
   unset ⇒ existing services are untouched ⇒ zero-touch contract preserved.
4. **Restrict to min-scale ≥ 1 components only** (realtime), never the default
   scale-to-zero webservice, to avoid the cold-start tax.
5. **Control plane via the AKS Dapr extension**, pinned version, scoped per
   vcluster tenant via the injector's namespace selectors.

Even executed perfectly, this still adds: a control plane to upgrade, a 3rd
sidecar on realtime pods, and a new CUE branch to maintain — for a benefit that
only materializes under broker-portability, which is hypothetical.

---

## Operational / tenancy / upgrade-surface notes

- **Control plane footprint:** Dapr adds placement, sidecar-injector, operator,
  and sentry pods. On a 3-node cluster already hosting factory MCPs + cafe-spec
  adapters + control-plane chatter, that is real, persistent overhead even
  before any app uses it.
- **vcluster tenancy:** the sidecar-injector and component CRs must be scoped
  per tenant; Dapr component scoping is by app-id/namespace, which maps onto
  vclusters but is one more cross-tenant RBAC/isolation surface to get right.
- **Upgrade surface:** Dapr 1.x supports only current + previous 2 minors
  (rolling). Latest stable **1.17.5** (2026-06-02), with **1.18.0-rc1** in
  flight (assumption as of 2026-06-07, from `dapr/dapr` releases). Adopting Dapr
  means a *new* runtime on the upgrade treadmill alongside Knative v1.22, Istio
  1.27, ArgoCD v3, Crossplane v2 — contradicting the substrate-upgrade
  prioritization that explicitly defers low-value additions.

---

## What this deletes vs adds (maintainability-doctrine summary)

- **Deletes:** at most, broker/redis client-lib usage in two templates (small,
  well-understood, already abstracted behind the binding contract).
- **Adds:** a control plane (4 components), a per-pod sidecar (3rd/4th
  container), CUE template branches, component CRs, port-conflict management,
  cold-start latency, a vcluster-tenancy isolation surface, and a perpetual
  upgrade obligation.

Net: **strongly additive.** Fails the "state what it deletes" bar. **Reject for
the runtime; park pub/sub-only behind a concrete broker-portability requirement
that does not exist today.**

---

## Sources

- Dapr releases / version: https://github.com/dapr/dapr/releases ; https://pypi.org/project/dapr/ ; https://docs.dapr.io/operations/support/support-release-policy/
- Dapr + Knative coexistence: https://github.com/dapr/dapr/issues/3067 ; https://github.com/knative/serving/issues/2761
- Sidecar footprint / tuning: https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-production/ ; https://github.com/dapr/dapr/issues/6581
- AKS Dapr extension: https://learn.microsoft.com/en-us/azure/aks/dapr
- Dapr pubsub + serverless scale-to-zero: https://oneuptime.com/blog/post/2026-03-31-dapr-pubsub-serverless-event-source/view
- Internal: BIND-1 binding contract (memory `binding-contract`), `cluster-sizing-default-3`, `upgrade-simplification-opportunities`, `factory/.../catalog/{webservice,redis,kafka,realtime-platform}.cd.yaml`, `REALTIME_SYSTEM.md`
