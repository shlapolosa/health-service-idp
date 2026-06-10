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
