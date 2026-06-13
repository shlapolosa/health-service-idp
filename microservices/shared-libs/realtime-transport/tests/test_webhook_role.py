"""Tests for the webhook role (RT bridge): the Svix webhook sink + the
consume->sink wiring of create_realtime_webhook_app.

aiokafka is mocked (no broker) and httpx is mocked (no Svix), mirroring the
existing role tests. Covers:
  * sink POSTs the correct body + headers to the Svix /msg endpoint,
  * engine_api normalization (with/without /api/v1),
  * default dotted event-type fallback + explicit mapping precedence,
  * topic->event-type map built from WEBHOOK_EVENTTYPE_<topic> env,
  * app wires consume->sink (the captured handler calls the injected sink),
  * to_event/identity default,
  * non-fatal: transient Svix error is logged+dropped (no raise),
  * non-breaking: the other roles still build.
"""

import asyncio
import sys
import types

import pytest
from fastapi.testclient import TestClient

from realtime_transport import (
    create_realtime_webhook_app,
    create_realtime_ingest_app,
    create_realtime_processor_app,
    make_webhook_sink,
)
from realtime_transport.realtime_agent import GenericRealtimeAgent
from realtime_transport.realtime_fastapi import _topic_event_type_map_from_env


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    import os
    for k in list(os.environ):
        if k.startswith(("CONSUME_", "PRODUCE_", "WEBHOOK_")) or k in (
            "STREAMING_TOPICS", "KAFKA_BOOTSTRAP_SERVERS",
        ):
            monkeypatch.delenv(k, raising=False)


# --- a fake aiokafka so the webhook app builds/starts without a broker ------

class _FakeProducer:
    def __init__(self, *a, **k):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass


class _FakeConsumer:
    def __init__(self, *a, **k):
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


def _install_fake_aiokafka(monkeypatch):
    mod = types.ModuleType("aiokafka")
    mod.AIOKafkaProducer = _FakeProducer
    mod.AIOKafkaConsumer = _FakeConsumer
    monkeypatch.setitem(sys.modules, "aiokafka", mod)


# --- a fake httpx so the sink hits no network -------------------------------

class _FakeResponse:
    def __init__(self, status_code=202, text=""):
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    # class-level capture so the test can assert what was POSTed.
    calls = []
    status = 202
    raise_n = 0  # number of leading attempts that raise (for retry tests)
    _attempt = 0

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeAsyncClient.calls.append({"url": url, "json": json, "headers": headers})
        _FakeAsyncClient._attempt += 1
        if _FakeAsyncClient._attempt <= _FakeAsyncClient.raise_n:
            raise RuntimeError("boom (transient)")
        return _FakeResponse(status_code=_FakeAsyncClient.status)


def _install_fake_httpx(monkeypatch, status=202, raise_n=0):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status = status
    _FakeAsyncClient.raise_n = raise_n
    _FakeAsyncClient._attempt = 0
    mod = types.ModuleType("httpx")
    mod.AsyncClient = _FakeAsyncClient
    monkeypatch.setitem(sys.modules, "httpx", mod)


# --- (A) the sink: body + headers + URL -------------------------------------

def test_sink_posts_correct_body_and_headers(monkeypatch):
    _install_fake_httpx(monkeypatch)
    sink = make_webhook_sink(
        engine_api="http://wd-svix.wd-webhook.svc.cluster.local:8071/api/v1",
        admin_token="tok123",
        app_id="platform-events",
        topic_to_event_type={"sensor_agg": "sensor.agg"},
    )
    asyncio.run(sink("sensor_agg", {"avg": 7}))
    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == (
        "http://wd-svix.wd-webhook.svc.cluster.local:8071/api/v1/app/platform-events/msg"
    )
    assert call["json"] == {"eventType": "sensor.agg", "payload": {"avg": 7}}
    assert call["headers"]["Authorization"] == "Bearer tok123"


def test_sink_normalizes_engine_api_without_api_v1(monkeypatch):
    _install_fake_httpx(monkeypatch)
    sink = make_webhook_sink(
        engine_api="http://wd-svix.wd-webhook.svc.cluster.local:8071",
        admin_token="t", app_id="app1",
    )
    asyncio.run(sink("sensor_agg", {"x": 1}))
    assert _FakeAsyncClient.calls[0]["url"].endswith("/api/v1/app/app1/msg")


def test_sink_default_dotted_event_type(monkeypatch):
    _install_fake_httpx(monkeypatch)
    sink = make_webhook_sink(engine_api="http://e/api/v1", admin_token="t", app_id="a")
    asyncio.run(sink("sensor_agg", {"x": 1}))
    # no explicit mapping -> dotted topic name
    assert _FakeAsyncClient.calls[0]["json"]["eventType"] == "sensor.agg"


def test_sink_explicit_mapping_precedence(monkeypatch):
    _install_fake_httpx(monkeypatch)
    sink = make_webhook_sink(
        engine_api="http://e/api/v1", admin_token="t", app_id="a",
        topic_to_event_type={"sensor_agg": "my.custom.type"},
    )
    asyncio.run(sink("sensor_agg", {"x": 1}))
    assert _FakeAsyncClient.calls[0]["json"]["eventType"] == "my.custom.type"


def test_sink_non_fatal_on_5xx_retries_then_drops(monkeypatch):
    # 5xx every time -> two attempts, then logged + dropped (no raise).
    _install_fake_httpx(monkeypatch, status=503)
    sink = make_webhook_sink(engine_api="http://e/api/v1", admin_token="t", app_id="a")
    asyncio.run(sink("sensor_agg", {"x": 1}))  # must NOT raise
    assert len(_FakeAsyncClient.calls) == 2  # one retry


def test_sink_non_fatal_on_transient_then_succeeds(monkeypatch):
    # first attempt raises, second succeeds (202).
    _install_fake_httpx(monkeypatch, status=202, raise_n=1)
    sink = make_webhook_sink(engine_api="http://e/api/v1", admin_token="t", app_id="a")
    asyncio.run(sink("sensor_agg", {"x": 1}))
    assert len(_FakeAsyncClient.calls) == 2


def test_sink_drops_on_4xx_without_retry(monkeypatch):
    _install_fake_httpx(monkeypatch, status=401)
    sink = make_webhook_sink(engine_api="http://e/api/v1", admin_token="bad", app_id="a")
    asyncio.run(sink("sensor_agg", {"x": 1}))
    assert len(_FakeAsyncClient.calls) == 1  # 4xx won't fix on retry


# --- (B) topic->event-type map from env -------------------------------------

def test_eventtype_map_from_env(monkeypatch):
    monkeypatch.setenv("WEBHOOK_EVENTTYPE_sensor_agg", "sensor.agg")
    monkeypatch.setenv("WEBHOOK_EVENTTYPE_other_topic", "other.topic")
    monkeypatch.setenv("WEBHOOK_ENGINE_API", "http://e/api/v1")  # not a mapping
    m = _topic_event_type_map_from_env()
    assert m == {"sensor_agg": "sensor.agg", "other_topic": "other.topic"}


# --- (C) app wires consume -> sink ------------------------------------------

def test_webhook_app_wires_consume_to_sink(monkeypatch):
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")

    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    received = []

    async def fake_sink(topic, message):
        received.append((topic, message))

    app = create_realtime_webhook_app(
        service_name="wd-bridge", sink=fake_sink, agent_class=_CapturingAgent,
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        handler = captured["sensor_agg"]
    asyncio.run(handler({"avg": 7}))
    assert received == [("sensor_agg", {"avg": 7})]


def test_webhook_app_to_event_default_identity(monkeypatch):
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")

    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    received = []

    async def fake_sink(topic, message):
        received.append(message)

    app = create_realtime_webhook_app(
        service_name="wd-bridge", sink=fake_sink, agent_class=_CapturingAgent,
    )
    with TestClient(app):
        handler = captured["sensor_agg"]
    asyncio.run(handler({"v": 1}))
    assert received == [{"v": 1}]  # identity to_event


def test_webhook_app_custom_to_event(monkeypatch):
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")

    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    received = []

    async def fake_sink(topic, message):
        received.append(message)

    app = create_realtime_webhook_app(
        service_name="wd-bridge", sink=fake_sink,
        to_event=lambda m: {"wrapped": m},
        agent_class=_CapturingAgent,
    )
    with TestClient(app):
        handler = captured["sensor_agg"]
    asyncio.run(handler({"v": 1}))
    assert received == [{"wrapped": {"v": 1}}]


def test_webhook_app_builds_default_sink_from_env(monkeypatch):
    # When no sink is injected, the app builds a Svix sink from binding env.
    _install_fake_aiokafka(monkeypatch)
    _install_fake_httpx(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")
    monkeypatch.setenv("WEBHOOK_ENGINE_API", "http://wd-svix.wd-webhook.svc:8071/api/v1")
    monkeypatch.setenv("WEBHOOK_ADMIN_TOKEN", "tok")
    monkeypatch.setenv("WEBHOOK_APP_ID", "platform-events")
    monkeypatch.setenv("WEBHOOK_EVENTTYPE_sensor_agg", "sensor.agg")

    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    app = create_realtime_webhook_app(service_name="wd-bridge", agent_class=_CapturingAgent)
    with TestClient(app):
        handler = captured["sensor_agg"]
    asyncio.run(handler({"avg": 7}))
    assert len(_FakeAsyncClient.calls) == 1
    assert _FakeAsyncClient.calls[0]["json"] == {
        "eventType": "sensor.agg", "payload": {"avg": 7},
    }
    assert _FakeAsyncClient.calls[0]["headers"]["Authorization"] == "Bearer tok"


def test_webhook_app_missing_env_is_non_fatal(monkeypatch):
    # No WEBHOOK_* env, no injected sink -> app still boots, /health 200,
    # message is dropped (logged) instead of crashing.
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")

    captured = {}

    class _CapturingAgent(GenericRealtimeAgent):
        def register_message_handler(self, topic, handler):
            captured[topic] = handler
            super().register_message_handler(topic, handler)

    app = create_realtime_webhook_app(service_name="wd-bridge", agent_class=_CapturingAgent)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        handler = captured["sensor_agg"]
    asyncio.run(handler({"avg": 7}))  # must NOT raise


# --- (D) non-breaking: other roles still build ------------------------------

def test_other_roles_still_build(monkeypatch):
    _install_fake_aiokafka(monkeypatch)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "fake:9092")
    monkeypatch.setenv("PRODUCE_sensor_raw", "sensor_raw")
    monkeypatch.setenv("CONSUME_sensor_raw", "sensor_raw")
    ingest = create_realtime_ingest_app(service_name="i")
    proc = create_realtime_processor_app(service_name="p")
    with TestClient(ingest) as ci:
        assert ci.get("/health").status_code == 200
    with TestClient(proc) as cp:
        assert cp.get("/health").status_code == 200
