"""Submit use-case — the gated action surface (`app.submit`).

OAM-first: validate (vela dry-run) → commit the OAM to the central gitops repo (intake
ledger / audit record) → route.

Routing (declarative-spine W4; legacy WFT retired in RETIRE-WFT #149, 2026-06-06):
  - Scaffold needed (webservice with `language:` and default/absent image):
      * per-service gitops repo EXISTS  → UPDATE path: commit the OAM directly to
        <svc>-gitops/oam/applications/application.yaml. ArgoCD syncs; no workflow.
      * repo does NOT exist             → DAY-0 path: create an AppContainerClaim
        (in-cluster, no Argo REST call). Its composition creates source + gitops
        repos, seeds the consumer OAM, and an ArgoCD Application pointing at the
        per-service repo. CI builds → pins the image sha back into the repo.
    The legacy oam-driven-contract WFT escape hatch (env SUBMIT_USE_WFT) was
    removed once the claim path was proven E2E (patient2-api, 2026-06-06); the
    archived template lives under execute/_archive/.
  - Otherwise (no webservice with language, or bring-your-own-image) → `oam-apply`
    (legacy: validate → ArgoCD app → ArgoCD syncs the file the MCP just committed).
    This path doesn't build images; retained until W7.

The central-ledger copy at oam/applications/<app>.yaml is the consumer's pristine
submission — it is never mutated by CI and is NOT reconciled by ArgoCD.
"""
from __future__ import annotations

import base64
import logging
from typing import Any

import yaml

from ..domain.models import SubmitResult
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.k8s_claim_client import K8sClaimClient
from ..infrastructure.vela_client import VelaClient

logger = logging.getLogger(__name__)
_OAM_TEMPLATE = "oam-apply"                       # legacy fallback for non-scaffold paths
_SVC_OAM_PATH = "oam/applications/application.yaml"  # single reconciled truth per service repo


class SubmitUseCase:
    def __init__(self, vela: VelaClient, github: GitHubClient, argo: ArgoWorkflowsClient,
                 gitops_branch: str = "main", claims: K8sClaimClient | None = None):
        self.vela = vela
        self.github = github
        self.argo = argo
        self.gitops_branch = gitops_branch
        # dependencies.py wires this. Kept Optional only so existing unit tests can
        # construct the use-case without a real cluster client; day-0 scaffolds and
        # submit_wait REQUIRE it (the legacy WFT fallback was retired in #149).
        self.claims = claims

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

        # 2a. identity topology rule (platform invariant, 2026-06-06):
        # an OAM with >=1 externally exposed webservice has EXACTLY ONE
        # identity component, which auths all of its APIs.
        topo_err = self._validate_identity_topology(app)
        if topo_err:
            return SubmitResult(ok=False, message=f"validation failed:\n{topo_err}")

        # 2b. validate (fail-fast gate)
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

        # 4. ROUTE (declarative-spine W4)
        scaffold = self._needs_scaffold(app)
        if scaffold is None:
            # No scaffolding (backing services / bring-your-own-image) → legacy oam-apply.
            return self._fire_oam_apply(app_name, namespace, target_vcluster, oam_yaml, sha, path)

        if self.claims is None:
            # Claim client not wired (should not happen in prod — dependencies.py
            # always provides it). No legacy WFT to fall back to since #149.
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but no claim client is "
                                        f"configured; cannot scaffold {app_name}")

        return self._declarative_scaffold(app, app_name, scaffold, target_vcluster, oam_yaml, sha)

    def submit_wait(self, oam_yaml: str) -> SubmitResult:
        """Deferred sibling of submit() — for OAMs whose ComponentDefinitions don't exist yet.

        Skips vela.dry_run (would fail by design — that's why the caller chose
        submit_wait) and routes straight to the declarative path. The wait is now
        intrinsic to the substrate, not a workflow:

          - The AppContainerClaim is created immediately; its Crossplane composition
            reconciles continuously and only progresses once the referenced CDs land.
          - ArgoCD reconciles the resulting Application; its health/sync conditions
            (read via app.status / StatusUseCase) report when prereqs are satisfied.

        RETIRE-WFT (#149): this replaces the oam-apply-wait WorkflowTemplate poll.
        There is no Argo REST call and no token on this path. Response shape is
        unchanged (SubmitResult); workflow_name carries the claim name so the
        existing {ok, commit_sha, workflow_name, message} contract holds. Poll
        progress with app.status(<name>).
        """
        try:
            app = yaml.safe_load(oam_yaml)
            md = app["metadata"]
            app_name = md["name"]
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, message=f"invalid OAM Application YAML: {e}")

        target_vcluster = self._target_vcluster(app)

        # SKIP vela.dry_run — caller chose submit_wait because it would fail.

        # Central-ledger commit (the durable gate / audit record), same as submit().
        path = f"oam/applications/{app_name}.yaml"
        committed, sha = self.github.commit_file(
            path, oam_yaml,
            message=f"oam: submit_wait {app_name} (capability-mcp app.submit_wait)",
            branch=self.gitops_branch,
        )
        if not committed:
            return SubmitResult(ok=False, message="gitops commit failed")

        scaffold = self._needs_scaffold(app)
        if scaffold is None or self.claims is None:
            # No scaffolding component (or no claim client): nothing to provision
            # imperatively. The OAM is committed to the ledger; once its CDs land
            # the consumer can re-run submit() to deliver. Report queued.
            return SubmitResult(ok=True, commit_sha=sha,
                                message=(f"queued {app_name}; committed {sha}; OAM stored in "
                                         f"the gitops ledger — resubmit once its "
                                         f"ComponentDefinitions are available"))

        # Same declarative provisioning as submit(): the claim/ArgoCD do the waiting.
        return self._declarative_scaffold(app, app_name, scaffold, target_vcluster, oam_yaml, sha)

    # ----------------------------------------------------------------------
    # Routing helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _validate_identity_topology(app: dict[str, Any]) -> str | None:
        """Platform invariant: >=1 exposed webservice => exactly ONE identity
        component (type auth0-idp) authing all the OAM's APIs. Multiple identity
        components per OAM are always rejected. Returns an error string or None.
        """
        comps = app.get("spec", {}).get("components", []) or []
        identity_comps = [c.get("name") for c in comps if c.get("type") == "auth0-idp"]

        def _is_exposed(c: dict[str, Any]) -> bool:
            for t in c.get("traits") or []:
                if t.get("type") == "expose-api":
                    return True
            return bool((c.get("properties") or {}).get("exposeApi"))

        exposed = [c.get("name") for c in comps
                   if c.get("type") in ("webservice", "webservice-shape") and _is_exposed(c)]

        if len(identity_comps) > 1:
            return ("identity topology: found %d identity components (%s) - an OAM must "
                    "have at most ONE; point every webservice's `identity:` ref and every "
                    "expose-api trait at the same component"
                    % (len(identity_comps), ", ".join(identity_comps)))
        if exposed and not identity_comps:
            return ("identity topology: components %s are externally exposed but the OAM "
                    "has no identity component - add ONE auth0-idp component and reference "
                    "it via `identity:` + expose-api(identity=...)" % ", ".join(exposed))
        return None

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

    _FW_FOR_LANG = {"python": "fastapi", "java": "springboot",
                    "rasa": "chatbot", "nodejs": "graphql-gateway"}

    @classmethod
    def _derive_framework(cls, lang: str, fw: str | None) -> str:
        """framework from language when unset/"auto" (single source of truth)."""
        if fw and fw != "auto":
            return fw
        return cls._FW_FOR_LANG.get(lang, "fastapi")

    @classmethod
    def _webservice_services(cls, app: dict[str, Any]) -> list[dict[str, str]]:
        """UNIFY-1 (#153): derive services[] from EVERY webservice component that
        needs scaffolding (language set, image absent/default). One AppContainerClaim
        per OAM ranges over this to emit one ApplicationClaim per service, all sharing
        the OAM-named repo (microservices/<name>/ per service). Backward compatible:
        a single-component OAM yields a one-element list.
        """
        services: list[dict[str, str]] = []
        for comp in app.get("spec", {}).get("components", []) or []:
            if comp.get("type") != "webservice":
                continue
            props = comp.get("properties") or {}
            lang = props.get("language")
            if not lang:
                continue
            img = props.get("image", "")
            default_img = f"healthidpuaeacr.azurecr.io/{comp.get('name')}:latest"
            if img and img != default_img:
                continue  # bring-your-own image: not scaffolded
            services.append({
                "name": comp.get("name"),
                "language": lang,
                "framework": cls._derive_framework(lang, props.get("framework")),
            })
        return services

    def _declarative_scaffold(self, app: dict[str, Any], app_name: str,
                              scaffold_comp: dict[str, Any],
                              target_vcluster: str | None, oam_yaml: str,
                              sha: str) -> SubmitResult:
        """Declarative-spine path: update via direct repo commit, day-0 via claim.

        UNIFY-1 (#153): tenancy unit is the OAM. ONE AppContainerClaim named after
        the OAM app, carrying services[] (one entry per scaffolded webservice). Its
        composition creates ONE source + ONE gitops repo and ranges over services[]
        to emit one ApplicationClaim per service, each scaffolding microservices/<name>/
        in the shared repo. No Argo REST call anywhere — the claim's composition owns
        repo creation, OAM seeding and the ArgoCD Application; CI closes the image loop.
        """
        svc_repo = f"{app_name}-gitops"           # repo is named after the OAM (shared)
        services = self._webservice_services(app)  # all scaffolded webservices

        # UPDATE path: the OAM repo already exists → the OAM file there is the single
        # reconciled truth; commit straight to it. ArgoCD picks it up.
        if self.github.repo_exists(svc_repo):
            ok, svc_sha = self.github.commit_file(
                _SVC_OAM_PATH, oam_yaml,
                message=f"oam: update {app_name} (capability-mcp app.submit)",
                branch=self.gitops_branch, repo=svc_repo,
            )
            if not ok:
                return SubmitResult(ok=False, commit_sha=sha,
                                    message=f"ledger committed {sha} but per-service "
                                            f"commit to {svc_repo} failed")
            # UNIFY-1 update-path reconcile: a NEW webservice component added to an
            # existing OAM must scaffold its microservices/<name>/ folder. The existing
            # AppContainerClaim only knows about the services it was created with, so
            # patch in any missing entries — the composition then emits an extra
            # ApplicationClaim for the new service. No trait needed. Best-effort: an
            # absent claim (legacy single-service claims pre-UNIFY-1) is a no-op.
            reconcile_msg = ""
            if self.claims is not None and services:
                added = self.claims.reconcile_services(name=app_name, services=services)
                if added:
                    reconcile_msg = f"; scaffolded new service(s): {', '.join(added)}"
            return SubmitResult(ok=True, commit_sha=svc_sha,
                                message=(f"updated {app_name}; committed {svc_sha} to "
                                         f"{svc_repo}/{_SVC_OAM_PATH}; ArgoCD will reconcile "
                                         f"(ledger {sha}){reconcile_msg}"))

        # DAY-0 path: create the AppContainerClaim named after the OAM. Composition
        # does the rest (one repo pair via templates, OAM seed, one ApplicationClaim
        # per service for code scaffolding, ArgoCD app). database/cache are resolved
        # from the FIRST scaffold component's OAM-style references (claim-level
        # backing-service knobs are shared across the monorepo, as before).
        props = scaffold_comp.get("properties") or {}
        comp_types = {c.get("name"): c.get("type", "")
                      for c in app.get("spec", {}).get("components", [])}

        def _resolve_dep(key: str, default: str) -> str:
            raw = props.get(key)
            if not raw:
                return default
            return comp_types.get(raw, raw)

        _lang = props.get("language", "python")
        _fw = self._derive_framework(_lang, props.get("framework"))
        ok, msg = self.claims.create_app_container_claim(
            name=app_name,
            oam_application_b64=base64.b64encode(oam_yaml.encode()).decode(),
            language=_lang,
            framework=_fw,
            services=services,
            database=_resolve_dep("database", "none"),
            cache=_resolve_dep("cache", "none"),
            delivery_target=target_vcluster or "host",
            description=f"OAM-driven via app.submit ({app_name})",
        )
        if not ok:
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but claim creation failed: {msg}")
        svc_count = len(services) or 1
        return SubmitResult(ok=True, commit_sha=sha, workflow_name=app_name,
                            message=(f"submitted {app_name}; committed {sha}; {msg}; "
                                     f"composition will create {svc_repo} + seed OAM + "
                                     f"ArgoCD app + scaffold {svc_count} service(s) "
                                     f"(target={target_vcluster or 'host'})"))

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
