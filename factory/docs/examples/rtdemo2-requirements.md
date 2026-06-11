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
