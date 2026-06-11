# realtime-transport tests

Repeatable regression suite. No Kafka broker required — `aiokafka` is mocked via
`sys.modules` so producer/consumer start without a network.

## Run

```bash
cd microservices/shared-libs/realtime-transport
PYTHONPATH=src python -m pytest tests/ -q
```

## Coverage

- **config binding resolution**: `CONSUME_*`/`STREAMING_TOPICS` -> streaming_topics,
  `PRODUCE_*` -> produce_topics, `REALTIME_PLATFORM_NAME` fallback; no agent identity required.
- **agent**: `GenericRealtimeAgent` / `RealtimeAgent` concrete + instantiable;
  status uses free-form string identity.
- **ws route registration** at build time (`WEBSOCKET_ENABLED` env / `websocket_endpoints`);
  reserved-path skip; disabled -> no `/ws`.
- **ws_json_default** serializes Enum/datetime payloads (RT-1 #167 drop bug).
- **ingest**: `POST /ingest` produces via mocked producer; custom `to_message`.
- **processor**: `transform -> produce`; identity default; `None` filters (no produce).
- **resilience**: Kafka unreachable -> ingest + gateway still build, `/health` 200.
