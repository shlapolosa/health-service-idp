"""MCP interface — FastMCP tools over Streamable-HTTP.

Two scopes (per design §12): read tools `catalog.*` + the gated action `app.submit`. (The ops surface
— propose-PR / dry-run / query-telemetry — is a later phase; not wired here.) The ASGI app adds the
Entra JWT middleware + a /healthz route. APIM fronts this in production (JWT pass-through + rate-limit).
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import dependencies as deps
from .auth import EntraJWTMiddleware

logger = logging.getLogger(__name__)

mcp = FastMCP("capability-catalog", stateless_http=True)


# ---- read surface (consumer-facing) ----
@mcp.tool(name="catalog.list", description="List published OAM capabilities (live ComponentDefinitions).")
def catalog_list(provisionable_only: bool = False) -> list[dict[str, Any]]:
    return deps.get_catalog().list_components(provisionable_only)


@mcp.tool(name="catalog.describe", description="Describe a capability incl. its parameter schema (rendered live by vela).")
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


@mcp.tool(name="catalog.scaffold", description="Return a minimal valid OAM Application snippet for a component.")
def catalog_scaffold(component: str, app_name: str = "my-app", namespace: str = "default") -> str:
    return deps.get_catalog().scaffold(component, app_name, namespace)


@mcp.tool(name="catalog.validate", description="Validate an OAM Application via `vela dry-run`.")
def catalog_validate(oam_yaml: str) -> dict[str, Any]:
    return deps.get_catalog().validate(oam_yaml)


# ---- gated action surface ----
@mcp.tool(name="app.submit",
          description="OAM-first provisioning: validate -> commit OAM to gitops (the gate) -> trigger "
                      "the oam-apply workflow. Never a raw apply.")
def app_submit(oam_yaml: str) -> dict[str, Any]:
    r = deps.get_submit().submit(oam_yaml)
    return {"ok": r.ok, "commit_sha": r.commit_sha, "workflow_name": r.workflow_name, "message": r.message}


async def _healthz(_request):
    return JSONResponse({"status": "ok"})


def build_app():
    """ASGI app: the FastMCP Streamable-HTTP app + Entra JWT middleware + /healthz."""
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    return app
