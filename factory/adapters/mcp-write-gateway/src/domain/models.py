"""Factory MCP domain models — the write surface of the Capability Factory.

Only one verb: `propose`. Takes a bundle of files + PR metadata, returns an audit record. All
mutations of the git tree pass through this gate — there are intentionally no other write tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProposeRequest:
    """Caller's PR proposal. Repo is constrained to an allow-list at the use-case layer."""
    repo: str                          # e.g. "health-service-idp" (without owner)
    title: str
    body: str
    files: dict[str, str]              # path → content; relative to repo root
    base: str = "main"                 # base branch the PR targets
    branch_prefix: str = "factory"     # branch name = <prefix>/<slug>-<unix-ts>


@dataclass
class ProposeResult:
    """One audit record per propose call — what the architect committed and where."""
    ok: bool
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    commits: list[str] = field(default_factory=list)   # commit SHAs in order
    message: str = ""
