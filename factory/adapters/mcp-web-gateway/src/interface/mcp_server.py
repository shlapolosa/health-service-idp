"""MCP interface — web.search + web.fetch over Streamable-HTTP.

The DISCOVER surface for the architect agent. The architect calls these only when the
catalog SCORE phase returns no fitting candidate (Phase 3a of the system-prompt reasoning).

DNS-rebind allow-list mirrors catalog + factory (set via ALLOWED_HOSTS env, comma-sep).
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
    hosts_raw = os.getenv("ALLOWED_HOSTS", "").strip()
    if not hosts_raw:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


mcp = FastMCP("capability-web", stateless_http=True,
              transport_security=_transport_security())


@mcp.tool(name="web.search",
          description="Search the web via SearXNG. Returns up to `limit` results "
                      "(title, url, snippet, engine). Use during DISCOVER phase when the "
                      "catalog has no fitting candidate for a capability request.")
def web_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    return deps.get_web().search(query=query, limit=limit)


@mcp.tool(name="web.fetch",
          description="HTTP GET a URL and return decoded text (text/html, text/plain, "
                      "application/json only). Size-capped at FETCH_MAX_BYTES env (default 200KB). "
                      "Honours ALLOWED_FETCH_DOMAINS if configured.")
def web_fetch(url: str, max_bytes: int | None = None) -> dict[str, Any]:
    return deps.get_web().fetch(url=url, max_bytes=max_bytes)


async def _healthz(_request):
    return JSONResponse({"status": "ok"})


def build_app():
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    return app
