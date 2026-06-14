"""Unit tests for app.delete — full-footprint teardown that defeats the GitOps
recreation loop. The fake k8s client records the ORDER of every mutation so we can
assert the recreation-safe invariants:

  - auto-sync is disabled on every ArgoCD app BEFORE any delete
  - the appcontainerclaim (recreation root) is deleted before leaf claims
  - protected platform apps are refused
  - missing resources (404) are idempotent
  - dry_run mutates nothing
"""
from __future__ import annotations

from src.application.delete_use_case import DeleteAppUseCase


class FakeClaims:
    """Records an ordered call log; lets tests inject 404s and discovered CRs."""

    def __init__(self, namespaces=None, claims_by_plural=None,
                 argocd_items=None, not_found=None):
        self.log: list[tuple[str, str]] = []           # (op, "plural/name")
        self._namespaces = namespaces or []
        self._claims_by_plural = claims_by_plural or {}  # plural -> [name, ...]
        self._argocd_items = argocd_items or []          # list of {metadata:{name,labels}}
        self._not_found = set(not_found or [])           # "plural/name" that 404 on delete

    # --- discovery ---
    def list_namespaces(self, prefix):
        return [n for n in self._namespaces
                if n == prefix or n.startswith(f"{prefix}-")]

    def list_namespaced_crs(self, group, version, plural, namespace, label_selector=None):
        if plural == "applications" and group == "argoproj.io":
            return self._argocd_items
        return [{"metadata": {"name": n}} for n in self._claims_by_plural.get(plural, [])]

    # --- mutations (logged) ---
    def disable_argocd_auto_sync(self, name, argocd_namespace="argocd"):
        self.log.append(("disable_autosync", f"applications/{name}"))
        return True

    def delete_cr(self, group, version, plural, name, namespace, argocd=False):
        key = f"{plural}/{name}"
        self.log.append(("delete", key))
        if key in self._not_found:
            return True, f"{key} already gone"
        return True, f"deleted {key}"

    def delete_namespace(self, name):
        self.log.append(("delete_ns", f"namespace/{name}"))
        return True, f"deleted namespace/{name}"

    # convenience views
    def ops(self, kind):
        return [k for op, k in self.log if op == kind]

    def first_index(self, predicate):
        for i, (op, k) in enumerate(self.log):
            if predicate(op, k):
                return i
        return -1


def test_autosync_disabled_before_any_delete():
    fc = FakeClaims(namespaces=["myapp", "myapp-rt"])
    r = DeleteAppUseCase(fc).delete("myapp")
    assert r.ok
    first_disable = fc.first_index(lambda op, k: op == "disable_autosync")
    first_delete = fc.first_index(lambda op, k: op in ("delete", "delete_ns"))
    assert first_disable != -1 and first_delete != -1
    assert first_disable < first_delete, "auto-sync must be disabled before any delete"
    assert "myapp" in r.auto_sync_disabled


def test_appcontainerclaim_deleted_before_leaf_claims():
    fc = FakeClaims(claims_by_plural={
        "appcontainerclaims": ["myapp"],
        "applicationclaims": ["myapp", "myapp-api"],
        "realtimeplatformclaims": ["myapp"],
    })
    DeleteAppUseCase(fc).delete("myapp")
    deletes = fc.ops("delete")
    acc = next(i for i, k in enumerate(deletes) if k.startswith("appcontainerclaims/"))
    leaf = next(i for i, k in enumerate(deletes) if k.startswith("applicationclaims/"))
    rt = next(i for i, k in enumerate(deletes) if k.startswith("realtimeplatformclaims/"))
    assert acc < leaf, "appcontainerclaim (recreation root) must precede applicationclaims"
    assert acc < rt, "appcontainerclaim must precede realtimeplatformclaims"


def test_oam_application_deleted_before_claims():
    fc = FakeClaims(claims_by_plural={"appcontainerclaims": ["myapp"]})
    DeleteAppUseCase(fc).delete("myapp")
    deletes = fc.ops("delete")
    oam = next(i for i, k in enumerate(deletes) if k.startswith("applications/myapp"))
    acc = next(i for i, k in enumerate(deletes) if k.startswith("appcontainerclaims/"))
    assert oam < acc, "OAM Application must be deleted before its claims"


def test_platform_app_guard():
    fc = FakeClaims()
    for protected in ("platform-definitions", "substrate-services"):
        r = DeleteAppUseCase(fc).delete(protected)
        assert not r.ok
        assert "protected" in r.message
    assert fc.log == [], "guard must short-circuit before any cluster call"


def test_empty_name_rejected():
    r = DeleteAppUseCase(FakeClaims()).delete("   ")
    assert not r.ok and "required" in r.message


def test_idempotent_when_resources_missing():
    # Every delete 404s; result must still be ok (already gone == success).
    fc = FakeClaims(
        claims_by_plural={"appcontainerclaims": ["myapp"]},
        not_found={"applications/myapp", "appcontainerclaims/myapp"},
    )
    r = DeleteAppUseCase(fc).delete("myapp")
    assert r.ok and not r.errors
    assert any("already gone" in d for d in r.deleted)


def test_dry_run_mutates_nothing():
    fc = FakeClaims(namespaces=["myapp"], claims_by_plural={"appcontainerclaims": ["myapp"]})
    r = DeleteAppUseCase(fc).delete("myapp", dry_run=True)
    assert r.ok and r.dry_run
    assert fc.log == [], "dry_run must not call any mutating client method"
    assert r.planned, "dry_run must surface the ordered plan"
    # plan order mirrors execution: disable-autosync first, namespace last.
    assert r.planned[0].startswith("disable-autosync")
    assert r.planned[-1].startswith("Namespace/")


def test_argocd_apps_discovered_by_suffix_and_label_minus_protected():
    # A labelled extra ArgoCD app + the deterministic suffix set; platform apps excluded.
    fc = FakeClaims(argocd_items=[
        {"metadata": {"name": "myapp-extra-app",
                      "labels": {"app.oam.dev/name": "myapp"}}},
        {"metadata": {"name": "platform-definitions",
                      "labels": {"app.kubernetes.io/managed-by": "capability-mcp"}}},
    ])
    r = DeleteAppUseCase(fc).delete("myapp", dry_run=True)
    disabled = [p for p in r.planned if p.startswith("disable-autosync")]
    names = {p.split("/")[-1] for p in disabled}
    assert "myapp" in names and "myapp-oam" in names and "myapp-extra-app" in names
    assert "platform-definitions" not in names, "protected app must never be targeted"


def test_purge_repos_surfaces_orphan_note():
    fc = FakeClaims()
    r = DeleteAppUseCase(fc).delete("myapp", purge_repos=True)
    assert r.ok and r.purge_repos
    assert "repos NOT purged" in r.message and "Orphan" in r.message
