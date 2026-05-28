"""Kubernetes catalog client — live reads of the OAM catalog.

Lists/gets KubeVela ComponentDefinitions + TraitDefinitions via the CustomObjectsApi (in-cluster
config). Parameter *schemas* are NOT read here — only `webservice` has a `component-schema-*`
ConfigMap, so schemas are rendered live by vela_client (see docs decision). This client supplies
name + description + workload kind + catalog annotations (category/status/revision).
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

    def list_traits(self) -> list[str]:
        return [it.get("metadata", {}).get("name", "") for it in self._list("traitdefinitions")]

    def get_component(self, name: str) -> dict[str, Any] | None:
        for c in self.list_components():
            if c["name"] == name:
                return c
        return None
