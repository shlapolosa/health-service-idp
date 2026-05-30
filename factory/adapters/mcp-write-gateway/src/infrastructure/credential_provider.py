"""GitHub App private-key resolver — picks the auth strategy by env.

GITHUB_APP_AUTH_MODE selects the implementation:
  - "env_pem"   (dev/local): read the PEM from GITHUB_APP_PEM or GITHUB_APP_PEM_PATH.
  - "key_vault" (prod):       fetch from Azure Key Vault via Workload Identity / DefaultAzureCredential.

Key Vault implementation caches the secret for 24h so we don't hammer KV on every PR. (PEM rotation
is rare; rotation triggers a pod restart anyway via the AKS Workload Identity webhook.)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class CredentialProvider(Protocol):
    def get_pem(self) -> str: ...


class EnvPemProvider:
    """Dev mode — PEM from env var or file path."""

    def get_pem(self) -> str:
        if path := os.getenv("GITHUB_APP_PEM_PATH"):
            return open(path).read()
        pem = os.environ.get("GITHUB_APP_PEM", "")
        if not pem:
            raise RuntimeError("EnvPemProvider: set GITHUB_APP_PEM or GITHUB_APP_PEM_PATH")
        # Allow `\n`-escaped single-line env (k8s Secret pattern).
        return pem.replace("\\n", "\n")


class KeyVaultPemProvider:
    """Prod mode — Azure Key Vault + DefaultAzureCredential (Workload Identity in AKS).

    DefaultAzureCredential automatically picks up the federated identity injected by the AKS
    Workload Identity webhook (env vars AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_FEDERATED_TOKEN_FILE,
    AZURE_AUTHORITY_HOST). Falls back to az CLI / Managed Identity / env vars in that order.
    """

    def __init__(self, vault_url: str, secret_name: str, cache_seconds: int = 86_400):
        self.vault_url = vault_url
        self.secret_name = secret_name
        self.cache_seconds = cache_seconds
        self._pem: str | None = None
        self._fetched_at: float = 0.0

    def get_pem(self) -> str:
        if self._pem and (time.time() - self._fetched_at) < self.cache_seconds:
            return self._pem
        # Imported lazily so tests / EnvPemProvider users don't pay the azure-* import cost.
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        client = SecretClient(vault_url=self.vault_url, credential=DefaultAzureCredential())
        secret = client.get_secret(self.secret_name)
        self._pem = secret.value or ""
        self._fetched_at = time.time()
        logger.info("KeyVaultPemProvider: fetched %s from %s (cached for %ds)",
                    self.secret_name, self.vault_url, self.cache_seconds)
        return self._pem


def build_credential_provider() -> CredentialProvider:
    """Factory — reads env, returns the right provider. Called from dependencies.py."""
    mode = os.environ.get("GITHUB_APP_AUTH_MODE", "env_pem").lower()
    if mode == "env_pem":
        return EnvPemProvider()
    if mode == "key_vault":
        vault_url = os.environ["AZURE_KEY_VAULT_URL"]
        secret_name = os.environ.get("GITHUB_APP_PEM_SECRET_NAME", "github-app-factorybot-pem")
        return KeyVaultPemProvider(vault_url, secret_name)
    raise ValueError(f"unknown GITHUB_APP_AUTH_MODE: {mode}")
