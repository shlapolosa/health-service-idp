"""GitHub App client — mints short-lived installation tokens, executes git ops.

Flow (RFC 7519 JWT → installation token, per GitHub docs):
  1. Sign a JWT with the App's PEM private key (issuer = app_id, valid 10 min).
  2. POST /app/installations/{install_id}/access_tokens with that JWT.
  3. Use the returned installation token (1h validity) for all repo API calls.

Why GitHub Apps over PAT (per the P8.2 design decision):
  - Per-installation, per-repo, fine-grained permissions (contents:write + pull_requests:write only).
  - Short-lived tokens (1h) minted from a long-lived private key in Key Vault.
  - "FactoryBot opened this PR" — clear audit identity, not the human PAT-holder.

Installation token is cached in-memory until 60s before expiry. GitHub returns expires_at; we honor it.
"""
from __future__ import annotations

import base64
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import jwt as pyjwt        # pyjwt[crypto] for RS256 signing
import requests

from .credential_provider import CredentialProvider

logger = logging.getLogger(__name__)
_API = "https://api.github.com"


class GitHubAppClient:
    """One App + one Installation. Construct N clients if you target multiple installations."""

    def __init__(self, app_id: str, installation_id: str, cred: CredentialProvider,
                 timeout: int = 30):
        if not app_id or not installation_id:
            raise ValueError("GitHubAppClient: app_id + installation_id required")
        self.app_id = app_id
        self.installation_id = installation_id
        self.cred = cred
        self.timeout = timeout
        self._token: Optional[str] = None
        self._token_exp: float = 0.0

    # ---- auth ----

    def _app_jwt(self) -> str:
        """RFC 7519 JWT signed with the App's PEM, valid for ~9 minutes (GitHub max is 10)."""
        now = int(time.time())
        payload = {"iat": now - 30, "exp": now + 9 * 60, "iss": str(self.app_id)}
        return pyjwt.encode(payload, self.cred.get_pem(), algorithm="RS256")

    def installation_token(self) -> str:
        """Cached installation token. Re-mints when < 60s left."""
        if self._token and time.time() < (self._token_exp - 60):
            return self._token
        r = requests.post(
            f"{_API}/app/installations/{self.installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {self._app_jwt()}",
                     "Accept": "application/vnd.github+json",
                     "User-Agent": "capability-factory-mcp"},
            timeout=self.timeout,
        )
        if r.status_code != 201:
            raise RuntimeError(f"installation token exchange failed: {r.status_code} {r.text[:200]}")
        body = r.json()
        self._token = body["token"]
        # GitHub returns ISO8601 with trailing Z.
        self._token_exp = datetime.strptime(body["expires_at"], "%Y-%m-%dT%H:%M:%SZ") \
            .replace(tzinfo=timezone.utc).timestamp()
        logger.info("github_app: minted installation token (expires_at=%s)", body["expires_at"])
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"token {self.installation_token()}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "capability-factory-mcp"}

    # ---- git ops ----

    def get_ref_sha(self, owner: str, repo: str, branch: str) -> str:
        r = requests.get(f"{_API}/repos/{owner}/{repo}/git/ref/heads/{branch}",
                         headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()["object"]["sha"]

    def create_branch(self, owner: str, repo: str, branch: str, sha: str) -> None:
        r = requests.post(f"{_API}/repos/{owner}/{repo}/git/refs",
                          headers=self._headers(),
                          json={"ref": f"refs/heads/{branch}", "sha": sha},
                          timeout=self.timeout)
        if r.status_code == 422 and "already exists" in r.text.lower():
            logger.info("github_app: branch %s/%s already exists, reusing", repo, branch)
            return
        r.raise_for_status()

    def commit_file(self, owner: str, repo: str, branch: str,
                    path: str, content: str, message: str) -> str:
        """Idempotent — fetches the existing blob sha if any. Returns commit sha."""
        url = f"{_API}/repos/{owner}/{repo}/contents/{path}"
        existing = requests.get(url, headers=self._headers(),
                                params={"ref": branch}, timeout=self.timeout)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        body = {"message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch}
        if sha:
            body["sha"] = sha
        r = requests.put(url, headers=self._headers(), json=body, timeout=self.timeout)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"commit_file {path} failed: {r.status_code} {r.text[:200]}")
        return r.json().get("commit", {}).get("sha", "")

    def open_pr(self, owner: str, repo: str, head: str, base: str,
                title: str, body: str) -> tuple[str, int]:
        r = requests.post(f"{_API}/repos/{owner}/{repo}/pulls",
                          headers=self._headers(),
                          json={"title": title, "body": body, "head": head, "base": base},
                          timeout=self.timeout)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"open_pr failed: {r.status_code} {r.text[:200]}")
        j = r.json()
        return j["html_url"], j["number"]

    def list_open_prs(self, owner: str, repo: str, head_prefix: str | None = None) -> list[dict]:
        r = requests.get(f"{_API}/repos/{owner}/{repo}/pulls",
                         headers=self._headers(),
                         params={"state": "open", "per_page": 100},
                         timeout=self.timeout)
        r.raise_for_status()
        out = []
        for p in r.json():
            head = (p.get("head") or {}).get("ref", "")
            if head_prefix and not head.startswith(head_prefix):
                continue
            out.append({"number": p["number"], "title": p["title"],
                        "html_url": p["html_url"], "head": head, "base": p["base"]["ref"]})
        return out
