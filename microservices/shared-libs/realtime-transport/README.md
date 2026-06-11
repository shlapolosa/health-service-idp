# realtime-transport

Role-aware realtime **transport** machinery — `ingest`, `processor`, `gateway` —
extracted from `agent_common` (RT-1, #167) **without the AI-agent identity baggage**.
The package owns bytes-in / bytes-out (Kafka/MQTT consume+produce, WebSocket fan-out,
JWT gate, binding-env resolution); the developer owns what the bytes mean.

This is a standalone Poetry package. `agent_common` is left untouched — the 18 AI
agents keep using it. Scaffolded realtime services should depend on **this** package.

## Roles

| Factory | Role | Surface | Dev slot |
|---|---|---|---|
| `create_realtime_ingest_app(service_name, produce_topic=None, to_message=None)` | ingest | `POST /ingest`, `/health` | `to_message(body) -> dict` (default: passthrough) |
| `create_realtime_processor_app(service_name, consume_topics=None, produce_topic=None, transform=None)` | processor | `/health` | `transform(msg) -> dict \| None` (default: identity; `None` filters) |
| `create_realtime_agent_app(service_name, websocket_endpoints=[{path:/ws}])` | gateway | `/ws`, `/health`, `/` | usually nothing (passthrough) |

- `produce_topic` defaults to the first `PRODUCE_*` binding env (the realtime-service CD injects these).
- `consume_topics` defaults to `CONSUME_*` / `STREAMING_TOPICS` (config resolution).
- `REALTIME_PLATFORM_NAME` triggers the best-effort platform-secret overlay.

## Resilience (RT-SVC-RESILIENCE)

Kafka init is **non-fatal** for all three roles. If the broker is unreachable at
startup the app still serves `/health` and `/ws`, logs the failure, and reconnects
in the background with capped exponential backoff. A broker blip never takes down
the HTTP ingest edge or live ws connections.

## Divergence from `agent_common`

- No `AgentType` / `ImplementationType` enums — identity is a plain string (`service_name`).
- No `BaseMicroserviceAgent` / `BaseProcessor` — the minimal lifecycle is inlined;
  this package has **zero** dependency on `agent_common`. `RealtimeAgent` is concrete
  (no abstract `_create_processor` / `_get_supported_task_types`); `GenericRealtimeAgent`
  is a thin alias kept for entrypoint naming compatibility.
- The AI-agent HTTP task endpoints (`AgentRequestModel` / `process_task` wiring) are dropped.

## Install (pinned wheel)

The CI publishes a wheel as a GitHub Release asset on every change under this path.
Scaffolds pin-install it (do **not** rely on `latest`):

```bash
pip install https://github.com/shlapolosa/health-service-idp/releases/download/realtime-transport-v0.1.0/realtime_transport-0.1.0-py3-none-any.whl
```

Bump `version` in `pyproject.toml` to cut a new release tag (`realtime-transport-v<version>`).

## Test

```bash
cd microservices/shared-libs/realtime-transport
PYTHONPATH=src python -m pytest tests/ -q
```
