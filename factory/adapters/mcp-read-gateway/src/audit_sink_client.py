"""HTTP client for the cafe-spec observe-audit-sink adapter.

observe-audit-sink is the factory-level Observe port. It stores an
append-only, hash-chained log of lifecycle state events emitted by
lifecycle-orchestrator. We read it to reconstruct "where is this
use-case now?" for the lifecycle.state MCP tool.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class AuditSinkClient:
    """Thin client for observe-audit-sink's GET /events endpoint."""

    base_url: str
    timeout_seconds: float = 5.0

    def get_events(self, use_case_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """Return all recorded events for a use_case_id, oldest first."""
        if not use_case_id:
            raise ValueError("use_case_id required")
        url = f"{self.base_url.rstrip('/')}/events"
        params = {"use_case_id": use_case_id, "limit": limit}
        resp = requests.get(url, params=params, timeout=self.timeout_seconds)
        if resp.status_code >= 400:
            raise ValueError(
                f"observe-audit-sink returned {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        events = data.get("events", []) if isinstance(data, dict) else []
        # Sort oldest first by _recorded_at for monotonic state reconstruction.
        return sorted(events, key=lambda e: e.get("_recorded_at", 0.0))
