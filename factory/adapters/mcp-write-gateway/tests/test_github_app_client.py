"""GitHubAppClient — JWT mint + installation-token exchange + caching.

We use a fake CredentialProvider returning a freshly-generated test RSA key, so the JWT mint path
is exercised end-to-end. The HTTP layer is mocked.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.infrastructure.github_app_client import GitHubAppClient


class _StubCred:
    def __init__(self, pem: str):
        self.pem = pem

    def get_pem(self) -> str:
        return self.pem


@pytest.fixture
def test_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode()


def _fake_response(status: int, payload: dict):
    r = type("R", (), {})()
    r.status_code = status
    r.text = str(payload)
    r.json = lambda: payload
    def _raise():
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
    r.raise_for_status = _raise
    return r


def test_installation_token_mint_and_cache(test_pem):
    client = GitHubAppClient("123", "456", _StubCred(test_pem))
    fake_201 = _fake_response(201, {"token": "ghs_install_aaa",
                                    "expires_at": "2099-01-01T00:00:00Z"})
    with patch("requests.post", return_value=fake_201) as mock_post:
        t1 = client.installation_token()
        t2 = client.installation_token()
    assert t1 == "ghs_install_aaa"
    assert t2 == t1
    # Cache hit: second call must NOT have re-hit the network.
    assert mock_post.call_count == 1


def test_installation_token_failure_raises(test_pem):
    client = GitHubAppClient("123", "456", _StubCred(test_pem))
    fake_403 = _fake_response(403, {"message": "Bad credentials"})
    with patch("requests.post", return_value=fake_403):
        with pytest.raises(RuntimeError):
            client.installation_token()


def test_create_branch_idempotent_on_already_exists(test_pem):
    client = GitHubAppClient("123", "456", _StubCred(test_pem))
    client._token = "tok"
    client._token_exp = 9_999_999_999
    fake_422 = _fake_response(422, {"message": "Reference already exists"})
    fake_422.text = "Reference already exists"
    with patch("requests.post", return_value=fake_422):
        # Must not raise — idempotency is the point.
        client.create_branch("o", "r", "factory/abc", "sha-1")


def test_constructor_rejects_blank_ids(test_pem):
    with pytest.raises(ValueError):
        GitHubAppClient("", "456", _StubCred(test_pem))
    with pytest.raises(ValueError):
        GitHubAppClient("123", "", _StubCred(test_pem))
