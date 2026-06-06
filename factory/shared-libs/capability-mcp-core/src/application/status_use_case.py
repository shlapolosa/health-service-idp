"""app.status use case — declarative delivery status from CR conditions (W5).

The declarative-spine path has no workflow to watch; the truth lives on the
resources themselves:

  - AppContainerClaim <name>      -> scaffold progress (repos, CI, seeding)
  - ArgoCD Application <name>-oam -> sync + health, aggregated from the
    destination cluster (host or vcluster) by ArgoCD itself

This is the canonical "where is my service" surface now that the legacy
oam-driven-contract / oam-apply-wait workflows are retired (RETIRE-WFT #149):
app.submit_wait routes through the same claim + ArgoCD path, so app.status(name)
is how consumers poll deferred (submit_wait) deliveries. It does not touch the
existing lifecycle.state surface (which stays audit-event-based for the
orchestrator's use-case trajectory — different key, different question).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..infrastructure.k8s_claim_client import K8sClaimClient

logger = logging.getLogger(__name__)


def _phase(claim_status: dict[str, Any] | None, argocd: dict[str, Any] | None) -> str:
    """Collapse the two sources into one coarse phase for human/agent consumption."""
    if argocd and argocd.get("health") == "Healthy" and argocd.get("sync") == "Synced":
        return "ready"
    if argocd:
        return "reconciling"
    if claim_status:
        if claim_status.get("ready"):
            return "scaffolded"
        return "scaffolding"
    return "unknown"


@dataclass
class StatusUseCase:
    """app.status(name) — where is my service right now?"""

    claims: K8sClaimClient

    def status_of(self, name: str) -> dict[str, Any]:
        if not name or not str(name).strip():
            return {"ok": False, "error": "name required"}
        name = name.strip()

        claim_status = self.claims.get_claim_status(name)
        argocd = self.claims.get_argocd_app_status(f"{name}-oam")

        result: dict[str, Any] = {
            "ok": True,
            "name": name,
            "phase": _phase(claim_status, argocd),
            "argocd": argocd,
            "scaffold": None,
        }
        if claim_status:
            result["scaffold"] = {
                "ready": claim_status.get("ready"),
                "source_repository": (claim_status.get("sourceRepository") or {}).get("url"),
                "gitops_repository": (claim_status.get("gitopsRepository") or {}).get("url"),
                "conditions": claim_status.get("conditions"),
            }
        if claim_status is None and argocd is None:
            result["note"] = (
                "no AppContainerClaim and no ArgoCD Application found — "
                "either not submitted yet, externally delivered (no managed "
                "destination), or deployed via the legacy workflow path"
            )
        return result
