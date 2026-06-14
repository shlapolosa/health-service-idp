"""app.delete use case — remove an OAM application's ENTIRE footprint and defeat
the GitOps recreation loop.

Why this is non-trivial (see the recreation-loop memory): deleting a single
resource is reversed in ~30s by a 7-layer cascade — ArgoCD app-of-apps selfHeal
resurrects the OAM Application, whose claims re-emit a Composition, whose Objects
re-create Jobs/namespaces. The ONLY teardown that holds is atomic and ordered:

  1. DISABLE ArgoCD auto-sync FIRST on every ArgoCD Application owning the app
     (patch spec.syncPolicy.automated = null). Without this, selfHeal undoes
     everything we delete below.
  2. Finalizer-patch ([]) + delete in the safe order:
       a. OAM Application  (core.oam.dev/applications/<app>) — stop re-emission
       b. AppContainerClaim — the recreation ROOT; delete BEFORE the leaf claims
       c. ApplicationClaim(s), then RealtimePlatformClaim / GraphqlPlatformClaim /
          WebhookPlatformClaim
       d. the ArgoCD Applications themselves
       e. the app's namespaces (<app>, <app>-*)
  3. NEVER touch the platform ArgoCD apps (platform-definitions / substrate-services)
     or any platform infra.

deletionPolicy:Orphan (W1) keeps the GitHub source + gitops repos: a delete does
NOT remove repositories. `purge_repos` is reserved for an explicit opt-in and is
NOT implemented here (the in-cluster client has no GitHub credential); when True
we surface a clear note rather than silently dropping the request.

Idempotent throughout — missing resources (404) are success. dry_run returns the
ordered plan without mutating anything.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from ..domain.models import DeleteResult
from ..infrastructure.k8s_claim_client import K8sClaimClient

logger = logging.getLogger(__name__)

# Platform-owned names that app.delete must NEVER tear down (guard).
_PROTECTED = frozenset({"platform-definitions", "substrate-services"})

# Claim CRs, in the recreation-safe delete order. appcontainerclaim is the ROOT
# (it re-emits ApplicationClaims via its composition) so it goes first.
_CLAIM_GROUP = "platform.example.org"
_CLAIM_VERSION = "v1alpha1"
_CLAIM_PLURALS = [
    "appcontainerclaims",        # recreation ROOT — delete before leaf claims
    "applicationclaims",
    "realtimeplatformclaims",
    "graphqlplatformclaims",
    "webhookplatformclaims",
]

# The OAM Application (re-emits claims when reconciled) — killed right after sync
# is disabled, before the claims.
_OAM_GROUP = "core.oam.dev"
_OAM_VERSION = "v1beta1"
_OAM_PLURAL = "applications"

# ArgoCD Application name suffixes app.submit / the composition create per app.
# Order doesn't matter for these (deleted last, after children are gone).
_ARGOCD_SUFFIXES = ["", "-oam", "-oam-application", "-app-of-apps"]


@dataclass
class DeleteAppUseCase:
    """app.delete(name) — remove the full footprint of OAM application `name`.

    The k8s client is injected (onion: this layer owns orchestration/ordering,
    the client owns transport). Construct with a fake client in unit tests.
    """

    claims: K8sClaimClient
    claim_namespace: str = "default"
    argocd_namespace: str = "argocd"

    def delete(self, app_name: str, purge_repos: bool = False,
               dry_run: bool = False) -> DeleteResult:
        name = (app_name or "").strip()
        if not name:
            return DeleteResult(ok=False, message="app_name required")
        if name in _PROTECTED:
            return DeleteResult(
                ok=False, app_name=name,
                message=f"refusing to delete protected platform app '{name}'",
            )

        argocd_apps = self._discover_argocd_apps(name)
        oam_targets = [(_OAM_GROUP, _OAM_VERSION, _OAM_PLURAL, name)]
        claim_targets = self._discover_claims(name)

        plan: list[str] = []
        plan += [f"disable-autosync ArgoCDApplication/{a}" for a in argocd_apps]
        plan += [f"Application/{n}" for _, _, _, n in oam_targets]
        plan += [f"{p}/{n}" for _, _, p, n in claim_targets]
        plan += [f"ArgoCDApplication/{a}" for a in argocd_apps]
        plan += [f"Namespace/{ns}" for ns in self.claims.list_namespaces(name)]

        if dry_run:
            return DeleteResult(
                ok=True, app_name=name, dry_run=True, purge_repos=purge_repos,
                planned=plan,
                message=f"dry-run: {len(plan)} action(s) planned for '{name}' "
                        f"(no changes made)",
            )

        result = DeleteResult(ok=True, app_name=name, purge_repos=purge_repos,
                              planned=plan)

        # STEP 1 — disable auto-sync on ALL ArgoCD apps FIRST (defeat selfHeal).
        for app in argocd_apps:
            if self.claims.disable_argocd_auto_sync(app, self.argocd_namespace):
                result.auto_sync_disabled.append(app)
            else:
                result.errors.append(f"could not disable auto-sync on {app}")

        # STEP 2 — finalizer-patch + delete in the recreation-safe order:
        #   OAM Application -> appcontainerclaim -> leaf claims -> ArgoCD apps.
        for g, v, p, n in oam_targets:
            self._delete_one(result, g, v, p, n)
        for g, v, p, n in claim_targets:
            self._delete_one(result, g, v, p, n)
        for app in argocd_apps:
            self._delete_one(result, "argoproj.io", "v1alpha1", "applications", app,
                             namespace=self.argocd_namespace)

        # STEP 3 — delete the app's namespaces (re-listed: composition may have
        # created more between plan and now; still idempotent).
        for ns in self.claims.list_namespaces(name):
            ok, msg = self.claims.delete_namespace(ns)
            (result.deleted if ok else result.errors).append(msg)

        if purge_repos:
            result.message = (
                "repos NOT purged: deletionPolicy:Orphan keeps the source + gitops "
                "repositories and the in-cluster client has no GitHub credential. "
                "Remove the repos manually if intended."
            )

        result.ok = not result.errors
        summary = (f"deleted {len(result.deleted)} resource(s) for '{name}'; "
                   f"auto-sync disabled on {len(result.auto_sync_disabled)} ArgoCD app(s)")
        result.message = (f"{summary}; {len(result.errors)} error(s)"
                          if result.errors else summary) + (
            f". {result.message}" if result.message else "")
        return result

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_argocd_apps(self, name: str) -> list[str]:
        """ArgoCD Applications owning `name`: the deterministic <name><suffix> set
        plus any live Application labelled for this app, minus protected platform
        apps. De-duplicated, never includes a protected name."""
        found: list[str] = []
        for suffix in _ARGOCD_SUFFIXES:
            cand = f"{name}{suffix}"
            if cand not in found:
                found.append(cand)
        # Label-discovered extras (app.submit / composition stamp these).
        for selector in (
            f"app.kubernetes.io/name={name}",
            f"app.oam.dev/name={name}",
            "app.kubernetes.io/managed-by=capability-mcp",
        ):
            for item in self.claims.list_namespaced_crs(
                "argoproj.io", "v1alpha1", "applications",
                self.argocd_namespace, label_selector=selector,
            ):
                n = (item.get("metadata") or {}).get("name")
                if not n:
                    continue
                labels = (item.get("metadata") or {}).get("labels") or {}
                # managed-by selector is broad: only keep if it belongs to this app.
                if selector.startswith("app.kubernetes.io/managed-by"):
                    if labels.get("app.kubernetes.io/name") != name and \
                       labels.get("app.oam.dev/name") != name and \
                       not (n == name or n.startswith(f"{name}-")):
                        continue
                if n not in found:
                    found.append(n)
        return [a for a in found if a not in _PROTECTED]

    def _discover_claims(self, name: str) -> list[tuple[str, str, str, str]]:
        """(group, version, plural, claim_name) tuples in delete order. For each
        claim kind we take the deterministically-named claim (== app name) plus any
        labelled/prefixed claim, preserving the ROOT-first plural ordering."""
        targets: list[tuple[str, str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for plural in _CLAIM_PLURALS:
            names: list[str] = [name]  # deterministic name == app name (may 404; fine)
            for item in self.claims.list_namespaced_crs(
                _CLAIM_GROUP, _CLAIM_VERSION, plural, self.claim_namespace,
            ):
                n = (item.get("metadata") or {}).get("name")
                if n and (n == name or n.startswith(f"{name}-")):
                    names.append(n)
            for n in names:
                key = (plural, n)
                if key in seen:
                    continue
                seen.add(key)
                targets.append((_CLAIM_GROUP, _CLAIM_VERSION, plural, n))
        return targets

    # ------------------------------------------------------------------

    def _delete_one(self, result: DeleteResult, group: str, version: str,
                    plural: str, name: str, namespace: str | None = None) -> None:
        ok, msg = self.claims.delete_cr(
            group, version, plural, name,
            namespace=namespace or self.claim_namespace,
        )
        (result.deleted if ok else result.errors).append(msg)
