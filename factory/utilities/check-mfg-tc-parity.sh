#!/usr/bin/env bash
# Wrapper for the MFG-TC parity audit (manufacturer = traditional-cloud).
#
# Validates that every ComponentDefinition in crossplane/oam/ has a matching
# M4 wire-shape schema and catalog.index.json entry in the sibling cafe-spec
# repo. Reports drift in either direction.
#
# Why: this repo (health-service-idp) is the runtime catalog for MFG-TC.
# The sibling cafe-spec is the spec layer that the compose agent reads
# from. Drift between them = capabilities the platform exposes but the
# agent cannot reason about.
#
# Exit 0 = parity. Exit 1 = drift. Exit 2 = sibling repo not present.
#
# Use locally, in CI, or in pre-commit. Safe (read-only).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SIBLING_AUDIT="$(cd "$REPO_ROOT/.." && pwd)/cafe-spec/scripts/audit-mfg-tc-parity.py"

if [[ ! -f "$SIBLING_AUDIT" ]]; then
    echo "ERROR: sibling audit script not found at: $SIBLING_AUDIT" >&2
    echo "       expected sibling cafe-spec repo at: $(cd "$REPO_ROOT/.." && pwd)/cafe-spec" >&2
    exit 2
fi

exec python3 "$SIBLING_AUDIT"
