"""
Interface Layer - Dependency Injection
Provides dependency injection for FastAPI controllers
"""

import os
from functools import lru_cache
from typing import Optional

from ..application.use_cases import (CreateVClusterUseCase,
                                     ProcessSlackCommandUseCase,
                                     VerifySlackRequestUseCase)
from ..domain.services import (SlackResponseBuilderService,
                               VClusterFactoryService,
                               VClusterValidationService)
from ..application.use_cases import VClusterDispatcherInterface
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.github_client import GitHubApiClient
from ..infrastructure.nlp_parser import EnhancedNLPParser
from ..infrastructure.slack_verifier import SlackSignatureVerifier


@lru_cache()
def get_github_client() -> GitHubApiClient:
    """Get GitHub API client singleton."""
    token = os.getenv("PERSONAL_ACCESS_TOKEN")
    repository = os.getenv("GITHUB_REPOSITORY", "shlapolosa/health-service-idp")

    if not token:
        raise ValueError("PERSONAL_ACCESS_TOKEN environment variable is required")

    return GitHubApiClient(token=token, repository=repository)


@lru_cache()
def get_argo_client() -> ArgoWorkflowsClient:
    """Get Argo Workflows client singleton."""
    # Argo server is accessible within the cluster
    argo_server_url = os.getenv("ARGO_SERVER_URL", "http://argo-server.argo:2746")
    argo_namespace = os.getenv("ARGO_NAMESPACE", "argo")
    
    return ArgoWorkflowsClient(server_url=argo_server_url, namespace=argo_namespace)


@lru_cache()
def get_vcluster_dispatcher() -> VClusterDispatcherInterface:
    """Get VCluster dispatcher based on configuration."""
    # Use environment variable to select dispatcher type
    dispatcher_type = os.getenv("VCLUSTER_DISPATCHER", "argo").lower()
    
    if dispatcher_type == "github":
        return get_github_client()
    elif dispatcher_type == "argo":
        return get_argo_client()
    else:
        # Default to Argo if invalid value
        return get_argo_client()


@lru_cache()
def get_nlp_parser() -> EnhancedNLPParser:
    """Get NLP parser singleton."""
    return EnhancedNLPParser()


@lru_cache()
def get_slack_verifier() -> Optional[SlackSignatureVerifier]:
    """Get Slack signature verifier singleton."""
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")

    if not signing_secret:
        return None

    return SlackSignatureVerifier(signing_secret)


@lru_cache()
def get_vcluster_factory_service() -> VClusterFactoryService:
    """Get VCluster factory service singleton."""
    return VClusterFactoryService()


@lru_cache()
def get_vcluster_validation_service() -> VClusterValidationService:
    """Get VCluster validation service singleton."""
    return VClusterValidationService()


@lru_cache()
def get_slack_response_builder_service() -> SlackResponseBuilderService:
    """Get Slack response builder service singleton."""
    return SlackResponseBuilderService()


def get_create_vcluster_use_case() -> CreateVClusterUseCase:
    """Get create VCluster use case with dependencies."""
    return CreateVClusterUseCase(
        parser=get_nlp_parser(),
        vcluster_dispatcher=get_vcluster_dispatcher(),
        factory=get_vcluster_factory_service(),
        validator=get_vcluster_validation_service(),
        response_builder=get_slack_response_builder_service(),
    )


def get_process_slack_command_use_case() -> ProcessSlackCommandUseCase:
    """Get process Slack command use case with dependencies."""
    return ProcessSlackCommandUseCase(
        create_vcluster_use_case=get_create_vcluster_use_case(),
        response_builder=get_slack_response_builder_service(),
    )


def get_verify_slack_request_use_case() -> Optional[VerifySlackRequestUseCase]:
    """Get verify Slack request use case with dependencies."""
    verifier = get_slack_verifier()

    if not verifier:
        return None

    return VerifySlackRequestUseCase(verifier)
