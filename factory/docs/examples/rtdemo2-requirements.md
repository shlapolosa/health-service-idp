# rtdemo2 — Requirements (SPEC-1)

A realtime sensor pipeline proving the RT-2 role model end-to-end.

## Flow
1. `rtdemo2-ingest` (role: ingest) — `POST /ingest` accepts a JSON telemetry
   reading `{"sensor_id": str, "value": number, "ts": iso8601}` and produces it
   to `sensor_raw`. Implement `to_message` in `src/handlers.py`: validate the
   three fields, reject (raise ValueError) on missing `sensor_id` or
   non-numeric `value`, and stamp `received_at`.
2. `rtdemo2-processor` (role: processor) — consumes `sensor_raw`, produces
   `sensor_agg`. Implement `transform` in `src/handlers.py`: maintain a rolling
   average of the last 10 `value` readings PER `sensor_id` and emit
   `{"sensor_id", "value", "rolling_avg", "count", "ts"}`. Return `None`
   (drop) for malformed messages.
3. `rtdemo2-gateway` (role: gateway) — consumes `sensor_agg` and streams to
   websocket clients on `/ws`. No custom logic; platform transport only.

## Acceptance Criteria
- One `POST` to the ingest edge (through APIM) results in one aggregated
  message delivered on `/ws` (through APIM).
- The post-deploy contract test (HARD-4) passes for every component.
- Malformed telemetry is rejected at the ingest edge with HTTP 4xx, not
  produced to `sensor_raw`.

## Acceptance blocks (structured — dev-agent contract)
> Schema: `factory/docs/contracts/requirements-acceptance-block.md`. The dev-agent turns each
> `kind: test` criterion into a failing pytest first (TDD red), then implements to green.

```acceptance
service: rtdemo2-ingest
criteria:
  - id: ing-1
    statement: "a valid reading is normalised and stamped with received_at"
    kind: test
    given: "a reading {sensor_id, value, ts} with a numeric value"
    when: "to_message is called"
    then: "it returns the reading with a received_at timestamp added"
  - id: ing-2
    statement: "a reading missing sensor_id is rejected"
    kind: test
    given: "a reading with no sensor_id"
    when: "to_message is called"
    then: "it raises ValueError (not produced to sensor_raw)"
  - id: ing-3
    statement: "a non-numeric value is rejected"
    kind: test
    given: "a reading whose value is non-numeric"
    when: "to_message is called"
    then: "it raises ValueError"
```

```acceptance
service: rtdemo2-processor
criteria:
  - id: proc-1
    statement: "rolling average of the last 10 values per sensor_id"
    kind: test
    given: "a sequence of readings for one sensor_id"
    when: "transform is called per reading"
    then: "the emitted message has rolling_avg over the last 10 values and a count"
  - id: proc-2
    statement: "malformed messages are dropped"
    kind: test
    given: "a message missing sensor_id or value"
    when: "transform is called"
    then: "it returns None (the message is dropped, not emitted)"
  - id: proc-3
    statement: "end-to-end one-in-one-out is proven post-deploy"
    kind: accepted-gap
    reason: "covered by the HARD-4 data-plane contract test (ct-<rev>), not a unit test"
```
