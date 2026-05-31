"""KB loader — raw read access to the capability-factory/kb/ tree.

Distinct from CapabilityScorer (which only consumes profile + maturity for ranking): this is the
read-side surface for kb.* MCP tools (the architect needs to inspect provisioning metadata too).

Lazy-loaded; in-memory cache survives a process lifetime (recreate the loader to pick up changes
from disk — typically via Knative scale-to-zero or pod restart from a fresh image build).

Mirrors CapabilityScorer._load() (scoring.py:31-45) for path discovery so the two stay in sync.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class KBLoader:
    def __init__(self, factory_dir: str | None = None):
        self.dir = Path(factory_dir or os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory"))
        self._kb: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        kb_dir = self.dir / "kb"
        if kb_dir.is_dir():
            for f in sorted(kb_dir.glob("*.yaml")):
                doc = yaml.safe_load(f.read_text())
                if isinstance(doc, dict) and doc.get("technology"):
                    self._kb[doc["technology"]] = doc
        self._loaded = True
        logger.info("KBLoader: loaded %d entries from %s", len(self._kb), kb_dir)

    def read(self, tech: str) -> dict[str, Any] | None:
        """Return the full KB doc for `tech`, or None if absent."""
        self._load()
        return self._kb.get(tech)

    def list(self, maturity: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
        """Return KB entries, optionally filtered by maturity (kb|published) and/or category."""
        self._load()
        out = list(self._kb.values())
        if maturity is not None:
            out = [e for e in out if e.get("maturity") == maturity]
        if category is not None:
            out = [e for e in out if e.get("category") == category]
        return out

    def all_technologies(self) -> list[str]:
        """Helper for diff: list every tech name we know about."""
        self._load()
        return sorted(self._kb.keys())
