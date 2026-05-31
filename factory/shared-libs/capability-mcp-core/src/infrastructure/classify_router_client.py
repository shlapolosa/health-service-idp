"""HTTP client for the cafe-spec classify-router adapter.

classify-router is a factory-level (cross-manufacturer) port: it accepts
a use-case description and returns which manufacturer should produce the
solution. Its M2 decision tree lives in cafe-spec; adding a new
manufacturer = adding a new branch (definition-only extensibility).

We expose its functionality as an MCP tool (factory.route) so consumer
agents — and the broader factory floor — can query routing without
needing to wire HTTP themselves.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class ClassifyRouterClient:
    """Thin HTTP client. classify-router is a stateless POST /classify endpoint."""

    base_url: str
    timeout_seconds: float = 5.0

    def classify(self, plain_text_description: str) -> dict[str, Any]:
        """Call POST /classify and return the routing decision.

        Raises requests.RequestException subclasses on transport failure;
        raises ValueError on non-2xx response with helpful diagnostics.
        """
        if not plain_text_description or not plain_text_description.strip():
            raise ValueError("plain_text_description must be non-empty")

        url = f"{self.base_url.rstrip('/')}/classify"
        body = {"plain_text_description": plain_text_description}
        resp = requests.post(url, json=body, timeout=self.timeout_seconds)
        if resp.status_code >= 400:
            raise ValueError(
                f"classify-router returned {resp.status_code}: {resp.text[:500]}"
            )
        return resp.json()
