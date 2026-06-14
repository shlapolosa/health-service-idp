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
        self._core = None

    def _load_config(self):
        from kubernetes import config
        try:
            config.load_incluster_config()
        except Exception:  # noqa: BLE001
            config.load_kube_config()

    def _custom_api(self):
        if self._api is None:
            from kubernetes import client
            self._load_config()
            self._api = client.CustomObjectsApi()
        return self._api

    def _core_api(self):
        if self._core is None:
            from kubernetes import client
            self._load_config()
            self._core = client.CoreV1Api()
        return self._core

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

    def update_oam_application(self, name: str, oam_application_b64: str) -> bool:
        """Stale-snapshot guard (2026-06-12). Refresh spec.oamApplication on the
        existing AppContainerClaim `name` so the claim's snapshot tracks the OAM
        that app.submit just committed to the per-service gitops repo.

        Why: the gitops-setup Job seeds oam/applications/application.yaml from
        this snapshot. It was day-0 write-once, so any Job re-run (composition
        change / Crossplane Object retry) re-seeded a STALE OAM over update-path
        commits (lost rtdemo2 env nudges + publishVersion, 2026-06-12). Keeping
        the snapshot in lockstep makes a re-seed a no-op; the Job-side guard
        additionally preserves diverged files.

        Best-effort sibling of reconcile_services: absent claim / RBAC error →
        False, never raises to the caller's happy path.
        """
        if not oam_application_b64:
            return False
        patch = {"spec": {"oamApplication": oam_application_b64}}
        try:
            self._custom_api().patch_namespaced_custom_object(
                group=_GROUP, version=_VERSION, namespace=self.namespace,
                plural=_PLURAL, name=name, body=patch,
            )
        except Exception as e:  # noqa: BLE001
            logger.info("update_oam_application: patch of %s skipped/failed (%s)", name, e)
            return False
        logger.info("✅ AppContainerClaim %s spec.oamApplication refreshed", name)
        return True

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

    # ----------------------------------------------------------------------
    # Teardown primitives (app.delete — defeat the GitOps recreation loop).
    # See the recreation-loop memory: a single-resource delete is reversed in
    # ~30s by the 7-layer cascade (ArgoCD selfHeal → OAM app → claims →
    # composition → Objects → Jobs). The use-case orders these primitives:
    # disable auto-sync FIRST, then finalizer-patch + delete in the safe order.
    # All are idempotent — a 404 ("already gone") is success, not an error.
    # ----------------------------------------------------------------------

    @staticmethod
    def _is_404(e: Exception) -> bool:
        return getattr(e, "status", None) == 404

    def list_namespaced_crs(self, group: str, version: str, plural: str,
                            namespace: str, label_selector: str | None = None) -> list[dict[str, Any]]:
        """List namespaced custom objects (name list survives missing CRD/RBAC as [])."""
        try:
            resp = self._custom_api().list_namespaced_custom_object(
                group=group, version=version, namespace=namespace, plural=plural,
                label_selector=label_selector or "",
            )
            return resp.get("items", []) or []
        except Exception as e:  # noqa: BLE001
            logger.info("list_namespaced_crs %s/%s skipped (%s)", plural, namespace, e)
            return []

    def disable_argocd_auto_sync(self, name: str, argocd_namespace: str = "argocd") -> bool:
        """Patch spec.syncPolicy.automated = null on an ArgoCD Application so selfHeal
        stops resurrecting deleted children. MUST run before any delete. Idempotent:
        a 404 (app already gone) returns True."""
        patch = {"spec": {"syncPolicy": {"automated": None}}}
        try:
            self._custom_api().patch_namespaced_custom_object(
                group="argoproj.io", version="v1alpha1", namespace=argocd_namespace,
                plural="applications", name=name, body=patch,
            )
            logger.info("✅ ArgoCD app %s auto-sync disabled", name)
            return True
        except Exception as e:  # noqa: BLE001
            if self._is_404(e):
                return True
            logger.warning("disable_argocd_auto_sync %s failed: %s", name, e)
            return False

    def delete_cr(self, group: str, version: str, plural: str, name: str,
                  namespace: str, argocd: bool = False) -> tuple[bool, str]:
        """Finalizer-patch ([]) then delete a single namespaced custom object.
        Clearing finalizers first guarantees the delete is not blocked by a stuck
        controller (the recreation-loop trap). Idempotent: 404 => already gone => ok."""
        try:
            self._custom_api().patch_namespaced_custom_object(
                group=group, version=version, namespace=namespace,
                plural=plural, name=name, body={"metadata": {"finalizers": []}},
            )
        except Exception as e:  # noqa: BLE001
            if not self._is_404(e):
                logger.info("finalizer-clear %s/%s: %s (continuing to delete)", plural, name, e)
        try:
            self._custom_api().delete_namespaced_custom_object(
                group=group, version=version, namespace=namespace, plural=plural, name=name,
            )
            return True, f"deleted {plural}/{name}"
        except Exception as e:  # noqa: BLE001
            if self._is_404(e):
                return True, f"{plural}/{name} already gone"
            return False, f"delete {plural}/{name} failed: {e}"

    def list_namespaces(self, prefix: str) -> list[str]:
        """Names of namespaces whose name == prefix or starts with prefix + '-'."""
        try:
            resp = self._core_api().list_namespace()
        except Exception as e:  # noqa: BLE001
            logger.info("list_namespaces skipped (%s)", e)
            return []
        out: list[str] = []
        for ns in resp.items:
            n = ns.metadata.name
            if n == prefix or n.startswith(f"{prefix}-"):
                out.append(n)
        return out

    def delete_namespace(self, name: str) -> tuple[bool, str]:
        """Delete a namespace. Idempotent: 404 => already gone => ok."""
        try:
            self._core_api().delete_namespace(name=name)
            return True, f"deleted namespace/{name}"
        except Exception as e:  # noqa: BLE001
            if self._is_404(e):
                return True, f"namespace/{name} already gone"
            return False, f"delete namespace/{name} failed: {e}"
