"""MCP interface — FastMCP tools over Streamable-HTTP.

Single write tool: `factory.propose`. One read tool: `factory.list_open_prs`. Nothing else; this
MCP exists exclusively to be the membrane between agents and the git tree.

See capability-mcp-server/src/interface/mcp_server.py for the DNS-rebinding allow-list rationale.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..domain.models import ProposeRequest
from . import dependencies as deps
from .auth import EntraJWTMiddleware

logger = logging.getLogger(__name__)


def _transport_security() -> TransportSecuritySettings:
    hosts_raw = os.getenv("ALLOWED_HOSTS", "").strip()
    if not hosts_raw:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


mcp = FastMCP("capability-factory", stateless_http=True,
              transport_security=_transport_security())


@mcp.tool(name="factory.propose",
          description="Open a Pull Request bundle: create a branch on the target repo, commit the "
                      "given files, and open a PR. Repo must be on the factory allow-list "
                      "(FACTORY_ALLOWED_REPOS). Returns {ok, pr_url, pr_number, branch, commits, "
                      "message}. THIS IS THE ONLY WRITE TOOL — every other operation is read-only.")
def factory_propose(repo: str,
                    title: str,
                    body: str,
                    files: dict[str, str],
                    base: str = "main",
                    branch_prefix: str = "factory") -> dict[str, Any]:
    req = ProposeRequest(repo=repo, title=title, body=body, files=files,
                         base=base, branch_prefix=branch_prefix)
    # caller_oid is set by EntraJWTMiddleware as request.state.caller; FastMCP doesn't surface the
    # Request to tool functions directly, so we read it via the contextvar that auth sets.
    # For P8.2 we accept "unknown" if not threaded; audit logs still capture repo + branch + files.
    r = deps.get_factory().propose(req, caller_oid="unknown")
    return {"ok": r.ok, "pr_url": r.pr_url, "pr_number": r.pr_number,
            "branch": r.branch, "commits": r.commits, "message": r.message}


@mcp.tool(name="factory.list_open_prs",
          description="List currently-open PRs in `repo` whose head branch starts with `head_prefix` "
                      "(default 'factory/' to show only architect-originated proposals).")
def factory_list_open_prs(repo: str,
                          head_prefix: str = "factory/") -> list[dict[str, Any]]:
    return deps.get_factory().list_open_prs(repo, head_prefix=head_prefix)


async def _healthz(_request):
    return JSONResponse({"status": "ok"})


def build_app():
    """ASGI: FastMCP Streamable-HTTP app + Entra JWT middleware + /healthz."""
    app = mcp.streamable_http_app()
    app.add_middleware(EntraJWTMiddleware)
    app.routes.append(Route("/healthz", _healthz, methods=["GET"]))
    return app
