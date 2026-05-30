"""Catalog use-cases — the read surface of the consumer-facing MCP."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

import yaml

from ..infrastructure.crossplane_dryrun_client import CrossplaneDryRunClient
from ..infrastructure.cue_param_parser import parse_parameter_block
from ..infrastructure.k8s_catalog_client import K8sCatalogClient
from ..infrastructure.recipes_loader import RecipesLoader
from ..infrastructure.vela_client import VelaClient
from .scoring import CapabilityScorer

logger = logging.getLogger(__name__)


def _describe_completeness(params: list[dict[str, Any]]) -> str:
    """Classify how complete the parameter descriptions are.

    "none"    — no params at all OR all descriptions empty (agent should fall back to the
                component-level description annotation)
    "partial" — some have descriptions, some don't
    "full"    — every parameter has a non-empty description
    """
    if not params:
        return "none"
    if all(not p.get("description") for p in params):
        return "none"
    if any(not p.get("description") for p in params):
        return "partial"
    return "full"


class CatalogUseCases:
    def __init__(self, k8s: K8sCatalogClient, vela: VelaClient, scorer: CapabilityScorer,
                 crossplane_dryrun: CrossplaneDryRunClient | None = None,
                 recipes: RecipesLoader | None = None):
        self.k8s = k8s
        self.vela = vela
        self.scorer = scorer
        # Optional so existing tests that instantiate CatalogUseCases(k8s, vela, scorer) still work.
        self.crossplane_dryrun = crossplane_dryrun
        self.recipes = recipes

    # ----------------------------------------------------------------------
    # Components
    # ----------------------------------------------------------------------

    def list_components(self, provisionable_only: bool = False) -> list[dict[str, Any]]:
        comps = self.k8s.list_components()
        if provisionable_only:
            comps = [c for c in comps if c.get("status") in ("", "beta", "GA")]
        return comps

    def describe(self, name: str) -> dict[str, Any]:
        meta = self.k8s.get_component(name) or {"name": name, "description": ""}
        meta["parameters"] = self.vela.render_schema(name)   # rendered LIVE
        # Enrich with applicable_traits so the agent gets the full picture in one round-trip.
        applicable: list[dict[str, str]] = []
        for t in self.k8s.list_traits():
            applies = t.get("appliesToWorkloads", []) or []
            if name in applies or "*" in applies:
                applicable.append({"name": t["name"], "description": t.get("description", "")})
        meta["applicable_traits"] = applicable
        meta["description_completeness"] = _describe_completeness(meta["parameters"])
        return meta

    def search(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """request = structured CapabilityRequest (category + qualityAttributes [+ weights])."""
        return [asdict(c) for c in self.scorer.score(request)]

    def scaffold(self, component: str, app_name: str = "my-app",
                 namespace: str = "default", with_traits: bool = False) -> str:
        """A minimal, valid OAM Application snippet for `component` (required params stubbed).

        If with_traits=True, include trait stubs for traits whose `appliesToWorkloads` includes
        this component type — the agent can then prune to what it actually wants.
        """
        described = self.describe(component)
        params = described.get("parameters", [])
        props = {p["name"]: f"<{p.get('type','string')}>" for p in params if p.get("required")}
        component_block: dict[str, Any] = {"name": app_name, "type": component, "properties": props}
        if with_traits:
            stubs: list[dict[str, Any]] = []
            for t in described.get("applicable_traits", []):
                trait_params = self.vela.render_trait_schema(t["name"])
                trait_props = {p["name"]: f"<{p.get('type','string')}>"
                               for p in trait_params if p.get("required")}
                stubs.append({"type": t["name"], "properties": trait_props})
            if stubs:
                component_block["traits"] = stubs
        app = {
            "apiVersion": "core.oam.dev/v1beta1",
            "kind": "Application",
            "metadata": {"name": app_name, "namespace": namespace},
            "spec": {"components": [component_block]},
        }
        return yaml.safe_dump(app, sort_keys=False)

    # ----------------------------------------------------------------------
    # Traits
    # ----------------------------------------------------------------------

    def list_traits(self) -> list[dict[str, Any]]:
        return self.k8s.list_traits()

    def describe_trait(self, name: str) -> dict[str, Any]:
        meta = self.k8s.get_trait(name) or {"name": name, "description": "",
                                            "namespace": "", "appliesToWorkloads": []}
        meta["parameters"] = self.vela.render_trait_schema(name)
        meta["description_completeness"] = _describe_completeness(meta["parameters"])
        return meta

    def traits_for(self, component_type: str) -> list[dict[str, Any]]:
        """Traits whose appliesToWorkloads includes `component_type` (or '*' meaning any)."""
        out: list[dict[str, Any]] = []
        for t in self.k8s.list_traits():
            applies = t.get("appliesToWorkloads", []) or []
            if component_type in applies or "*" in applies:
                out.append(t)
        return out

    # ----------------------------------------------------------------------
    # Policies + WorkflowSteps — vela show does not work; parse CUE template ourselves.
    # ----------------------------------------------------------------------

    def list_policies(self) -> list[dict[str, Any]]:
        return self.k8s.list_policies()

    def describe_policy(self, name: str) -> dict[str, Any]:
        meta = self.k8s.get_policy(name) or {"name": name, "description": "",
                                             "namespace": "", "cue_template": ""}
        meta["parameters"] = parse_parameter_block(meta.pop("cue_template", ""))
        return meta

    def list_workflow_steps(self) -> list[dict[str, Any]]:
        return self.k8s.list_workflow_steps()

    def describe_workflow_step(self, name: str) -> dict[str, Any]:
        meta = self.k8s.get_workflow_step(name) or {"name": name, "description": "",
                                                    "namespace": "", "cue_template": ""}
        meta["parameters"] = parse_parameter_block(meta.pop("cue_template", ""))
        return meta

    # ----------------------------------------------------------------------
    # Connectivity recipes
    # ----------------------------------------------------------------------

    def connectivity_recipes(self, category_a: str | None = None,
                             category_b: str | None = None) -> list[dict[str, Any]]:
        if self.recipes is None:
            return []
        return self.recipes.recipes_for(category_a, category_b)

    # ----------------------------------------------------------------------
    # Validation (existing)
    # ----------------------------------------------------------------------

    def validate(self, oam_yaml: str) -> dict[str, Any]:
        ok, diag = self.vela.dry_run(oam_yaml)
        return {"ok": ok, "diagnostics": diag}

    def dry_run_oam(self, oam_yaml: str) -> dict[str, Any]:
        """Alias of `validate`, exposed as `oam.dry_run` for agent-prompt clarity."""
        return self.validate(oam_yaml)

    def dry_run_crossplane(self, yaml_text: str) -> dict[str, Any]:
        """Server-side dry-run for Crossplane XRD/Composition/MR YAML. Returns {ok, diagnostics}."""
        if self.crossplane_dryrun is None:
            return {"ok": False, "diagnostics": "crossplane_dryrun client not configured"}
        ok, diag = self.crossplane_dryrun.dry_run(yaml_text)
        return {"ok": ok, "diagnostics": diag}
