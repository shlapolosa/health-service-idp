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

from . import requirements_spec
from ..domain.models import SubmitResult
from ..infrastructure.argo_client import ArgoWorkflowsClient
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.k8s_claim_client import K8sClaimClient
from ..infrastructure.vela_client import VelaClient

logger = logging.getLogger(__name__)
_OAM_TEMPLATE = "oam-apply"                       # legacy fallback for non-scaffold paths
_SVC_OAM_PATH = "oam/applications/application.yaml"  # single reconciled truth per service repo
# SPEC-1 (#173, dev-agent W1): where the use-case spec lands.
_SVC_REQUIREMENTS_PATH = "REQUIREMENTS.md"        # app monorepo root (per-service gitops repo)


class SubmitUseCase:
    def __init__(self, vela: VelaClient, github: GitHubClient, argo: ArgoWorkflowsClient,
                 gitops_branch: str = "main", claims: K8sClaimClient | None = None,
                 apim_products: Any | None = None):
        self.vela = vela
        self.github = github
        self.argo = argo
        self.gitops_branch = gitops_branch
        # dependencies.py wires this. Kept Optional only so existing unit tests can
        # construct the use-case without a real cluster client; day-0 scaffolds and
        # submit_wait REQUIRE it (the legacy WFT fallback was retired in #149).
        self.claims = claims
        # APIM-PRODUCT-1 (#161): per-OAM Developer-Portal product reconciler. Optional
        # so existing unit tests construct without it; when absent the product step is
        # a silent no-op (purely additive — submit never depends on it succeeding).
        self.apim_products = apim_products

    # ----------------------------------------------------------------------
    # Public surface (MCP tools wrap these)
    # ----------------------------------------------------------------------

    def submit(self, oam_yaml: str, requirements: str | None = None) -> SubmitResult:
        # 1. parse + identify the app
        try:
            app = yaml.safe_load(oam_yaml)
            md = app["metadata"]
            app_name = md["name"]
            namespace = md.get("namespace", "default")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, message=f"invalid OAM Application YAML: {e}")

        # SPEC-1 (#173, dev-agent W1): optional REQUIREMENTS.md travels with the
        # submission. Validate fail-fast (before any commit), then carry the
        # normalized content + deterministic hash through both routes. Omitted
        # => exactly today's behaviour (no spec commit, spec_hash=None).
        try:
            spec = self._prepare_requirements(requirements)
        except requirements_spec.RequirementsError as e:
            return SubmitResult(ok=False, message=f"invalid requirements: {e}")

        # GQL-1 (#155): render-inject explicit `sources:` onto any graphql-gateway
        # component that omitted them, before validation/commit. app.submit is the
        # only place that can see sibling components, so it authors the authoritative
        # explicit list; the template's runtime kubectl discovery stays as fallback.
        oam_yaml = self._inject_graphql_sources(app, namespace, oam_yaml)

        # External-by-default (user decision 2026-06-07): graphql-gateway and
        # realtime-service are inherently external-facing - auto-attach the
        # expose-api trait (APIM publication; websocket API type for realtime)
        # wired to the OAM's singleton identity. Runs BEFORE topology
        # validation so exposure=>identity is enforced on the result.
        oam_yaml = self._auto_expose_external_components(app, oam_yaml)

        target_vcluster = self._target_vcluster(app)

        # 2a. identity topology rule (platform invariant, 2026-06-06):
        # an OAM with >=1 externally exposed webservice has EXACTLY ONE
        # identity component, which auths all of its APIs.
        topo_err = self._validate_identity_topology(app)
        if topo_err:
            return SubmitResult(ok=False, message=f"validation failed:\n{topo_err}")
        advisory = self._backing_sharing_advisory(app)

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

        # SPEC-1: commit the spec next to the OAM in the central ledger (audit/
        # discovery sibling). Best-effort — a failed spec commit never blocks the
        # OAM provisioning that already committed (purely additive).
        self._commit_ledger_requirements(app_name, spec)

        # 4. ROUTE (declarative-spine W4)
        scaffold = self._needs_scaffold(app)
        if scaffold is None:
            # No scaffolding (backing services / bring-your-own-image) → legacy oam-apply.
            return self._attach_spec_hash(self._reconcile_apim_product(app, self._with_advisory(
                self._fire_oam_apply(app_name, namespace, target_vcluster, oam_yaml, sha, path),
                advisory)), spec)

        if self.claims is None:
            # Claim client not wired (should not happen in prod — dependencies.py
            # always provides it). No legacy WFT to fall back to since #149.
            return SubmitResult(ok=False, commit_sha=sha,
                                message=f"committed {sha} but no claim client is "
                                        f"configured; cannot scaffold {app_name}")

        return self._attach_spec_hash(self._reconcile_apim_product(app, self._with_advisory(
            self._declarative_scaffold(app, app_name, scaffold, target_vcluster, oam_yaml, sha,
                                       spec),
            advisory)), spec)

    @staticmethod
    def _auto_expose_external_components(app: dict[str, Any], oam_yaml: str) -> str:
        """External-by-default: graphql-gateway + realtime-service components get
        the expose-api trait auto-attached (identity = the OAM's singleton
        auth0-idp; apiType websocket for realtime-service). Explicit traits are
        left untouched; OAMs without an identity component will then fail the
        exposure=>identity invariant with its existing actionable message.

        Role-aware since 2026-06-12 (rtdemo2): RT-2 realtime-service roles are
        gateway (consume->/ws, external), ingest (POST->produce, external) and
        processor (consume->transform->produce, INTERNAL — no HTTP surface to
        publish). Auto-attaching expose-api to a processor put a phantom
        websocket API into APIM, so processors are skipped; an explicit
        consumer-supplied expose-api trait on a processor is still respected
        (this function only ever ADDS traits, never removes them)."""
        comps = app.get("spec", {}).get("components", []) or []
        identity = next((c.get("name") for c in comps if c.get("type") == "auth0-idp"), None)
        changed = False
        for comp in comps:
            ctype = comp.get("type")
            if ctype not in ("graphql-gateway", "realtime-service"):
                continue
            if ctype == "realtime-service":
                role = str((comp.get("properties") or {}).get("role", "gateway")).strip()
                if role == "processor":
                    continue  # internal role: never auto-expose
            traits = comp.setdefault("traits", [])
            if any(t.get("type") == "expose-api" for t in traits):
                continue
            props: dict[str, Any] = {}
            if identity:
                props["identity"] = identity
            if ctype == "realtime-service":
                props["apiType"] = "websocket"
            traits.append({"type": "expose-api", "properties": props})
            changed = True
        if changed:
            return yaml.safe_dump(app, sort_keys=False)
        return oam_yaml

    @staticmethod
    def _backing_sharing_advisory(app: dict[str, Any]) -> str | None:
        """Cache/db are capacity resources, not singletons (unlike auth0-idp/
        realtime-platform/graphql-gateway): >1 per OAM is ALLOWED for deliberate
        isolation, but the frugal default is ONE shared instance referenced by
        every webservice — so we advise rather than reject (user decision
        2026-06-07). Sharing is collision-safe since the templates namespace
        cache keys and tables by service name."""
        comps = app.get("spec", {}).get("components", []) or []
        notes = []
        for btype, ref in (("redis", "cache:"), ("postgresql", "database:")):
            names = [c.get("name") for c in comps if c.get("type") == btype]
            if len(names) > 1:
                notes.append(f"advisory: {len(names)} {btype} components ({', '.join(names)}) - "
                             f"the frugal default is ONE shared instance referenced via `{ref}`; "
                             f"keep multiples only for deliberate isolation")
        return "\n".join(notes) or None

    @staticmethod
    def _with_advisory(result: "SubmitResult", advisory: str | None) -> "SubmitResult":
        if advisory and result.ok:
            return SubmitResult(ok=result.ok, commit_sha=result.commit_sha,
                                workflow_name=result.workflow_name,
                                message=f"{result.message}\n{advisory}")
        return result

    def _reconcile_apim_product(self, app: dict[str, Any],
                                result: "SubmitResult") -> "SubmitResult":
        """APIM-PRODUCT-1 (#161): after a successful submit, create/converge ONE
        APIM Developer-Portal product per OAM grouping all its external APIs.

        Purely additive and best-effort: it NEVER flips a successful submit to a
        failure (the per-service APIs + their validate-jwt are already in place; the
        product is a discovery layer). When no api ids are external, or no reconciler
        is wired, it is a silent no-op. Membership = _external_api_ids (incl. the
        always-external graphql-gateway). Day-0 ordering (product before svc/* APIs)
        is handled by the Job's skip-404 + the EVENT-2-sibling sensor."""
        if self.apim_products is None or not result.ok:
            return result
        api_ids = self._external_api_ids(app)
        if not api_ids:
            return result  # nothing external → no product needed
        app_name = app.get("metadata", {}).get("name", "")
        md = app.get("metadata", {}) or {}
        anns = md.get("annotations", {}) or {}
        display = anns.get("displayName") or app_name
        description = anns.get("description", "")
        try:
            ok, msg = self.apim_products.reconcile_product(
                app_name=app_name, api_ids=api_ids,
                display_name=display, description=description,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("APIM product reconcile failed for %s (non-fatal): %s",
                           app_name, e)
            return SubmitResult(ok=result.ok, commit_sha=result.commit_sha,
                                workflow_name=result.workflow_name,
                                message=f"{result.message}\n"
                                        f"note: APIM product step failed (non-fatal): {e}")
        return SubmitResult(ok=result.ok, commit_sha=result.commit_sha,
                            workflow_name=result.workflow_name,
                            message=f"{result.message}\n{msg}")

    def submit_wait(self, oam_yaml: str, requirements: str | None = None) -> SubmitResult:
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
            namespace = md.get("namespace", "default")
        except Exception as e:  # noqa: BLE001
            return SubmitResult(ok=False, message=f"invalid OAM Application YAML: {e}")

        # SPEC-1 (#173): same optional requirements handling as submit() (fail-fast).
        try:
            spec = self._prepare_requirements(requirements)
        except requirements_spec.RequirementsError as e:
            return SubmitResult(ok=False, message=f"invalid requirements: {e}")

        # GQL-1 (#155): same render-injection as submit() so the deferred path also
        # commits the authoritative explicit sources to the ledger.
        oam_yaml = self._inject_graphql_sources(app, namespace, oam_yaml)

        # External-by-default (user decision 2026-06-07): graphql-gateway and
        # realtime-service are inherently external-facing - auto-attach the
        # expose-api trait (APIM publication; websocket API type for realtime)
        # wired to the OAM's singleton identity. Runs BEFORE topology
        # validation so exposure=>identity is enforced on the result.
        oam_yaml = self._auto_expose_external_components(app, oam_yaml)

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

        # SPEC-1: commit the spec sibling to the ledger (best-effort), same as submit().
        self._commit_ledger_requirements(app_name, spec)

        scaffold = self._needs_scaffold(app)
        if scaffold is None or self.claims is None:
            # No scaffolding component (or no claim client): nothing to provision
            # imperatively. The OAM is committed to the ledger; once its CDs land
            # the consumer can re-run submit() to deliver. Report queued.
            return self._attach_spec_hash(SubmitResult(ok=True, commit_sha=sha,
                                message=(f"queued {app_name}; committed {sha}; OAM stored in "
                                         f"the gitops ledger — resubmit once its "
                                         f"ComponentDefinitions are available")), spec)

        # Same declarative provisioning as submit(): the claim/ArgoCD do the waiting.
        return self._attach_spec_hash(
            self._declarative_scaffold(app, app_name, scaffold, target_vcluster, oam_yaml, sha,
                                       spec), spec)

    # ----------------------------------------------------------------------
    # SPEC-1 (#173, dev-agent W1): REQUIREMENTS.md handling
    # ----------------------------------------------------------------------

    @staticmethod
    def _prepare_requirements(requirements: str | None) -> tuple[str, str] | None:
        """Decode → validate → normalize → hash the optional requirements blob.

        Returns (normalized_content, spec_hash) when requirements are supplied,
        or None when omitted (legacy behaviour). Raises
        requirements_spec.RequirementsError on malformed/empty content so the
        caller can fail fast BEFORE any commit."""
        if requirements is None or (isinstance(requirements, str) and not requirements.strip()):
            return None
        return requirements_spec.prepare(requirements)

    def _commit_ledger_requirements(self, app_name: str,
                                    spec: tuple[str, str] | None) -> None:
        """Commit the spec next to the OAM in the central gitops ledger as
        `oam/applications/<app>-REQUIREMENTS.md`. Best-effort (additive): a
        failure is logged, never raised — the OAM has already committed."""
        if spec is None:
            return
        content, shash = spec
        path = f"oam/applications/{app_name}-REQUIREMENTS.md"
        ok, _ = self.github.commit_file(
            path, content,
            message=f"spec: requirements for {app_name} ({shash})",
            branch=self.gitops_branch,
        )
        if not ok:
            logger.warning("SPEC-1: ledger requirements commit failed for %s "
                           "(non-fatal)", app_name)

    def _commit_monorepo_requirements(self, svc_repo: str,
                                      spec: tuple[str, str] | None) -> str:
        """Commit REQUIREMENTS.md at the app monorepo root. Idempotent: the
        github client fetches the existing blob sha and a PUT of identical
        content is a no-op update (same content => no churn). Returns a short
        message fragment for the SubmitResult. Best-effort: a missing repo
        (day-0) or transport error is reported, never raised."""
        if spec is None:
            return ""
        content, shash = spec
        try:
            ok, _ = self.github.commit_file(
                _SVC_REQUIREMENTS_PATH, content,
                message=f"spec: requirements ({shash}) (capability-mcp app.submit)",
                branch=self.gitops_branch, repo=svc_repo,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("SPEC-1: monorepo requirements commit raised for %s "
                           "(non-fatal): %s", svc_repo, e)
            return f"; spec {shash} (ledger only — monorepo commit errored)"
        if ok:
            return f"; spec {shash} -> {svc_repo}/{_SVC_REQUIREMENTS_PATH}"
        return f"; spec {shash} (ledger only — monorepo not ready yet)"

    @staticmethod
    def _attach_spec_hash(result: "SubmitResult",
                          spec: tuple[str, str] | None) -> "SubmitResult":
        """Thread the spec hash into the returned SubmitResult (the W3 trigger
        re-fire key). No-op when no requirements travelled with the submit."""
        if spec is None:
            return result
        result.spec_hash = spec[1]
        return result

    # ----------------------------------------------------------------------
    # Routing helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _is_exposed(c: dict[str, Any]) -> bool:
        """A webservice-class component is externally exposed iff it carries the
        `expose-api` trait OR sets `properties.exposeApi`. Factored out of
        _validate_identity_topology so the APIM-product membership helper
        (_external_api_ids) reuses the exact same predicate (APIM-PRODUCT-1 #161)."""
        for t in c.get("traits") or []:
            if t.get("type") == "expose-api":
                return True
        return bool((c.get("properties") or {}).get("exposeApi"))

    # Component types whose exposure is gated by the _is_exposed predicate.
    _EXPOSABLE_TYPES = ("webservice", "webservice-shape", "realtime-service")

    @classmethod
    def _external_api_ids(cls, app: dict[str, Any]) -> list[str]:
        """APIM-PRODUCT-1 (#161): authoritative external-API id set for an OAM.

        The product members = every webservice-class component carrying expose-api
        (the _is_exposed predicate) UNION every graphql-gateway component. The
        gateway is ALWAYS external (user decision 2026-06-07) — it is handled as a
        platform singleton and is deliberately NOT in _validate_identity_topology's
        `exposed` predicate, so it must be unioned in explicitly here or the gateway
        API would never become a product member.

        api-id == component name: the expose-api trait imports with
        `--api-id "$SVC_NAME"` where SVC_NAME == context.name (expose-api.yaml:168),
        and EVENT-2 uses the identical id. So the member id set IS the component-name
        set — no APIM lookup needed. Order-preserving, de-duplicated.

        NOTE membership uses the EXPOSED predicate, not the scaffold set
        (_webservice_services): a bring-your-own-image webservice is exposed but not
        scaffolded and is still a member.
        """
        comps = app.get("spec", {}).get("components", []) or []
        ids: list[str] = []
        for c in comps:
            ctype = c.get("type")
            name = c.get("name")
            if not name:
                continue
            is_external = (
                (ctype in cls._EXPOSABLE_TYPES and cls._is_exposed(c))
                or ctype == "graphql-gateway"  # always external (singleton)
            )
            if is_external and name not in ids:
                ids.append(name)
        return ids

    @staticmethod
    def _validate_identity_topology(app: dict[str, Any]) -> str | None:
        """Platform invariant: >=1 exposed webservice => exactly ONE identity
        component (type auth0-idp) authing all the OAM's APIs. Multiple identity
        components per OAM are always rejected. Returns an error string or None.
        """
        comps = app.get("spec", {}).get("components", []) or []
        identity_comps = [c.get("name") for c in comps if c.get("type") == "auth0-idp"]

        _is_exposed = SubmitUseCase._is_exposed

        exposed = [c.get("name") for c in comps
                   if c.get("type") in ("webservice", "webservice-shape", "realtime-service")
                   and _is_exposed(c)]

        if len(identity_comps) > 1:
            return ("identity topology: found %d identity components (%s) - an OAM must "
                    "have at most ONE; point every webservice's `identity:` ref and every "
                    "expose-api trait at the same component"
                    % (len(identity_comps), ", ".join(identity_comps)))
        if exposed and not identity_comps:
            return ("identity topology: components %s are externally exposed but the OAM "
                    "has no identity component - add ONE auth0-idp component and reference "
                    "it via `identity:` + expose-api(identity=...)" % ", ".join(exposed))

        # Singleton platform components (user invariant 2026-06-07, same class
        # as one-identity-per-OAM): an OAM declares at most ONE realtime-platform
        # and at most ONE graphql-gateway; every webservice REUSES it via its
        # `realtime:` ref / the gateway's sources list instead of declaring
        # another instance.
        for singleton_type, reuse_hint in (
            ("realtime-platform", "bind webservices to it via `realtime: <name>`"),
            ("graphql-gateway", "add upstream services to its `sources:` instead"),
        ):
            dupes = [c.get("name") for c in comps if c.get("type") == singleton_type]
            if len(dupes) > 1:
                return ("singleton topology: found %d %s components (%s) - an OAM must "
                        "declare at most ONE; %s"
                        % (len(dupes), singleton_type, ", ".join(dupes), reuse_hint))
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
            if comp.get("type") not in self._SCAFFOLD_TYPES:
                continue
            props = comp.get("properties") or {}
            lang = props.get("language")
            if not lang and comp.get("type") == "graphql-gateway":
                # GQL-1: gateway implementation language is a platform detail
                # (nodejs/Mesh) - consumers declare intent, default it instead
                # of skipping (caught patient7: gateway not scaffolded).
                lang = "nodejs"
            if not lang and comp.get("type") == "rasa-chatbot":
                # RASA-CONTAINER (#178): bot implementation language is a
                # platform detail — consumers declare intent only.
                lang = "rasa"
            if not lang and comp.get("type") == "camunda-orchestrator":
                # CAMUNDA-WORKFLOW: the workflow implementation (processes/*.bpmn +
                # workers/) is a platform-shaped variant — consumers declare intent
                # only; default the scaffold language to the camunda flavor.
                lang = "camunda"
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

    # RT-1 (#156): component types that trigger source-code scaffolding.
    # realtime-service is a fastapi variant (websocket+aiokafka) — it scaffolds
    # exactly like webservice but carries flavor:realtime (see _webservice_services).
    # RASA-CONTAINER (#178): rasa-chatbot scaffolds variant-only bot files
    # (domain/data/config/actions) into the monorepo on the prebaked rasa-base
    # image — routed through the claim path like every other scaffold type.
    # (Caught live: it previously fell through to the legacy oam-apply path.)
    # CAMUNDA-WORKFLOW: camunda-orchestrator scaffolds a variant-only workflow
    # repo (processes/*.bpmn + workers/ job-worker handlers) into the monorepo
    # on the prebaked zeebe-worker base image — same claim path as every other
    # scaffold type.
    _SCAFFOLD_TYPES = ("webservice", "graphql-gateway", "realtime-service",
                       "rasa-chatbot", "camunda-orchestrator")

    _FW_FOR_LANG = {"python": "fastapi", "java": "springboot",
                    "rasa": "chatbot", "nodejs": "graphql-gateway",
                    "camunda": "zeebe-worker"}

    @classmethod
    def _derive_framework(cls, lang: str, fw: str | None) -> str:
        """framework from language when unset/"auto" (single source of truth)."""
        if fw and fw != "auto":
            return fw
        return cls._FW_FOR_LANG.get(lang, "fastapi")

    # Component types that scaffold into the monorepo. webservice is the original
    # UNIFY-1 case; graphql-gateway (GQL-1 #155) is a nodejs/graphql-gateway shape
    # whose scaffold-claim was previously only emitted by its CD — but in the
    # app.submit monorepo flow the gateway never got a microservices/<name>/ folder
    # because the walk keyed on `type == "webservice"` only. Including it here
    # scaffolds the gateway zero-touch like every webservice (patient5 monorepo proof).

    @classmethod
    def _webservice_services(cls, app: dict[str, Any]) -> list[dict[str, str]]:
        """UNIFY-1 (#153) + GQL-1 (#155): derive services[] from EVERY scaffoldable
        component that needs scaffolding (language set, image absent/default). One
        AppContainerClaim per OAM ranges over this to emit one ApplicationClaim per
        service, all sharing the OAM-named repo (microservices/<name>/ per service).
        Backward compatible: a single-component OAM yields a one-element list.

        GQL-1: `type: graphql-gateway` components with `language: nodejs` are now
        included as `{language:"nodejs", framework:"graphql-gateway"}` so the gateway
        scaffolds into the monorepo exactly like a webservice (previously skipped).
        """
        services: list[dict[str, str]] = []
        for comp in app.get("spec", {}).get("components", []) or []:
            ctype = comp.get("type")
            if ctype not in cls._SCAFFOLD_TYPES:
                continue
            props = comp.get("properties") or {}
            lang = props.get("language")
            if not lang and comp.get("type") == "graphql-gateway":
                # GQL-1: gateway implementation language is a platform detail
                # (nodejs/Mesh) - consumers declare intent, default it instead
                # of skipping (caught patient7: gateway not scaffolded).
                lang = "nodejs"
            if not lang and comp.get("type") == "rasa-chatbot":
                # RASA-CONTAINER (#178): bot implementation language is a
                # platform detail — consumers declare intent only.
                lang = "rasa"
            if not lang and comp.get("type") == "camunda-orchestrator":
                # CAMUNDA-WORKFLOW: workflow (bpmn+workers) is a platform-shaped
                # variant — consumers declare intent only.
                lang = "camunda"
            if not lang:
                continue
            img = props.get("image", "")
            default_img = f"healthidpuaeacr.azurecr.io/{comp.get('name')}:latest"
            if img and img != default_img:
                continue  # bring-your-own image: not scaffolded
            entry: dict[str, str] = {
                "name": comp.get("name"),
                "language": lang,
                "framework": cls._derive_framework(lang, props.get("framework")),
            }
            # RT-1 (#156): realtime-service carries flavor:realtime so the
            # AppContainerClaim composition sets ApplicationClaim.serviceFlavor
            # and the mscv Job seeds the websocket+aiokafka fastapi variant.
            # RT-2: role selects WHICH realtime main.py the scaffold emits —
            # gateway (consume->ws), ingest (POST->produce), or processor
            # (consume->transform->produce). Defaults to gateway (RT-1 shape).
            if ctype == "realtime-service":
                entry["flavor"] = "realtime"
                role = str(props.get("role", "gateway")).strip() or "gateway"
                if role not in ("gateway", "ingest", "processor"):
                    role = "gateway"
                entry["role"] = role
            services.append(entry)
        return services

    @staticmethod
    def _inject_graphql_sources(app: dict[str, Any], namespace: str,
                                oam_yaml: str) -> str:
        """GQL-1 (#155): render-inject explicit `sources:` onto graphql-gateway
        components that omit them.

        app.submit is the only render stage that can see sibling components (the CD's
        CUE template only sees its own component's params). For each graphql-gateway
        component WITHOUT an explicit `sources:`, derive the list from the OAM's
        sibling webservice components:

            sources:
              - name: <svc>
                url:  http://<svc>.<ns>.svc.cluster.local
                specPath: /openapi.json

        This becomes the authoritative federated source list (pins exact in-cluster
        URLs, removes the cold-start race). The template's runtime kubectl+annotation
        discovery stays as the zero-config fallback when no sources are present.

        Mutates `app` in place and returns the re-serialised YAML when a change was
        made; otherwise returns the original `oam_yaml` untouched (no reformatting).
        """
        comps = app.get("spec", {}).get("components", []) or []
        gateways = [c for c in comps if c.get("type") == "graphql-gateway"]
        if not gateways:
            return oam_yaml

        webservice_names = [
            c.get("name") for c in comps
            if c.get("type") in ("webservice", "webservice-shape") and c.get("name")
        ]

        changed = False
        for gw in gateways:
            props = gw.setdefault("properties", {})
            if props.get("sources"):
                continue  # explicit sources already supplied — leave them authoritative
            if not webservice_names:
                continue  # nothing to federate; runtime fallback handles discovery
            props["sources"] = [
                {
                    "name": svc,
                    "url": f"http://{svc}.{namespace}.svc.cluster.local",
                    "specPath": "/openapi.json",
                }
                for svc in webservice_names
            ]
            changed = True

        return yaml.safe_dump(app, sort_keys=False) if changed else oam_yaml

    def _declarative_scaffold(self, app: dict[str, Any], app_name: str,
                              scaffold_comp: dict[str, Any],
                              target_vcluster: str | None, oam_yaml: str,
                              sha: str,
                              spec: tuple[str, str] | None = None) -> SubmitResult:
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
            # Stale-snapshot guard (2026-06-12): also refresh the claim's
            # spec.oamApplication with the OAM just committed. The gitops-setup
            # Job seeds from that snapshot; left at day-0 it clobbered these
            # update-path commits whenever the Job re-ran (rtdemo2). Best-effort
            # like reconcile_services — never fails the submit (the repo commit
            # above is already the durable truth).
            if self.claims is not None:
                try:
                    self.claims.update_oam_application(
                        name=app_name,
                        oam_application_b64=base64.b64encode(oam_yaml.encode()).decode(),
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning("oamApplication snapshot refresh failed for %s "
                                   "(non-fatal): %s", app_name, e)
            # SPEC-1: the monorepo exists on the update path — land REQUIREMENTS.md
            # at its root (idempotent; the github client no-ops an unchanged blob).
            spec_msg = self._commit_monorepo_requirements(svc_repo, spec)
            return SubmitResult(ok=True, commit_sha=svc_sha,
                                message=(f"updated {app_name}; committed {svc_sha} to "
                                         f"{svc_repo}/{_SVC_OAM_PATH}; ArgoCD will reconcile "
                                         f"(ledger {sha}){reconcile_msg}{spec_msg}"))

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
        # SPEC-1: on day-0 the monorepo doesn't exist yet (the composition creates
        # it asynchronously), so the spec lives in the central ledger for now and is
        # re-landed at the monorepo root on the next (update-path) submit. We still
        # attempt the monorepo commit best-effort in case the repo already exists.
        spec_msg = self._commit_monorepo_requirements(svc_repo, spec)
        return SubmitResult(ok=True, commit_sha=sha, workflow_name=app_name,
                            message=(f"submitted {app_name}; committed {sha}; {msg}; "
                                     f"composition will create {svc_repo} + seed OAM + "
                                     f"ArgoCD app + scaffold {svc_count} service(s) "
                                     f"(target={target_vcluster or 'host'}){spec_msg}"))

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
