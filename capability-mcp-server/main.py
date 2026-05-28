"""Entrypoint — serve the capability MCP over Streamable-HTTP."""
import logging
import os

import uvicorn

from src.interface.mcp_server import build_app

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
