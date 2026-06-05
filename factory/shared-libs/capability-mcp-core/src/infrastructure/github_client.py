"""GitHub client — the gitops-commit gate.

slack-api-server/src/infrastructure/github_client.py is repository-dispatch only (no commit_file),
so `commit_file` (Contents API GET sha -> PUT) is genuinely net-new — this is the gate where the
consumer's validated OAM Application is committed to the gitops repo before provisioning.
"""
from __future__ import annotations

import base64
import logging
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)
_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, owner: str, gitops_repo: str, timeout: int = 30):
        self.token = token
        self.owner = owner
        self.gitops_repo = gitops_repo  # e.g. "health-service-idp-gitops"
        self.timeout = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "capability-mcp",
        }

    def repo_exists(self, repo: str) -> bool:
        """True when `repo` exists under self.owner. Used by app.submit routing:
        per-service gitops repo present => update path (direct commit), absent => day-0
        (create AppContainerClaim)."""
        try:
            r = requests.get(f"{_API}/repos/{self.owner}/{repo}",
                             headers=self._headers(), timeout=self.timeout)
            return r.status_code == 200
        except requests.RequestException as e:  # noqa: BLE001
            logger.error("repo_exists transport error for %s: %s", repo, e)
            return False

    def commit_file(self, path: str, content: str, message: str,
                    branch: str = "main", repo: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Create or update `path` on `branch`. Returns (ok, commit_sha).
        Targets the central gitops repo unless `repo` overrides it (declarative-spine W4:
        updates to already-scaffolded apps commit straight to the per-service gitops repo).
        Idempotent: fetches the existing blob sha first so re-submits update rather than 409."""
        target_repo = repo or self.gitops_repo
        url = f"{_API}/repos/{self.owner}/{target_repo}/contents/{path}"
        existing_sha = self._existing_sha(url, branch)
        body = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if existing_sha:
            body["sha"] = existing_sha
        try:
            resp = requests.put(url, headers=self._headers(), json=body, timeout=self.timeout)
            if resp.status_code in (200, 201):
                sha = resp.json().get("commit", {}).get("sha")
                logger.info("✅ committed %s -> %s@%s (%s)", path, target_repo, branch, sha)
                return True, sha
            logger.error("commit_file failed %s: %s", resp.status_code, resp.text[:200])
            return False, None
        except requests.RequestException as e:  # noqa: BLE001
            logger.error("commit_file transport error: %s", e)
            return False, None

    def _existing_sha(self, url: str, branch: str) -> Optional[str]:
        try:
            r = requests.get(url, headers=self._headers(), params={"ref": branch}, timeout=self.timeout)
            if r.status_code == 200:
                return r.json().get("sha")
        except requests.RequestException:
            pass
        return None
