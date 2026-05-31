"""Crossplane / kubectl server-side dry-run client.

`crossplane.dry_run` validates XRD + Composition + Crossplane managed resource YAML via
`kubectl apply --dry-run=server -f -`. Catches structural errors and CRD-existence checks that
`vela dry-run` doesn't cover (vela validates OAM Applications; this validates the resources OAM
renders into).

Uses the in-cluster ServiceAccount via the kubectl binary baked into the image (Dockerfile:11).
RBAC implication: the MCP SA needs the verb permissions implied by the resource being dry-run.
For initial dev we lean on permissive RBAC; tightening is P8.2's job (the factory MCP runs with
narrower perms by design).
"""
from __future__ import annotations

import logging
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class CrossplaneDryRunClient:
    def __init__(self, kubectl_bin: str = "kubectl", timeout: int = 60):
        self.kubectl_bin = kubectl_bin
        self.timeout = timeout

    def dry_run(self, yaml_text: str) -> tuple[bool, str]:
        """Server-side dry-run apply. Returns (ok, diagnostics).

        `kubectl apply --dry-run=server` runs admission controllers + CRD schema validation but
        commits nothing. It is the right call for XRD/Composition/Crossplane MR validation.
        """
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=True) as f:
            f.write(yaml_text)
            f.flush()
            try:
                out = subprocess.run(
                    [self.kubectl_bin, "apply", "--dry-run=server", "-f", f.name,
                     "--validate=strict"],
                    capture_output=True, text=True, timeout=self.timeout,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:  # noqa: BLE001
                return False, f"kubectl dry-run unavailable: {e}"
        ok = out.returncode == 0
        return ok, (out.stdout if ok else (out.stderr or out.stdout))
