"""Catalog use-cases — the read surface of the consumer-facing MCP."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

import yaml

from ..infrastructure.k8s_catalog_client import K8sCatalogClient
from ..infrastructure.vela_client import VelaClient
from .scoring import CapabilityScorer

logger = logging.getLogger(__name__)


class CatalogUseCases:
    def __init__(self, k8s: K8sCatalogClient, vela: VelaClient, scorer: CapabilityScorer):
        self.k8s = k8s
        self.vela = vela
        self.scorer = scorer

    def list_components(self, provisionable_only: bool = False) -> list[dict[str, Any]]:
        comps = self.k8s.list_components()
        if provisionable_only:
            comps = [c for c in comps if c.get("status") in ("", "beta", "GA")]
        return comps

    def describe(self, name: str) -> dict[str, Any]:
        meta = self.k8s.get_component(name) or {"name": name, "description": ""}
        meta["parameters"] = self.vela.render_schema(name)   # rendered LIVE, not from ConfigMaps
        return meta

    def search(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """request = structured CapabilityRequest (category + qualityAttributes [+ weights])."""
        return [asdict(c) for c in self.scorer.score(request)]

    def scaffold(self, component: str, app_name: str = "my-app",
                 namespace: str = "default") -> str:
        """A minimal, valid OAM Application snippet for `component` (required params stubbed)."""
        params = self.describe(component).get("parameters", [])
        props = {p["name"]: f"<{p.get('type','string')}>" for p in params if p.get("required")}
        app = {
            "apiVersion": "core.oam.dev/v1beta1",
            "kind": "Application",
            "metadata": {"name": app_name, "namespace": namespace},
            "spec": {"components": [{"name": app_name, "type": component, "properties": props}]},
        }
        return yaml.safe_dump(app, sort_keys=False)

    def validate(self, oam_yaml: str) -> dict[str, Any]:
        ok, diag = self.vela.dry_run(oam_yaml)
        return {"ok": ok, "diagnostics": diag}
