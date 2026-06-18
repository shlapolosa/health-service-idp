#!/usr/bin/env bash
# Re-vendor the architect's deterministic artifact engines from their source-of-truth,
# then gate on selftest. Run this when the upstream skill engines change; commit the result.
# The vendored copies here are what the architect-v1 agent attaches as Code-Interpreter files.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"

# archimate-view + drawio-c4 are Claude-Code skills (author-local source of truth)
cp "${HOME}/.claude/skills/archimate-view/archi_layout.py" "$HERE/archimate_view.py"
cp "${HOME}/.claude/skills/drawio-c4/drawio_c4.py"        "$HERE/drawio_c4.py"
# traceability engine lives in-repo
cp "$ROOT/factory/docs/analysis/wellness-archimate/check_traceability.py" "$HERE/traceability.py"

python3 "$HERE/selftest.py"
echo "re-vendored engines + selftest PASSED — review git diff and commit"
