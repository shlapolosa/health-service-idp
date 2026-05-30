"""Kubernetes catalog client — live reads of the OAM catalog.

Lists/gets KubeVela ComponentDefinitions, TraitDefinitions, PolicyDefinitions,
WorkflowStepDefinitions via the CustomObjectsApi (in-cluster config). Parameter *schemas* are
NOT read here for ComponentDefinitions/TraitDefinitions — those are rendered live by
vela_client via `vela show`. For PolicyDefinitions + WorkflowStepDefinitions (which vela show
does not support) we expose the raw `spec.schematic.cue.template` so the use case can run it
through `cue_param_parser`.

Listing scope:
- `list_components()` stays NAMESPACED (default ns) — platform-curated CDs deliberately scoped.
- `list_traits()`, `list_policies()`, `list_workflow_steps()` are CLUSTER-WIDE — the agent
  should see vanilla vela-system traits (affinity, annotations, command, ...) alongside the
  platform's autoscaler/ingress/kafka-* traits.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_GROUP = "core.oam.dev"
_VERSION = "v1beta1"
_DESC_ANN = "definition.oam.dev/description"
_CATEGORY_ANN = "catalog.oam.dev/category"
_STATUS_ANN = "catalog.oam.dev/status"


class K8sCatalogClient:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self._api = None

    @property
    def api(self):
        if self._api is None:
            from kubernetes import client, config
            try:
                config.load_incluster_config()
            except Exception:  # noqa: BLE001 — local dev fallback
                config.load_kube_config()
            self._api = client.CustomObjectsApi()
        return self._api

    def _list(self, plural: str) -> list[dict[str, Any]]:
        return self.api.list_namespaced_custom_object(
            _GROUP, _VERSION, self.namespace, plural
        ).get("items", [])

    def _list_all_namespaces(self, plural: str) -> list[dict[str, Any]]:
        return self.api.list_cluster_custom_object(
            _GROUP, _VERSION, plural
        ).get("items", [])

    def list_components(self) -> list[dict[str, Any]]:
        out = []
        for it in self._list("componentdefinitions"):
            md = it.get("metadata", {})
            ann = md.get("annotations", {}) or {}
            spec = it.get("spec", {})
            wl = spec.get("workload", {}).get("definition", {})
            out.append({
                "name": md.get("name", ""),
                "description": ann.get(_DESC_ANN, ""),
                "workload_kind": f"{wl.get('kind','')}/{wl.get('apiVersion','')}".strip("/"),
                "category": ann.get(_CATEGORY_ANN, ""),
                "status": ann.get(_STATUS_ANN, ""),
                "revision": (it.get("status", {}).get("latestRevision", {}) or {}).get("name", ""),
            })
        return out

    def get_component(self, name: str) -> dict[str, Any] | None:
        for c in self.list_components():
            if c["name"] == name:
                return c
        return None

    # ----------------------------------------------------------------------
    # TraitDefinitions — cluster-wide. Returns rich dicts with appliesToWorkloads.
    # ----------------------------------------------------------------------

    def list_traits(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in self._list_all_namespaces("traitdefinitions"):
            md = it.get("metadata", {})
            ann = md.get("annotations", {}) or {}
            spec = it.get("spec", {}) or {}
            out.append({
                "name": md.get("name", ""),
                "namespace": md.get("namespace", ""),
                "description": ann.get(_DESC_ANN, ""),
                "appliesToWorkloads": spec.get("appliesToWorkloads", []) or [],
                "conflictsWith": spec.get("conflictsWith", []) or [],
                "podDisruptive": bool(spec.get("podDisruptive", False)),
            })
        return out

    def get_trait(self, name: str) -> dict[str, Any] | None:
        for t in self.list_traits():
            if t["name"] == name:
                return t
        return None

    # ----------------------------------------------------------------------
    # PolicyDefinitions — cluster-wide. Includes raw CUE template for local parsing
    # (vela show does not support PolicyDefinitions).
    # ----------------------------------------------------------------------

    def list_policies(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in self._list_all_namespaces("policydefinitions"):
            md = it.get("metadata", {})
            ann = md.get("annotations", {}) or {}
            out.append({
                "name": md.get("name", ""),
                "namespace": md.get("namespace", ""),
                "description": ann.get(_DESC_ANN, ""),
            })
        return out

    def get_policy(self, name: str) -> dict[str, Any] | None:
        for it in self._list_all_namespaces("policydefinitions"):
            md = it.get("metadata", {})
            if md.get("name") != name:
                continue
            ann = md.get("annotations", {}) or {}
            spec = it.get("spec", {}) or {}
            return {
                "name": md.get("name", ""),
                "namespace": md.get("namespace", ""),
                "description": ann.get(_DESC_ANN, ""),
                "cue_template": ((spec.get("schematic") or {}).get("cue") or {}).get("template", ""),
            }
        return None

    # ----------------------------------------------------------------------
    # WorkflowStepDefinitions — cluster-wide. Same shape as PolicyDefinitions.
    # ----------------------------------------------------------------------

    def list_workflow_steps(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in self._list_all_namespaces("workflowstepdefinitions"):
            md = it.get("metadata", {})
            ann = md.get("annotations", {}) or {}
            out.append({
                "name": md.get("name", ""),
                "namespace": md.get("namespace", ""),
                "description": ann.get(_DESC_ANN, ""),
            })
        return out

    def get_workflow_step(self, name: str) -> dict[str, Any] | None:
        for it in self._list_all_namespaces("workflowstepdefinitions"):
            md = it.get("metadata", {})
            if md.get("name") != name:
                continue
            ann = md.get("annotations", {}) or {}
            spec = it.get("spec", {}) or {}
            return {
                "name": md.get("name", ""),
                "namespace": md.get("namespace", ""),
                "description": ann.get(_DESC_ANN, ""),
                "cue_template": ((spec.get("schematic") or {}).get("cue") or {}).get("template", ""),
            }
        return None
