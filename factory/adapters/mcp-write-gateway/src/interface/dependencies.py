"""DI factories — @lru_cache singletons backed by env vars."""
from __future__ import annotations

import os
from functools import lru_cache

from ..application.factory_use_cases import FactoryUseCases
from ..infrastructure.credential_provider import build_credential_provider
from ..infrastructure.github_app_client import GitHubAppClient


def _allowed_repos() -> set[str]:
    # Comma-separated short-name allow-list, e.g. "health-service-idp,health-service-idp-gitops"
    raw = os.environ.get("FACTORY_ALLOWED_REPOS", "health-service-idp,health-service-idp-gitops")
    return {r.strip() for r in raw.split(",") if r.strip()}


@lru_cache
def get_github_app() -> GitHubAppClient:
    return GitHubAppClient(
        app_id=os.environ.get("GITHUB_APP_ID", ""),
        installation_id=os.environ.get("GITHUB_APP_INSTALLATION_ID", ""),
        cred=build_credential_provider(),
    )


@lru_cache
def get_factory() -> FactoryUseCases:
    return FactoryUseCases(
        gh=get_github_app(),
        owner=os.environ.get("GITHUB_OWNER", "shlapolosa"),
        allowed_repos=_allowed_repos(),
    )
