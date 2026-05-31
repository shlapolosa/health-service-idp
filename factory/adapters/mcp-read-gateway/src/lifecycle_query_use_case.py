"""lifecycle.state use case — reconstructs use-case state from audit events.

Reads observe-audit-sink's append-only log via AuditSinkClient and rebuilds
the use-case's state trajectory:

  {
    "use_case_id": "...",
    "current_state": "executing",
    "history": [
      {"from": "_initial", "to": "received", "at": 1...},
      {"from": "received", "to": "classifying", "at": 1...},
      ...
    ],
    "event_count": 12
  }

The orchestrator's state emissions are best-effort (fire-and-forget).
If events are dropped during an audit-sink outage, the reconstructed
history is missing those transitions but `current_state` still reflects
the latest recorded event. Operators reading this can spot gaps by
checking event_count vs expected pipeline length.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .audit_sink_client import AuditSinkClient

logger = logging.getLogger(__name__)


@dataclass
class LifecycleQueryUseCase:
    """lifecycle.state(use_case_id) — what state is this use-case in right now?"""

    client: AuditSinkClient

    def state_of(self, use_case_id: str) -> dict[str, Any]:
        if not use_case_id or not str(use_case_id).strip():
            return {"ok": False, "error": "use_case_id required"}

        try:
            events = self.client.get_events(use_case_id)
        except Exception as e:
            logger.exception("audit-sink fetch failed")
            return {"ok": False, "error": str(e)}

        if not events:
            return {
                "ok": True,
                "use_case_id": use_case_id,
                "current_state": None,
                "history": [],
                "event_count": 0,
                "note": "no events recorded yet — use-case may not have been intook",
            }

        history = [
            {
                "from": e.get("from_state"),
                "to": e.get("to_state"),
                "at": e.get("_recorded_at"),
                "caller": e.get("caller_identity"),
            }
            for e in events
        ]
        latest = events[-1]
        return {
            "ok": True,
            "use_case_id": use_case_id,
            "current_state": latest.get("to_state"),
            "history": history,
            "event_count": len(events),
        }
