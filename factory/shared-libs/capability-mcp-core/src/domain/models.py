"""Domain models — plain dataclasses, no framework deps (onion: innermost layer)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CatalogComponent:
    """A published OAM ComponentDefinition as the catalog exposes it."""
    name: str
    description: str
    workload_kind: str = ""              # e.g. serving.knative.dev/v1 Service
    category: str = ""                   # from catalog.oam.dev/category annotation, if present
    status: str = ""                     # alpha|beta|GA|deprecated, if annotated
    revision: str = ""                   # KubeVela definitionRevision, if present
    parameters: list[dict[str, Any]] = field(default_factory=list)  # vela-rendered schema rows


@dataclass
class ValidationResult:
    ok: bool
    diagnostics: str = ""                # vela dry-run output / errors


@dataclass
class ScoredCandidate:
    technology: str
    score: float                         # lower = better (penalty sum)
    passed_hard: bool
    detail: dict[str, Any] = field(default_factory=dict)
    reason: str = ""                     # human-readable, feeds the ADR


@dataclass
class SubmitResult:
    ok: bool
    commit_sha: Optional[str] = None     # gitops commit (the gate)
    workflow_name: Optional[str] = None  # oam-apply workflow triggered
    message: str = ""
    # SPEC-1 (#173, dev-agent W1): deterministic hash of the normalized
    # REQUIREMENTS.md this submit committed, when `requirements` was supplied.
    # The dev-agent trigger (W3) keys re-fires on this value. None when no
    # requirements travelled with the submission (exactly today's behaviour).
    spec_hash: Optional[str] = None


@dataclass
class DeleteResult:
    """app.delete — outcome of tearing down an OAM application's full footprint.

    `planned` is the ordered list of (kind, name) the use-case discovered and
    intends to act on; on a real run `deleted`/`auto_sync_disabled` record what
    actually happened. dry_run returns ok=True with planned populated and the
    delete lists empty. Defeating the GitOps recreation loop hinges on
    `auto_sync_disabled` happening BEFORE any delete (see recreation-loop
    memory): the result surfaces that ordering for auditability.
    """
    ok: bool
    app_name: str = ""
    dry_run: bool = False
    purge_repos: bool = False
    planned: list[str] = field(default_factory=list)        # "Kind/name" entries, in action order
    auto_sync_disabled: list[str] = field(default_factory=list)  # ArgoCD apps patched first
    deleted: list[str] = field(default_factory=list)        # "Kind/name" actually deleted
    errors: list[str] = field(default_factory=list)         # non-fatal per-resource failures
    message: str = ""
