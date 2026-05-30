"""CredentialProvider — env-pem mode + mode selection. Key Vault is import-only here (no live call)."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.infrastructure.credential_provider import (
    EnvPemProvider, KeyVaultPemProvider, build_credential_provider,
)

_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\nMIIBOQIBAAJBAKj\n-----END RSA PRIVATE KEY-----\n"
)


def test_env_pem_inline(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_PEM", _PEM)
    monkeypatch.delenv("GITHUB_APP_PEM_PATH", raising=False)
    assert EnvPemProvider().get_pem() == _PEM


def test_env_pem_inline_newline_escape(monkeypatch):
    """k8s Secret-mounted single-line env: literal `\\n` should be expanded."""
    monkeypatch.delenv("GITHUB_APP_PEM_PATH", raising=False)
    monkeypatch.setenv("GITHUB_APP_PEM", _PEM.replace("\n", "\\n"))
    out = EnvPemProvider().get_pem()
    assert "\n" in out
    assert "BEGIN RSA PRIVATE KEY" in out


def test_env_pem_path(tmp_path, monkeypatch):
    p = tmp_path / "factory.pem"
    p.write_text(_PEM)
    monkeypatch.setenv("GITHUB_APP_PEM_PATH", str(p))
    monkeypatch.delenv("GITHUB_APP_PEM", raising=False)
    assert EnvPemProvider().get_pem() == _PEM


def test_env_pem_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_APP_PEM", raising=False)
    monkeypatch.delenv("GITHUB_APP_PEM_PATH", raising=False)
    with pytest.raises(RuntimeError):
        EnvPemProvider().get_pem()


def test_build_credential_provider_selects_env_pem(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_AUTH_MODE", "env_pem")
    monkeypatch.setenv("GITHUB_APP_PEM", _PEM)
    p = build_credential_provider()
    assert isinstance(p, EnvPemProvider)


def test_build_credential_provider_selects_key_vault(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_AUTH_MODE", "key_vault")
    monkeypatch.setenv("AZURE_KEY_VAULT_URL", "https://kv-w4x7ibwk4e2is.vault.azure.net/")
    p = build_credential_provider()
    assert isinstance(p, KeyVaultPemProvider)
    assert p.vault_url == "https://kv-w4x7ibwk4e2is.vault.azure.net/"


def test_build_credential_provider_unknown_mode(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_AUTH_MODE", "telepathy")
    with pytest.raises(ValueError):
        build_credential_provider()
