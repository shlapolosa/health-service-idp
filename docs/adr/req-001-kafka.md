# ADR REQ-001: Publish `kafka` for messaging requests

## Context

A tenant-scoped messaging capability is needed for **fan-out** event streams with a **handful of consumers**. The request explicitly requires **strong durability**, **P99 latency under 50 ms**, **horizontal scaling**, and **replicated availability** on **AKS**, while also preferring a **light footprint** and **low cost ceiling** because several instances may run per tenant.

The deterministic scorer selected `kafka` as the top valid candidate. Although footprint is an important preference, the request contains hard requirements that take precedence: **durability** and **latency** must be satisfied, and the platform capability must be publishable as a reliable default rather than an optimistic best fit.

## Decision

Publish **`kafka`** as the messaging capability for this request class.

`kafka` fits the mandatory quality attributes best overall:

- **Durability: strong** — satisfies the required durability bar.
- **Read pattern: fan-out** — native fit via consumer groups and retained logs.
- **Latency P99 < 50 ms** — offered latency of ~20 ms meets the requirement.
- **Throughput: high** — comfortably supports the requested throughput class.
- **Scaling model: horizontal** — aligns with partition-based scale-out.
- **Availability: replicated** — supports replicated, multi-zone resilient deployments on AKS.

The scorer penalized `kafka` for **footprint** (`heavy`) and for **ordering** because it provides **per-partition** rather than true **per-subject** ordering. Even with those penalties, it remains the best candidate that passes all hard gates.

## Alternatives Considered

### `nats-jetstream`

`nats-jetstream` is attractive on non-functional efficiency:

- **Footprint: light**
- **Latency: ~5 ms**
- **Ordering: per-subject**
- **Fan-out**, **high throughput**, **horizontal scaling**, and **replicated availability**

However, it was filtered out because **durability** is **tunable** and does **not satisfy the required strong durability guarantee** as scored. Since **durability.required = true**, this disqualifies it despite its otherwise excellent fit, especially for lightweight multi-tenant deployment.

## Tradeoffs

Choosing `kafka` prioritizes **strong durability** and broad operational confidence over **light footprint** and simpler tenant density. This increases resource consumption and likely raises operational cost per tenant. It also means consumers must design around **per-partition ordering** rather than assuming strict **per-subject ordering**.

## Consequences

- Capability consumers get a durable, replicated, low-latency event backbone that meets the hard requirements.
- Platform teams should expect higher AKS resource usage and more operational overhead than lighter brokers.
- Subject-to-partition keying guidance will be needed to approximate the requested **per-subject ordering**.
- Cost efficiency may be lower for small tenant footprints, but the published capability remains compliant with the mandatory durability requirement.

## References

- CapabilityRequest REQ-001
- Deterministic scorer output for messaging candidates
- Apache Kafka platform capability profile on AKS