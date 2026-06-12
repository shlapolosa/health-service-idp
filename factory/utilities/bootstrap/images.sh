#!/usr/bin/env bash
# bootstrap phase: images
#
# Builds + pushes all container images for factory adapters + per-line MCPs.
# Tags are read from each service's knative-service.yaml so a single image
# version source of truth.
#
# Usage: images.sh [--build-only|--push-only|--tag <tag>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

ACR_REGISTRY="${ACR_REGISTRY:-healthidpuaeacr}"
MODE="${1:-build-and-push}"

phase "images / build + push"

require_cmd docker
require_cmd az
require_cmd grep
require_cmd sed

declare -A SERVICES=(
    ["capability-mcp-factory"]="factory/adapters/mcp-read-gateway/Dockerfile"
    ["capability-factory-mcp"]="factory/adapters/mcp-write-gateway/Dockerfile"
    ["capability-web-mcp"]="factory/adapters/mcp-web-gateway/Dockerfile"
    ["capability-mcp-mfg-tc"]="factory/production-lines/traditional-cloud/adapters/compose-mcp/Dockerfile"
    ["slack-api-server"]="factory/adapters/intake-slack/Dockerfile"
)

declare -A KSVC_FILES=(
    # GitOps-owned ksvcs live under factory/substrate/services/ (#163 SUBSTRATE-GITOPS)
    ["capability-mcp-factory"]="factory/substrate/services/capability-mcp-factory/knative-service.yaml"
    ["capability-factory-mcp"]="factory/adapters/mcp-write-gateway/knative-service.yaml"
    ["capability-web-mcp"]="factory/adapters/mcp-web-gateway/knative-service.yaml"
    ["capability-mcp-mfg-tc"]="factory/substrate/services/capability-mcp-mfg-tc/knative-service.yaml"
    ["slack-api-server"]="factory/substrate/services/slack-api-server/knative-service.yaml"
)

# Discover tag from knative-service.yaml — single source of truth
discover_tag() {
    local svc=$1 ksvc_file="${KSVC_FILES[$svc]}"
    [[ -f "$REPO_ROOT/$ksvc_file" ]] || { echo ""; return 1; }
    grep -E "^\s*image:" "$REPO_ROOT/$ksvc_file" | head -1 \
        | sed -E 's/.*:([^:]+)$/\1/' | tr -d ' '
}

if [[ "$MODE" != "push-only" ]]; then
    info "building images locally"

    # Pre-build helpers — some services need to stage content from outside
    # the repo (e.g. mcp-read-gateway bakes sibling cafe-spec manifests).
    if [[ -x "$REPO_ROOT/factory/adapters/mcp-read-gateway/build-helpers/stage-cafe-spec.sh" ]]; then
        step "staging sibling cafe-spec manifests for mcp-read-gateway"
        bash "$REPO_ROOT/factory/adapters/mcp-read-gateway/build-helpers/stage-cafe-spec.sh" \
            | sed 's/^/    /'
    fi

    for svc in "${!SERVICES[@]}"; do
        local_dockerfile="${SERVICES[$svc]}"
        if [[ ! -f "$REPO_ROOT/$local_dockerfile" ]]; then
            warn "no Dockerfile at $local_dockerfile — skip $svc"
            continue
        fi
        tag=$(discover_tag "$svc" || echo "latest")
        image="$ACR_REGISTRY.azurecr.io/$svc:$tag"
        step "build  $image"
        # --platform linux/amd64 — Mac M-series defaults to arm64 only;
        # AKS nodes are AMD64. See memory: docker-build-amd64-mandatory.
        docker build --platform linux/amd64 -f "$REPO_ROOT/$local_dockerfile" -t "$image" "$REPO_ROOT"
    done
fi

if [[ "$MODE" != "build-only" ]]; then
    info "pushing images to $ACR_REGISTRY.azurecr.io"
    acr_login "$ACR_REGISTRY"
    for svc in "${!SERVICES[@]}"; do
        tag=$(discover_tag "$svc" || echo "latest")
        image="$ACR_REGISTRY.azurecr.io/$svc:$tag"
        step "push   $image"
        docker push "$image" 2>&1 | tail -3 || warn "push failed for $svc — continuing"
    done
fi

ok "images phase complete"
