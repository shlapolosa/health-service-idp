"""Shared fixtures — fake GitHub App client + in-memory event log."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Make src/ importable without installing the package.
_PKG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG_ROOT))


@pytest.fixture
def fake_gh():
    """In-memory GitHub App stand-in — records calls + supports configurable failure injection."""
    class _Fake:
        def __init__(self):
            self.refs: dict[tuple[str, str], str] = {("health-service-idp", "main"): "sha-main"}
            self.branches: list[tuple[str, str, str]] = []
            self.commits: list[dict[str, Any]] = []
            self.prs: list[dict[str, Any]] = []
            self.next_pr = 1
            self.fail_on: str | None = None  # one of: get_ref_sha, create_branch, commit_file, open_pr

        # ---- factory hooks ----
        def get_ref_sha(self, owner, repo, branch):
            if self.fail_on == "get_ref_sha":
                raise RuntimeError("injected: get_ref_sha")
            return self.refs[(repo, branch)]

        def create_branch(self, owner, repo, branch, sha):
            if self.fail_on == "create_branch":
                raise RuntimeError("injected: create_branch")
            self.branches.append((repo, branch, sha))
            self.refs[(repo, branch)] = sha

        def commit_file(self, owner, repo, branch, path, content, message):
            if self.fail_on == "commit_file":
                raise RuntimeError("injected: commit_file")
            sha = f"commit-{len(self.commits)+1}"
            self.commits.append({"repo": repo, "branch": branch, "path": path,
                                 "content": content, "message": message, "sha": sha})
            return sha

        def open_pr(self, owner, repo, head, base, title, body):
            if self.fail_on == "open_pr":
                raise RuntimeError("injected: open_pr")
            n = self.next_pr
            self.next_pr += 1
            self.prs.append({"number": n, "head": head, "base": base,
                             "title": title, "body": body})
            return (f"https://github.com/{owner}/{repo}/pull/{n}", n)

        def list_open_prs(self, owner, repo, head_prefix=None):
            return [{"number": p["number"], "title": p["title"],
                     "html_url": f"https://github.com/{owner}/{repo}/pull/{p['number']}",
                     "head": p["head"], "base": p["base"]}
                    for p in self.prs
                    if (not head_prefix) or p["head"].startswith(head_prefix)]

    return _Fake()
