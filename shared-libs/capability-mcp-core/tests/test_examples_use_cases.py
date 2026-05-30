"""ExamplesUseCases tests — pattern enum + sandboxed file reads + deterministic pattern_for()."""
from __future__ import annotations

import pytest

from src.application.examples_use_cases import ExamplesUseCases
from src.infrastructure.examples_loader import ExamplesLoader


def test_patterns_lists_known(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    names = uc.patterns()
    # Six patterns (a–f); see examples_loader._PATTERNS.
    assert {"pattern-a-helm-chart", "pattern-b-helm-cluster-perms",
            "pattern-c-operator-backed", "pattern-d-xrd-composition",
            "pattern-e-composite-oam", "pattern-f-trait"} <= set(names)


def test_read_pattern_a(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    files = uc.read("pattern-a-helm-chart")
    # The exemplar is present in our tmp repo_root.
    assert "crossplane/oam/nats-jetstream-componentdefinition.yaml" in files
    assert "ComponentDefinition" in files["crossplane/oam/nats-jetstream-componentdefinition.yaml"]


def test_read_unknown_pattern_raises(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    with pytest.raises(ValueError):
        uc.read("pattern-z-bogus")


def test_pattern_for_helm_no_perms(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    out = uc.pattern_for("helm-chart", requires_cluster_permissions=False)
    assert out["pattern"] == "pattern-a-helm-chart"


def test_pattern_for_helm_with_perms(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    out = uc.pattern_for("helm-chart", requires_cluster_permissions=True)
    assert out["pattern"] == "pattern-b-helm-cluster-perms"


def test_pattern_for_managed_service(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    out = uc.pattern_for("managed-service")
    assert out["pattern"] == "pattern-d-xrd-composition"
    # The exemplar for D is application-claim-composition.yaml (present in our tmp repo).
    assert "crossplane/application-claim-composition.yaml" in out["files"]


def test_pattern_for_unknown_kind_raises(repo_root):
    uc = ExamplesUseCases(ExamplesLoader(str(repo_root)))
    with pytest.raises(ValueError):
        uc.pattern_for("nonsense")
