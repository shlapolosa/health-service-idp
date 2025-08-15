"""Pytest configuration for slack-api-server tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    # Use mock Argo client for tests
    monkeypatch.setenv("ARGO_USE_MOCK", "true")
    
    # Set other test environment variables
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("PERSONAL_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "test-org/test-repo")
    monkeypatch.setenv("ARGO_SERVER_URL", "https://test-argo-server:2746")
    monkeypatch.setenv("ARGO_NAMESPACE", "argo")
    monkeypatch.setenv("ARGO_TOKEN_FILE", "/tmp/test-argo-token")


@pytest.fixture
def enable_real_argo(monkeypatch):
    """Fixture to enable real Argo API calls for integration tests."""
    monkeypatch.setenv("ARGO_USE_MOCK", "false")
    yield
    monkeypatch.setenv("ARGO_USE_MOCK", "true")