"""Dependency injection — @lru_cache factories reading env vars (mirrors slack-api-server pattern)."""
from __future__ import annotations

import os
from functools import lru_cache

from ..application.catalog_use_cases import CatalogUseCases
from ..application.examples_use_cases import ExamplesUseCases
from ..application.kb_use_cases import KBUseCases
from ..application.route_use_case import RouteUseCase
from ..application.scoring import CapabilityScorer
from ..application.submit_use_case import SubmitUseCase
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.classify_router_client import ClassifyRouterClient
from ..infrastructure.crossplane_dryrun_client import CrossplaneDryRunClient
from ..infrastructure.examples_loader import ExamplesLoader
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.k8s_catalog_client import K8sCatalogClient
from ..infrastructure.kb_loader import KBLoader
from ..infrastructure.recipes_loader import RecipesLoader
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


# ---- P8.1 additions: KB loader, examples loader, crossplane dry-run ----

@lru_cache
def get_kb_loader() -> KBLoader:
    return KBLoader(os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory"))


@lru_cache
def get_examples_loader() -> ExamplesLoader:
    # REPO_ROOT mounts the source tree containing crossplane/oam/* exemplars.
    # In the container image we COPY the relevant paths to /repo (see Dockerfile).
    return ExamplesLoader(os.getenv("REPO_ROOT", "/repo"))


@lru_cache
def get_crossplane_dryrun() -> CrossplaneDryRunClient:
    return CrossplaneDryRunClient(kubectl_bin=os.getenv("KUBECTL_BIN", "kubectl"))


@lru_cache
def get_recipes_loader() -> RecipesLoader:
    return RecipesLoader(os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory"))


@lru_cache
def get_kb() -> KBUseCases:
    return KBUseCases(get_kb_loader(), get_k8s_catalog())


@lru_cache
def get_examples() -> ExamplesUseCases:
    return ExamplesUseCases(get_examples_loader())


@lru_cache
def get_catalog() -> CatalogUseCases:
    return CatalogUseCases(get_k8s_catalog(), get_vela(), get_scorer(),
                           crossplane_dryrun=get_crossplane_dryrun(),
                           recipes=get_recipes_loader())


@lru_cache
def get_claims() -> "K8sClaimClient":
    from ..infrastructure.k8s_claim_client import K8sClaimClient
    return K8sClaimClient(namespace=os.getenv("CLAIM_NAMESPACE", "default"))


@lru_cache
def get_status():
    from ..application.status_use_case import StatusUseCase
    return StatusUseCase(get_claims())


@lru_cache
def get_submit() -> SubmitUseCase:
    return SubmitUseCase(get_vela(), get_github(), get_argo(),
                         gitops_branch=os.getenv("GITOPS_BRANCH", "main"),
                         claims=get_claims())


# ---- S4 additions: factory.route (classify-router proxy) ----

@lru_cache
def get_classify_router() -> ClassifyRouterClient:
    return ClassifyRouterClient(
        base_url=os.getenv(
            "CLASSIFY_ROUTER_URL",
            "http://classify-router.default.svc.cluster.local",
        ),
        timeout_seconds=float(os.getenv("CLASSIFY_ROUTER_TIMEOUT_SECONDS", "5")),
    )


@lru_cache
def get_route() -> RouteUseCase:
    return RouteUseCase(get_classify_router())
