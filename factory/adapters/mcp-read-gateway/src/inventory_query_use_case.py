"""platform.inventory — live deployment-state aggregator (OBS-B).

Answers "what's actually deployed?" by joining the desired-vs-live truth across
the platform, per OAM Application:

  - OAM app     : application.core.oam.dev → components[] (name, type), status/health.
  - ArgoCD      : matching Application(s) sync + health + DRIFT (OutOfSync == drift).
  - Knative     : ksvc per component → image @digest, latestReadyRevision, Ready.
  - Crossplane  : claims/Objects readiness for backing infra (SYNCED + READY).
  - HARD-4      : latest contract-test verdict per component (the ct-<comp>-* Jobs).

READ-ONLY. Reuses the in-cluster CustomObjectsApi / CoreV1Api access path that
K8sClaimClient (capability-mcp-core) already uses for app.status — no new RBAC
surface, no token, no kubectl shell-out. The factory ksvc runs as the
`capability-mcp-server` SA, which already get/list's OAM apps, ArgoCD apps,
ksvcs and claims.

Shape (per app):
  { name, namespace, oamHealth, oamPhase,
    argocd: { sync, health, drift, apps: [{name, sync, health}] },
    components: [ { name, type, image, digest, revision, ready, contractTest } ],
    claims: [ { kind, name, ready, synced } ] }
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_OAM_GROUP = "core.oam.dev"
_OAM_VERSION = "v1beta1"
_OAM_PLURAL = "applications"

_ARGO_GROUP = "argoproj.io"
_ARGO_VERSION = "v1alpha1"
_ARGO_PLURAL = "applications"

_KSVC_GROUP = "serving.knative.dev"
_KSVC_VERSION = "v1"
_KSVC_PLURAL = "services"

# Crossplane claim kinds this platform emits backing infra through. We discover
# claims by label correlation (app.kubernetes.io/name == app) rather than
# enumerating every CRD, so new claim kinds need no code change — but we keep a
# known-plurals map for the common ones to read readiness without a CRD walk.
_CLAIM_KINDS = [
    ("platform.example.org", "v1alpha1", "appcontainerclaims", "AppContainerClaim"),
    ("platform.example.org", "v1alpha1", "applicationclaims", "ApplicationClaim"),
    ("platform.example.org", "v1alpha1", "realtimeplatformclaims", "RealtimePlatformClaim"),
    ("platform.example.org", "v1alpha1", "webhookplatformclaims", "WebhookPlatformClaim"),
]


class InventoryQueryUseCase:
    """Aggregate live deployment state. Lazily builds the kube clients; every
    sub-read is best-effort (a missing CRD / RBAC gap degrades one field to
    null, never fails the whole inventory)."""

    def __init__(self) -> None:
        self._custom = None
        self._core = None

    # ---- kube access (same fallback pattern as K8sClaimClient) ----
    def _apis(self):
        if self._custom is None:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:  # noqa: BLE001
                config.load_kube_config()
            self._custom = client.CustomObjectsApi()
            self._core = client.CoreV1Api()
        return self._custom, self._core

    # ---- public entrypoint ----
    def inventory(
        self,
        app: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return {ok, apps: [...]}. Optionally filter by app name and/or namespace."""
        try:
            custom, _core = self._apis()
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"kube client init failed: {e}", "apps": []}

        ns = namespace or "default"
        try:
            if app:
                obj = custom.get_namespaced_custom_object(
                    group=_OAM_GROUP, version=_OAM_VERSION, namespace=ns,
                    plural=_OAM_PLURAL, name=app,
                )
                oam_apps = [obj]
            else:
                resp = custom.list_namespaced_custom_object(
                    group=_OAM_GROUP, version=_OAM_VERSION, namespace=ns,
                    plural=_OAM_PLURAL,
                )
                oam_apps = resp.get("items", [])
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"OAM application list failed: {e}", "apps": []}

        out_apps = [self._aggregate_app(o, ns) for o in oam_apps]
        return {"ok": True, "count": len(out_apps), "apps": out_apps}

    # ---- per-app aggregation ----
    def _aggregate_app(self, oam: dict[str, Any], ns: str) -> dict[str, Any]:
        meta = oam.get("metadata", {})
        name = meta.get("name", "unknown")
        spec = oam.get("spec", {})
        status = oam.get("status", {})

        comp_specs = spec.get("components", []) or []
        components: list[dict[str, Any]] = []
        for c in comp_specs:
            cname = c.get("name")
            ctype = c.get("type")
            components.append(self._component_state(cname, ctype, ns))

        return {
            "name": name,
            "namespace": ns,
            "oamPhase": status.get("status"),
            "oamHealth": self._oam_health(status),
            "argocd": self._argocd_for_app(name),
            "components": components,
            "claims": self._claims_for_app(name, ns),
        }

    @staticmethod
    def _oam_health(status: dict[str, Any]) -> Optional[bool]:
        # KubeVela exposes per-service health under status.services[].healthy;
        # the printed HEALTHY column aggregates them. Treat all-healthy as true.
        svcs = status.get("services") or []
        if not svcs:
            return None
        return all(bool(s.get("healthy")) for s in svcs)

    # ---- ArgoCD: correlate by name prefix; report drift ----
    def _argocd_for_app(self, app_name: str) -> dict[str, Any]:
        custom, _ = self._apis()
        try:
            resp = custom.list_namespaced_custom_object(
                group=_ARGO_GROUP, version=_ARGO_VERSION, namespace="argocd",
                plural=_ARGO_PLURAL,
            )
        except Exception as e:  # noqa: BLE001
            return {"sync": None, "health": None, "drift": None, "error": str(e), "apps": []}

        matched: list[dict[str, Any]] = []
        for a in resp.get("items", []):
            an = a.get("metadata", {}).get("name", "")
            # rtdemo2-* / webhookdemo-* family correlation.
            if an == app_name or an.startswith(app_name + "-"):
                st = a.get("status", {}) or {}
                sync = (st.get("sync") or {}).get("status")
                health = (st.get("health") or {}).get("status")
                matched.append({"name": an, "sync": sync, "health": health})

        if not matched:
            return {"sync": None, "health": None, "drift": None, "apps": []}

        any_outofsync = any(m["sync"] == "OutOfSync" for m in matched)
        # Roll-up: if any child app is OutOfSync the app has drift.
        any_unhealthy = any(m["health"] not in ("Healthy", None) for m in matched)
        return {
            "sync": "OutOfSync" if any_outofsync else "Synced",
            "health": "Degraded" if any_unhealthy else "Healthy",
            "drift": any_outofsync,
            "apps": matched,
        }

    # ---- Knative ksvc per component (image@digest, revision, ready) + contract test ----
    def _component_state(self, cname: Optional[str], ctype: Optional[str], ns: str) -> dict[str, Any]:
        comp: dict[str, Any] = {
            "name": cname,
            "type": ctype,
            "image": None,
            "digest": None,
            "revision": None,
            "ready": None,
            "contractTest": self._contract_test(cname, ns),
        }
        if not cname:
            return comp

        custom, _ = self._apis()
        # A component may map to <name> or <name>-realtime-service etc. Try the
        # bare name first, then common suffixes used by realtime-platform.
        candidates = [cname, f"{cname}-realtime-service"]
        for ksvc_name in candidates:
            try:
                ksvc = custom.get_namespaced_custom_object(
                    group=_KSVC_GROUP, version=_KSVC_VERSION, namespace=ns,
                    plural=_KSVC_PLURAL, name=ksvc_name,
                )
            except Exception:  # noqa: BLE001
                continue
            status = ksvc.get("status", {}) or {}
            rev_name = status.get("latestReadyRevisionName")
            comp["revision"] = rev_name
            conds = status.get("conditions", []) or []
            ready_cond = next((c for c in conds if c.get("type") == "Ready"), None)
            comp["ready"] = (ready_cond.get("status") == "True") if ready_cond else None
            # Desired image is on the ksvc template spec.
            spec_containers = (
                ksvc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            )
            if spec_containers:
                comp["image"] = spec_containers[0].get("image")
            # Resolved image (the digest Knative actually pulled) lives on the
            # ROOT Revision, not the Service: Revision.status.containerStatuses[].imageDigest.
            # This is the HARD-3 truth — even when the ksvc spec says ":latest", the
            # revision pins the exact sha256 that is running.
            digest_image = self._revision_digest(rev_name, ns)
            if digest_image:
                comp["digest"] = (
                    digest_image.split("@", 1)[1] if "@sha256:" in digest_image else digest_image
                )
                if not comp["image"]:
                    comp["image"] = digest_image
            # Fallback: spec image already carries an @sha256 digest.
            elif comp["image"] and "@sha256:" in comp["image"]:
                comp["digest"] = comp["image"].split("@", 1)[1]
            break
        return comp

    def _revision_digest(self, rev_name: Optional[str], ns: str) -> Optional[str]:
        """Read Revision.status.containerStatuses[0].imageDigest (the resolved sha256
        Knative actually pulled). This is where the digest lives — the Service status
        does not surface it."""
        if not rev_name:
            return None
        custom, _ = self._apis()
        try:
            rev = custom.get_namespaced_custom_object(
                group=_KSVC_GROUP, version=_KSVC_VERSION, namespace=ns,
                plural="revisions", name=rev_name,
            )
        except Exception:  # noqa: BLE001
            return None
        cs = (rev.get("status", {}) or {}).get("containerStatuses") or []
        return cs[0].get("imageDigest") if cs else None

    # ---- HARD-4 contract test: latest ct-<component>-* Job verdict ----
    def _contract_test(self, cname: Optional[str], ns: str) -> dict[str, Any]:
        if not cname:
            return {"status": None}
        try:
            from kubernetes import client
            _, _core = self._apis()
            batch = client.BatchV1Api()
        except Exception:  # noqa: BLE001
            return {"status": None}
        try:
            jobs = batch.list_namespaced_job(
                namespace=ns,
                label_selector="app.kubernetes.io/component=contract-test",
            )
        except Exception as e:  # noqa: BLE001
            return {"status": None, "error": str(e)}

        # ct-<component>-<gen>; pick the newest matching this component.
        prefix = f"ct-{cname}-"
        mine = [j for j in jobs.items if (j.metadata.name or "").startswith(prefix)]
        if not mine:
            return {"status": "none"}
        mine.sort(key=lambda j: j.metadata.creation_timestamp, reverse=True)
        latest = mine[0]
        st = latest.status
        if st and st.succeeded:
            verdict = "pass"
        elif st and st.failed:
            verdict = "fail"
        else:
            verdict = "running"
        return {"status": verdict, "job": latest.metadata.name}

    # ---- Crossplane claims readiness for the app's backing infra ----
    def _claims_for_app(self, app_name: str, ns: str) -> list[dict[str, Any]]:
        custom, _ = self._apis()
        out: list[dict[str, Any]] = []
        for group, version, plural, kind in _CLAIM_KINDS:
            try:
                resp = custom.list_namespaced_custom_object(
                    group=group, version=version, namespace=ns, plural=plural,
                )
            except Exception:  # noqa: BLE001
                continue  # CRD not installed → skip
            for item in resp.get("items", []):
                cn = item.get("metadata", {}).get("name", "")
                if cn != app_name and not cn.startswith(app_name + "-") and app_name not in cn:
                    continue
                conds = (item.get("status", {}) or {}).get("conditions", []) or []
                ready = self._cond(conds, "Ready")
                synced = self._cond(conds, "Synced")
                out.append({"kind": kind, "name": cn, "ready": ready, "synced": synced})
        return out

    @staticmethod
    def _cond(conds: list[dict[str, Any]], ctype: str) -> Optional[bool]:
        c = next((x for x in conds if x.get("type") == ctype), None)
        if not c:
            return None
        return c.get("status") == "True"
