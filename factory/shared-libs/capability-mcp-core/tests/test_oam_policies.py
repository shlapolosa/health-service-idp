"""Tests for the extracted platform-composition policies (oam_policies) and their
surfacing through catalog_use_cases.validate (oam.dry_run).

These lock the two new behaviours added 2026-06-19:
  1. validate_policies() flags an exposed-without-identity OAM (and singleton dupes).
  2. CatalogUseCases.validate() appends `platform-policy:` violations to the
     dry-run diagnostics and flips ok=False — so the architect, which self-corrects
     on what oam.dry_run reports, discovers them PRE-propose.
"""
from unittest.mock import MagicMock

from src.application import oam_policies
from src.application.catalog_use_cases import CatalogUseCases
from src.application.submit_use_case import SubmitUseCase

_EXPOSED_NO_IDENTITY = {
    "spec": {
        "components": [
            {"name": "patient-api", "type": "webservice",
             "traits": [{"type": "expose-api", "properties": {}}]},
        ]
    }
}

_COMPLIANT = {
    "spec": {
        "components": [
            {"name": "idp", "type": "auth0-idp"},
            {"name": "patient-api", "type": "webservice",
             "properties": {"identity": "idp"},
             "traits": [{"type": "expose-api", "properties": {"identity": "idp"}}]},
        ]
    }
}


def test_validate_policies_flags_exposed_without_identity():
    violations = oam_policies.validate_policies(_EXPOSED_NO_IDENTITY)
    assert len(violations) == 1
    assert "identity topology" in violations[0]
    assert "patient-api" in violations[0]


def test_validate_policies_clean_for_compliant_oam():
    assert oam_policies.validate_policies(_COMPLIANT) == []


def test_validate_policies_flags_duplicate_singletons():
    app = {"spec": {"components": [
        {"name": "rt-a", "type": "realtime-platform"},
        {"name": "rt-b", "type": "realtime-platform"},
    ]}}
    violations = oam_policies.validate_policies(app)
    assert any("singleton topology" in v and "realtime-platform" in v for v in violations)


def test_validate_policies_flags_multiple_identities():
    app = {"spec": {"components": [
        {"name": "idp-a", "type": "auth0-idp"},
        {"name": "idp-b", "type": "auth0-idp"},
    ]}}
    violations = oam_policies.validate_policies(app)
    assert any("at most ONE" in v and "identity topology" in v for v in violations)


def test_submit_delegates_identically():
    """submit's _validate_identity_topology keeps its single-string contract and
    returns the same first-violation message the policy module produces."""
    msg = SubmitUseCase._validate_identity_topology(_EXPOSED_NO_IDENTITY)
    assert msg == oam_policies.validate_policies(_EXPOSED_NO_IDENTITY)[0]
    assert SubmitUseCase._validate_identity_topology(_COMPLIANT) is None


def _validate_yaml(oam_yaml: str, dry_run_ok: bool = True, dry_run_diag: str = "ok"):
    vela = MagicMock()
    vela.dry_run.return_value = (dry_run_ok, dry_run_diag)
    uc = CatalogUseCases(MagicMock(), vela, MagicMock())
    return uc.validate(oam_yaml)


def test_dry_run_surfaces_platform_policy_violation():
    import yaml
    res = _validate_yaml(yaml.safe_dump(_EXPOSED_NO_IDENTITY))
    assert res["ok"] is False  # policy flips ok even though vela passed
    assert "platform-policy:" in res["diagnostics"]
    assert "identity topology" in res["diagnostics"]
    assert "ok" in res["diagnostics"]  # original vela diagnostics preserved


def test_dry_run_clean_oam_passes_through():
    import yaml
    res = _validate_yaml(yaml.safe_dump(_COMPLIANT))
    assert res["ok"] is True
    assert "platform-policy:" not in res["diagnostics"]
