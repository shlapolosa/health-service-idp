#!/usr/bin/env bash
# stage-cafe-spec.sh — copy sibling cafe-spec/manufacturers/ into this
# adapter's local cafe-spec-staging/ dir so the Dockerfile can COPY it
# (Docker build context can't reach outside the repo).
#
# Run this BEFORE `docker build`. Idempotent — overwrites staging dir.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADAPTER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${ADAPTER_DIR}/../../.." && pwd)"
SIBLING="$(cd "${REPO_ROOT}/.." && pwd)/cafe-spec"
STAGING="${ADAPTER_DIR}/cafe-spec-staging"

if [[ ! -d "$SIBLING/manufacturers" ]]; then
    echo "ERROR: sibling cafe-spec not found at $SIBLING" >&2
    echo "       expected $SIBLING/manufacturers/<id>/manifest.yaml" >&2
    exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING"

# Copy only the manifests (the runtime only reads manifest.yaml per manufacturer).
# Skip the heavy m4-catalog/m5-templates/governance subdirs to keep the
# image small. If factory.list_manufacturers needs more fields later,
# extend this rsync.
for mfg_dir in "$SIBLING/manufacturers"/*/; do
    mfg_id=$(basename "$mfg_dir")
    [[ -f "$mfg_dir/manifest.yaml" ]] || continue
    mkdir -p "$STAGING/manufacturers/$mfg_id"
    cp "$mfg_dir/manifest.yaml" "$STAGING/manufacturers/$mfg_id/"
done

# Top-level cafe-spec metadata for completeness
cp "$SIBLING/manufacturers/README.md" "$STAGING/manufacturers/" 2>/dev/null || true
cp "$SIBLING/manufacturers/manifest.schema.json" "$STAGING/manufacturers/" 2>/dev/null || true

count=$(find "$STAGING/manufacturers" -name 'manifest.yaml' | wc -l | tr -d ' ')
echo "staged $count manufacturer manifests under $STAGING"
ls -la "$STAGING/manufacturers/" 2>&1 | head -10
