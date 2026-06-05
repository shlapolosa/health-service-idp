"""Kubernetes client for AppContainerClaim creation — the day-0 bootstrap surface.

Declarative-spine W4: when app.submit receives an OAM whose webservice needs
scaffolding and the per-service gitops repo does not exist yet, it creates an
AppContainerClaim directly (in-cluster SA, no Argo REST call, no token). The
claim's composition creates source + gitops repos, seeds the consumer OAM, and
(when deliveryTarget is set) an ArgoCD Application pointing at the per-service
repo. The auto-scaffold-bootstrap trait renders the SAME claim (deterministic
name = component name) once the OAM reconciles on the host, so both writers
converge via server-side apply.

Follows the load_incluster_config()/load_kube_config() fallback pattern from
k8s_catalog_client.py.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_GROUP = "platform.example.org"
_VERSION = "v1alpha1"
_PLURAL = "appcontainerclaims"


class K8sClaimClient:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self._api = None

    def _custom_api(self):
        if self._api is None:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:  # noqa: BLE001
                config.load_kube_config()
            self._api = client.CustomObjectsApi()
        return self._api

    def create_app_container_claim(
        self,
        name: str,
        oam_application_b64: str,
        language: str = "python",
        framework: str = "fastapi",
        delivery_target: str = "host",
        github_org: str = "shlapolosa",
        docker_registry: str = "healthidpuaeacr.azurecr.io",
        description: str = "created by app.submit (declarative spine)",
    ) -> tuple[bool, str]:
        """Create (or converge onto) the AppContainerClaim `name`. Returns (ok, message).

        Idempotent: a 409 means the claim already exists (trait-rendered or an earlier
        submit) — that is success, the composition is already reconciling. We do NOT
        patch oamApplication on conflict: the seed is write-once; updates flow as
        direct commits to the per-service gitops repo.
        """
        body: dict[str, Any] = {
            "apiVersion": f"{_GROUP}/{_VERSION}",
            "kind": "AppContainerClaim",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": name,
                    "app.kubernetes.io/managed-by": "capability-mcp",
                },
            },
            "spec": {
                "name": name,
                "description": description,
                "gitHubOrg": github_org,
                "dockerRegistry": docker_registry,
                "language": language,
                "framework": framework,
                "deliveryTarget": delivery_target,
                "oamApplication": oam_application_b64,
            },
        }
        try:
            self._custom_api().create_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, body=body,
            )
            logger.info("✅ AppContainerClaim %s/%s created", self.namespace, name)
            return True, f"AppContainerClaim {name} created"
        except Exception as e:  # noqa: BLE001
            status = getattr(e, "status", None)
            if status == 409:
                logger.info("AppContainerClaim %s already exists — converging (no-op)", name)
                return True, f"AppContainerClaim {name} already exists (converging)"
            logger.error("AppContainerClaim create failed: %s", e)
            return False, f"AppContainerClaim create failed: {e}"

    def get_claim_status(self, name: str) -> Optional[dict[str, Any]]:
        """Return the claim's .status (or None). Used by lifecycle.state (W5)."""
        try:
            obj = self._custom_api().get_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, name=name,
            )
            return obj.get("status")
        except Exception:  # noqa: BLE001
            return None
