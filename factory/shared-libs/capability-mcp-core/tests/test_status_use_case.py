"""Unit tests for app.status (W5) — phase collapse from claim + ArgoCD sources."""
from __future__ import annotations

from src.application.status_use_case import StatusUseCase


class FakeClaims:
    def __init__(self, claim_status=None, argocd=None):
        self._claim = claim_status
        self._argocd = argocd

    def get_claim_status(self, name):
        return self._claim

    def get_argocd_app_status(self, name, argocd_namespace="argocd"):
        return self._argocd


def test_ready_when_synced_and_healthy():
    uc = StatusUseCase(FakeClaims(
        claim_status={"ready": True},
        argocd={"sync": "Synced", "health": "Healthy", "revision": "abc", "operation_phase": "Succeeded"},
    ))
    r = uc.status_of("my-svc")
    assert r["ok"] and r["phase"] == "ready"
    assert r["argocd"]["health"] == "Healthy"


def test_reconciling_when_argocd_progressing():
    uc = StatusUseCase(FakeClaims(
        claim_status={"ready": True},
        argocd={"sync": "OutOfSync", "health": "Progressing", "revision": "abc", "operation_phase": None},
    ))
    assert uc.status_of("my-svc")["phase"] == "reconciling"


def test_scaffolding_when_only_claim_not_ready():
    uc = StatusUseCase(FakeClaims(claim_status={"ready": False}, argocd=None))
    r = uc.status_of("my-svc")
    assert r["phase"] == "scaffolding"
    assert r["scaffold"]["ready"] is False


def test_unknown_with_note_when_nothing_found():
    uc = StatusUseCase(FakeClaims())
    r = uc.status_of("ghost")
    assert r["phase"] == "unknown" and "note" in r


def test_empty_name_rejected():
    uc = StatusUseCase(FakeClaims())
    assert not uc.status_of("  ")["ok"]
