"""factory.from_requirement (PROPOSE / approval gate) — the front-door must drive
the architect to open a REVIEW PR and return it, and must NEVER deploy.

These tests use a fake architect client (no network) and assert:
  - happy path: a reply containing a PR URL -> ok with pr_url/pr_number
  - the use case has NO submit dependency (it cannot deploy)
  - empty text / token failure / transport failure -> precise, non-masking errors
  - a reply with NO PR URL -> ok=False with a diagnostic (architect didn't propose)
"""
from __future__ import annotations

import pytest

from src.application.from_requirement_use_case import (
    FromRequirementUseCase, ProposeResult, FromRequirementError,
)


class _FakeArchitect:
    """Stand-in for ArchitectClient. Records calls; returns a canned reply or raises."""
    def __init__(self, reply=None, raises=None):
        self._reply = reply
        self._raises = raises
        self.calls = []

    def propose_architecture(self, text, token):
        self.calls.append((text, token))
        if self._raises:
            raise self._raises
        return self._reply


_PR = "https://github.com/shlapolosa/health-service-idp-gitops/pull/42"
_HAPPY = (
    "I derived the architecture and validated it with oam.dry_run (clean) and my "
    "traceability gate is COVERED.\n"
    f"PR: {_PR}\n"
    "Coverage: 3/3 requirements traced to components; 0 orphans."
)


def test_proposes_review_pr_and_does_not_deploy():
    arch = _FakeArchitect(reply=_HAPPY)
    uc = FromRequirementUseCase(arch, token_provider=lambda: "tok")
    res = uc.from_requirement("I need a notes API with a Postgres store")
    assert isinstance(res, ProposeResult)
    assert res.ok is True
    assert res.pr_url == _PR
    assert res.pr_number == 42
    assert "merge" in res.message.lower()
    # the architect was driven exactly once with the token
    assert arch.calls and arch.calls[0][1] == "tok"


def test_no_submit_dependency():
    # The use case must be constructible with ONLY an architect + token provider —
    # i.e. it has no SubmitUseCase and therefore cannot deploy.
    uc = FromRequirementUseCase(_FakeArchitect(reply=_HAPPY), token_provider=lambda: "t")
    assert not hasattr(uc, "submit")
    import src.application.from_requirement_use_case as mod
    assert "SubmitUseCase" not in mod.__dict__  # not imported into the module


def test_empty_text_rejected():
    uc = FromRequirementUseCase(_FakeArchitect(reply=_HAPPY), token_provider=lambda: "t")
    res = uc.from_requirement("   ")
    assert res.ok is False and "non-empty" in res.message


def test_token_failure_surfaced():
    def boom():
        raise RuntimeError("no credential")
    uc = FromRequirementUseCase(_FakeArchitect(reply=_HAPPY), token_provider=boom)
    res = uc.from_requirement("x")
    assert res.ok is False and "token" in res.message.lower()


def test_architect_transport_failure_surfaced():
    arch = _FakeArchitect(raises=RuntimeError("502 from foundry"))
    uc = FromRequirementUseCase(arch, token_provider=lambda: "t")
    res = uc.from_requirement("x")
    assert res.ok is False and "architect call failed" in res.message


def test_reply_without_pr_url_is_not_ok():
    arch = _FakeArchitect(reply="I could not open a PR; the repo was not allow-listed.")
    uc = FromRequirementUseCase(arch, token_provider=lambda: "t")
    res = uc.from_requirement("x")
    assert res.ok is False
    assert "did not open a review PR" in res.message
    # non-masking: surfaces the raw reply for debugging
    assert "allow-listed" in res.message


def test_extract_pr_helper():
    url, n = FromRequirementUseCase.extract_pr(f"see {_PR} please")
    assert url == _PR and n == 42
    with pytest.raises(FromRequirementError):
        FromRequirementUseCase.extract_pr("no link here")
