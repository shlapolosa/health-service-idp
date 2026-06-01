"""Submit use-case — the gated action surface (`app.submit`).

OAM-first: validate (vela dry-run) → commit the OAM to the gitops repo (THE GATE) → trigger the
deployment workflow.

Routing (2026-05-30, Stage 3 of oam-apply consolidation plan):
  - If the OAM has a webservice component with `language:` set → fire `oam-driven-contract`
    (the proven /microservice chain forked + extended to accept consumer OAM). This builds the
    source repo, scaffolds boilerplate code, builds + pushes the image to ACR, AND overlays the
    consumer's OAM as the deployed state (overwriting the chain's boilerplate OAM at
    apps/oam-application.yaml in the per-service gitops repo).
  - Otherwise (no webservice with language, or OAM is purely backing services / pre-built
    image webservice) → fall back to `oam-apply` (legacy: validate → ArgoCD app → ArgoCD syncs
    the file the MCP just committed). This path doesn't build images; consumer must bring their
    own ACR image.
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
_OAM_TEMPLATE = "oam-apply"                       # legacy fallback for non-scaffold paths
_OAM_WAIT_TEMPLATE = "oam-apply-wait"             # deferred poll for missing-CD case
_OAM_DRIVEN_TEMPLATE = "oam-driven-contract"      # forked /microservice chain (Stage 3+)


class SubmitUseCase:
    def __init__(self, vela: VelaClient, github: GitHubClient, argo: ArgoWorkflowsClient,
                 gitops_branch: str = "main"):
        self.vela = vela
        self.github = github
        self.argo = argo
        self.gitops_branch = gitops_branch

    # ----------------------------------------------------------------------
    # Public surface (MCP tools wrap these)
    # ----------------------------------------------------------------------

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

        # 3. commit to gitops (the durable gate; applies to both routes)
        path = f"oam/applications/{app_name}.yaml"
        committed, sha = self.github.commit_file(
            path, oam_yaml,
            message=f"oam: submit {app_name} (capability-mcp app.submit)",
            branch=self.gitops_branch,
        )
        if not committed:
            return SubmitResult(ok=False, message="gitops commit failed")

        # 4. ROUTE: scaffold-needed → oam-driven-contract; otherwise → oam-apply
        scaffold = self._needs_scaffold(app)
        if scaffold is not None:
            return self._fire_oam_driven_contract(app, app_name, namespace, scaffold,
                                                  target_vcluster, oam_yaml, sha)
        return self._fire_oam_apply(app_name, namespace, target_vcluster, oam_yaml, sha, path)

    def submit_wait(self, oam_yaml: str) -> SubmitResult:
        """Deferred sibling of submit() — for OAMs whose ComponentDefinitions don't exist yet.

        Skips vela.dry_run (would fail by design) and fires oam-apply-wait, which polls vela
        dry-run until prereqs land then creates the ArgoCD Application. Does NOT route through
        oam-driven-contract — the contract assumes valid OAM at submit-time; submit_wait is
        explicitly for the case where the OAM references not-yet-merged CDs.
        """
        try:
            app = yaml.safe_load(oam_yaml)
            md = app["metadata"]
            app_name = md["name"]
            namespace = md.get("namespace", "default")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, message=f"invalid OAM Application YAML: {e}")

        target_vcluster = self._target_vcluster(app)

        # SKIP vela.dry_run — caller chose submit_wait because it would fail.

        path = f"oam/applications/{app_name}.yaml"
        committed, sha = self.github.commit_file(
            path, oam_yaml,
            message=f"oam: submit_wait {app_name} (capability-mcp app.submit_wait)",
            branch=self.gitops_branch,
        )
        if not committed:
            return SubmitResult(ok=False, message="gitops commit failed")

        try:
            wf = self.argo.create_workflow_from_template(_OAM_WAIT_TEMPLATE, {
                "oam-application": base64.b64encode(oam_yaml.encode()).decode(),
                "app-name": app_name,
                "namespace": namespace,
                "target-vcluster": target_vcluster or "host",
                "gitops-path": path,
            })
            wf_name = wf.get("metadata", {}).get("name", "unknown")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but oam-apply-wait trigger failed: {e}")

        return SubmitResult(ok=True, commit_sha=sha, workflow_name=wf_name,
                            message=f"queued {app_name}; committed {sha}; workflow {wf_name} "
                                    f"will poll vela dry-run until ready")

    # ----------------------------------------------------------------------
    # Routing helpers
    # ----------------------------------------------------------------------

    def _needs_scaffold(self, app: dict[str, Any]) -> dict[str, Any] | None:
        """Inspect OAM components; return the webservice component dict that needs scaffolding,
        or None if no scaffolding is needed.

        Scaffolding is needed when:
          - any component of type == "webservice" has a `language:` property set
          AND
          - its image is either omitted OR points at the default auto-scaffold path
            (healthidpuaeacr.azurecr.io/<component-name>:latest)

        Returns the FIRST such component. (Multi-webservice OAMs are deferred to Stage 4 —
        for now we scaffold just the first; the consumer's OAM still drives multi-component
        deployment via apply-consumer-oam.)
        """
        for comp in app.get("spec", {}).get("components", []) or []:
            if comp.get("type") != "webservice":
                continue
            props = comp.get("properties") or {}
            lang = props.get("language")
            if not lang:
                continue
            # Image must be the auto-default (or absent) — if consumer set a non-default
            # ACR image, treat as bring-your-own and use the legacy oam-apply path.
            img = props.get("image", "")
            default_img = f"healthidpuaeacr.azurecr.io/{comp.get('name')}:latest"
            if img and img != default_img:
                # Pre-built image supplied → no scaffold needed; fall through to oam-apply.
                continue
            return comp
        return None

    def _fire_oam_driven_contract(self, app: dict[str, Any], app_name: str, namespace: str,
                                  scaffold_comp: dict[str, Any], target_vcluster: str | None,
                                  oam_yaml: str, sha: str) -> SubmitResult:
        """Fire the forked /microservice chain with the consumer's OAM passed in.

        The workflow will create source + gitops repos, scaffold boilerplate code, build + push
        the image to ACR, then (via the apply-consumer-oam step) overwrite the boilerplate OAM
        in the per-service gitops repo with the consumer's actual OAM. ArgoCD reconciles.
        """
        props = scaffold_comp.get("properties") or {}
        # Build component name → type map so we can resolve OAM-style
        # references like `database: <component-name>` into the workflow's
        # expected type literal (postgresql, redis, …). Falls back to the
        # raw value when the reference doesn't match a sibling component.
        comp_types = {c.get("name"): c.get("type", "") for c in app.get("spec", {}).get("components", [])}
        def _resolve_dep(key: str, default: str) -> str:
            raw = props.get(key)
            if not raw:
                return default
            return comp_types.get(raw, raw)
        params = {
            "resource-name": scaffold_comp["name"],
            "namespace": namespace,
            "user": "capability-mcp",
            "description": f"OAM-driven via app.submit ({app_name})",
            "microservice-language": props.get("language", "python"),
            "microservice-framework": props.get("framework", "auto"),
            "microservice-database": _resolve_dep("database", "none"),
            "microservice-cache": _resolve_dep("cache", "none"),
            "target-vcluster": target_vcluster or "host",
            "auto-create-dependencies": "true",
            # The forked-only param — consumer's full OAM, base64-encoded, multi-component-safe.
            "oam-application": base64.b64encode(oam_yaml.encode()).decode(),
        }
        try:
            wf = self.argo.create_workflow_from_template(_OAM_DRIVEN_TEMPLATE, params)
            wf_name = wf.get("metadata", {}).get("name", "unknown")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but oam-driven-contract trigger failed: {e}")
        return SubmitResult(ok=True, commit_sha=sha, workflow_name=wf_name,
                            message=(f"submitted {app_name}; committed {sha}; workflow {wf_name}; "
                                     f"scaffold target = {scaffold_comp['name']} "
                                     f"({props.get('language','?')})"))

    def _fire_oam_apply(self, app_name: str, namespace: str, target_vcluster: str | None,
                        oam_yaml: str, sha: str, path: str) -> SubmitResult:
        """Legacy path for bring-your-own-image consumers / no-webservice OAMs."""
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
                            message=f"submitted {app_name} (bring-your-own-image path); "
                                    f"committed {sha}; workflow {wf_name}")

    @staticmethod
    def _target_vcluster(app: dict[str, Any]) -> str | None:
        for comp in app.get("spec", {}).get("components", []):
            tgt = (comp.get("properties", {}) or {}).get("targetEnvironment")
            if tgt:
                return tgt
        return None
