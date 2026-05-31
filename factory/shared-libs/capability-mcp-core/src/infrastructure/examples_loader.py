"""Examples loader — sandboxed read of exemplar OAM/Crossplane artifacts for the architect.

Pattern table (mirrors capability-factory/schema/quality-attributes-v0.yaml provisioning.patterns):
  pattern-a-helm-chart          — single Helm Release CD (no special perms)
  pattern-b-helm-cluster-perms  — Helm Release CD + ClusterRoleBinding scaffolding
  pattern-c-operator-backed     — Object CR pointing at a pre-installed operator
  pattern-d-xrd-composition     — XRD + Composition + claim-creating CD
  pattern-e-composite-oam       — multi-component OAM (e.g. realtime-platform)
  pattern-f-trait               — TraitDefinition + (optional) admission hook

The agent (Foundry chat in P8.3, or scripts/architect.py in P8.1) calls `examples.read(<pattern>)`
to get the exemplar files as context for LLM template-fill (Phase 5 of agent reasoning).

Read is sandboxed: only files under crossplane/, oam/traits/, and capability-factory/ are exposed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Hard-coded pattern → file list. Add new patterns by appending; never trust LLM input as a path.
# Files are resolved relative to REPO_ROOT (image-baked at /repo, or set explicitly in local dev).
_PATTERNS: dict[str, list[str]] = {
    "pattern-a-helm-chart": [
        # Best-fit single-Helm-Release CD — nats-jetstream is the cleanest example we have.
        # If/when a chart without cluster-perms lands (e.g. postgres-bitnami CD), prefer that.
        "crossplane/oam/nats-jetstream-componentdefinition.yaml",
    ],
    "pattern-b-helm-cluster-perms": [
        "crossplane/oam/nats-jetstream-componentdefinition.yaml",
        # Architect emits a ClusterRoleBinding alongside; we don't have a checked-in exemplar yet
        # — note for the architect prompt: "see kb.cluster_permissions for the verbs to grant".
    ],
    "pattern-c-operator-backed": [
        # Kafka via Strimzi is the canonical case. CD is not yet in the repo (kafka is maturity:kb,
        # not yet published). Until it lands, use the auth0-idp CD which follows the Object pattern.
        "crossplane/oam/auth0-idp-componentdefinition.yaml",
    ],
    "pattern-d-xrd-composition": [
        "crossplane/application-claim-composition.yaml",
        "crossplane/oam/crossplane-xrds.yaml",
    ],
    "pattern-e-composite-oam": [
        "crossplane/oam/realtime-platform-component-definition.yaml",
    ],
    "pattern-f-trait": [
        "crossplane/oam/policy-trait-definitions.yaml",
    ],
}

# Allowed path prefixes — any file outside these is silently dropped (defence-in-depth against
# accidentally including non-exemplar configs if the pattern table grows).
_ALLOWED_PREFIXES: tuple[str, ...] = ("crossplane/", "oam/", "capability-factory/")


class ExamplesLoader:
    def __init__(self, repo_root: str | None = None):
        self.root = Path(repo_root or os.getenv("REPO_ROOT", "/repo"))

    def patterns(self) -> list[str]:
        """List known artifact patterns."""
        return list(_PATTERNS.keys())

    def read(self, pattern: str) -> dict[str, str]:
        """Return {relative_path: content} for the exemplar files of `pattern`.

        Raises ValueError on unknown pattern. Silently skips files outside the sandbox or missing
        from disk (so an incomplete repo doesn't crash the MCP)."""
        if pattern not in _PATTERNS:
            raise ValueError(f"unknown pattern: {pattern}; known: {sorted(_PATTERNS)}")
        out: dict[str, str] = {}
        for rel in _PATTERNS[pattern]:
            if not any(rel.startswith(p) for p in _ALLOWED_PREFIXES):
                logger.warning("examples_loader: path %s outside sandbox, skipping", rel)
                continue
            p = self.root / rel
            if not p.is_file():
                logger.warning("examples_loader: %s missing on disk under %s", rel, self.root)
                continue
            out[rel] = p.read_text()
        return out

    def pattern_for(self, kind: str, requires_cluster_permissions: bool = False) -> str:
        """Deterministic mapping from KB provisioning.kind → exemplar pattern name.

        This is THE Phase-4 (pattern-match) decision. Keeping it co-located with the loader so
        the choice is one function call away wherever the architect runs (Foundry agent, CLI,
        KB-watch). Mirrors capability-factory/schema/quality-attributes-v0.yaml provisioning.patterns.
        """
        if kind == "helm-chart":
            return "pattern-b-helm-cluster-perms" if requires_cluster_permissions else "pattern-a-helm-chart"
        if kind == "operator-backed":
            return "pattern-c-operator-backed"
        if kind == "managed-service":
            return "pattern-d-xrd-composition"
        if kind == "composite":
            return "pattern-e-composite-oam"
        if kind == "trait":
            return "pattern-f-trait"
        raise ValueError(f"unknown provisioning.kind: {kind}")
