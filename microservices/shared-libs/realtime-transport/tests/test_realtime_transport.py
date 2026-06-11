"""Tests for realtime-transport: config binding resolution, role factories,
ws-route registration, ws_json_default, and Kafka-init resilience.

Ported from agent-common/tests/test_realtime_config.py and adapted to the new
package (no AgentType/ImplementationType; identity is plain strings), plus new
ingest/processor/resilience coverage. aiokafka is mocked so no broker is needed.
"""

import json
import sys
import types

import pytest
from fastapi.testclient import TestClient

from realtime_transport.config import get_realtime_config
from realtime_transport.realtime_agent import GenericRealtimeAgent, RealtimeAgent
from realtime_transport.realtime_fastapi import (
    create_realtime_agent_app,
    create_realtime_ingest_app,
    create_realtime_processor_app,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in list(__import__("os").environ):
        if k.startswith(("CONSUME_", "PRODUCE_")) or k in (
            "STREAMING_TOPICS", "WEBSOCKET_ENABLED", "REALTIME_PLATFORM",
            "REALTIME_PLATFORM_NAME", "KAFKA_BOOTSTRAP_SERVERS",
        ):
            monkeypatch.delenv(k, raising=False)


# --- (A) config requires NO agent identity ----------------------------------

def test_config_needs_no_agent_identity():
    cfg = get_realtime_config("rtdemo-gateway")
    assert cfg.service_name == "rtdemo-gateway"


def test_service_name_defaults_from_env(monkeypatch):
    monkeypatch.setenv("SERVICE_NAME", "rtdemo-ingest")
    assert get_realtime_config().service_name == "rtdemo-ingest"


# --- (B) GenericRealtimeAgent concrete + plain-string identity --------------

def test_generic_realtime_agent_instantiable():
    cfg = get_realtime_config("rtdemo")
    agent = GenericRealtimeAgent(agent_type="rtdemo", agent_name="rtdemo-gw",
                                 description="x", config=cfg)
    assert agent._get_supported_task_types() == ["stream", "passthrough"]


def test_realtime_agent_is_concrete():
    # Divergence from agent_common: base is concrete here (no abstract methods).
    cfg = get_realtime_config("x")
    agent = RealtimeAgent(service_type="x", service_name="x", description="x", config=cfg)
    assert agent.name == "x"


def test_status_accepts_freeform_service_type():
    cfg = get_realtime_config("rtdemo-gateway")
    agent = GenericRealtimeAgent(agent_type="rtdemo", agent_name="rtdemo-gateway",
                                 description="x", config=cfg)
    status = agent.get_realtime_status()
    assert status.service_type == "rtdemo"
    assert isinstance(status.service_name, str)


# --- binding-env resolution -------------------------------------------------

def test_realtime_platform_from_cd_env_name(monkeypatch):
    monkeypatch.setenv("REALTIME_PLATFORM_NAME", "rtdemo-stream")
    assert get_realtime_config("x").realtime_platform == "rtdemo-stream"


def test_streaming_topics_from_consume_binding(monkeypatch):
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")
    monkeypatch.setenv("CONSUME_other", "other")
    assert get_realtime_config("x").streaming_topics == ["other", "sensor_agg"]


def test_streaming_topics_explicit_precedence(monkeypatch):
    monkeypatch.setenv("STREAMING_TOPICS", "a,b")
    monkeypatch.setenv("CONSUME_x", "x")
    assert get_realtime_config("x").streaming_topics == ["a", "b"]


def test_produce_topics_from_produce_binding(monkeypatch):
    monkeypatch.setenv("PRODUCE_sensor_raw", "sensor_raw")
    monkeypatch.setenv("PRODUCE_z", "z")
    assert get_realtime_config("x").produce_topics == ["sensor_raw", "z"]


# --- ws route registration at BUILD time ------------------------------------

def _ws_routes(app):
    return [r.path for r in app.routes if r.__class__.__name__ == "APIWebSocketRoute"]


def test_ws_route_registered_with_env(monkeypatch):
    monkeypatch.setenv("WEBSOCKET_ENABLED", "true")
    app = create_realtime_agent_app(
        agent_class=GenericRealtimeAgent, service_name="rtdemo-stream",
        description="x", websocket_endpoints=[{"path": "/ws"}],
    )
    routes = _ws_routes(app)
    assert "/ws" in routes
    assert routes.count("/ws") == 1  # reserved-path skip: not double-registered


def test_ws_route_skipped_when_disabled(monkeypatch):
    monkeypatch.delenv("WEBSOCKET_ENABLED", raising=False)
    app = create_realtime_agent_app(
        agent_class=GenericRealtimeAgent, service_name="plain", description="x",
    )
    assert _ws_routes(app) == []


# --- ws payload serialization (datetime/Enum) -------------------------------

def test_ws_json_default_serializes_event_payload():
    from realtime_transport.models import (
        ws_json_default, WebSocketMessage, RealtimeEvent, EventType,
    )
    ev = RealtimeEvent(
        event_type=EventType.DATA_PROCESSED, source_service="rtdemo-stream",
        source_agent="rtdemo",
        data={"topic": "sensor_agg", "message": {"marker": "RT2-TELEMETRY"}},
    )
    msg = WebSocketMessage(message_type="event", payload=ev.__dict__,
                           correlation_id=ev.correlation_id)
    out = json.dumps(msg.dict(), default=ws_json_default)
    assert "RT2-TELEMETRY" in out
    assert "data_processed" in out  # EventType -> .value


# --- a fake aiokafka so apps build/start without a broker -------------------

class _FakeProducer:
    sent = []

    def __init__(self, *a, **k):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_and_wait(self, topic, value, key=None):
        _FakeProducer.sent.append((topic, value, key))


class _FakeConsumer:
    def __init__(self, *a, **k):
        self._topics = a

    async def start(self):
        pass

    async def stop(self):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


def _install_fake_aiokafka(monkeypatch, producer=_FakeProducer, consumer=_FakeConsumer):
    mod = types.ModuleType("aiokafka")
    mod.AIOKafkaProducer = producer
    mod.AIOKafkaConsumer = consumer
    monkeypatch.setitem(sys.modules, "aiokafka", mod)


# --- ingest: POST /ingest produces via the (mocked) producer ----------------

def test_ingest_produces_on_post(monkeypatch):
    _FakeProducer.sent = []
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("PRODUCE_sensor_raw", "sensor_raw")

    app = create_realtime_ingest_app(service_name="rtdemo-ingest")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        resp = client.post("/ingest", json={"v": 42})
        assert resp.status_code == 200
        assert resp.json()["topic"] == "sensor_raw"
    assert _FakeProducer.sent == [("sensor_raw", {"v": 42}, None)]


def test_ingest_custom_to_message(monkeypatch):
    _FakeProducer.sent = []
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")

    app = create_realtime_ingest_app(
        service_name="rtdemo-ingest", produce_topic="sensor_raw",
        to_message=lambda b: {"doubled": b["v"] * 2},
    )
    with TestClient(app) as client:
        client.post("/ingest", json={"v": 5})
    assert _FakeProducer.sent[0][1] == {"doubled": 10}


# --- processor: transform -> produce (identity default) ---------------------

def test_processor_transform_produces(monkeypatch):
    _FakeProducer.sent = []
    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_raw", "sensor_raw")
    monkeypatch.setenv("PRODUCE_sensor_agg", "sensor_agg")

    app = create_realtime_processor_app(
        service_name="rtdemo-proc",
        transform=lambda m: {"avg": m["x"]},
        agent_class=_CapturingAgent,
    )
    with TestClient(app):
        handler = captured["sensor_raw"]
    import asyncio
    asyncio.run(handler({"x": 7}))
    assert _FakeProducer.sent == [("sensor_agg", {"avg": 7}, None)]


def test_processor_transform_none_filters(monkeypatch):
    _FakeProducer.sent = []
    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_raw", "sensor_raw")
    monkeypatch.setenv("PRODUCE_sensor_agg", "sensor_agg")

    app = create_realtime_processor_app(
        service_name="rtdemo-proc", transform=lambda m: None,
        agent_class=_CapturingAgent,
    )
    with TestClient(app):
        handler = captured["sensor_raw"]
    import asyncio
    asyncio.run(handler({"x": 1}))
    assert _FakeProducer.sent == []  # None result is filtered, never produced


# --- RT-SVC-RESILIENCE: Kafka unreachable -> app still builds, /health 200 --

def test_ingest_resilient_when_kafka_unreachable(monkeypatch):
    class _BrokenProducer(_FakeProducer):
        async def start(self):
            raise ConnectionError("broker down")

    _install_fake_aiokafka(monkeypatch, producer=_BrokenProducer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "down:9092")
    monkeypatch.setenv("PRODUCE_sensor_raw", "sensor_raw")

    app = create_realtime_ingest_app(service_name="rtdemo-ingest")
    with TestClient(app) as client:
        # Startup must NOT crash; /health stays 200 even though Kafka is down.
        assert client.get("/health").status_code == 200


def test_gateway_resilient_when_kafka_unreachable(monkeypatch):
    class _BrokenProducer(_FakeProducer):
        async def start(self):
            raise ConnectionError("broker down")

    _install_fake_aiokafka(monkeypatch, producer=_BrokenProducer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "down:9092")
    monkeypatch.setenv("WEBSOCKET_ENABLED", "true")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")

    app = create_realtime_agent_app(service_name="rtdemo-gw",
                                    websocket_endpoints=[{"path": "/ws"}])
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
