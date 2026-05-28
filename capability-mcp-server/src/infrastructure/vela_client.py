"""Vela CLI client — live schema render + OAM validation.

`catalog.describe` renders parameter schemas LIVE via `vela show <component> --format markdown`
(decision: only `webservice` has a component-schema-* ConfigMap, but vela renders all ~15 live).
`catalog.validate` / app.submit pre-check use `vela dry-run`. The vela + kubectl binaries are baked
into the image (see Dockerfile).
"""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

_ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<desc>[^|]*?)\s*\|\s*(?P<type>[^|]+?)\s*\|"
                  r"\s*(?P<required>[^|]+?)\s*\|\s*(?P<default>[^|]*?)\s*\|")


class VelaClient:
    def __init__(self, vela_bin: str = "vela", timeout: int = 60):
        self.vela_bin = vela_bin
        self.timeout = timeout

    def render_schema(self, component: str) -> list[dict[str, Any]]:
        """Return parameter rows for a ComponentDefinition, rendered live by vela."""
        try:
            out = subprocess.run(
                [self.vela_bin, "show", component, "--format", "markdown"],
                capture_output=True, text=True, timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:  # noqa: BLE001
            logger.error("vela show %s failed: %s", component, e)
            return []
        rows: list[dict[str, Any]] = []
        for line in out.stdout.splitlines():
            m = _ROW.match(line)
            if not m:
                continue
            name = m.group("name")
            if name in ("NAME", "") or set(name) <= {"-", " "}:  # header / divider
                continue
            rows.append({
                "name": name,
                "description": m.group("desc"),
                "type": m.group("type"),
                "required": m.group("required").lower() in ("true", "yes", "✓"),
                "default": m.group("default"),
            })
        return rows

    def dry_run(self, oam_yaml: str) -> tuple[bool, str]:
        """Validate an OAM Application via `vela dry-run`. Returns (ok, diagnostics)."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=True) as f:
            f.write(oam_yaml)
            f.flush()
            try:
                out = subprocess.run(
                    [self.vela_bin, "dry-run", "-f", f.name],
                    capture_output=True, text=True, timeout=self.timeout,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:  # noqa: BLE001
                return False, f"vela dry-run unavailable: {e}"
        ok = out.returncode == 0
        return ok, (out.stdout if ok else (out.stderr or out.stdout))
