"""Unit tests for LifecycleQueryUseCase (lifecycle.state MCP tool).

Mocks AuditSinkClient.get_events; asserts the reconstructed state +
history shape.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lifecycle_query_use_case import LifecycleQueryUseCase


def _client_with_events(events: list[dict]) -> MagicMock:
    m = MagicMock()
    m.get_events.return_value = events
    return m


def test_returns_empty_when_no_events():
    client = _client_with_events([])
    out = LifecycleQueryUseCase(client).state_of("uc-1")
    assert out["ok"] is True
    assert out["use_case_id"] == "uc-1"
    assert out["current_state"] is None
    assert out["event_count"] == 0
    assert out["history"] == []


def test_returns_current_state_from_latest_event():
    events = [
        {"from_state": "_initial", "to_state": "received", "_recorded_at": 1.0,
         "caller_identity": "n8n"},
        {"from_state": "received", "to_state": "classifying", "_recorded_at": 2.0,
         "caller_identity": "n8n"},
        {"from_state": "classifying", "to_state": "classified", "_recorded_at": 3.0,
         "caller_identity": "n8n"},
    ]
    out = LifecycleQueryUseCase(_client_with_events(events)).state_of("uc-2")
    assert out["ok"] is True
    assert out["current_state"] == "classified"
    assert out["event_count"] == 3
    assert len(out["history"]) == 3
    assert out["history"][0] == {
        "from": "_initial", "to": "received", "at": 1.0, "caller": "n8n",
    }


def test_history_preserves_caller_identity():
    events = [
        {"from_state": "approval_requested", "to_state": "approved",
         "_recorded_at": 10.0, "caller_identity": "alice@example.com"},
    ]
    out = LifecycleQueryUseCase(_client_with_events(events)).state_of("uc-3")
    assert out["history"][0]["caller"] == "alice@example.com"


def test_rejects_empty_use_case_id():
    out = LifecycleQueryUseCase(MagicMock()).state_of("")
    assert out["ok"] is False
    assert "required" in out["error"]


def test_handles_client_failure():
    client = MagicMock()
    client.get_events.side_effect = RuntimeError("audit-sink down")
    out = LifecycleQueryUseCase(client).state_of("uc-x")
    assert out["ok"] is False
    assert "audit-sink down" in out["error"]


def test_handles_full_happy_path():
    """The end-to-end lifecycle for a /microservice Slack request."""
    transitions = [
        ("_initial", "received"),
        ("received", "classifying"),
        ("classifying", "classified"),
        ("classified", "composing"),
        ("composing", "composed"),
        ("composed", "governing"),
        ("governing", "governed"),
        ("governed", "approval_requested"),
        ("approval_requested", "approved"),
        ("approved", "submitting"),
        ("submitting", "executing"),
    ]
    events = [
        {
            "from_state": frm, "to_state": to, "_recorded_at": float(idx),
            "caller_identity": "slack",
        }
        for idx, (frm, to) in enumerate(transitions)
    ]
    out = LifecycleQueryUseCase(_client_with_events(events)).state_of("uc-happy")
    assert out["current_state"] == "executing"
    assert out["event_count"] == 11
