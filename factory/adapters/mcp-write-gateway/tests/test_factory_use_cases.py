"""FactoryUseCases — propose flow + allow-list + audit + failure injection."""
from __future__ import annotations

import logging

import pytest

from src.application.factory_use_cases import FactoryUseCases, _slug
from src.domain.models import ProposeRequest

_OWNER = "shlapolosa"
_REPOS = {"health-service-idp", "health-service-idp-gitops"}


def _req(**kw) -> ProposeRequest:
    base = dict(
        repo="health-service-idp", title="feat: introduce nats-jetstream",
        body="body", files={"docs/adr/x.md": "content"},
        base="main", branch_prefix="factory",
    )
    base.update(kw)
    return ProposeRequest(**base)


def test_slug_helper_strips_and_truncates():
    assert _slug("feat: introduce NATS-jetstream!") == "feat-introduce-nats-jetstream"
    assert _slug("a" * 200, maxlen=10) == "a" * 10
    assert _slug("") == "proposal"


def test_propose_happy_path(fake_gh):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req(), caller_oid="agent-1234")
    assert r.ok is True
    assert r.pr_url.startswith("https://github.com/shlapolosa/health-service-idp/pull/")
    assert r.pr_number == 1
    assert r.branch.startswith("factory/feat-introduce-nats-jetstream-")
    assert len(r.commits) == 1
    assert fake_gh.branches[0][0] == "health-service-idp"
    assert fake_gh.commits[0]["path"] == "docs/adr/x.md"
    assert fake_gh.prs[0]["base"] == "main"


def test_propose_audit_log_contains_caller_oid(fake_gh, caplog):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    with caplog.at_level(logging.INFO, logger="src.application.factory_use_cases"):
        uc.propose(_req(), caller_oid="oid-abc-123")
    msgs = [r.message for r in caplog.records if r.levelno >= logging.INFO]
    audit = [m for m in msgs if "AUDIT factory.propose" in m]
    assert audit, f"no audit log line, got: {msgs}"
    assert "oid-abc-123" in audit[0]
    assert "health-service-idp" in audit[0]


def test_propose_rejects_repo_outside_allow_list(fake_gh):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req(repo="some-random-repo"))
    assert r.ok is False
    assert "allow-list" in r.message
    # Verify NOTHING was attempted against GitHub.
    assert fake_gh.branches == []
    assert fake_gh.commits == []
    assert fake_gh.prs == []


def test_propose_rejects_empty_files(fake_gh):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req(files={}))
    assert r.ok is False
    assert "empty" in r.message.lower()


def test_propose_rejects_empty_title(fake_gh):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req(title=""))
    assert r.ok is False
    assert "title" in r.message.lower()


def test_propose_branch_create_failure(fake_gh):
    fake_gh.fail_on = "create_branch"
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req())
    assert r.ok is False
    assert "branch setup" in r.message
    assert fake_gh.commits == []  # no commits attempted after branch failure


def test_propose_commit_failure_preserves_branch_in_result(fake_gh):
    fake_gh.fail_on = "commit_file"
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req())
    assert r.ok is False
    assert r.branch is not None  # branch was created even though commit failed
    assert "commit failed" in r.message


def test_propose_pr_failure_after_commits(fake_gh):
    fake_gh.fail_on = "open_pr"
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    r = uc.propose(_req(files={"a.md": "1", "b.md": "2"}))
    assert r.ok is False
    assert len(r.commits) == 2  # commits succeeded; only PR open failed
    assert "open_pr failed" in r.message


def test_list_open_prs_filters_by_head_prefix(fake_gh):
    fake_gh.prs.extend([
        {"number": 10, "head": "factory/abc-1", "base": "main", "title": "T1", "body": ""},
        {"number": 11, "head": "feature/xyz", "base": "main", "title": "T2", "body": ""},
    ])
    fake_gh.next_pr = 12
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    out = uc.list_open_prs("health-service-idp", head_prefix="factory/")
    assert {p["number"] for p in out} == {10}


def test_list_open_prs_rejects_unknown_repo(fake_gh):
    uc = FactoryUseCases(fake_gh, _OWNER, _REPOS)
    with pytest.raises(ValueError):
        uc.list_open_prs("some-random-repo")
