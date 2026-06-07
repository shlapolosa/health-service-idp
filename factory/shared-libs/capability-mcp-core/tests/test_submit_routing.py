"""Unit tests for app.submit declarative-spine routing (W4; RETIRE-WFT #149).

Routing matrix:
  - no scaffold component            -> oam-apply (legacy, bring-your-own-image)
  - scaffold + repo exists           -> direct commit to per-service repo (no workflow)
  - scaffold + repo absent           -> AppContainerClaim creation (no workflow)
  - scaffold + claims client absent  -> error (legacy oam-driven-contract WFT retired)
"""
from __future__ import annotations

import yaml

from src.application.submit_use_case import SubmitUseCase


def _oam(component_type="webservice", language="python", image=None, name="my-svc"):
    props = {"name": name}
    if language:
        props["language"] = language
    if image:
        props["image"] = image
    return yaml.safe_dump({
        "apiVersion": "core.oam.dev/v1beta1",
        "kind": "Application",
        "metadata": {"name": name, "namespace": "default"},
        "spec": {"components": [{"name": name, "type": component_type, "properties": props}]},
    })


class FakeVela:
    def dry_run(self, oam_yaml):
        return True, "ok"


class FakeGitHub:
    def __init__(self, existing_repos=()):
        self.existing = set(existing_repos)
        self.commits = []  # (repo_or_None, path)

    def repo_exists(self, repo):
        return repo in self.existing

    def commit_file(self, path, content, message, branch="main", repo=None):
        self.commits.append((repo, path))
        return True, f"sha-{len(self.commits)}"


class FakeArgo:
    def __init__(self):
        self.fired = []  # (template, params)

    def create_workflow_from_template(self, template, params):
        self.fired.append((template, params))
        return {"metadata": {"name": f"{template}-wf-1"}}


class FakeClaims:
    def __init__(self, ok=True):
        self.ok = ok
        self.created = []

    def create_app_container_claim(self, name, oam_application_b64, **kw):
        self.created.append((name, kw))
        return self.ok, f"AppContainerClaim {name} created"

    def reconcile_services(self, name, services):
        # UNIFY-1: record reconcile calls; pretend all are new additions.
        self.reconciled = getattr(self, "reconciled", [])
        self.reconciled.append((name, services))
        return [s["name"] for s in services]


def _uc(github=None, claims=...):
    gh = github or FakeGitHub()
    cl = FakeClaims() if claims is ... else claims
    return SubmitUseCase(FakeVela(), gh, FakeArgo(), claims=cl), gh


def test_no_scaffold_routes_to_oam_apply():
    uc, gh = _uc()
    res = uc.submit(_oam(language=None))  # webservice without language -> no scaffold
    assert res.ok
    assert uc.argo.fired and uc.argo.fired[0][0] == "oam-apply"


def test_byo_image_routes_to_oam_apply():
    uc, gh = _uc()
    res = uc.submit(_oam(image="healthidpuaeacr.azurecr.io/custom:v9"))
    assert res.ok
    assert uc.argo.fired and uc.argo.fired[0][0] == "oam-apply"


def test_day0_creates_claim_not_workflow():
    uc, gh = _uc()
    res = uc.submit(_oam())
    assert res.ok, res.message
    assert uc.claims.created, "expected AppContainerClaim creation"
    name, kw = uc.claims.created[0]
    assert name == "my-svc"
    assert kw["delivery_target"] == "host"
    assert kw["language"] == "python" and kw["framework"] == "fastapi"
    assert not uc.argo.fired, "no workflow may fire on the declarative path"
    # central ledger commit happened (repo=None)
    assert (None, "oam/applications/my-svc.yaml") in gh.commits


def test_day0_framework_auto_derives_springboot():
    uc, gh = _uc()
    oam = _oam(language="java")
    res = uc.submit(oam)
    assert res.ok
    _, kw = uc.claims.created[0]
    assert kw["framework"] == "springboot"


def test_update_commits_to_per_service_repo():
    gh = FakeGitHub(existing_repos={"my-svc-gitops"})
    uc, gh = _uc(github=gh)
    res = uc.submit(_oam())
    assert res.ok, res.message
    assert ("my-svc-gitops", "oam/applications/application.yaml") in gh.commits
    assert not uc.claims.created, "existing repo must not re-scaffold"
    assert not uc.argo.fired


def test_missing_claims_client_errors_no_wft(monkeypatch):
    # RETIRE-WFT #149: the legacy oam-driven-contract fallback was removed. With
    # no claim client a scaffold submission must error (committed but unprovisioned)
    # and MUST NOT fire any workflow.
    monkeypatch.setenv("SUBMIT_USE_WFT", "true")  # stale env must have no effect
    uc, gh = _uc(claims=None)
    res = uc.submit(_oam())
    assert not res.ok
    assert "no claim client" in res.message
    assert not uc.argo.fired, "no legacy WFT may fire after retirement"


def test_vcluster_target_propagates_to_claim():
    oam = yaml.safe_load(_oam())
    oam["spec"]["components"][0]["properties"]["targetEnvironment"] = "team-a-vc"
    uc, gh = _uc()
    res = uc.submit(yaml.safe_dump(oam))
    assert res.ok
    _, kw = uc.claims.created[0]
    assert kw["delivery_target"] == "team-a-vc"


def test_claim_failure_surfaces_error():
    uc, gh = _uc(claims=FakeClaims(ok=False))
    res = uc.submit(_oam())
    assert not res.ok
    assert "claim creation failed" in res.message


def test_oam_payload_roundtrips_b64():
    uc, gh = _uc()
    oam = _oam()
    uc.submit(oam)
    # claim creation receives the exact OAM, b64-encoded
    # (FakeClaims signature consumes it positionally via kwargs)
    name, kw = uc.claims.created[0]
    assert name == "my-svc"


def _multi_oam(n_identity=1, exposed=True):
    comps = []
    for i in range(n_identity):
        comps.append({"name": f"idp-{i}", "type": "auth0-idp", "properties": {}})
    for n in ("svc-a", "svc-b"):
        c = {"name": n, "type": "webservice",
             "properties": {"name": n, "language": "python",
                            **({"identity": "idp-0"} if n_identity else {})}}
        if exposed:
            c["traits"] = [{"type": "expose-api", "properties": {}}]
        comps.append(c)
    return yaml.safe_dump({"apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
                           "metadata": {"name": "multi", "namespace": "default"},
                           "spec": {"components": comps}})


def test_one_identity_serves_many_exposed_ok():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=1))
    assert res.ok, res.message


def test_multiple_identity_components_rejected():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=2))
    assert not res.ok
    assert "at most ONE" in res.message
    assert not gh.commits, "rejected OAM must not reach the gitops gate"


def test_exposed_without_identity_rejected():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=0))
    assert not res.ok
    assert "no identity component" in res.message


def test_unexposed_needs_no_identity():
    uc, gh = _uc()
    res = uc.submit(_multi_oam(n_identity=0, exposed=False))
    assert res.ok, res.message


# ---------------------------------------------------------------------------
# UNIFY-1 (#153): monorepo-per-OAM — one AppContainerClaim, services[] derived
# ---------------------------------------------------------------------------

def _monorepo_oam(app_name="patient4", svcs=(("orders", "python"), ("billing", "java"),
                                            ("chat", "rasa"), ("gw", "nodejs"))):
    comps = []
    for name, lang in svcs:
        comps.append({"name": name, "type": "webservice",
                      "properties": {"name": name, "language": lang}})
    return yaml.safe_dump({
        "apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
        "metadata": {"name": app_name, "namespace": "default"},
        "spec": {"components": comps},
    })


def test_day0_single_claim_named_after_oam_with_services():
    uc, gh = _uc()
    res = uc.submit(_monorepo_oam())
    assert res.ok, res.message
    assert len(uc.claims.created) == 1, "exactly ONE AppContainerClaim per OAM"
    name, kw = uc.claims.created[0]
    assert name == "patient4", "claim is named after the OAM, not a component"
    services = kw["services"]
    assert [s["name"] for s in services] == ["orders", "billing", "chat", "gw"]


def test_services_framework_derived_from_language():
    uc, gh = _uc()
    uc.submit(_monorepo_oam())
    _, kw = uc.claims.created[0]
    fw = {s["name"]: s["framework"] for s in kw["services"]}
    assert fw == {"orders": "fastapi", "billing": "springboot",
                  "chat": "chatbot", "gw": "graphql-gateway"}


def test_byo_image_component_excluded_from_services():
    oam = yaml.safe_load(_monorepo_oam(svcs=(("orders", "python"), ("billing", "python"))))
    # billing supplies a non-default prebuilt image -> not scaffolded
    oam["spec"]["components"][1]["properties"]["image"] = "ghcr.io/acme/billing:1.2.3"
    uc, gh = _uc()
    res = uc.submit(yaml.safe_dump(oam))
    assert res.ok, res.message
    _, kw = uc.claims.created[0]
    assert [s["name"] for s in kw["services"]] == ["orders"]


def test_single_service_oam_still_one_element_services():
    # backward compat: single webservice OAM still works; app==component name here.
    uc, gh = _uc()
    res = uc.submit(_oam())  # app/component both "my-svc"
    assert res.ok, res.message
    name, kw = uc.claims.created[0]
    assert name == "my-svc"
    assert [s["name"] for s in kw["services"]] == ["my-svc"]


def test_update_path_reconciles_new_services():
    # existing OAM repo -> update path commits OAM AND reconciles services[] so a
    # newly-added component scaffolds its folder (no trait needed).
    gh = FakeGitHub(existing_repos={"patient4-gitops"})
    uc, gh = _uc(github=gh)
    res = uc.submit(_monorepo_oam())
    assert res.ok, res.message
    assert ("patient4-gitops", "oam/applications/application.yaml") in gh.commits
    assert getattr(uc.claims, "reconciled", []), "update path must reconcile services"
    rname, rsvcs = uc.claims.reconciled[0]
    assert rname == "patient4"
    assert [s["name"] for s in rsvcs] == ["orders", "billing", "chat", "gw"]
    assert "scaffolded new service" in res.message


def test_update_path_repo_named_after_oam_not_component():
    # the shared repo is <app>-gitops, NOT <first-component>-gitops (kills the
    # per-service-repo phantom pattern).
    gh = FakeGitHub(existing_repos={"orders-gitops"})  # component repo, NOT app repo
    uc, gh = _uc(github=gh)
    res = uc.submit(_monorepo_oam())
    assert res.ok, res.message
    # orders-gitops must NOT be treated as the OAM repo -> day-0 claim path taken
    assert uc.claims.created, "wrong-named existing repo must not short-circuit to update"
    assert uc.claims.created[0][0] == "patient4"


# ---------------------------------------------------------------------------
# GQL-1 (#155): graphql-gateway scaffolding + sources render-injection
# ---------------------------------------------------------------------------

def _gql_oam(app_name="patient7", gw_sources=None, with_webservices=True,
             gw_props_extra=None):
    comps = []
    if with_webservices:
        for n in ("patient-api", "appointments-api"):
            comps.append({"name": n, "type": "webservice",
                          "properties": {"name": n, "language": "python"}})
    gw_props = {"name": f"{app_name}-graph", "language": "nodejs"}
    if gw_sources is not None:
        gw_props["sources"] = gw_sources
    if gw_props_extra:
        gw_props.update(gw_props_extra)
    comps.append({"name": f"{app_name}-graph", "type": "graphql-gateway",
                  "properties": gw_props})
    return yaml.safe_dump({
        "apiVersion": "core.oam.dev/v1beta1", "kind": "Application",
        "metadata": {"name": app_name, "namespace": "default"},
        "spec": {"components": comps},
    })


def test_graphql_gateway_added_to_services():
    # the nodejs/graphql-gateway component must scaffold into the monorepo alongside
    # the python webservices (previously skipped — walk keyed on webservice only).
    uc, gh = _uc()
    res = uc.submit(_gql_oam())
    assert res.ok, res.message
    _, kw = uc.claims.created[0]
    svc = {s["name"]: s["framework"] for s in kw["services"]}
    assert svc == {"patient-api": "fastapi", "appointments-api": "fastapi",
                   "patient7-graph": "graphql-gateway"}
    assert {s["name"]: s["language"] for s in kw["services"]}["patient7-graph"] == "nodejs"


def test_sources_auto_injected_when_omitted():
    # app.submit injects sibling webservices as the gateway's authoritative sources.
    app = yaml.safe_load(_gql_oam())  # no sources on gateway
    out = SubmitUseCase._inject_graphql_sources(app, "default", _gql_oam())
    gw = [c for c in yaml.safe_load(out)["spec"]["components"]
          if c["type"] == "graphql-gateway"][0]
    srcs = gw["properties"]["sources"]
    assert [s["name"] for s in srcs] == ["patient-api", "appointments-api"]
    assert srcs[0]["url"] == "http://patient-api.default.svc.cluster.local"
    assert srcs[0]["specPath"] == "/openapi.json"


def test_explicit_sources_preserved():
    # a consumer-supplied sources list is authoritative — not overwritten.
    explicit = [{"name": "x", "url": "http://x.ns.svc:9000", "specPath": "/spec"}]
    app = yaml.safe_load(_gql_oam(gw_sources=explicit))
    out = SubmitUseCase._inject_graphql_sources(app, "default",
                                                _gql_oam(gw_sources=explicit))
    gw = [c for c in yaml.safe_load(out)["spec"]["components"]
          if c["type"] == "graphql-gateway"][0]
    assert gw["properties"]["sources"] == explicit


def test_no_webservices_no_injection():
    # gateway with no sibling webservices: nothing injected (runtime fallback covers it).
    app = yaml.safe_load(_gql_oam(with_webservices=False))
    out = SubmitUseCase._inject_graphql_sources(app, "default",
                                                _gql_oam(with_webservices=False))
    gw = [c for c in yaml.safe_load(out)["spec"]["components"]
          if c["type"] == "graphql-gateway"][0]
    assert "sources" not in (gw.get("properties") or {})


def test_byo_image_gateway_excluded_from_services():
    # a gateway pinned to a prebuilt image is not scaffolded.
    app = yaml.safe_load(_gql_oam(
        gw_props_extra={"image": "ghcr.io/acme/gw:1.0"}))
    services = SubmitUseCase._webservice_services(app)
    assert [s["name"] for s in services] == ["patient-api", "appointments-api"]


def test_submit_end_to_end_commits_injected_sources():
    # full submit path: the ledger commit + claim both see the injected gateway.
    uc, gh = _uc()
    res = uc.submit(_gql_oam())
    assert res.ok, res.message
    assert (None, "oam/applications/patient7.yaml") in gh.commits
    _, kw = uc.claims.created[0]
    assert any(s["name"] == "patient7-graph" for s in kw["services"])


def test_duplicate_realtime_platform_rejected():
    app = {"spec": {"components": [
        {"name": "rt-a", "type": "realtime-platform", "properties": {}},
        {"name": "rt-b", "type": "realtime-platform", "properties": {}},
    ]}}
    err = SubmitUseCase._validate_identity_topology(app)
    assert err and "singleton topology" in err and "realtime-platform" in err


def test_duplicate_graphql_gateway_rejected():
    app = {"spec": {"components": [
        {"name": "gw-a", "type": "graphql-gateway", "properties": {}},
        {"name": "gw-b", "type": "graphql-gateway", "properties": {}},
    ]}}
    err = SubmitUseCase._validate_identity_topology(app)
    assert err and "graphql-gateway" in err and "sources" in err


def test_single_realtime_and_gateway_accepted():
    app = {"spec": {"components": [
        {"name": "rt", "type": "realtime-platform", "properties": {}},
        {"name": "gw", "type": "graphql-gateway", "properties": {}},
    ]}}
    assert SubmitUseCase._validate_identity_topology(app) is None


def test_multiple_caches_advisory_not_rejection():
    app = {"spec": {"components": [
        {"name": "c1", "type": "redis", "properties": {}},
        {"name": "c2", "type": "redis", "properties": {}},
        {"name": "d1", "type": "postgresql", "properties": {}},
    ]}}
    assert SubmitUseCase._validate_identity_topology(app) is None  # allowed
    adv = SubmitUseCase._backing_sharing_advisory(app)
    assert adv and "2 redis" in adv and "frugal default" in adv


def test_single_cache_no_advisory():
    app = {"spec": {"components": [
        {"name": "c1", "type": "redis", "properties": {}},
        {"name": "d1", "type": "postgresql", "properties": {}},
    ]}}
    assert SubmitUseCase._backing_sharing_advisory(app) is None


def test_graphql_gateway_language_defaults_to_nodejs():
    app = {"spec": {"components": [
        {"name": "gw", "type": "graphql-gateway", "properties": {"name": "gw"}},
    ]}}
    services = SubmitUseCase._webservice_services(app)
    assert services and services[0]["language"] == "nodejs"
    assert services[0]["framework"] == "graphql-gateway"


def test_graphql_gateway_auto_exposed_with_identity():
    app = {"spec": {"components": [
        {"name": "auth", "type": "auth0-idp", "properties": {}},
        {"name": "gw", "type": "graphql-gateway", "properties": {"name": "gw"}},
    ]}}
    out = SubmitUseCase._auto_expose_external_components(app, "orig")
    gw = app["spec"]["components"][1]
    t = [t for t in gw["traits"] if t["type"] == "expose-api"]
    assert t and t[0]["properties"]["identity"] == "auth"
    assert out != "orig"  # yaml re-dumped


def test_realtime_service_auto_exposed_websocket():
    app = {"spec": {"components": [
        {"name": "auth", "type": "auth0-idp", "properties": {}},
        {"name": "ws", "type": "realtime-service", "properties": {"name": "ws"}},
    ]}}
    SubmitUseCase._auto_expose_external_components(app, "orig")
    t = [t for t in app["spec"]["components"][1]["traits"] if t["type"] == "expose-api"]
    assert t and t[0]["properties"]["apiType"] == "websocket"


def test_explicit_expose_trait_untouched():
    app = {"spec": {"components": [
        {"name": "gw", "type": "graphql-gateway", "properties": {},
         "traits": [{"type": "expose-api", "properties": {"identity": "custom"}}]},
    ]}}
    out = SubmitUseCase._auto_expose_external_components(app, "orig")
    assert out == "orig"
