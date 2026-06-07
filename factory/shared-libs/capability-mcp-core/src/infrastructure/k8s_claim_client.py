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
        database: str = "none",
        cache: str = "none",
        services: list[dict[str, str]] | None = None,
    ) -> tuple[bool, str]:
        """Create (or converge onto) the AppContainerClaim `name`. Returns (ok, message).

        Idempotent: a 409 means the claim already exists (trait-rendered or an earlier
        submit) — that is success, the composition is already reconciling. We do NOT
        patch oamApplication on conflict: the seed is write-once; updates flow as
        direct commits to the per-service gitops repo.

        UNIFY-1 (#153): `services` (one entry {name, language, framework} per
        webservice component of the OAM) is set on spec.services[]. The composition
        ranges over it to emit one ApplicationClaim per service, all sharing this
        claim's repo (monorepo-per-OAM). Omitted/empty → the composition falls back
        to the single-service path (appContainer == name) for full backward compat.
        """
        spec: dict[str, Any] = {
            "name": name,
            "description": description,
            "gitHubOrg": github_org,
            "dockerRegistry": docker_registry,
            "language": language,
            "framework": framework,
            "database": database,
            "cache": cache,
            "deliveryTarget": delivery_target,
            "oamApplication": oam_application_b64,
        }
        if services:
            spec["services"] = services
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
            "spec": spec,
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

    def reconcile_services(self, name: str, services: list[dict[str, str]]) -> list[str]:
        """UNIFY-1 (#153) update-path reconcile. Patch the existing AppContainerClaim
        `name` to ADD any service entries not already in spec.services[]. Returns the
        list of newly added service names (empty if nothing to do / claim absent).

        Closes the update-path scaffold gap: adding a webservice component to an
        existing OAM scaffolds its microservices/<name>/ folder with no trait — the
        composition emits an extra ApplicationClaim for the added service. Existing
        entries are never mutated (write-once scaffold), so this is purely additive
        and safe to re-run.
        """
        if not services:
            return []
        try:
            obj = self._custom_api().get_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, name=name,
            )
        except Exception as e:  # noqa: BLE001
            # Legacy single-service claims (pre-UNIFY-1) or no claim at all: no-op.
            logger.info("reconcile_services: claim %s not found (%s) — skipping", name, e)
            return []

        existing = (obj.get("spec") or {}).get("services") or []
        existing_names = {s.get("name") for s in existing}
        to_add = [s for s in services if s.get("name") not in existing_names]
        if not to_add:
            return []

        merged = existing + to_add
        patch = {"spec": {"services": merged}}
        try:
            self._custom_api().patch_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, name=name, body=patch,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("reconcile_services: patch of %s failed: %s", name, e)
            return []
        added = [s.get("name") for s in to_add]
        logger.info("✅ AppContainerClaim %s services reconciled (+%s)", name, ", ".join(added))
        return added

    def get_claim_status(self, name: str) -> Optional[dict[str, Any]]:
        """Return the claim's .status (or None). Used by app.status (W5)."""
        try:
            obj = self._custom_api().get_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, name=name,
            )
            return obj.get("status")
        except Exception:  # noqa: BLE001
            return None

    def get_argocd_app_status(self, name: str, argocd_namespace: str = "argocd") -> Optional[dict[str, Any]]:
        """Return {sync, health, revision} for the ArgoCD Application `name` (or None).

        W5: ArgoCD aggregates health from the destination cluster (host OR vcluster),
        so this is the one status surface that works across tenancy targets.
        """
        try:
            obj = self._custom_api().get_namespaced_custom_object(
                group="argoproj.io", version="v1alpha1", namespace=argocd_namespace,
                plural="applications", name=name,
            )
            st = obj.get("status") or {}
            return {
                "sync": (st.get("sync") or {}).get("status"),
                "health": (st.get("health") or {}).get("status"),
                "revision": (st.get("sync") or {}).get("revision"),
                "operation_phase": ((st.get("operationState") or {}).get("phase")),
            }
        except Exception:  # noqa: BLE001
            return None
