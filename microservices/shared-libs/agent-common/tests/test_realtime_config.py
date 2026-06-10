"""Regression tests for the RT-1 (#167) realtime-gateway lib fixes.

Two additive changes to agent_common are guarded here:
  (A) get_agent_config() accepts optional default_agent_type /
      default_implementation_type so a non-AI-agent consumer (the realtime
      stream gateway) isn't forced to set AGENT_TYPE / IMPLEMENTATION_TYPE,
      WITHOUT weakening the requirement for the 18 AI-agent microservices that
      call it with no args.
  (B) GenericRealtimeAgent is a concrete, instantiable RealtimeAgent (the base
      left _create_processor / _get_supported_task_types abstract).
"""

import os

import pytest

from agent_common.config import get_agent_config
from agent_common.realtime_agent import GenericRealtimeAgent, RealtimeAgent
from agent_common.realtime_fastapi import create_realtime_agent_app


@pytest.fixture(autouse=True)
def _clear_agent_env(monkeypatch):
    monkeypatch.delenv("AGENT_TYPE", raising=False)
    monkeypatch.delenv("IMPLEMENTATION_TYPE", raising=False)


# --- (A) get_agent_config defaults -----------------------------------------

def test_defaults_used_when_env_absent():
    cfg = get_agent_config(
        default_agent_type="orchestrator",
        default_implementation_type="deterministic",
    )
    assert cfg.service_name == "orchestrator-deterministic"


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("AGENT_TYPE", "developer")
    monkeypatch.setenv("IMPLEMENTATION_TYPE", "anthropic")
    cfg = get_agent_config(default_agent_type="orchestrator")
    assert cfg.service_name == "developer-anthropic"


def test_regression_still_required_without_defaults():
    # The 18 AI-agent microservices call with no args; the contract must hold.
    with pytest.raises(ValueError, match="AGENT_TYPE"):
        get_agent_config()


# --- (B) GenericRealtimeAgent concrete --------------------------------------

def test_generic_realtime_agent_instantiable():
    cfg = get_agent_config(
        default_agent_type="orchestrator",
        default_implementation_type="deterministic",
    )
    agent = GenericRealtimeAgent(
        agent_type="orchestrator",
        agent_name="rtdemo",
        description="x",
        config=cfg,
    )
    assert agent._get_supported_task_types() == ["stream", "passthrough"]
    assert agent.processor is not None


def test_base_realtime_agent_still_abstract():
    cfg = get_agent_config(
        default_agent_type="orchestrator",
        default_implementation_type="deterministic",
    )
    with pytest.raises(TypeError):
        RealtimeAgent(
            agent_type="orchestrator",
            agent_name="x",
            description="x",
            config=cfg,
        )


# --- get_realtime_status feeds the /health readiness probe ------------------

def test_get_realtime_status_accepts_freeform_service_type():
    # The gateway's agent_type is a service-name fragment ("rtdemo"), NOT an
    # AgentType enum. AgentRealtimeStatus must accept it as a plain string,
    # otherwise /health 500s and the Knative readiness probe never passes
    # (regression for RT-1 #167 "Initial scale was never achieved").
    cfg = get_agent_config(
        default_agent_type="orchestrator",
        default_implementation_type="deterministic",
    )
    agent = GenericRealtimeAgent(
        agent_type="rtdemo",
        agent_name="rtdemo-gateway",
        description="x",
        config=cfg,
    )
    status = agent.get_realtime_status()
    assert status.agent_type == "rtdemo"
    assert isinstance(status.implementation_type, str)


# --- /ws route must register at app-BUILD time (config loads later) ----------

def _ws_routes(app):
    return [r.path for r in app.routes if r.__class__.__name__ == "APIWebSocketRoute"]


def test_ws_route_registered_with_env_when_config_none(monkeypatch):
    # Gateway case: config is None at build time (loaded later in lifespan).
    # WEBSOCKET_ENABLED env must still trigger /ws registration, else /ws 404s
    # and the readiness probe / clients fail (RT-1 #167).
    monkeypatch.setenv("WEBSOCKET_ENABLED", "true")
    app = create_realtime_agent_app(
        agent_class=GenericRealtimeAgent,
        service_name="rtdemo-stream",
        description="x",
        endpoints=[],
        websocket_endpoints=[{"path": "/ws"}],
    )
    routes = _ws_routes(app)
    assert "/ws" in routes
    # reserved-path skip: /ws not double-registered despite being in the list
    assert routes.count("/ws") == 1


def test_ws_route_skipped_when_disabled(monkeypatch):
    monkeypatch.delenv("WEBSOCKET_ENABLED", raising=False)
    app = create_realtime_agent_app(
        agent_class=GenericRealtimeAgent,
        service_name="plain",
        description="x",
        endpoints=[],
    )
    assert _ws_routes(app) == []


# --- data-flow wiring: gateway must consume its declared topic --------------

def test_realtime_platform_from_cd_env_name(monkeypatch):
    # CD injects REALTIME_PLATFORM_NAME; without honoring it realtime_platform
    # stays None and the Kafka consumer/producer never initialize (no data → ws).
    monkeypatch.delenv("REALTIME_PLATFORM", raising=False)
    monkeypatch.setenv("REALTIME_PLATFORM_NAME", "rtdemo-stream")
    cfg = get_agent_config(default_agent_type="orchestrator", default_implementation_type="deterministic")
    assert cfg.realtime_platform == "rtdemo-stream"


def test_streaming_topics_from_consume_binding(monkeypatch):
    # CD injects CONSUME_<topic>=<topic>; the consumer must subscribe to it.
    monkeypatch.delenv("STREAMING_TOPICS", raising=False)
    monkeypatch.setenv("CONSUME_sensor_agg", "sensor_agg")
    monkeypatch.setenv("CONSUME_other", "other")
    cfg = get_agent_config(default_agent_type="orchestrator", default_implementation_type="deterministic")
    assert cfg.streaming_topics == ["other", "sensor_agg"]  # sorted


def test_streaming_topics_explicit_precedence(monkeypatch):
    monkeypatch.setenv("STREAMING_TOPICS", "a,b")
    monkeypatch.setenv("CONSUME_x", "x")
    cfg = get_agent_config(default_agent_type="orchestrator", default_implementation_type="deterministic")
    assert cfg.streaming_topics == ["a", "b"]
