"""Lightweight CUE `parameter:` block parser.

PolicyDefinitions + WorkflowStepDefinitions are not introspectable via `vela show` (verified
empirically: vela show errors on them). We fall back to reading their CUE template from the k8s
API and extracting parameter metadata ourselves.

This parser is intentionally narrow: it understands the subset of CUE that platform-authored
parameter blocks use, not the full CUE language. If a definition uses a CUE feature outside this
subset (e.g. complex constraints, computed fields), the parser may return empty/imprecise rows.
ComponentDefinitions + TraitDefinitions go through `vela_client.render_schema` instead — that
path is mature and handles the full CUE feature set.

Recognised patterns inside `parameter: { ... }`:
  // +usage=<description>
  name?: <type>                       → optional, no default
  name: <type>                        → required, no default
  name?: *<default> | <type>          → optional, with default
  name?: <enum1> | <enum2> | <enum3>  → optional, type printed as `e1 | e2 | e3`
  name: [...string]                   → required, type `[]string`
  name?: [string]: string             → optional, type `map[string]string`

Any line that doesn't match is skipped (defence-in-depth — never crash on weird CUE).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Matches `name?: <rhs>` or `name: <rhs>`. The RHS extends to end-of-line; trailing `// ...`
# comments are stripped manually after the match (the regex is greedy on rhs to support map
# types like `name?: [string]: string` which have an extra colon in the RHS).
# `?:` marks the field optional; bare `:` marks it required.
_FIELD_RE = re.compile(r"^\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P<opt>\??)\s*:\s*(?P<rhs>.+)$")
_USAGE_RE = re.compile(r"^\s*//\s*\+usage=(?P<text>.+?)\s*$")
_DEFAULT_RE = re.compile(r"^\*(?P<default>[^|]+?)\s*\|\s*(?P<type>.+)$")
_TRAILING_COMMENT_RE = re.compile(r"\s*//[^\n]*$")


def parse_parameter_block(cue_template: str) -> list[dict[str, Any]]:
    """Extract parameter rows from a CUE template's `parameter: { ... }` block.

    Returns a list of dicts shaped like `vela_client.render_schema` output:
      {name, description, type, required, default}

    Returns [] if no `parameter:` block is present (some workflow steps legitimately have none).
    """
    rows: list[dict[str, Any]] = []
    in_block = False
    depth = 0
    pending_usage = ""
    for raw in cue_template.splitlines():
        if not in_block:
            if re.match(r"^\s*parameter\s*:\s*\{", raw):
                in_block = True
                depth = 1
            continue
        # Track brace depth so we know when the parameter block ends.
        depth += raw.count("{") - raw.count("}")
        if depth <= 0:
            break
        u = _USAGE_RE.match(raw)
        if u:
            pending_usage = u.group("text").strip()
            continue
        m = _FIELD_RE.match(raw)
        if not m:
            # Reset pending usage if a blank/non-field line breaks the +usage→field adjacency.
            if not raw.strip():
                pending_usage = ""
            continue
        rhs = _TRAILING_COMMENT_RE.sub("", m.group("rhs")).rstrip(",").strip()
        # Skip block openings: `name: {` is a nested struct, not a parameter.
        if rhs.endswith("{") or rhs == "{":
            pending_usage = ""
            continue
        default = ""
        type_ = rhs
        dmatch = _DEFAULT_RE.match(rhs)
        if dmatch:
            default = dmatch.group("default").strip().strip('"')
            type_ = dmatch.group("type").strip()
        rows.append({
            "name": m.group("name"),
            "description": pending_usage,
            "type": type_,
            "required": m.group("opt") == "",
            "default": default,
        })
        pending_usage = ""
    return rows
