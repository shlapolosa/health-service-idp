"""Connectivity recipes loader.

Reads `capability-factory/connectivity-recipes/recipes.yaml` (baked into the container by the
existing `COPY capability-factory/ /capability-factory/` Dockerfile step). Exposes the recipes
as queryable data for the architect's Phase 5 SYNTHESISE step — so the LLM can pick from a
pre-approved set instead of inventing wiring patterns.

The recipes.yaml schema (authored by P8.5):
  recipes:
    - id: <kebab-case>
      triggers:
        and?: [...]
        composite?: { contains: [<category>, <category>] }
        kb_profile?: ...
      emit: [<trait_yaml_path>, ...]
      docs: |
        Free-text explanation for the ADR
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_REL_PATH = "connectivity-recipes/recipes.yaml"


class RecipesLoader:
    def __init__(self, capability_factory_dir: str | None = None):
        root = capability_factory_dir or os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory")
        self.path = Path(root) / _REL_PATH
        self._cache: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if self._cache is not None:
            return self._cache
        if not self.path.is_file():
            logger.warning("recipes_loader: %s missing on disk", self.path)
            self._cache = []
            return self._cache
        try:
            doc = yaml.safe_load(self.path.read_text()) or {}
        except yaml.YAMLError as e:  # noqa: BLE001
            logger.error("recipes_loader: parse error on %s: %s", self.path, e)
            self._cache = []
            return self._cache
        self._cache = list(doc.get("recipes", []) or [])
        return self._cache

    def list_recipes(self) -> list[dict[str, Any]]:
        return self._load()

    def recipes_for(self, category_a: str | None = None,
                    category_b: str | None = None) -> list[dict[str, Any]]:
        """Filter recipes by composite component categories.

        Both args optional. If both provided, returns recipes whose composite.contains is a
        superset of {category_a, category_b}. If one provided, returns recipes whose triggers
        mention that category anywhere. If neither, returns all recipes.
        """
        recipes = self._load()
        if not category_a and not category_b:
            return recipes
        wanted = {c for c in (category_a, category_b) if c}
        matches: list[dict[str, Any]] = []
        for r in recipes:
            triggers = r.get("triggers", {}) or {}
            categories: set[str] = set()
            composite = triggers.get("composite", {}) or {}
            for c in composite.get("contains", []) or []:
                categories.add(c)
            and_clause = triggers.get("and", []) or []
            for cond in and_clause:
                if isinstance(cond, dict) and "category" in cond:
                    categories.add(cond["category"])
            if wanted.issubset(categories) if len(wanted) == 2 else (wanted & categories):
                matches.append(r)
        return matches
