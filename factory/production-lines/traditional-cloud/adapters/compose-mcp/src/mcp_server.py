"""capability-mcp-mfg-tc — line-scoped MCP tool surface for Traditional Cloud.

This service hosts ONLY tools that belong to the Traditional Cloud
production line (MFG-TC):

  - catalog.list, catalog.describe, catalog.search, catalog.scaffold,
    catalog.validate                              — MFG-TC's M4 catalog
  - catalog.traits, catalog.describe_trait,
    catalog.traits_for                            — MFG-TC's traits
  - catalog.policies, catalog.describe_policy     — MFG-TC's policies
  - catalog.workflow_steps,
    catalog.describe_workflow_step                — MFG-TC's workflow steps
  - catalog.connectivity_recipes                  — MFG-TC's composition recipes
  - app.submit, app.submit_wait                   — MFG-TC's Execute trigger

Factory-level tools (oam.dry_run, examples.*, kb.*, factory.route,
factory.list_manufacturers) belong in capability-mcp-factory.

Adding a new ComponentDefinition to MFG-TC = adding the CD yaml + the M4
schema (per `cafe-spec/manufacturers/traditional-cloud/EXTENDING.md`).
The catalog tools auto-discover via the k8s API; no code change here.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route

# Import the shared use cases + dependency wiring from capability-mcp-core.
from capability_mcp_core.interface import dependencies as deps  # type: ignore
from capability_mcp_core.interface.auth import EntraJWTMiddleware  # type: ignore

logger = logging.getLogger(__name__)


def _transport_security() -> TransportSecuritySettings:
    hosts_raw = os.getenv("ALLOWED_HOSTS", "").strip()
    if not hosts_raw:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


mcp = FastMCP(
    "capability-mcp-mfg-tc",
    stateless_http=True,
    transport_security=_transport_security(),
)


# ============================================================
#  MFG-TC catalog (read surface)
# ============================================================


@mcp.tool(name="catalog.list",
          description="List MFG-TC ComponentDefinitions (live from the cluster).")
def catalog_list(provisionable_only: bool = False) -> list[dict[str, Any]]:
    return deps.get_catalog().list_components(provisionable_only)


@mcp.tool(name="catalog.describe",
          description="Describe an MFG-TC component including parameters and applicable traits.")
def catalog_describe(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe(name)


@mcp.tool(name="catalog.search",
          description="Rank MFG-TC components by relevance to a use-case description.")
def catalog_search(query: str, top: int = 5) -> list[dict[str, Any]]:
    return deps.get_catalog().search(query, top)


@mcp.tool(name="catalog.scaffold",
          description="Generate an OAM Application skeleton for a component.")
def catalog_scaffold(component: str, with_traits: bool = False) -> dict[str, Any]:
    return deps.get_catalog().scaffold(component, with_traits=with_traits)


@mcp.tool(name="catalog.validate", description="Validate an OAM Application via `vela dry-run`.")
def catalog_validate(oam_yaml: str) -> dict[str, Any]:
    return deps.get_catalog().dry_run_oam(oam_yaml)


# ---- Traits, policies, workflow steps (MFG-TC's M4 secondary surface) ----
@mcp.tool(name="catalog.traits",
          description="List MFG-TC TraitDefinitions with appliesToWorkloads.")
def catalog_traits() -> list[dict[str, Any]]:
    return deps.get_catalog().list_traits()


@mcp.tool(name="catalog.describe_trait",
          description="Describe a trait's parameter schema.")
def catalog_describe_trait(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_trait(name)


@mcp.tool(name="catalog.traits_for",
          description="Traits applicable to the given component type.")
def catalog_traits_for(component_type: str) -> list[dict[str, Any]]:
    return deps.get_catalog().traits_for(component_type)


@mcp.tool(name="catalog.policies",
          description="List MFG-TC PolicyDefinitions.")
def catalog_policies() -> list[dict[str, Any]]:
    return deps.get_catalog().list_policies()


@mcp.tool(name="catalog.describe_policy",
          description="Describe a policy's parameter schema.")
def catalog_describe_policy(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_policy(name)


@mcp.tool(name="catalog.workflow_steps",
          description="List MFG-TC WorkflowStepDefinitions.")
def catalog_workflow_steps() -> list[dict[str, Any]]:
    return deps.get_catalog().list_workflow_steps()


@mcp.tool(name="catalog.describe_workflow_step",
          description="Describe a workflow step's parameter schema.")
def catalog_describe_workflow_step(name: str) -> dict[str, Any]:
    return deps.get_catalog().describe_workflow_step(name)


@mcp.tool(name="catalog.connectivity_recipes",
          description="Composition recipes between component categories.")
def catalog_connectivity_recipes(
    category_a: str = "", category_b: str = ""
) -> list[dict[str, Any]]:
    return deps.get_catalog().connectivity_recipes(
        category_a or None, category_b or None
    )


# ============================================================
#  MFG-TC gated actions (Execute trigger)
# ============================================================


@mcp.tool(name="app.submit",
          description="OAM-first provisioning for MFG-TC: validate -> commit OAM to gitops -> "
                      "trigger the oam-driven-contract workflow. Never a raw apply. "
                      "Optionally pass `requirements`: a REQUIREMENTS.md (markdown text, or "
                      "base64 of it) authored alongside the OAM — use-case summary, per-component "
                      "responsibilities, and a '## Acceptance Criteria' section phrased as "
                      "externally-verifiable contract checks, plus Non-Goals. When supplied it is "
                      "committed next to the OAM in the central ledger and at the app monorepo "
                      "root as REQUIREMENTS.md, and a deterministic `spec_hash` is returned (the "
                      "dev-agent keys its implementation re-fires on it). Omit it for the exact "
                      "legacy behaviour.")
def app_submit(oam_yaml: str, requirements: str | None = None) -> dict[str, Any]:
    r = deps.get_submit().submit(oam_yaml, requirements=requirements)
    return {
        "ok": r.ok,
        "commit_sha": r.commit_sha,
        "workflow_name": r.workflow_name,
        "message": r.message,
        "spec_hash": r.spec_hash,
    }


@mcp.tool(name="app.status",
          description="Status of a submitted service: AppContainerClaim scaffold progress + "
                      "ArgoCD Application sync/health (aggregated from host or vcluster). "
                      "Phases: scaffolding -> scaffolded -> reconciling -> ready.")
def app_status(name: str) -> dict[str, Any]:
    return deps.get_status().status_of(name)


@mcp.tool(name="app.submit_wait",
          description="Deferred OAM provisioning for MFG-TC consumers whose OAM references CDs "
                      "not yet present. Commits to gitops + fires oam-apply-wait. "
                      "Returns same shape as app.submit. Accepts the same optional "
                      "`requirements` (REQUIREMENTS.md markdown/base64) as app.submit.")
def app_submit_wait(oam_yaml: str, requirements: str | None = None) -> dict[str, Any]:
    r = deps.get_submit().submit_wait(oam_yaml, requirements=requirements)
    return {
        "ok": r.ok,
        "commit_sha": r.commit_sha,
        "workflow_name": r.workflow_name,
        "message": r.message,
        "spec_hash": r.spec_hash,
    }


# ============================================================
#  ASGI wiring
# ============================================================


async def _healthz(_request):
    return JSONResponse({"status": "ok", "service": "capability-mcp-mfg-tc"})


# Declarative-spine W6: plain REST mirror of app.submit / app.status for
# in-cluster intakes (slack-api-server) that don't speak MCP. Same use cases,
# same gate, same response shape — one contract, two transports.
async def _api_submit(request):
    try:
        body = await request.json()
        oam_yaml = body.get("oam_yaml", "")
        requirements = body.get("requirements")  # SPEC-1: optional, additive
        if not oam_yaml:
            return JSONResponse({"ok": False, "message": "oam_yaml required"}, status_code=400)
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": False, "message": "invalid JSON body"}, status_code=400)
    r = deps.get_submit().submit(oam_yaml, requirements=requirements)
    return JSONResponse({
        "ok": r.ok,
        "commit_sha": r.commit_sha,
        "workflow_name": r.workflow_name,
        "message": r.message,
        "spec_hash": r.spec_hash,
    }, status_code=200 if r.ok else 422)


async def _api_status(request):
    name = request.path_params.get("name", "")
    return JSONResponse(deps.get_status().status_of(name))


def build_app():
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    app.routes.append(Route("/api/submit", _api_submit, methods=["POST"]))
    app.routes.append(Route("/api/status/{name}", _api_status, methods=["GET"]))
    return app
