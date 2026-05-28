# ADR REQ-001: Publish `nats-jetstream` for messaging requests

## Context

A capability request was raised for a messaging platform on **AKS** that provides **durable**, **lightweight**, **low-latency** fan-out event streaming for a **handful of consumers** per stream, with **several instances per tenant**. The key quality attributes were:

- **durability: strong** _(required)_
- **readPattern: fan-out** _(required)_
- **ordering: per-subject**
- **latencyP99Ms: max 50** _(required)_
- **footprint: light**
- **throughputClass: high**
- **scalingModel: horizontal**
- **availabilityClass: replicated**
- Constraint: **costCeiling: low**

The deterministic scorer ranked `nats-jetstream` first and `kafka` second. This ADR records why the selected technology is the best fit for the stated quality attributes and why the runner-up is not being published for this request.

## Decision

Publish **`nats-jetstream`** as the messaging capability for this request.

`nats-jetstream` is the strongest fit because it satisfies all required attributes without compromise: **strong durability**, **fan-out** consumption, **per-subject ordering**, **horizontal scaling**, and **replicated** availability. It also materially aligns with the non-functional priorities that dominate this request: **light footprint**, **low cost**, and **P99 latency well under 50 ms** (scored offer: **5 ms**).

This makes it especially suitable for multi-tenant deployment patterns where many small, durable messaging instances must run efficiently on AKS.

## Alternatives Considered

### `kafka`

`kafka` passed the hard requirements, but it is a weaker fit overall.

- It meets **strong durability**, **fan-out**, **horizontal scaling**, and latency requirements.
- However, its ordering model is **per-partition**, not the requested **per-subject** ordering.
- Its operational and resource profile is **heavy**, which conflicts with the requested **footprint: light** and the stated need to run **several instances per tenant**.
- That heavier footprint also works against the **low cost ceiling**.

Kafka would be more compelling if the primary driver were maximum aggregate throughput at larger cluster scale, but that is not the dominant need here.

## Tradeoffs

Choosing `nats-jetstream` favors:

- better **footprint**
- lower expected **cost**
- simpler fit for **low-latency** replicated event fan-out
- closer alignment to **per-subject ordering**

The tradeoff is that Kafka remains stronger as a general-purpose ecosystem choice for very large-scale streaming estates and extreme throughput scenarios. We are explicitly not optimizing for that here.

## Consequences

- Platform teams can standardize on a messaging capability that is efficient for **tenant-dense AKS deployments**.
- Consumers get durable fan-out streams with predictable **low latency** and ordering semantics aligned to the request.
- We avoid over-provisioning and operational overhead associated with heavier brokers.
- Future requests centered on massive shared streaming backbones may still justify publishing Kafka separately.

## References

- Capability request: `REQ-001`
- Deterministic scorer result: `nats-jetstream` ranked above `kafka`
- Runtime constraint: **AKS**
- Requestor: `human:socrates`