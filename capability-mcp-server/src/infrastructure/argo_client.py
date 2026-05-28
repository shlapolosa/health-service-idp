"""Argo Workflows client — focused lift of slack-api-server's ArgoWorkflowsClient
(see slack-api-server/src/infrastructure/argo_client.py:602 create_workflow_from_template).

Only the submit primitive is needed here: POST a Workflow that references a WorkflowTemplate,
authenticated with the in-cluster Argo Bearer token from ARGO_TOKEN_FILE. Used by app.submit to
trigger the `oam-apply` WorkflowTemplate. We do NOT depend on slack-api-server (Phase-2: no changes
to it) — this is a self-contained copy of the proven pattern.
"""
from __future__ import annotations

import logging
import os
from typing import Dict

import requests

logger = logging.getLogger(__name__)


class ArgoWorkflowsClient:
    def __init__(self, server_url: str, namespace: str = "argo", timeout: int = 30,
                 token_file: str | None = None):
        self.server_url = server_url.rstrip("/")
        self.namespace = namespace
        self.timeout = timeout
        self.base_url = f"{self.server_url}/api/v1"
        self.token_file = token_file or os.getenv("ARGO_TOKEN_FILE")

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token_file and os.path.exists(self.token_file):
            try:
                token = open(self.token_file).read().strip()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to read Argo token file %s: %s", self.token_file, e)
        else:
            logger.warning("Argo token file not found: %s", self.token_file)
        return headers

    def create_workflow_from_template(self, template: str, parameters: Dict,
                                      namespace: str | None = None) -> Dict:
        """Submit a Workflow that references WorkflowTemplate `template` with `parameters`.
        Returns the Argo API response (or raises on transport failure)."""
        ns = namespace or self.namespace
        workflow_spec = {
            "namespace": ns,
            "serverDryRun": False,
            "workflow": {
                "metadata": {
                    "generateName": f"{template}-",
                    "namespace": ns,
                    "labels": {"created-by": "capability-mcp", "template": template},
                },
                "spec": {
                    "workflowTemplateRef": {"name": template},
                    "arguments": {
                        "parameters": [{"name": k, "value": str(v)} for k, v in parameters.items()]
                    },
                },
            },
        }
        resp = requests.post(
            f"{self.base_url}/workflows/{ns}",
            headers=self._auth_headers(),
            json=workflow_spec,
            timeout=self.timeout,
            verify=False,  # internal cluster TLS, matches slack-api-server
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("✅ submitted workflow %s", data.get("metadata", {}).get("name"))
        return data
