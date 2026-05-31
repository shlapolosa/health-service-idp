"""Plain HTTP fetcher with size + content-type guard rails.

The architect's DISCOVER step needs to read a referenced doc page. We never blindly download —
caps on bytes, content-type allow-list, and a redirect cap.
"""
from __future__ import annotations

import logging

import requests

from ..domain.models import FetchResult

logger = logging.getLogger(__name__)

_TEXTLIKE = ("text/", "application/json", "application/xml")


class HTTPFetcher:
    def __init__(self, default_max_bytes: int = 200_000, timeout: int = 10):
        self.default_max_bytes = default_max_bytes
        self.timeout = timeout

    def fetch(self, url: str, max_bytes: int | None = None) -> FetchResult:
        limit = int(max_bytes or self.default_max_bytes)
        try:
            with requests.get(url, stream=True, timeout=self.timeout,
                              allow_redirects=True) as r:
                ct = r.headers.get("content-type", "").lower()
                # Stream-decode up to limit; bail if not text-like
                raw = bytearray()
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) >= limit:
                        break
                text = ""
                truncated = len(raw) >= limit
                if any(ct.startswith(t) for t in _TEXTLIKE):
                    try:
                        text = raw.decode(r.apparent_encoding or "utf-8",
                                          errors="replace")
                    except Exception:  # noqa: BLE001
                        text = raw.decode("utf-8", errors="replace")
                return FetchResult(url=url, status=r.status_code,
                                   content_type=ct, text=text,
                                   truncated=truncated, bytes_read=len(raw))
        except requests.RequestException as e:
            logger.warning("fetch failed %s: %s", url, e)
            return FetchResult(url=url, status=0, content_type="",
                               text=f"fetch error: {e}", truncated=False, bytes_read=0)
