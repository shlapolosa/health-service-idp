"""Entrypoint — uvicorn on PORT (default 8080)."""
from __future__ import annotations

import logging
import os

import uvicorn

from src.interface.mcp_server import build_app

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
