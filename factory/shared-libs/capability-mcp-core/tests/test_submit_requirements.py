"""Unit tests for SPEC-1 (#173, dev-agent W1): the use-case spec (REQUIREMENTS.md)
travels with app.submit into the central ledger + app monorepo root.

Contract (acceptance criteria phrased as tests):
  - submit WITHOUT requirements is byte-for-byte today's behaviour (regression):
    no spec commits, spec_hash is None.
  - submit WITH valid requirements: both the central-ledger sibling
    (oam/applications/<app>-REQUIREMENTS.md) AND the app monorepo root
    (REQUIREMENTS.md in <app>-gitops) are committed, and a deterministic
    spec_hash is returned.
  - malformed requirements (empty / no '## Acceptance Criteria' / empty section)
    => validation error BEFORE any commit (fail-fast, OAM never reaches gitops).
  - resubmit identical content => identical hash + identical committed content
    (idempotent: no spec drift, no re-fire churn).

Mocks the github client the same way test_submit_routing.py does, extended to
record committed CONTENT so idempotency can be asserted.
"""
from __future__ import annotations

import base64

import pytest
import yaml

from src.application import requirements_spec
from src.application.submit_use_case import SubmitUseCase

# Reuse the routing-test fakes (single source of truth for the fake surface).
from tests.test_submit_routing import FakeApimProducts, FakeArgo, FakeClaims, FakeVela, _oam


class RecordingGitHub:
    """Like test_submit_routing.FakeGitHub but content-aware: stores the latest
    blob per (repo, path) so tests can assert idempotent content + which paths
    were written. `missing_repos` lets a day-0 monorepo commit be simulated as
    failing (the composition hasn't created the repo yet)."""

    def __init__(self, existing_repos=(), missing_repos=()):
        self.existing = set(existing_repos)
        self.missing = set(missing_repos)
        self.commits = []                       # (repo, path)
        self.blobs: dict[tuple, str] = {}       # (repo, path) -> content
        self.commit_count: dict[tuple, int] = {}

    def repo_exists(self, repo):
        return repo in self.existing

    def commit_file(self, path, content, message, branch="main", repo=None):
        key = (repo, path)
        if repo in self.missing:
            return False, None                  # repo not created yet (day-0)
        self.commits.append(key)
        self.blobs[key] = content
        self.commit_count[key] = self.commit_count.get(key, 0) + 1
        return True, f"sha-{len(self.commits)}"


def _uc(github=None, claims=..., apim=...):
    gh = github or RecordingGitHub()
    cl = FakeClaims() if claims is ... else claims
    ap = FakeApimProducts() if apim is ... else apim
    return SubmitUseCase(FakeVela(), gh, FakeArgo(), claims=cl, apim_products=ap), gh


_VALID_REQS = """# Use Case

Ingest wearable heart-rate telemetry and surface anomalies.

## Components & Responsibilities

- ingest (webservice): accept device telemetry, publish to sensor_raw.

## Acceptance Criteria

- POST /ingest with {device_id, hr} -> a message appears on topic sensor_raw.
- GET /healthz -> 200.

## Non-Goals

- No historical backfill.
"""


# ---------------------------------------------------------------------------
# Pure helper: requirements_spec
# ---------------------------------------------------------------------------

def test_spec_hash_deterministic_and_normalized():
    a, ha = requirements_spec.prepare(_VALID_REQS)
    # trailing whitespace + CRLF + extra blank lines must not change the hash
    noisy = _VALID_REQS.replace("\n", "\r\n").replace("## Non-Goals",
                                                       "\n\n## Non-Goals  ")
    b, hb = requirements_spec.prepare(noisy)
    assert ha == hb, "normalization must make trivially-different specs hash equal"
    assert ha.startswith("spec-") and len(ha) == len("spec-") + 12


def test_base64_requirements_decoded():
    b64 = base64.b64encode(_VALID_REQS.encode()).decode()
    decoded = requirements_spec.decode_requirements(b64)
    assert "## Acceptance Criteria" in decoded


def test_literal_markdown_passthrough_not_treated_as_b64():
    # markdown with headings/newlines must never be mistaken for base64
    assert requirements_spec.decode_requirements(_VALID_REQS) == _VALID_REQS


@pytest.mark.parametrize("bad", [
    "",
    "   \n  \n",
    "# Use Case\n\njust prose, no criteria section\n",
    "## Acceptance Criteria\n",                       # heading but empty section
    "## Acceptance Criteria\n## Non-Goals\nx\n",       # section empty before next heading
])
def test_validate_rejects_malformed(bad):
    with pytest.raises(requirements_spec.RequirementsError):
        requirements_spec.prepare(bad)


# ---------------------------------------------------------------------------
# submit() integration
# ---------------------------------------------------------------------------

def test_submit_without_requirements_is_unchanged_regression():
    uc, gh = _uc()
    res = uc.submit(_oam())
    assert res.ok, res.message
    assert res.spec_hash is None
    # only the OAM ledger commit + (day-0) no per-service commit; NO *-REQUIREMENTS.md
    assert all(not p.endswith("REQUIREMENTS.md") for _, p in gh.commits)
    # day-0 claim path still creates the claim (unchanged behaviour)
    assert uc.claims.created


def test_submit_with_requirements_commits_ledger_sibling_day0():
    uc, gh = _uc()
    res = uc.submit(_oam(), requirements=_VALID_REQS)
    assert res.ok, res.message
    assert res.spec_hash and res.spec_hash.startswith("spec-")
    # central-ledger sibling next to oam/applications/my-svc.yaml
    assert (None, "oam/applications/my-svc-REQUIREMENTS.md") in gh.commits
    # content is the normalized spec, and hash matches the file content
    content = gh.blobs[(None, "oam/applications/my-svc-REQUIREMENTS.md")]
    assert requirements_spec.spec_hash(content) == res.spec_hash


def test_submit_with_requirements_commits_monorepo_root_update_path():
    # repo exists -> update path -> REQUIREMENTS.md lands at the monorepo root
    gh = RecordingGitHub(existing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    res = uc.submit(_oam(), requirements=_VALID_REQS)
    assert res.ok, res.message
    assert ("my-svc-gitops", "REQUIREMENTS.md") in gh.commits
    assert (None, "oam/applications/my-svc-REQUIREMENTS.md") in gh.commits
    assert res.spec_hash
    assert f"spec {res.spec_hash}" in res.message


def test_day0_monorepo_absent_is_ledger_only_nonfatal():
    # day-0: monorepo doesn't exist yet -> ledger holds the spec, submit still ok
    gh = RecordingGitHub(missing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    res = uc.submit(_oam(), requirements=_VALID_REQS)
    assert res.ok, res.message
    assert (None, "oam/applications/my-svc-REQUIREMENTS.md") in gh.commits
    assert ("my-svc-gitops", "REQUIREMENTS.md") not in gh.commits
    assert "ledger only" in res.message
    assert res.spec_hash  # hash still returned (W3 keys on it)


def test_malformed_requirements_rejected_before_any_commit():
    uc, gh = _uc()
    res = uc.submit(_oam(), requirements="# Use Case\n\nno criteria here\n")
    assert not res.ok
    assert "invalid requirements" in res.message
    assert not gh.commits, "malformed spec must fail-fast: OAM never reaches gitops"
    assert not uc.claims.created


def test_resubmit_identical_content_is_idempotent():
    gh = RecordingGitHub(existing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    r1 = uc.submit(_oam(), requirements=_VALID_REQS)
    r2 = uc.submit(_oam(), requirements=_VALID_REQS)
    assert r1.spec_hash == r2.spec_hash, "same content => same hash (no drift)"
    mono = ("my-svc-gitops", "REQUIREMENTS.md")
    led = (None, "oam/applications/my-svc-REQUIREMENTS.md")
    # committed content is identical across resubmits (idempotent; the real
    # github client no-ops an unchanged blob via its existing-sha PUT)
    assert gh.blobs[mono] == _normalized()
    assert gh.blobs[led] == _normalized()


def test_resubmit_changed_content_changes_hash():
    gh = RecordingGitHub(existing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    r1 = uc.submit(_oam(), requirements=_VALID_REQS)
    changed = _VALID_REQS + "\n- additionally: GET /metrics -> 200.\n"
    r2 = uc.submit(_oam(), requirements=changed)
    assert r1.spec_hash != r2.spec_hash, "spec edit must change the hash (W3 re-fire)"


def test_submit_wait_carries_requirements():
    uc, gh = _uc()
    res = uc.submit_wait(_oam(), requirements=_VALID_REQS)
    assert res.ok, res.message
    assert res.spec_hash
    assert (None, "oam/applications/my-svc-REQUIREMENTS.md") in gh.commits


def _normalized() -> str:
    return requirements_spec.normalize(_VALID_REQS)


# --- RT-2 (#176): realtime role travels through services[] -------------------

def _mk_app(components):
    return {"spec": {"components": components}}


def test_realtime_role_default_gateway():
    from src.application.submit_use_case import SubmitUseCase
    app = _mk_app([{"name": "gw", "type": "realtime-service",
                    "properties": {"language": "python"}}])
    services = SubmitUseCase._webservice_services(app)
    assert services[0]["flavor"] == "realtime"
    assert services[0]["role"] == "gateway"


def test_realtime_role_explicit_processor():
    from src.application.submit_use_case import SubmitUseCase
    app = _mk_app([{"name": "proc", "type": "realtime-service",
                    "properties": {"language": "python", "role": "processor"}}])
    services = SubmitUseCase._webservice_services(app)
    assert services[0]["role"] == "processor"


def test_realtime_role_invalid_falls_back_to_gateway():
    from src.application.submit_use_case import SubmitUseCase
    app = _mk_app([{"name": "x", "type": "realtime-service",
                    "properties": {"language": "python", "role": "bogus"}}])
    services = SubmitUseCase._webservice_services(app)
    assert services[0]["role"] == "gateway"


def test_webservice_has_no_role():
    from src.application.submit_use_case import SubmitUseCase
    app = _mk_app([{"name": "web", "type": "webservice",
                    "properties": {"language": "python"}}])
    services = SubmitUseCase._webservice_services(app)
    assert "role" not in services[0]
