"""DI factories — env-driven, @lru_cache singletons."""
from __future__ import annotations

import os
from functools import lru_cache

from ..application.web_use_cases import WebUseCases
from ..infrastructure.http_fetcher import HTTPFetcher
from ..infrastructure.searxng_client import SearXNGClient


def _csv(env: str) -> set[str]:
    return {x.strip() for x in os.environ.get(env, "").split(",") if x.strip()}


@lru_cache
def get_searxng() -> SearXNGClient:
    return SearXNGClient()


@lru_cache
def get_fetcher() -> HTTPFetcher:
    return HTTPFetcher(default_max_bytes=int(os.environ.get("FETCH_MAX_BYTES", "200000")))


@lru_cache
def get_web() -> WebUseCases:
    return WebUseCases(
        searxng=get_searxng(),
        fetcher=get_fetcher(),
        allowed_fetch_domains=_csv("ALLOWED_FETCH_DOMAINS"),
        blocked_search_terms=_csv("BLOCKED_SEARCH_TERMS"),
        max_query_len=int(os.environ.get("MAX_QUERY_LEN", "300")),
    )
