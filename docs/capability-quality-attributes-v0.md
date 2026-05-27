# Capability Quality-Attribute Vocabulary (v0)

**Status:** draft / design — the keystone schema for the capability-factory (publisher) flow.
Not yet wired to any agent or pipeline.

## Why this exists
One shared vocabulary, used three times, so non-deterministic agent output stays reviewable
and deterministic downstream:

| Used by | As | Direction |
|---|---|---|
| `CapabilityRequest.qualityAttributes` (intake) | desired levels (+ optional hard `required`) | what is **asked for** |
| KB technology `profile` (selection) | declared levels | what a tech **offers** |
| Acceptance thresholds (later, #4) | measurable gates | what a published capability must **prove** |

Because all three speak the same field names + value domains, the architect agent can run a
**deterministic match** (filter on hard constraints, weighted-distance on soft) and the LLM only
writes the *narrative* (the ADR). Same request ⇒ same ranking.

## Capability categories
Every KB entry and request is tagged with one category; it selects the relevant attribute subset
(e.g. `ordering` is meaningless for a cache).

`messaging` · `datastore` · `cache` · `compute-service` · `analytics` · `identity` · `secret-config`

## Value-domain types (these drive scoring)
- **ordered-enum** — ordinal, has `betterDirection`. Score = ordinal gap; under-provision penalised
  hard, over-provision penalised lightly (cost).
- **unordered-enum** — matched via a compatibility table (full / partial / none).
- **numeric** — has unit + `betterDirection`; can be a hard threshold.
- **boolean** — match / mismatch; can be hard.

### Scoring semantics
1. **Hard filter:** request attributes with `required: true` (or a numeric hard threshold) eliminate
   any candidate that fails them.
2. **Soft rank:** remaining candidates scored = Σ(weightᵢ × penaltyᵢ). Lowest penalty wins.
3. **Tie-break:** lower `costClass`, then `maturity` (published > kb).
4. Output = ranked shortlist **with per-attribute match detail** → feeds the ADR the human reviews.

## The attributes (v0)
`core` = needed to start; others are v0.1.

### A. Data & state semantics — *datastore, messaging, cache*
| key | type | domain (ordered →) | better | hard? | tier |
|---|---|---|---|---|---|
| `durability` | ordered-enum | ephemeral < weak < tunable < strong | higher | ✓ | core |
| `consistency` | ordered-enum | eventual < read-your-writes < bounded-staleness < strong | higher | ✓ | core |
| `ordering` | unordered-enum | none · per-key · per-partition · global | — | ✓ | core |
| `retention` | enum | none · time-bounded · indefinite | — | | v0.1 |
| `statefulness` | enum | stateless · ephemeral · persistent | — | | core |

### B. Access pattern — *all*
| key | type | domain | better | hard? | tier |
|---|---|---|---|---|---|
| `readPattern` | unordered-enum | single-reader · multi-reader · fan-out | — | ✓ | core |
| `writePattern` | enum | single-writer · multi-writer | — | | v0.1 |
| `queryModel` | unordered-enum | key-value · document · relational · columnar · stream · blob · none | — | ✓ | core |

### C. Performance — *all*
| key | type | domain / unit | better | hard? | tier |
|---|---|---|---|---|---|
| `latencyP99Ms` | numeric | milliseconds | lower | ✓ | core |
| `throughputClass` | ordered-enum | low < medium < high < very-high | higher | ✓ | core |
| `payloadSize` | ordered-enum | small < medium < large | — | | v0.1 |

### D. Scalability & elasticity — *all*
| key | type | domain | better | hard? | tier |
|---|---|---|---|---|---|
| `scalingModel` | unordered-enum | vertical · horizontal · both | — | ✓ | core |
| `maxScaleClass` | ordered-enum | small < medium < large < massive | higher | | core |
| `scaleToZero` | boolean | — | — | | v0.1 |

### E. Availability & resilience — *datastore, messaging, compute-service*
| key | type | domain | better | hard? | tier |
|---|---|---|---|---|---|
| `availabilityClass` | ordered-enum | single < replicated < ha-multizone | higher | ✓ | core |
| `rpoSeconds` / `rtoSeconds` | numeric | seconds | lower | | v0.1 (→ acceptance) |

### F. Footprint & cost — *all*
| key | type | domain | better | hard? | tier |
|---|---|---|---|---|---|
| `footprint` | ordered-enum | light < medium < heavy | lower | | core |
| `costClass` | ordered-enum | low < medium < high | lower | | core (tie-break) |

### G. Operability — *all*
| key | type | domain | tier |
|---|---|---|---|
| `managed` | enum | self-hosted-helm · operator-backed · external-managed | v0.1 |
| `observability` | boolean | ships metrics/dashboards | v0.1 |

### H. Security & tenancy — *all*
| key | type | domain | hard? | tier |
|---|---|---|---|---|
| `encryptionAtRest` / `encryptionInTransit` | boolean | — | ✓ | core |
| `authModel` | unordered-enum | none · basic · mTLS · oidc | | v0.1 |
| `isolation` | ordered-enum | shared < namespace < dedicated-vcluster | | core |

### I. Platform topology — *all* (deployment knob, carried on the request)
| key | type | domain | tier |
|---|---|---|---|
| `targetEnvironment` | enum | host · shared-vcluster · dedicated-vcluster | core |

## Worked example (validates the vocabulary against the original ask)
Request: *"realtime data propagation — durable, multi-read, lightweight, low-latency, highly scalable topics."*
```yaml
category: messaging
qualityAttributes:
  durability:      { level: strong, required: true }
  ordering:        per-partition
  readPattern:     { level: fan-out, required: true }
  footprint:       light            # soft preference
  latencyP99Ms:    { max: 50, required: true }
  throughputClass: very-high
  scalingModel:    horizontal
  maxScaleClass:   large
```
Deterministic scoring over the KB:

| Tech | durability | readPattern | footprint | latency | throughput | scaling | verdict |
|---|---|---|---|---|---|---|---|
| **Kafka** | strong ✓ | fan-out ✓ | heavy ✗ | ~20ms ✓ | very-high ✓ | horizontal ✓ | strong, **loses on "lightweight"** |
| **NATS JetStream** | tunable→strong ✓ | fan-out ✓ | **light ✓** | very-low ✓ | high (≈) | horizontal ✓ | **wins on footprint/latency** |
| Pulsar | strong ✓ | fan-out ✓ | heavy ✗ | low ✓ | very-high ✓ | horizontal ✓ | strong, heavy |
| Redis Streams | weak ✗(hard-fail) | multi ✓ | light ✓ | very-low ✓ | high | vertical-ish | **filtered out (durability)** |

The point: the vocabulary makes the **Kafka-vs-NATS tradeoff explicit and reproducible** — Redis is
auto-filtered (fails the hard `durability` constraint), and whether Kafka or NATS wins is decided by
how the request weights `footprint`/`latency` vs `throughput`. The ADR then *explains* that choice for
the human reviewer. (It is **not** a blind "recommend Kafka.")

## Category weighting defaults (DECIDED)
The platform supplies per-category default weights (high=3 / med=2 / low=1); a `CapabilityRequest` only
overrides when it cares. Lives at `capability-factory/weightings/category-defaults.yaml`.

| category | high | med | low |
|---|---|---|---|
| messaging | durability, ordering, readPattern, throughputClass | latencyP99Ms, scalingModel | footprint, costClass |
| datastore | durability, consistency, availabilityClass, queryModel | latencyP99Ms | footprint |
| cache | latencyP99Ms, footprint, throughputClass | scalingModel | durability |
| compute-service | latencyP99Ms, scalingModel/scaleToZero | footprint | durability |
| analytics | throughputClass, queryModel, maxScaleClass | availabilityClass | latencyP99Ms |
| identity | encryption*, authModel, availabilityClass | — | footprint |

## Capability KB — schema + seed entries
Each technology the architect can productize is a git-versioned file at `capability-factory/kb/<tech>.yaml`,
profiled with the **same vocabulary** so scoring is deterministic.

**Schema:**
```yaml
technology: <name>
category: messaging | datastore | cache | compute-service | analytics | identity
profile: { <attribute>: <value>, ... }     # uses the vocabulary above
version: { current: "<x.y>", tracked: "<semver range>" }
upstreamSource: github:<org>/<repo>          # powers version/CVE watch (the architect upgrade loop)
provisioning: helm:<chart> | operator:<name> | claim:<xrd>
maturity: kb | published                     # kb = productizable; published = in the live catalog
```

**Seed entries** (the four scored in the worked example, + two stubs):
```yaml
# kb/kafka.yaml
technology: kafka
category: messaging
profile: { durability: strong, ordering: per-partition, readPattern: fan-out, footprint: heavy, latencyP99Ms: 20, throughputClass: very-high, scalingModel: horizontal, costClass: high }
version: { current: "3.7", tracked: ">=3.6" }
upstreamSource: github:apache/kafka
provisioning: operator:strimzi
maturity: kb
```
```yaml
# kb/nats-jetstream.yaml
technology: nats-jetstream
category: messaging
profile: { durability: tunable, ordering: per-subject, readPattern: fan-out, footprint: light, latencyP99Ms: 5, throughputClass: high, scalingModel: horizontal, costClass: low }
version: { current: "2.10", tracked: ">=2.10" }
upstreamSource: github:nats-io/nats-server
provisioning: helm:nats
maturity: kb
```
```yaml
# kb/postgres.yaml
technology: postgres
category: datastore
profile: { durability: strong, consistency: strong, queryModel: relational, readPattern: multi-reader, availabilityClass: replicated, latencyP99Ms: 10, footprint: medium, costClass: medium }
version: { current: "16", tracked: ">=15" }
upstreamSource: github:postgres/postgres
provisioning: helm:bitnami-postgresql
maturity: kb
```
```yaml
# kb/redis.yaml
technology: redis
category: cache
profile: { durability: weak, consistency: eventual, queryModel: key-value, readPattern: multi-reader, latencyP99Ms: 1, throughputClass: very-high, footprint: light, costClass: low }
version: { current: "7.2", tracked: ">=7" }
upstreamSource: github:redis/redis
provisioning: helm:bitnami-redis
maturity: kb
```
```yaml
# stubs — profiles TBD
# kb/pulsar.yaml   → category: messaging  (durable, multi-tenant, tiered storage; footprint heavy)
# kb/mongodb.yaml  → category: datastore  (document, tunable consistency, horizontal sharding)
```

## CapabilityRequest — intake template
The artifact the orchestrator/intake emits; lives at `capability-factory/requests/<id>.yaml`.
```yaml
intent: "<original natural-language ask — preserved for the ADR>"
category: messaging
qualityAttributes:
  durability:   { level: strong, required: true }   # hard constraint → filter
  readPattern:  { level: fan-out, required: true }
  latencyP99Ms: { max: 50, required: true }
  footprint:    light                                # soft → category-default weight unless overridden
weights: {}                                          # optional per-attribute override of category defaults
constraints: { runtime: aks, costCeiling: medium }
requestedBy: <agent|human>
```

## Remaining open (later)
- Numeric attributes (`latencyP99Ms`, throughput) double as **acceptance thresholds** (design doc #4) — the
  value *requested* is later *measured*.
- Reconcile this v0 vocabulary against real benchmark data; promote `v0.1` attributes to `core` as needed.
