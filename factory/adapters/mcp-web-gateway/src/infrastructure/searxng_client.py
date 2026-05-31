"""SearXNG client — talks to a SearXNG instance over its JSON search API.

The default backend is the in-cluster SearXNG (`http://searxng.search.svc.cluster.local:8080`).
For local dev, override with `SEARXNG_URL=http://localhost:8888`.

We pass `format=json` and never expose the raw user query downstream — only sanitised matches.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ..domain.models import SearchResult

logger = logging.getLogger(__name__)


class SearXNGClient:
    def __init__(self, base_url: str | None = None, timeout: int = 15):
        self.base_url = (base_url or os.environ.get("SEARXNG_URL", "http://searxng.search.svc.cluster.local:8080")).rstrip("/")
        self.timeout = timeout

    def search(self, query: str, limit: int = 8,
               categories: str = "general") -> list[SearchResult]:
        if not query or not query.strip():
            return []
        try:
            r = requests.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json", "categories": categories},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error("searxng query failed: %s", e)
            return []
        try:
            data = r.json()
        except ValueError as e:
            logger.error("searxng non-json response: %s", e)
            return []
        results: list[SearchResult] = []
        for item in (data.get("results") or [])[:limit]:
            results.append(SearchResult(
                title=str(item.get("title") or "")[:300],
                url=str(item.get("url") or ""),
                snippet=str(item.get("content") or "")[:500],
                engine=str(item.get("engine") or ""),
            ))
        return results
