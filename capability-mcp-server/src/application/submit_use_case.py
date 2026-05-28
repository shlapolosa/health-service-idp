"""Submit use-case — the gated action surface (`app.submit`).

OAM-first: validate (vela dry-run) → commit the OAM to the gitops repo (THE GATE) → trigger the
`oam-apply` WorkflowTemplate (which ensures repos/vCluster, waits for ClusterGateway, then creates the
ArgoCD Application applying the committed OAM). Never a raw `kubectl apply`. See docs §7, §8-P3.
"""
from __future__ import annotations

import base64
import logging
from typing import Any

import yaml

from ..domain.models import SubmitResult
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.vela_client import VelaClient

logger = logging.getLogger(__name__)
_OAM_TEMPLATE = "oam-apply"


class SubmitUseCase:
    def __init__(self, vela: VelaClient, github: GitHubClient, argo: ArgoWorkflowsClient,
                 gitops_branch: str = "main"):
        self.vela = vela
        self.github = github
        self.argo = argo
        self.gitops_branch = gitops_branch

    def submit(self, oam_yaml: str) -> SubmitResult:
        # 1. parse + identify the app
        try:
            app = yaml.safe_load(oam_yaml)
            md = app["metadata"]
            app_name = md["name"]
            namespace = md.get("namespace", "default")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, message=f"invalid OAM Application YAML: {e}")

        target_vcluster = self._target_vcluster(app)

        # 2. validate (fail-fast gate)
        ok, diag = self.vela.dry_run(oam_yaml)
        if not ok:
            return SubmitResult(ok=False, message=f"validation failed:\n{diag}")

        # 3. commit to gitops (the durable gate)
        path = f"oam/applications/{app_name}.yaml"
        committed, sha = self.github.commit_file(
            path, oam_yaml,
            message=f"oam: submit {app_name} (capability-mcp app.submit)",
            branch=self.gitops_branch,
        )
        if not committed:
            return SubmitResult(ok=False, message="gitops commit failed")

        # 4. trigger oam-apply (ensure prereqs → wait-for-clustergateway → create ArgoCD app)
        try:
            wf = self.argo.create_workflow_from_template(_OAM_TEMPLATE, {
                "oam-application": base64.b64encode(oam_yaml.encode()).decode(),
                "app-name": app_name,
                "namespace": namespace,
                "target-vcluster": target_vcluster or "host",
                "gitops-path": path,
            })
            wf_name = wf.get("metadata", {}).get("name", "unknown")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but oam-apply trigger failed: {e}")

        return SubmitResult(ok=True, commit_sha=sha, workflow_name=wf_name,
                            message=f"submitted {app_name}; committed {sha}; workflow {wf_name}")

    @staticmethod
    def _target_vcluster(app: dict[str, Any]) -> str | None:
        for comp in app.get("spec", {}).get("components", []):
            tgt = (comp.get("properties", {}) or {}).get("targetEnvironment")
            if tgt:
                return tgt
        return None
