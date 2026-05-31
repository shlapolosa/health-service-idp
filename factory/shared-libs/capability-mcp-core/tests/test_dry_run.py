"""Dry-run client tests.

- vela.dry_run is exercised against the real binary if available, skipped otherwise (avoids tying
  CI to vela installation).
- crossplane.dry_run is tested with a mocked subprocess so the verb behaviour (ok flag + diagnostics
  string) is locked without needing a live cluster.
"""
from __future__ import annotations

import shutil
import subprocess
from unittest.mock import patch

import pytest

from src.infrastructure.crossplane_dryrun_client import CrossplaneDryRunClient
from src.infrastructure.vela_client import VelaClient


def test_crossplane_dryrun_ok():
    """`kubectl apply --dry-run=server` returns 0 → ok=True, diagnostics carries stdout."""
    client = CrossplaneDryRunClient()
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="applied (dry-run)", stderr="")
    with patch("subprocess.run", return_value=fake):
        ok, diag = client.dry_run("kind: Composition\napiVersion: apiextensions.crossplane.io/v1\n")
    assert ok is True
    assert "applied" in diag


def test_crossplane_dryrun_fail():
    """Non-zero exit → ok=False, diagnostics carries stderr."""
    client = CrossplaneDryRunClient()
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                       stderr="error: no matches for kind")
    with patch("subprocess.run", return_value=fake):
        ok, diag = client.dry_run("bogus\n")
    assert ok is False
    assert "no matches" in diag


def test_crossplane_dryrun_kubectl_missing():
    """FileNotFoundError from subprocess (no kubectl on PATH) → ok=False with descriptive msg."""
    client = CrossplaneDryRunClient(kubectl_bin="does-not-exist-xyz")
    ok, diag = client.dry_run("kind: X\n")
    assert ok is False
    assert "unavailable" in diag


@pytest.mark.skipif(shutil.which("vela") is None, reason="vela not installed")
def test_vela_dryrun_invalid_oam():
    """Real vela call — an obviously invalid YAML should fail dry-run."""
    ok, diag = VelaClient().dry_run("not: a: valid: oam\n")
    assert ok is False
    assert diag  # something diagnostic, content varies by vela version
