"""capability-mcp-factory — factory-scoped MCP tool surface.

This service is the factory-level (cross-manufacturer) MCP gateway. It hosts
ONLY tools whose responsibility is the factory itself, not any specific
production line:

  - oam.dry_run, crossplane.dry_run        — generic validation (mfg-agnostic)
  - examples.patterns, examples.read,
    examples.pattern_for                    — cross-mfg exemplar library
  - kb.read, kb.list, kb.diff               — factory knowledge base
  - factory.route                           — which manufacturer should produce this?
  - factory.list_manufacturers              — what production lines exist?

Per-manufacturer tools (catalog.*, app.submit, app.submit_wait) belong to
the per-line MCPs (e.g. capability-mcp-mfg-tc). The monolithic
capability-mcp-server remains deployed alongside this service during the
S2 refactor transition — both routes return identical results because both
import the same use-case modules.

Phase 1 (this commit): proxy by import. Both services use the same
underlying use cases. Future phase: split source trees once per-line
divergence emerges (e.g. mfg-tc needs different catalog filters than mfg-ai).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route

# Import the shared use-case + dependency wiring from capability-mcp-core
# (the extracted shared library at factory/shared-libs/capability-mcp-core/). At build
# time the src tree is baked into the image as the `capability_mcp_core`
# package; at runtime it is on PYTHONPATH (see Dockerfile).
from capability_mcp_core.interface import dependencies as deps  # type: ignore
from capability_mcp_core.interface.auth import EntraJWTMiddleware  # type: ignore

# Factory-local use cases (defined in this service, not in the monolith).
from .audit_sink_client import AuditSinkClient
from .lifecycle_query_use_case import LifecycleQueryUseCase

logger = logging.getLogger(__name__)


def _transport_security() -> TransportSecuritySettings:
    hosts_raw = os.getenv("ALLOWED_HOSTS", "").strip()
    if not hosts_raw:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


mcp = FastMCP(
    "capability-mcp-factory",
    stateless_http=True,
    transport_security=_transport_security(),
)


# ============================================================
#  Factory-scoped tools
# ============================================================


# ---- Validation (mfg-agnostic) ----
@mcp.tool(
    name="oam.dry_run",
    description="Validate an OAM Application YAML via `vela dry-run`. "
                "Returns {ok: bool, diagnostics: str}.",
)
def oam_dry_run(oam_yaml: str) -> dict[str, Any]:
    return deps.get_catalog().dry_run_oam(oam_yaml)


@mcp.tool(
    name="crossplane.dry_run",
    description="Server-side dry-run for Crossplane XRD/Composition/MR YAML "
                "via `kubectl apply --dry-run=server`.",
)
def crossplane_dry_run(yaml_text: str) -> dict[str, Any]:
    return deps.get_catalog().dry_run_crossplane(yaml_text)


# ---- Examples (cross-mfg exemplar library) ----
@mcp.tool(name="examples.patterns",
          description="List exemplar OAM/Crossplane patterns shipped with the platform.")
def examples_patterns() -> list[dict[str, Any]]:
    return deps.get_examples().patterns()


@mcp.tool(name="examples.read",
          description="Read the YAML body of a named exemplar pattern.")
def examples_read(name: str) -> dict[str, Any]:
    return deps.get_examples().read(name)


@mcp.tool(name="examples.pattern_for",
          description="Pick the right exemplar for a kind + permission requirement.")
def examples_pattern_for(kind: str, requires_cluster_permissions: bool = False) -> dict[str, Any]:
    return deps.get_examples().pattern_for(kind, requires_cluster_permissions)


# ---- Knowledge base ----
@mcp.tool(name="kb.read", description="Read a knowledge-base entry by name.")
def kb_read(name: str) -> dict[str, Any]:
    return deps.get_kb().read(name)


@mcp.tool(name="kb.list", description="List available knowledge-base entries.")
def kb_list() -> list[dict[str, Any]]:
    return deps.get_kb().list()


@mcp.tool(name="kb.diff", description="Diff a knowledge-base entry against current state.")
def kb_diff(name: str) -> dict[str, Any]:
    return deps.get_kb().diff(name)


# ---- Factory routing (S4) ----
@mcp.tool(
    name="factory.route",
    description="Ask the factory which production line (manufacturer) should produce this use-case. "
                "Wraps the cafe-spec classify-router. Returns "
                "{manufacturer, archetype, sub_archetype, confidence, action, rationale}.",
)
def factory_route(plain_text_description: str) -> dict[str, Any]:
    return deps.get_route().route(plain_text_description)


# ---- Factory metadata: list registered manufacturers ----
@mcp.tool(
    name="factory.list_manufacturers",
    description="List all manufacturers registered in cafe-spec/manufacturers/. "
                "Returns [{id, name, version, status, target_substrate}].",
)
def factory_list_manufacturers() -> list[dict[str, Any]]:
    cafe_spec_root = os.getenv("CAFE_SPEC_ROOT", "/cafe-spec")
    manufacturers_dir = Path(cafe_spec_root) / "manufacturers"
    if not manufacturers_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    try:
        import yaml
    except ImportError:
        return [{"error": "yaml not available"}]
    for entry in sorted(manufacturers_dir.iterdir()):
        manifest = entry / "manifest.yaml"
        if not manifest.is_file():
            continue
        try:
            data = yaml.safe_load(manifest.read_text()) or {}
            meta = data.get("metadata", {})
            spec = data.get("spec", {})
            out.append({
                "id": meta.get("id", entry.name),
                "name": meta.get("name", entry.name),
                "version": meta.get("version", "unknown"),
                "status": spec.get("status", {}).get("overall", "unknown"),
                "target_substrate": spec.get("target_substrate", {}).get("name", "unknown"),
            })
        except Exception as e:
            logger.warning("failed to parse %s: %s", manifest, e)
    return out


# ---- Lifecycle observability (S5) ----
def _lifecycle_query() -> LifecycleQueryUseCase:
    """Build on demand (audit-sink URL is env-driven; cheap to construct)."""
    client = AuditSinkClient(
        base_url=os.getenv(
            "OBSERVE_AUDIT_SINK_URL",
            "http://observe-audit-sink.default.svc.cluster.local",
        ),
        timeout_seconds=float(os.getenv("OBSERVE_AUDIT_SINK_TIMEOUT_SECONDS", "5")),
    )
    return LifecycleQueryUseCase(client)


@mcp.tool(
    name="lifecycle.state",
    description="Query the current lifecycle state + transition history for a use-case "
                "by id. Reads from observe-audit-sink (the factory Observe port). "
                "Returns {ok, use_case_id, current_state, history: [{from,to,at,caller}], event_count}. "
                "Useful for tracking 'where is my request right now?' without scraping individual adapters.",
)
def lifecycle_state(use_case_id: str) -> dict[str, Any]:
    return _lifecycle_query().state_of(use_case_id)


# ============================================================
#  ASGI wiring
# ============================================================


async def _healthz(_request):
    return JSONResponse({"status": "ok", "service": "capability-mcp-factory"})


def build_app():
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    return app
