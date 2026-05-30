"""Web MCP domain models — the DISCOVER surface for the architect agent.

Two read tools: web.search (SearXNG-backed) + web.fetch (size-capped GET). Neither mutates
anything; both are gated by a domain allow/block list at the use-case layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    engine: str = ""


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str = ""
    text: str = ""              # decoded if text/html / text/plain / application/json; empty otherwise
    truncated: bool = False
    bytes_read: int = 0
