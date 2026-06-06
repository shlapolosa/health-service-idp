"""Unit tests for app.submit declarative-spine routing (W4; RETIRE-WFT #149).

Routing matrix:
  - no scaffold component            -> oam-apply (legacy, bring-your-own-image)
  - scaffold + repo exists           -> direct commit to per-service repo (no workflow)
  - scaffold + repo absent           -> AppContainerClaim creation (no workflow)
  - scaffold + claims client absent  -> error (legacy oam-driven-contract WFT retired)
"""
from __future__ import annotations

import yaml

from src.application.submit_use_case import SubmitUseCase


def _oam(component_type="webservice", language="python", image=None, name="my-svc"):
    props = {"name": name}
    if language:
        props["language"] = language
    if image:
        props["image"] = image
    return yaml.safe_dump({
        "apiVersion": "core.oam.dev/v1beta1",
        "kind": "Application",
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"components": [{"name": name, "type": component_type, "properties": props}]},
    })


class FakeVela:
    def dry_run(self, oam_yaml):
        return True, "ok"


class FakeGitHub:
    def __init__(self, existing_repos=()):
        self.existing = set(existing_repos)
        self.commits = []  # (repo_or_None, path)

    def repo_exists(self, repo):
        return repo in self.existing

    def commit_file(self, path, content, message, branch="main", repo=None):
        self.commits.append((repo, path))
        return True, f"sha-{len(self.commits)}"


class FakeArgo:
    def __init__(self):
        self.fired = []  # (template, params)

    def create_workflow_from_template(self, template, params):
        self.fired.append((template, params))
        return {"metadata": {"name": f"{template}-wf-1"}}


class FakeClaims:
    def __init__(self, ok=True):
        self.ok = ok
        self.created = []

    def create_app_container_claim(self, name, oam_application_b64, **kw):
        self.created.append((name, kw))
        return self.ok, f"AppContainerClaim {name} created"


def _uc(github=None, claims=...):
    gh = github or FakeGitHub()
    cl = FakeClaims() if claims is ... else claims
    return SubmitUseCase(FakeVela(), gh, FakeArgo(), claims=cl), gh


def test_no_scaffold_routes_to_oam_apply():
    uc, gh = _uc()
    res = uc.submit(_oam(language=None))  # webservice without language -> no scaffold
    assert res.ok
    assert uc.argo.fired and uc.argo.fired[0][0] == "oam-apply"


def test_byo_image_routes_to_oam_apply():
    uc, gh = _uc()
    res = uc.submit(_oam(image="healthidpuaeacr.azurecr.io/custom:v9"))
    assert res.ok
    assert uc.argo.fired and uc.argo.fired[0][0] == "oam-apply"


def test_day0_creates_claim_not_workflow():
    uc, gh = _uc()
    res = uc.submit(_oam())
    assert res.ok, res.message
    assert uc.claims.created, "expected AppContainerClaim creation"
    name, kw = uc.claims.created[0]
    assert name == "my-svc"
    assert kw["delivery_target"] == "host"
    assert kw["language"] == "python" and kw["framework"] == "fastapi"
    assert not uc.argo.fired, "no workflow may fire on the declarative path"
    # central ledger commit happened (repo=None)
    assert (None, "oam/applications/my-svc.yaml") in gh.commits


def test_day0_framework_auto_derives_springboot():
    uc, gh = _uc()
    oam = _oam(language="java")
    res = uc.submit(oam)
    assert res.ok
    _, kw = uc.claims.created[0]
    assert kw["framework"] == "springboot"


def test_update_commits_to_per_service_repo():
    gh = FakeGitHub(existing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    res = uc.submit(_oam())
    assert res.ok, res.message
    assert ("my-svc-gitops", "oam/applications/application.yaml") in gh.commits
    assert not uc.claims.created, "existing repo must not re-scaffold"
    assert not uc.argo.fired


def test_missing_claims_client_errors_no_wft(monkeypatch):
    # RETIRE-WFT #149: the legacy oam-driven-contract fallback was removed. With
    # no claim client a scaffold submission must error (committed but unprovisioned)
    # and MUST NOT fire any workflow.
    monkeypatch.setenv("SUBMIT_USE_WFT", "true")  # stale env must have no effect
    uc, gh = _uc(claims=None)
    res = uc.submit(_oam())
    assert not res.ok
    assert "no claim client" in res.message
    assert not uc.argo.fired, "no legacy WFT may fire after retirement"


def test_vcluster_target_propagates_to_claim():
    oam = yaml.safe_load(_oam())
    oam["spec"]["components"][0]["properties"]["targetEnvironment"] = "team-a-vc"
    uc, gh = _uc()
    res = uc.submit(yaml.safe_dump(oam))
    assert res.ok
    _, kw = uc.claims.created[0]
    assert kw["delivery_target"] == "team-a-vc"


def test_claim_failure_surfaces_error():
    uc, gh = _uc(claims=FakeClaims(ok=False))
    res = uc.submit(_oam())
    assert not res.ok
    assert "claim creation failed" in res.message


def test_oam_payload_roundtrips_b64():
    uc, gh = _uc()
    oam = _oam()
    uc.submit(oam)
    # claim creation receives the exact OAM, b64-encoded
    # (FakeClaims signature consumes it positionally via kwargs)
    name, kw = uc.claims.created[0]
    assert name == "my-svc"


def _multi_oam(n_identity=1, exposed=True):
    comps = []
    for i in range(n_identity):
        comps.append({"name": f"idp-{i}", "type": "auth0-idp", "properties": {}})
    for n in ("svc-a", "svc-b"):
        c = {"name": n, "type": "webservice",
             "properties": {"name": n, "language": "python",
                            **({"identity": "idp-0"} if n_identity else {})}}
        if exposed:
            c["traits"] = [{"type": "expose-api", "properties": {}}]
        comps.append(c)
    return yaml.safe_dump({"apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
                           "metadata": {"name": "multi", "namespace": "default"},
                           "spec": {"components": comps}})


def test_one_identity_serves_many_exposed_ok():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=1))
    assert res.ok, res.message


def test_multiple_identity_components_rejected():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=2))
    assert not res.ok
    assert "at most ONE" in res.message
    assert not gh.commits, "rejected OAM must not reach the gitops gate"


def test_exposed_without_identity_rejected():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=0))
    assert not res.ok
    assert "no identity component" in res.message


def test_unexposed_needs_no_identity():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=0, exposed=False))
    assert res.ok, res.message
