"""Dependency injection — @lru_cache factories reading env vars (mirrors slack-api-server pattern)."""
from __future__ import annotations

import os
from functools import lru_cache

from ..application.catalog_use_cases import CatalogUseCases
from ..application.scoring import CapabilityScorer
from ..application.submit_use_case import SubmitUseCase
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.k8s_catalog_client import K8sCatalogClient
from ..infrastructure.vela_client import VelaClient


@lru_cache
def get_argo() -> ArgoWorkflowsClient:
    return ArgoWorkflowsClient(
        server_url=os.getenv("ARGO_SERVER_URL", "http://argo-server.argo:2746"),
        namespace=os.getenv("ARGO_NAMESPACE", "argo"),
        token_file=os.getenv("ARGO_TOKEN_FILE", "/var/run/secrets/argo/token"),
    )


@lru_cache
def get_github() -> GitHubClient:
    return GitHubClient(
        token=os.getenv("PERSONAL_ACCESS_TOKEN", ""),
        owner=os.getenv("GITHUB_OWNER", "shlapolosa"),
        gitops_repo=os.getenv("GITOPS_REPO", "health-service-idp-gitops"),
    )


@lru_cache
def get_k8s_catalog() -> K8sCatalogClient:
    return K8sCatalogClient(namespace=os.getenv("OAM_NAMESPACE", "default"))


@lru_cache
def get_vela() -> VelaClient:
    return VelaClient(vela_bin=os.getenv("VELA_BIN", "vela"))


@lru_cache
def get_scorer() -> CapabilityScorer:
    return CapabilityScorer(os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory"))


@lru_cache
def get_catalog() -> CatalogUseCases:
    return CatalogUseCases(get_k8s_catalog(), get_vela(), get_scorer())


@lru_cache
def get_submit() -> SubmitUseCase:
    return SubmitUseCase(get_vela(), get_github(), get_argo(),
                         gitops_branch=os.getenv("GITOPS_BRANCH", "main"))
