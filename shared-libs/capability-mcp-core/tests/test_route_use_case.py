"""Unit tests for RouteUseCase (factory.route MCP tool).

Mocks classify-router HTTP responses; asserts shape conformance + error handling.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.route_use_case import RouteUseCase


def _client_returning(payload: dict) -> MagicMock:
    m = MagicMock()
    m.classify.return_value = payload
    return m


def test_route_returns_ok_with_traditional_cloud():
    client = _client_returning({
        "archetype": "web-service-api-gateway",
        "manufacturer": "traditional-cloud",
        "confidence": 0.85,
        "action": "proceed",
        "rationale": "matched M2 branch",
        "alternates": [],
    })
    out = RouteUseCase(client).route("build me a python webservice")
    assert out["ok"] is True
    assert out["manufacturer"] == "traditional-cloud"
    assert out["archetype"] == "web-service-api-gateway"
    assert out["confidence"] == 0.85
    assert out["action"] == "proceed"


def test_route_includes_sub_archetype_when_returned():
    client = _client_returning({
        "archetype": "datastore-backed-service",
        "sub_archetype": "relational-postgres",
        "manufacturer": "traditional-cloud",
        "confidence": 0.9,
        "action": "proceed",
    })
    out = RouteUseCase(client).route("webservice with postgres")
    assert out["sub_archetype"] == "relational-postgres"


def test_route_returns_unknown_manufacturer_on_fallback():
    client = _client_returning({
        "archetype": "_unknown_",
        "manufacturer": "_unknown_",
        "confidence": 0.0,
        "action": "ask-clarifying-question",
        "rationale": "no branch matched",
    })
    out = RouteUseCase(client).route("totally ambiguous request")
    assert out["ok"] is True
    assert out["manufacturer"] == "_unknown_"
    assert out["action"] == "ask-clarifying-question"


def test_route_handles_other_manufacturer():
    """The contract MUST support more than one manufacturer — proves
    multi-mfg shape works even before MFG-AI is built."""
    client = _client_returning({
        "archetype": "agentic-workflow",
        "manufacturer": "ai-use-case",
        "confidence": 0.78,
        "action": "proceed",
    })
    out = RouteUseCase(client).route("build me a multi-agent reasoning system")
    assert out["manufacturer"] == "ai-use-case"


def test_route_rejects_empty_description():
    client = MagicMock()
    out = RouteUseCase(client).route("")
    assert out["ok"] is False
    assert "non-empty" in out["error"]
    client.classify.assert_not_called()


def test_route_rejects_whitespace_description():
    client = MagicMock()
    out = RouteUseCase(client).route("   \n  ")
    assert out["ok"] is False


def test_route_handles_client_exception():
    client = MagicMock()
    client.classify.side_effect = RuntimeError("connection refused")
    out = RouteUseCase(client).route("build me a webservice")
    assert out["ok"] is False
    assert "connection refused" in out["error"]


def test_route_handles_missing_fields_gracefully():
    """classify-router may return partial responses — defaults must apply."""
    client = _client_returning({})
    out = RouteUseCase(client).route("foo")
    assert out["ok"] is True
    assert out["manufacturer"] == "_unknown_"
    assert out["confidence"] == 0.0
    assert out["action"] == "ask-clarifying-question"
