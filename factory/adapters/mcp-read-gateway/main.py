"""capability-mcp-factory entrypoint — serve the factory MCP over Streamable-HTTP.

Sibling to capability-mcp-server (the monolith); during S2 refactor both
run side-by-side. This service hosts only factory-level (cross-manufacturer)
tools; per-line tools live in capability-mcp-mfg-tc.
"""
import logging
import os

import uvicorn

from src.mcp_server import build_app

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
