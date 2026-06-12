"""Stale-snapshot guard (2026-06-12).

The gitops-setup Job seeds oam/applications/application.yaml from the
AppContainerClaim's spec.oamApplication. That snapshot was day-0 write-once, so
a Job re-run (composition change / Crossplane Object retry) re-seeded a STALE
OAM over update-path commits (live failure: rtdemo2 lost env nudges +
publishVersion). Fix is two-sided:

  (a) Job script: preserve a diverged repo file (tested via the composition's
      embedded script — see test_composition_seed_guard below).
  (b) app.submit update path: refresh spec.oamApplication after committing the
      OAM to the per-service repo (best-effort, like reconcile_services).
"""
from __future__ import annotations

import base64
import pathlib

import yaml

from src.application.submit_use_case import SubmitUseCase
from src.infrastructure.k8s_claim_client import K8sClaimClient


def _oam(name="my-svc"):
    return yaml.safe_dump({
        "apiVersion": "core.oam.dev/v1beta1",
        "kind": "Application",
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"components": [{"name": name, "type": "webservice",
                                 "properties": {"name": name, "language": "python"}}]},
    })


class FakeVela:
    def dry_run(self, oam_yaml):
        return True, "ok"


class FakeGitHub:
    def __init__(self, existing_repos=()):
        self.existing = set(existing_repos)
        self.commits = []

    def repo_exists(self, repo):
        return repo in self.existing

    def commit_file(self, path, content, message, branch="main", repo=None):
        self.commits.append((repo, path, content))
        return True, f"sha-{len(self.commits)}"


class FakeArgo:
    def create_workflow_from_template(self, template, params):
        return {"metadata": {"name": f"{template}-wf-1"}}


class BareClaims:
    """Pre-fix claims client surface: NO update_oam_application method."""

    def __init__(self):
        self.created = []

    def create_app_container_claim(self, name, oam_application_b64, **kw):
        self.created.append((name, kw))
        return True, f"AppContainerClaim {name} created"

    def reconcile_services(self, name, services):
        return []


class RefreshClaims(BareClaims):
    def __init__(self, raises=False):
        super().__init__()
        self.raises = raises
        self.refreshed = []

    def update_oam_application(self, name, oam_application_b64):
        if self.raises:
            raise RuntimeError("boom")
        self.refreshed.append((name, oam_application_b64))
        return True


def _uc(github, claims):
    return SubmitUseCase(FakeVela(), github, FakeArgo(), claims=claims,
                         apim_products=None)


# ---------------------------------------------------------------------------
# (b) update path refreshes spec.oamApplication
# ---------------------------------------------------------------------------

def test_update_path_refreshes_claim_oam_snapshot():
    claims = RefreshClaims()
    uc = _uc(FakeGitHub(existing_repos=("my-svc-gitops",)), claims)
    res = uc.submit(_oam())
    assert res.ok
    assert claims.refreshed, "update path must refresh spec.oamApplication"
    name, b64 = claims.refreshed[0]
    assert name == "my-svc"
    decoded = yaml.safe_load(base64.b64decode(b64).decode())
    assert decoded["metadata"]["name"] == "my-svc"


def test_update_path_survives_claims_without_refresh_method():
    # Backward compat: a claims client predating update_oam_application
    # (AttributeError) must not fail the submit.
    uc = _uc(FakeGitHub(existing_repos=("my-svc-gitops",)), BareClaims())
    res = uc.submit(_oam())
    assert res.ok


def test_update_path_survives_refresh_failure():
    claims = RefreshClaims(raises=True)
    uc = _uc(FakeGitHub(existing_repos=("my-svc-gitops",)), claims)
    res = uc.submit(_oam())
    assert res.ok


def test_day0_path_does_not_call_refresh():
    # Day-0 carries the OAM inside create_app_container_claim already.
    claims = RefreshClaims()
    uc = _uc(FakeGitHub(), claims)
    res = uc.submit(_oam())
    assert res.ok
    assert claims.created and not claims.refreshed


# ---------------------------------------------------------------------------
# K8sClaimClient.update_oam_application patch body + error swallowing
# ---------------------------------------------------------------------------

class _FakeApi:
    def __init__(self, raises=False):
        self.raises = raises
        self.patches = []

    def patch_namespaced_custom_object(self, **kw):
        if self.raises:
            raise RuntimeError("404")
        self.patches.append(kw)


def test_claim_client_patches_oam_application():
    c = K8sClaimClient()
    c._api = _FakeApi()
    assert c.update_oam_application("rtdemo2", "b64payload") is True
    body = c._api.patches[0]["body"]
    assert body == {"spec": {"oamApplication": "b64payload"}}
    assert c._api.patches[0]["name"] == "rtdemo2"


def test_claim_client_refresh_best_effort_on_error():
    c = K8sClaimClient()
    c._api = _FakeApi(raises=True)
    assert c.update_oam_application("rtdemo2", "b64payload") is False


def test_claim_client_refresh_noop_on_empty_payload():
    c = K8sClaimClient()
    c._api = _FakeApi()
    assert c.update_oam_application("rtdemo2", "") is False
    assert not c._api.patches


# ---------------------------------------------------------------------------
# (a) Job-side guard: the gitops-setup script preserves diverged OAM files
# ---------------------------------------------------------------------------

_COMPOSITION = pathlib.Path(__file__).resolve().parents[3] / \
    "substrate" / "crossplane" / "app-container-claim-composition.yaml"


def test_composition_seed_guard_preserves_diverged_oam():
    text = _COMPOSITION.read_text()
    assert "preserving consumer OAM (update-path commits present)" in text
    assert "cmp -s /tmp/oam-seed.yaml oam/applications/application.yaml" in text
    # The unconditional verbatim re-seed message must be gone.
    assert "re-seeded consumer OAM (oamApplication set)" not in text
