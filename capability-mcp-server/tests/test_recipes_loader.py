"""Unit tests for connectivity recipes loader."""
import textwrap

import pytest

from src.infrastructure.recipes_loader import RecipesLoader


@pytest.fixture
def recipes_dir(tmp_path):
    root = tmp_path / "capability-factory"
    (root / "connectivity-recipes").mkdir(parents=True)
    (root / "connectivity-recipes" / "recipes.yaml").write_text(textwrap.dedent("""
        recipes:
          - id: web-service-exposed
            triggers:
              and:
                - { category: compute-service }
                - { qa: { exposure: public } }
            emit: [oam/traits/expose-https.yaml]
            docs: |
              Public compute services get HTTPS termination.
          - id: web-service-needs-db
            triggers:
              composite:
                contains: [compute-service, datastore]
            emit: [oam/traits/datastore-secret-binding.yaml]
            docs: |
              DB connection string binding.
          - id: producer-needs-broker
            triggers:
              composite:
                contains: [compute-service, messaging]
            emit: [oam/traits/broker-producer-binding.yaml]
            docs: |
              BROKER_URL env vars.
    """))
    return root


def test_list_returns_all(recipes_dir):
    loader = RecipesLoader(str(recipes_dir))
    recipes = loader.list_recipes()
    assert len(recipes) == 3
    assert {r["id"] for r in recipes} == {
        "web-service-exposed", "web-service-needs-db", "producer-needs-broker"}


def test_filter_by_composite_pair(recipes_dir):
    loader = RecipesLoader(str(recipes_dir))
    matches = loader.recipes_for("compute-service", "datastore")
    assert len(matches) == 1
    assert matches[0]["id"] == "web-service-needs-db"


def test_filter_by_single_category(recipes_dir):
    loader = RecipesLoader(str(recipes_dir))
    matches = loader.recipes_for("compute-service")
    # All 3 mention compute-service somewhere
    assert len(matches) == 3


def test_filter_by_unknown_category(recipes_dir):
    loader = RecipesLoader(str(recipes_dir))
    matches = loader.recipes_for("nonexistent-category")
    assert matches == []


def test_no_filter_returns_all(recipes_dir):
    loader = RecipesLoader(str(recipes_dir))
    assert len(loader.recipes_for()) == 3


def test_missing_file_returns_empty(tmp_path):
    loader = RecipesLoader(str(tmp_path / "nonexistent"))
    assert loader.list_recipes() == []
    assert loader.recipes_for("a", "b") == []
