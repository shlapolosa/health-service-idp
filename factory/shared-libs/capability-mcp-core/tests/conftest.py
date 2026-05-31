"""Test fixtures for capability-mcp-server P8.1 surface.

We build a self-contained capability-factory/ tree + repo-root in a tmp dir so tests don't depend
on the real repo layout. The fixtures mirror the production paths exactly (the same paths the
in-cluster image bakes in) so the loaders exercise their real code paths.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make src/ importable as `from src...` without installing the package.
_HERE = Path(__file__).resolve()
_PKG_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_PKG_ROOT))


@pytest.fixture
def factory_dir(tmp_path) -> Path:
    """A minimal capability-factory/ with one KB entry (kafka — the operator-backed case)."""
    root = tmp_path / "capability-factory"
    (root / "kb").mkdir(parents=True)
    (root / "schema").mkdir()
    (root / "weightings").mkdir()
    (root / "kb" / "kafka.yaml").write_text(
        "technology: kafka\n"
        "category: messaging\n"
        "profile: {durability: strong, throughputClass: very-high}\n"
        "provisioning:\n"
        "  kind: operator-backed\n"
        "  source: operator:strimzi\n"
        "  requires_cluster_permissions: false\n"
        "maturity: kb\n"
    )
    (root / "kb" / "nats-jetstream.yaml").write_text(
        "technology: nats-jetstream\n"
        "category: messaging\n"
        "profile: {durability: strong, footprint: light}\n"
        "provisioning:\n"
        "  kind: helm-chart\n"
        "  source: helm:nats\n"
        "  requires_cluster_permissions: true\n"
        "  cluster_permissions:\n"
        "    - {resources: [namespaces], verbs: [create]}\n"
        "maturity: published\n"
    )
    (root / "schema" / "quality-attributes-v0.yaml").write_text(
        "version: v0\nattributes: {}\n"
    )
    (root / "weightings" / "category-defaults.yaml").write_text(
        "categories: {messaging: {high: [durability], med: [], low: []}}\n"
    )
    return root


@pytest.fixture
def repo_root(tmp_path) -> Path:
    """A minimal /repo with the nats-jetstream CD as the pattern-A exemplar."""
    root = tmp_path / "repo"
    (root / "crossplane" / "oam").mkdir(parents=True)
    (root / "crossplane" / "oam" / "nats-jetstream-componentdefinition.yaml").write_text(
        "apiVersion: core.oam.dev/v1beta1\nkind: ComponentDefinition\n"
        "metadata: {name: nats-jetstream}\nspec: {workload: {definition: {apiVersion: helm.crossplane.io/v1beta1, kind: Release}}}\n"
    )
    (root / "crossplane" / "application-claim-composition.yaml").write_text(
        "apiVersion: apiextensions.crossplane.io/v1\nkind: Composition\n"
    )
    return root


@pytest.fixture
def fake_k8s():
    """An in-memory K8sCatalogClient stand-in that returns a controllable set of CDs + traits +
    policies + workflow steps."""
    class _Fake:
        def __init__(self):
            self.cds: dict[str, dict] = {}
            self.traits: dict[str, dict] = {}
            self.policies: dict[str, dict] = {}
            self.workflow_steps: dict[str, dict] = {}

        # Components
        def list_components(self):
            return list(self.cds.values())

        def get_component(self, name):
            return self.cds.get(name)

        def add(self, name: str, revision: str = "v1"):
            self.cds[name] = {"name": name, "description": "", "workload_kind": "",
                              "category": "", "status": "", "revision": revision}

        # Traits
        def list_traits(self):
            return list(self.traits.values())

        def get_trait(self, name):
            return self.traits.get(name)

        def add_trait(self, name: str, applies: list[str] | None = None,
                      description: str = "", namespace: str = "vela-system"):
            self.traits[name] = {"name": name, "namespace": namespace,
                                 "description": description,
                                 "appliesToWorkloads": applies or [],
                                 "conflictsWith": [], "podDisruptive": False}

        # Policies
        def list_policies(self):
            return [{k: v for k, v in p.items() if k != "cue_template"}
                    for p in self.policies.values()]

        def get_policy(self, name):
            return self.policies.get(name)

        def add_policy(self, name: str, cue_template: str = "", description: str = "",
                       namespace: str = "vela-system"):
            self.policies[name] = {"name": name, "namespace": namespace,
                                   "description": description, "cue_template": cue_template}

        # WorkflowSteps
        def list_workflow_steps(self):
            return [{k: v for k, v in w.items() if k != "cue_template"}
                    for w in self.workflow_steps.values()]

        def get_workflow_step(self, name):
            return self.workflow_steps.get(name)

        def add_workflow_step(self, name: str, cue_template: str = "", description: str = "",
                              namespace: str = "vela-system"):
            self.workflow_steps[name] = {"name": name, "namespace": namespace,
                                         "description": description,
                                         "cue_template": cue_template}

    return _Fake()
