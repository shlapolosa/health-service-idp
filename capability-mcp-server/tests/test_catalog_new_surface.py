"""Unit tests for the 6 new catalog use cases (traits / policies / workflow-steps / recipes)
+ the enriched describe/scaffold behaviour."""
import textwrap
from unittest.mock import MagicMock

import pytest

from src.application.catalog_use_cases import CatalogUseCases
from src.infrastructure.recipes_loader import RecipesLoader


@pytest.fixture
def fake_vela():
    v = MagicMock()
    # Default: empty parameter rows; override per-test as needed
    v.render_schema.return_value = []
    v.render_trait_schema = v.render_schema
    return v


@pytest.fixture
def fake_scorer():
    return MagicMock()


@pytest.fixture
def recipes(tmp_path):
    root = tmp_path / "capability-factory"
    (root / "connectivity-recipes").mkdir(parents=True)
    (root / "connectivity-recipes" / "recipes.yaml").write_text(textwrap.dedent("""
        recipes:
          - id: web-service-needs-db
            triggers:
              composite:
                contains: [compute-service, datastore]
            emit: [oam/traits/datastore-secret-binding.yaml]
            docs: |
              DB binding.
    """))
    return RecipesLoader(str(root))


def test_describe_enriches_with_applicable_traits(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add("webservice")
    fake_k8s.add_trait("autoscaler", applies=["webservice", "tfjob"])
    fake_k8s.add_trait("ingress", applies=["webservice"])
    fake_k8s.add_trait("affinity", applies=[])  # vanilla, applies to anything
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)

    meta = uc.describe("webservice")
    trait_names = {t["name"] for t in meta["applicable_traits"]}
    assert trait_names == {"autoscaler", "ingress"}
    assert meta["description_completeness"] == "none"  # no params


def test_describe_completeness_full(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add("webservice")
    fake_vela.render_schema.return_value = [
        {"name": "image", "description": "Image to deploy", "type": "string",
         "required": True, "default": ""},
        {"name": "port", "description": "Listen port", "type": "int",
         "required": False, "default": "8080"},
    ]
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    meta = uc.describe("webservice")
    assert meta["description_completeness"] == "full"


def test_describe_completeness_partial(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add("webservice")
    fake_vela.render_schema.return_value = [
        {"name": "image", "description": "Image to deploy", "type": "string",
         "required": True, "default": ""},
        {"name": "port", "description": "", "type": "int", "required": False, "default": "8080"},
    ]
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    assert uc.describe("webservice")["description_completeness"] == "partial"


def test_scaffold_with_traits(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add("webservice")
    fake_k8s.add_trait("autoscaler", applies=["webservice"])
    fake_vela.render_schema.side_effect = lambda name: {
        "webservice": [{"name": "image", "description": "", "type": "string",
                        "required": True, "default": ""}],
        "autoscaler": [{"name": "minReplicas", "description": "", "type": "int",
                        "required": True, "default": ""}],
    }.get(name, [])
    fake_vela.render_trait_schema = fake_vela.render_schema
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    out = uc.scaffold("webservice", "my-app", with_traits=True)
    assert "traits:" in out
    assert "autoscaler" in out
    assert "minReplicas" in out


def test_traits_for_filters_by_applicability(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_trait("autoscaler", applies=["webservice", "tfjob"])
    fake_k8s.add_trait("ingress", applies=["webservice"])
    fake_k8s.add_trait("kafka-consumer", applies=["webservice"])
    fake_k8s.add_trait("affinity", applies=[])  # not applicable to anything specific
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    out = uc.traits_for("webservice")
    assert {t["name"] for t in out} == {"autoscaler", "ingress", "kafka-consumer"}
    out_tfjob = uc.traits_for("tfjob")
    assert {t["name"] for t in out_tfjob} == {"autoscaler"}


def test_traits_for_includes_wildcard_traits(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_trait("autoscaler", applies=["webservice"])
    fake_k8s.add_trait("annotations", applies=["*"])
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    out = uc.traits_for("webservice")
    assert {t["name"] for t in out} == {"autoscaler", "annotations"}


def test_list_traits_returns_rich_dicts(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_trait("autoscaler", applies=["webservice"], description="HPA")
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    out = uc.list_traits()
    assert len(out) == 1
    assert out[0]["name"] == "autoscaler"
    assert out[0]["appliesToWorkloads"] == ["webservice"]
    assert out[0]["description"] == "HPA"


def test_describe_trait_includes_parameters(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_trait("autoscaler", applies=["webservice"])
    fake_vela.render_schema.return_value = [
        {"name": "minReplicas", "description": "", "type": "int",
         "required": True, "default": ""},
    ]
    fake_vela.render_trait_schema = fake_vela.render_schema
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    meta = uc.describe_trait("autoscaler")
    assert meta["name"] == "autoscaler"
    assert meta["appliesToWorkloads"] == ["webservice"]
    assert meta["parameters"][0]["name"] == "minReplicas"


def test_describe_policy_parses_cue_template(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_policy("topology", cue_template=textwrap.dedent("""
        parameter: {
          // +usage=clusters to target
          clusters?: [...string]
          // +usage=target namespace
          namespace?: string
        }
    """))
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    meta = uc.describe_policy("topology")
    names = {p["name"] for p in meta["parameters"]}
    assert names == {"clusters", "namespace"}


def test_describe_workflow_step_parses_cue_template(fake_k8s, fake_vela, fake_scorer):
    fake_k8s.add_workflow_step("apply-application", cue_template=textwrap.dedent("""
        parameter: {
          // +usage=parallelism
          parallelism?: *5 | int
        }
    """))
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)
    meta = uc.describe_workflow_step("apply-application")
    assert meta["parameters"][0]["name"] == "parallelism"
    assert meta["parameters"][0]["default"] == "5"


def test_connectivity_recipes_no_loader_returns_empty(fake_k8s, fake_vela, fake_scorer):
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer)  # no recipes arg
    assert uc.connectivity_recipes() == []


def test_connectivity_recipes_filters(fake_k8s, fake_vela, fake_scorer, recipes):
    uc = CatalogUseCases(fake_k8s, fake_vela, fake_scorer, recipes=recipes)
    out = uc.connectivity_recipes("compute-service", "datastore")
    assert len(out) == 1
    assert out[0]["id"] == "web-service-needs-db"
