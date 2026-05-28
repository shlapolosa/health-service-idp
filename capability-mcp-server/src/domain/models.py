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
