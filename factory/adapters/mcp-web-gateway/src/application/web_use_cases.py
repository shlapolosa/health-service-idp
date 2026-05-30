"""Web use-cases — wraps SearXNG + HTTPFetcher with policy (allow-list, query length cap).

The architect agent calls these via the MCP tools `web.search` + `web.fetch`. The MCP itself
sits behind APIM (subscription key) so only trusted callers (Foundry agent's project connection)
can reach it.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict
from urllib.parse import urlparse

from ..domain.models import FetchResult, SearchResult
from ..infrastructure.http_fetcher import HTTPFetcher
from ..infrastructure.searxng_client import SearXNGClient

logger = logging.getLogger(__name__)


class WebUseCases:
    def __init__(self, searxng: SearXNGClient, fetcher: HTTPFetcher,
                 allowed_fetch_domains: set[str] | None = None,
                 blocked_search_terms: set[str] | None = None,
                 max_query_len: int = 300):
        self.searxng = searxng
        self.fetcher = fetcher
        self.allowed_fetch_domains = allowed_fetch_domains or set()  # empty = no restriction
        self.blocked_search_terms = blocked_search_terms or set()
        self.max_query_len = max_query_len

    def search(self, query: str, limit: int = 8) -> list[dict]:
        q = (query or "").strip()[:self.max_query_len]
        if not q:
            return []
        ql = q.lower()
        for t in self.blocked_search_terms:
            if t.lower() in ql:
                logger.info("AUDIT web.search blocked-term=%s in query", t)
                return []
        results: list[SearchResult] = self.searxng.search(q, limit=limit)
        logger.info("AUDIT web.search q=%r results=%d", q[:80], len(results))
        return [asdict(r) for r in results]

    def fetch(self, url: str, max_bytes: int | None = None) -> dict:
        try:
            host = urlparse(url).hostname or ""
        except Exception:  # noqa: BLE001
            host = ""
        if self.allowed_fetch_domains and host not in self.allowed_fetch_domains:
            # Match suffix too (foo.example.com matches example.com)
            if not any(host.endswith("." + d) or host == d for d in self.allowed_fetch_domains):
                logger.info("AUDIT web.fetch denied host=%s (not in allow-list)", host)
                return asdict(FetchResult(url=url, status=403, content_type="",
                                          text=f"host not in allow-list: {host}",
                                          truncated=False, bytes_read=0))
        r = self.fetcher.fetch(url, max_bytes=max_bytes)
        logger.info("AUDIT web.fetch host=%s status=%s bytes=%d truncated=%s",
                    host, r.status, r.bytes_read, r.truncated)
        return asdict(r)
