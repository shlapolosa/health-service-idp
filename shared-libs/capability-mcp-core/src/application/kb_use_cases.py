"""KB use-cases — the read surface of `kb.*` MCP tools.

Bridges KBLoader (raw KB YAML reads) and K8sCatalogClient (live OAM ComponentDefinitions) so the
architect agent can answer "does the KB and the OAM agree for this technology?" — the gap signal
that decides whether Phase 5 (SYNTHESISE) of agent reasoning needs to run.

KB ⊃ OAM means a tech is documented but not yet implemented (architect should produce OAM).
OAM ⊃ KB means an implementation exists with no KB ledger entry (orphan — needs KB row backfilled).
"""
from __future__ import annotations

import logging
from typing import Any

from ..infrastructure.k8s_catalog_client import K8sCatalogClient
from ..infrastructure.kb_loader import KBLoader

logger = logging.getLogger(__name__)


class KBUseCases:
    def __init__(self, kb: KBLoader, k8s: K8sCatalogClient):
        self.kb = kb
        self.k8s = k8s

    def read(self, tech: str) -> dict[str, Any] | None:
        """Single KB entry by technology name."""
        return self.kb.read(tech)

    def list(self, maturity: str | None = None,
             category: str | None = None) -> list[dict[str, Any]]:
        """All KB entries, optionally filtered."""
        return self.kb.list(maturity=maturity, category=category)

    def diff(self, tech: str) -> dict[str, Any]:
        """KB-vs-cluster gap report for one technology.

        gap_kind:
          none        — KB row exists with maturity=published AND cluster has matching CD
          needs_oam   — KB row exists (any maturity) but cluster has no matching CD
          oam_orphan  — cluster has a CD but no KB row
          drift       — both present but maturity != published (KB still says kb)
        """
        kb_entry = self.kb.read(tech)
        cd = self.k8s.get_component(tech)
        kb_present = kb_entry is not None
        oam_present = cd is not None
        oam_revision = (cd or {}).get("revision", "") if oam_present else ""

        if oam_present and not kb_present:
            gap_kind = "oam_orphan"
        elif kb_present and not oam_present:
            gap_kind = "needs_oam"
        elif kb_present and oam_present:
            gap_kind = "none" if (kb_entry or {}).get("maturity") == "published" else "drift"
        else:
            gap_kind = "unknown"  # neither side knows about this technology

        return {
            "technology": tech,
            "kb_present": kb_present,
            "oam_present": oam_present,
            "oam_revision": oam_revision,
            "maturity": (kb_entry or {}).get("maturity"),
            "provisioning_kind": ((kb_entry or {}).get("provisioning") or {}).get("kind"),
            "requires_cluster_permissions": ((kb_entry or {}).get("provisioning") or {}).get(
                "requires_cluster_permissions", False),
            "gap_kind": gap_kind,
        }
