# ADR REQ-001: Publish `kafka` for messaging requests

## Context

A tenant-scoped messaging capability is requested for **fan-out** event streams with **strong durability** and **P99 latency under 50 ms**. The request also prefers a **light footprint**, expects **high throughput**, requires **horizontal scaling**, and needs **replicated availability** on **AKS** under a **low cost ceiling**.

The deterministic scorer selected `kafka` as the winner among ranked candidates. This ADR records why `kafka` is the platform capability to publish for this request, and why the runner-up was not selected.

## Decision

Publish **`kafka`** as the messaging capability for this request.

`kafka` satisfies all hard requirements, most importantly **durability: strong** and **readPattern: fan-out**. It also meets the **latencyP99Ms <= 50** target with an offered profile of roughly **20 ms**, supports **high/very-high throughput**, scales **horizontally**, and provides **replicated / HA** deployment characteristics suitable for AKS.

While `kafka` is not ideal on **footprint** and only offers **per-partition ordering** rather than explicit **per-subject ordering**, it remains the best valid option because it is the only ranked candidate that passed the hard filter for **required strong durability**.

## Alternatives Considered

- **`nats-jetstream`**  
  This was the strongest functional fit on several requested attributes: **fan-out**, **per-subject ordering**, **very low latency** (~5 ms), **light footprint**, **high throughput**, **horizontal scaling**, and **replicated availability**.  
  However, it was **filtered out** because **durability is tunable and does not satisfy the required `strong` durability hard constraint** in the scorer. Despite its better fit for footprint and latency-sensitive multi-tenant operation, it cannot be published for this request because it fails a mandatory quality attribute.

## Tradeoffs

Choosing `kafka` trades **operational footprint** and some ordering precision for guaranteed compliance with **strong durability**. In practice:

- **Pros:** strong durability, proven fan-out consumption model, high throughput, horizontal scale, replicated operation.
- **Cons:** **heavy footprint** is a poor match for “several instances per tenant,” and **per-partition ordering** may require subject-to-partition keying to approximate the requested **per-subject ordering**.

## Consequences

- Platform teams should expect higher resource consumption and potentially higher tenant operating cost than a lighter broker.
- Capability guidance must document partition-key strategy to preserve effective **per-subject ordering** where needed.
- This decision prioritizes **durability** over **footprint** and **latency headroom**.

## References

- CapabilityRequest REQ-001
- Deterministic scorer output: winner `kafka`, runner-up `nats-jetstream`
- Quality attributes considered: **durability**, **readPattern**, **ordering**, **latencyP99Ms**, **footprint**, **throughputClass**, **scalingModel**, **availabilityClass**