"""Factory use-cases — the only write surface in the Capability Factory.

`propose(req)` is the single verb. The flow:

  1. Validate repo is in the allow-list (defence: caller can't open PRs against anything other
     than the configured proposable repos).
  2. Resolve base-branch SHA via GitHub App.
  3. Create a new branch off that SHA.
  4. Commit each file (Contents API, idempotent — refetch sha if exists).
  5. Open a PR.
  6. Emit an audit log line with the caller OID (set by the auth middleware), repo, branch, PR
     number, and the list of files. This is the audit trail referenced by the P8.2 design.

NO retry-loop, NO automatic merge, NO secondary effects. The PR is the membrane — every change
goes through human (or future automated-gate) review.
"""
from __future__ import annotations

import logging
import re
import time

from ..domain.models import ProposeRequest, ProposeResult
from ..infrastructure.github_app_client import GitHubAppClient

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slug(s: str, maxlen: int = 40) -> str:
    s = _SLUG_RE.sub("-", (s or "proposal").lower()).strip("-")
    return s[:maxlen] or "proposal"


class FactoryUseCases:
    def __init__(self, gh: GitHubAppClient, owner: str, allowed_repos: set[str]):
        if not allowed_repos:
            raise ValueError("FactoryUseCases: allowed_repos must be non-empty")
        self.gh = gh
        self.owner = owner
        self.allowed_repos = allowed_repos

    def propose(self, req: ProposeRequest, caller_oid: str = "unknown") -> ProposeResult:
        # ---- validate ----
        if req.repo not in self.allowed_repos:
            return ProposeResult(ok=False,
                                 message=f"repo not in allow-list: {req.repo} "
                                         f"(allowed: {sorted(self.allowed_repos)})")
        if not req.files:
            return ProposeResult(ok=False, message="files dict is empty")
        if not req.title:
            return ProposeResult(ok=False, message="title required")

        branch = f"{req.branch_prefix.rstrip('/')}/{_slug(req.title)}-{int(time.time())}"

        # ---- resolve base + create branch ----
        try:
            base_sha = self.gh.get_ref_sha(self.owner, req.repo, req.base)
            self.gh.create_branch(self.owner, req.repo, branch, base_sha)
        except Exception as e:  # noqa: BLE001
            logger.exception("factory: branch setup failed")
            return ProposeResult(ok=False, message=f"branch setup failed: {e}")

        # ---- commit each file ----
        commits: list[str] = []
        for path, content in req.files.items():
            try:
                sha = self.gh.commit_file(self.owner, req.repo, branch, path, content,
                                          message=f"factory: {path}")
                commits.append(sha)
            except Exception as e:  # noqa: BLE001
                logger.exception("factory: commit_file %s failed", path)
                return ProposeResult(ok=False, branch=branch, commits=commits,
                                     message=f"commit failed at {path}: {e}")

        # ---- open PR ----
        try:
            url, number = self.gh.open_pr(self.owner, req.repo, head=branch, base=req.base,
                                          title=req.title, body=req.body)
        except Exception as e:  # noqa: BLE001
            logger.exception("factory: open_pr failed")
            return ProposeResult(ok=False, branch=branch, commits=commits,
                                 message=f"open_pr failed: {e}")

        # ---- audit ----
        logger.info(
            "AUDIT factory.propose caller_oid=%s owner=%s repo=%s branch=%s "
            "pr=%d files=%s commits=%d",
            caller_oid, self.owner, req.repo, branch, number,
            list(req.files.keys()), len(commits),
        )
        return ProposeResult(ok=True, pr_url=url, pr_number=number,
                             branch=branch, commits=commits,
                             message="proposed")

    def list_open_prs(self, repo: str, head_prefix: str | None = "factory/") -> list[dict]:
        if repo not in self.allowed_repos:
            raise ValueError(f"repo not in allow-list: {repo}")
        return self.gh.list_open_prs(self.owner, repo, head_prefix=head_prefix)
