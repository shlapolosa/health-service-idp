"""Deterministic capability scorer — the reproducible core of `catalog.search`.

Loads the git-versioned `capability-factory/` tree (schema + weightings + kb) and scores each KB
candidate against a structured CapabilityRequest: hard-constraint filter, then weighted-distance soft
rank, tie-break on costClass then maturity. The LLM (architect agent) only writes the ADR narrative;
this scoring is what makes the recommendation reproducible. See docs/capability-quality-attributes-v0.md.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from ..domain.models import ScoredCandidate

logger = logging.getLogger(__name__)
_WEIGHT = {"high": 3, "med": 2, "low": 1}


class CapabilityScorer:
    def __init__(self, factory_dir: str | None = None):
        self.dir = Path(factory_dir or os.getenv("CAPABILITY_FACTORY_DIR", "/capability-factory"))
        self._schema: dict[str, Any] = {}
        self._weights: dict[str, Any] = {}
        self._kb: list[dict[str, Any]] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._schema = (yaml.safe_load((self.dir / "schema/quality-attributes-v0.yaml").read_text())
                        or {}).get("attributes", {})
        self._weights = (yaml.safe_load((self.dir / "weightings/category-defaults.yaml").read_text())
                         or {}).get("categories", {})
        self._kb = []
        kb_dir = self.dir / "kb"
        if kb_dir.is_dir():
            for f in sorted(kb_dir.glob("*.yaml")):
                doc = yaml.safe_load(f.read_text())
                if isinstance(doc, dict) and doc.get("technology"):
                    self._kb.append(doc)
        self._loaded = True

    # --- helpers ---
    def _rank(self, attr: str, value: Any) -> int | None:
        domain = self._schema.get(attr, {}).get("domain")
        if isinstance(domain, list) and value in domain:
            return domain.index(value)
        return None

    def _weight_for(self, category: str, attr: str, overrides: dict[str, Any]) -> int:
        if attr in overrides:                      # explicit per-request override
            return _WEIGHT.get(overrides[attr], int(overrides[attr]) if str(overrides[attr]).isdigit() else 1)
        cat = self._weights.get(category, {})
        for tier in ("high", "med", "low"):
            if attr in (cat.get(tier) or []):
                return _WEIGHT[tier]
        return 1                                   # scored but un-tiered → minimal weight

    @staticmethod
    def _req_parts(spec: Any) -> tuple[Any, bool, Any]:
        """Normalise a request attribute to (level, required, max)."""
        if isinstance(spec, dict):
            return spec.get("level"), bool(spec.get("required")), spec.get("max")
        return spec, False, None

    def _hard_ok(self, attr: str, req_level: Any, req_max: Any, offer: Any) -> bool:
        meta = self._schema.get(attr, {})
        t = meta.get("type")
        if req_max is not None:                    # numeric upper bound
            try:
                return float(offer) <= float(req_max)
            except (TypeError, ValueError):
                return False
        if t == "ordered-enum":
            ro, oo = self._rank(attr, req_level), self._rank(attr, offer)
            if ro is None or oo is None:
                return offer == req_level
            return oo >= ro if meta.get("better") == "higher" else oo <= ro
        return offer == req_level                  # unordered-enum / boolean → exact

    def _penalty(self, attr: str, req_level: Any, req_max: Any, offer: Any, weight: int) -> float:
        meta = self._schema.get(attr, {})
        t = meta.get("type")
        if req_max is not None:
            try:
                over = float(offer) - float(req_max)
                return weight * (over / max(float(req_max), 1.0)) if over > 0 else 0.0
            except (TypeError, ValueError):
                return float(weight)
        if t == "ordered-enum":
            ro, oo = self._rank(attr, req_level), self._rank(attr, offer)
            if ro is None or oo is None:
                return 0.0 if offer == req_level else float(weight)
            gap = (ro - oo) if meta.get("better") == "higher" else (oo - ro)
            return weight * gap if gap > 0 else 0.0  # only under-provision penalised
        return 0.0 if offer == req_level else float(weight)

    def score(self, request: dict[str, Any]) -> list[ScoredCandidate]:
        self._load()
        category = request.get("category", "")
        qa = request.get("qualityAttributes", {}) or {}
        overrides = request.get("weights", {}) or {}
        candidates = [c for c in self._kb if c.get("category") == category] or self._kb

        results: list[ScoredCandidate] = []
        for c in candidates:
            profile = c.get("profile", {})
            passed, score, detail, fails = True, 0.0, {}, []
            for attr, spec in qa.items():
                level, required, mx = self._req_parts(spec)
                offer = profile.get(attr)
                if offer is None:
                    if required:
                        passed = False; fails.append(f"{attr}: not offered")
                    continue
                if required and not self._hard_ok(attr, level, mx, offer):
                    passed = False; fails.append(f"{attr}: {offer} fails required {level or mx}")
                    continue
                w = self._weight_for(category, attr, overrides)
                p = self._penalty(attr, level, mx, offer, w)
                score += p
                detail[attr] = {"offer": offer, "weight": w, "penalty": round(p, 3)}
            reason = ("filtered out — " + "; ".join(fails)) if not passed else \
                     f"score {round(score,3)} (lower is better)"
            results.append(ScoredCandidate(c["technology"], score, passed, detail, reason))

        cost_rank = {"low": 0, "medium": 1, "high": 2}
        mat_rank = {"published": 0, "kb": 1}
        prof = {c["technology"]: c.get("profile", {}) for c in candidates}
        matr = {c["technology"]: c.get("maturity", "kb") for c in candidates}
        results.sort(key=lambda r: (
            not r.passed_hard, r.score,
            cost_rank.get(prof.get(r.technology, {}).get("costClass", "high"), 9),
            mat_rank.get(matr.get(r.technology, "kb"), 9),
        ))
        return results
