"""Examples use-cases — exposes the pattern table + exemplar file reads to MCP tools.

Thin wrapper over ExamplesLoader; lives in the application layer so the interface (mcp_server.py)
only ever talks to use-case classes, not infrastructure directly (onion).
"""
from __future__ import annotations

import logging
from typing import Any

from ..infrastructure.examples_loader import ExamplesLoader

logger = logging.getLogger(__name__)


class ExamplesUseCases:
    def __init__(self, loader: ExamplesLoader):
        self.loader = loader

    def patterns(self) -> list[str]:
        return self.loader.patterns()

    def read(self, pattern: str) -> dict[str, str]:
        return self.loader.read(pattern)

    def pattern_for(self, kind: str, requires_cluster_permissions: bool = False) -> dict[str, Any]:
        """Deterministic pick: KB provisioning → exemplar pattern. Returns {pattern, files}.

        The architect agent calls this with kb_entry.provisioning.kind to pick which exemplars
        to feed into the LLM template-fill step. One round-trip; both name and content in one shot.
        """
        name = self.loader.pattern_for(kind, requires_cluster_permissions)
        return {"pattern": name, "files": self.loader.read(name)}
