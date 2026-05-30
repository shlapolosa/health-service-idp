"""MCP interface — FastMCP tools over Streamable-HTTP.

Two scopes (per design §12): read tools `catalog.*` + the gated action `app.submit`. (The ops surface
— propose-PR / dry-run / query-telemetry — is a later phase; not wired here.) The ASGI app adds the
Entra JWT middleware + a /healthz route. APIM fronts this in production (JWT pass-through + rate-limit).

DNS-rebinding-protection note: FastMCP 1.27+ ships TransportSecuritySettings with `allowed_hosts=[]`
which only accepts `localhost`. Behind APIM/Knative the inbound Host is `<svc>.<ns>.<extip>.nip.io`,
so we configure the allow-list via `ALLOWED_HOSTS` env (CSV) — empty means accept anything. APIM's
validate-jwt is the primary security boundary; this is defence-in-depth.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import dependencies as deps
from .auth import EntraJWTMiddleware

logger = logging.getLogger(__name__)


def _transport_security() -> TransportSecuritySettings:
    """Build the security settings from env. Empty ALLOWED_HOSTS → protection disabled (dev)."""
    hosts_raw = os.getenv("ALLOWED_HOSTS", "").strip()
    if not hosts_raw:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


mcp = FastMCP("capability-catalog", stateless_http=True,
              transport_security=_transport_security())


# ---- read surface (consumer-facing) ----
@mcp.tool(name="catalog.list", description="List published OAM capabilities (live ComponentDefinitions).")
def catalog_list(provisionable_only: bool = False) -> list[dict[str, Any]]:
    return deps.get_catalog().list_components(provisionable_only)


@mcp.tool(name="catalog.describe",
          description="Describe a capability incl. its parameter schema (rendered live by vela), "
                      "plus applicable_traits (traits whose appliesToWorkloads includes this "
                      "component) and description_completeness ∈ {none, partial, full}. "
                      "Single round-trip gives the agent everything to author the component block.")
def catalog_describe(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe(name)


@mcp.tool(name="catalog.search",
          description="Deterministically rank KB technologies for a structured CapabilityRequest "
                      "(category + qualityAttributes [+ weights]). Returns ranked candidates with per-attribute detail.")
def catalog_search(category: str, qualityAttributes: dict[str, Any],
                   weights: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return deps.get_catalog().search({
        "category": category, "qualityAttributes": qualityAttributes, "weights": weights or {},
    })


@mcp.tool(name="catalog.scaffold",
          description="Return a minimal valid OAM Application snippet for a component. "
                      "with_traits=true includes trait stubs for traits whose appliesToWorkloads "
                      "matches this component (agent then prunes to what it needs).")
def catalog_scaffold(component: str, app_name: str = "my-app", namespace: str = "default",
                     with_traits: bool = False) -> str:
    return deps.get_catalog().scaffold(component, app_name, namespace, with_traits=with_traits)


@mcp.tool(name="catalog.validate", description="Validate an OAM Application via `vela dry-run`.")
def catalog_validate(oam_yaml: str) -> dict[str, Any]:
    return deps.get_catalog().validate(oam_yaml)


# ---- Trait / Policy / WorkflowStep / Recipe surface (added 2026-05-30) ----
# These complete the metadata surface an agent needs to author compliant OAM:
# - traits (with appliesToWorkloads + per-trait parameters)
# - policies (e.g. topology for vCluster routing)
# - workflow steps (for spec.workflow blocks)
# - connectivity recipes (pre-approved trait sets for composite component combinations)

@mcp.tool(name="catalog.traits",
          description="List all TraitDefinitions in the cluster (vela-system vanilla + platform). "
                      "Each entry includes name, namespace, description, appliesToWorkloads "
                      "(which component types accept it; empty/['*'] = any).")
def catalog_traits() -> list[dict[str, Any]]:
    return deps.get_catalog().list_traits()


@mcp.tool(name="catalog.describe_trait",
          description="Describe a TraitDefinition incl. its parameter schema (rendered live by vela). "
                      "Returns name, namespace, description, appliesToWorkloads, parameters, "
                      "description_completeness ∈ {none, partial, full}.")
def catalog_describe_trait(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_trait(name)


@mcp.tool(name="catalog.traits_for",
          description="Return traits applicable to a given component type. Filters all "
                      "TraitDefinitions by appliesToWorkloads. Use during Phase 5 SYNTHESISE "
                      "before emitting trait blocks in an OAM Application.")
def catalog_traits_for(component_type: str) -> list[dict[str, Any]]:
    return deps.get_catalog().traits_for(component_type)


@mcp.tool(name="catalog.policies",
          description="List all PolicyDefinitions in the cluster (e.g. topology for vCluster routing, "
                      "health for health checks, override for component-spec overrides). "
                      "Each entry: name, namespace, description.")
def catalog_policies() -> list[dict[str, Any]]:
    return deps.get_catalog().list_policies()


@mcp.tool(name="catalog.describe_policy",
          description="Describe a PolicyDefinition incl. parameters parsed from its CUE template. "
                      "Returns name, namespace, description, parameters. Note: vela show does NOT "
                      "support PolicyDefinitions — parameters parsed from raw CUE.")
def catalog_describe_policy(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_policy(name)


@mcp.tool(name="catalog.workflow_steps",
          description="List all WorkflowStepDefinitions in the cluster. Reference these by name "
                      "in OAM Application spec.workflow.steps[].type. Each entry: name, namespace, "
                      "description.")
def catalog_workflow_steps() -> list[dict[str, Any]]:
    return deps.get_catalog().list_workflow_steps()


@mcp.tool(name="catalog.describe_workflow_step",
          description="Describe a WorkflowStepDefinition incl. parameters parsed from its CUE template. "
                      "Returns name, namespace, description, parameters.")
def catalog_describe_workflow_step(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_workflow_step(name)


@mcp.tool(name="catalog.connectivity_recipes",
          description="Return pre-approved connectivity recipes for composite OAM. Optional "
                      "category_a / category_b filter (e.g. 'compute-service' + 'datastore' "
                      "→ web-service-needs-db). When both provided, returns recipes whose "
                      "composite.contains is a superset of {a, b}. When neither, returns all.")
def catalog_connectivity_recipes(category_a: str | None = None,
                                 category_b: str | None = None) -> list[dict[str, Any]]:
    return deps.get_catalog().connectivity_recipes(category_a, category_b)


# ---- KB read surface (P8.1) — the architect's view of the documented capability ledger ----
@mcp.tool(name="kb.read",
          description="Read a single KB entry by technology name. Returns the full document "
                      "(profile + version + provisioning + maturity) or null if absent.")
def kb_read(tech: str) -> dict[str, Any] | None:
    return deps.get_kb().read(tech)


@mcp.tool(name="kb.list",
          description="List KB entries; optional filters: maturity (kb|published), category "
                      "(messaging|datastore|cache|compute-service|analytics|identity|secret-config).")
def kb_list(maturity: str | None = None,
            category: str | None = None) -> list[dict[str, Any]]:
    return deps.get_kb().list(maturity=maturity, category=category)


@mcp.tool(name="kb.diff",
          description="Report KB-vs-cluster gap for a technology. Returns gap_kind ∈ "
                      "{none, needs_oam, oam_orphan, drift, unknown} plus presence flags.")
def kb_diff(tech: str) -> dict[str, Any]:
    return deps.get_kb().diff(tech)


# ---- Exemplar surface (P8.1) — feeds the architect's LLM template-fill step ----
@mcp.tool(name="examples.patterns",
          description="List known artifact patterns: pattern-{a-helm-chart,b-helm-cluster-perms,"
                      "c-operator-backed,d-xrd-composition,e-composite-oam,f-trait}.")
def examples_patterns() -> list[str]:
    return deps.get_examples().patterns()


@mcp.tool(name="examples.read",
          description="Return exemplar files for a pattern. Output: {relative_path: file_content}. "
                      "Pattern must be from examples.patterns(); other inputs raise.")
def examples_read(pattern: str) -> dict[str, str]:
    return deps.get_examples().read(pattern)


@mcp.tool(name="examples.pattern_for",
          description="Deterministic pick: given KB provisioning (kind + requires_cluster_permissions), "
                      "return the chosen pattern name AND its exemplar files in one round-trip.")
def examples_pattern_for(kind: str,
                         requires_cluster_permissions: bool = False) -> dict[str, Any]:
    return deps.get_examples().pattern_for(kind, requires_cluster_permissions)


# ---- Validate surface (P8.1) — closed-loop gates for synthesised artifacts ----
@mcp.tool(name="oam.dry_run",
          description="Validate an OAM Application YAML via `vela dry-run`. "
                      "Returns {ok: bool, diagnostics: str}. Same engine as catalog.validate; "
                      "exposed under oam.* for agent-prompt clarity.")
def oam_dry_run(oam_yaml: str) -> dict[str, Any]:
    return deps.get_catalog().dry_run_oam(oam_yaml)


@mcp.tool(name="crossplane.dry_run",
          description="Server-side dry-run apply for Crossplane XRD/Composition/MR YAML "
                      "via `kubectl apply --dry-run=server`. Returns {ok, diagnostics}.")
def crossplane_dry_run(yaml_text: str) -> dict[str, Any]:
    return deps.get_catalog().dry_run_crossplane(yaml_text)


# ---- gated action surface ----
@mcp.tool(name="app.submit",
          description="OAM-first provisioning: validate -> commit OAM to gitops (the gate) -> trigger "
                      "the oam-apply workflow. Never a raw apply.")
def app_submit(oam_yaml: str) -> dict[str, Any]:
    r = deps.get_submit().submit(oam_yaml)
    return {"ok": r.ok, "commit_sha": r.commit_sha, "workflow_name": r.workflow_name, "message": r.message}


@mcp.tool(name="app.submit_wait",
          description="Deferred OAM provisioning for consumers whose OAM references ComponentDefinitions "
                      "that don't exist yet. Commits OAM to gitops + fires the oam-apply-wait workflow, "
                      "which polls `vela dry-run` until prerequisites are satisfied then creates the "
                      "ArgoCD Application. Consumer never blocks. 72h hard cap. Returns same shape as app.submit.")
def app_submit_wait(oam_yaml: str) -> dict[str, Any]:
    r = deps.get_submit().submit_wait(oam_yaml)
    return {"ok": r.ok, "commit_sha": r.commit_sha, "workflow_name": r.workflow_name, "message": r.message}


async def _healthz(_request):
    return JSONResponse({"status": "ok"})


def build_app():
    """ASGI app: the FastMCP Streamable-HTTP app + Entra JWT middleware + /healthz."""
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    return app
