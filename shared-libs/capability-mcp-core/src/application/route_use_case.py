"""Route use case — wraps classify-router for MCP exposure as `factory.route`.

Why this lives in capability-mcp-server today: the monolithic catalog MCP is
the only deployed factory-facing MCP. After the S2 split, factory.route moves
to capability-mcp-factory (where it conceptually belongs — it's a factory
port, not an MFG-TC concern). Until then, registering it here is the
simplest additive move.

The use case is intentionally thin: validation + structured return shape.
Routing logic itself lives in classify-router's M2 decision tree.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..infrastructure.classify_router_client import ClassifyRouterClient

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """The MCP-exposed shape of a routing decision."""

    manufacturer: str
    archetype: str
    confidence: float
    action: str
    sub_archetype: str | None = None
    rationale: str = ""
    alternates: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "manufacturer": self.manufacturer,
            "archetype": self.archetype,
            "sub_archetype": self.sub_archetype,
            "confidence": self.confidence,
            "action": self.action,
            "rationale": self.rationale,
            "alternates": self.alternates or [],
        }


@dataclass
class RouteUseCase:
    """factory.route: ask classify-router which production line should
    produce this use-case."""

    client: ClassifyRouterClient

    def route(self, plain_text_description: str) -> dict[str, Any]:
        """Return the manufacturer + archetype + confidence + action.

        Adding a new manufacturer is a definition-only change: extend
        classify-router's M2 decision tree YAML; this code does not
        need to know which manufacturers exist.
        """
        if not plain_text_description or not plain_text_description.strip():
            return {
                "ok": False,
                "error": "plain_text_description must be non-empty",
            }
        try:
            raw = self.client.classify(plain_text_description)
        except Exception as e:
            logger.exception("classify-router call failed")
            return {"ok": False, "error": str(e)}

        result = RouteResult(
            manufacturer=raw.get("manufacturer", "_unknown_"),
            archetype=raw.get("archetype", "_unknown_"),
            confidence=float(raw.get("confidence", 0.0)),
            action=raw.get("action", "ask-clarifying-question"),
            sub_archetype=raw.get("sub_archetype"),
            rationale=raw.get("rationale", ""),
            alternates=raw.get("alternates", []),
        )
        return {"ok": True, **result.as_dict()}
