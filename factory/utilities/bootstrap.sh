#!/usr/bin/env bash
# bootstrap.sh — single entry point to bring the factory floor up / down.
#
# Real-world analogy: this is the building manager. It can stand up the
# whole factory (substrate → factory cross-line services → production
# lines → verify), or run any single phase.
#
# Usage:
#   ./utilities/bootstrap.sh up [--phase <phase>] [--skip-images]
#   ./utilities/bootstrap.sh down [--keep-data]
#   ./utilities/bootstrap.sh status
#   ./utilities/bootstrap.sh images [build|push|build-and-push]
#   ./utilities/bootstrap.sh phase <phase>     # one phase only
#
# Phases (in order):
#   secrets                    — k8s secrets from .env + ACR pull secret
#   substrate                  — Crossplane + Argo + Knative + ArgoCD + Istio
#   images                     — docker build + push of all service images
#   factory                    — cross-mfg adapter Knative services
#   production-line:<id>       — per-line catalog + composition + execute + compose-mcp
#                                (default: production-line:traditional-cloud)
#   verify                     — health checks across all components
#
# Examples:
#   ./utilities/bootstrap.sh up                                   # full bring-up
#   ./utilities/bootstrap.sh up --skip-images                     # skip rebuild
#   ./utilities/bootstrap.sh phase substrate                      # substrate only
#   ./utilities/bootstrap.sh phase production-line:traditional-cloud
#   ./utilities/bootstrap.sh status                               # quick health
#   ./utilities/bootstrap.sh down --keep-data                     # preserve volumes
#
# Environment:
#   EXPECTED_KUBE_CONTEXT      — abort if current context differs (optional)
#   ACR_REGISTRY               — Azure Container Registry name (default: healthidpuaeacr)
#   AZURE_SUBSCRIPTION         — Azure subscription id (used by Azure-side steps)
#
# Idempotent — designed for repeated invocation.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./bootstrap/helpers/common.sh
. "${SCRIPT_DIR}/bootstrap/helpers/common.sh"

cmd_up() {
    local skip_images=false
    local only_phase=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-images) skip_images=true; shift ;;
            --phase)       only_phase="$2"; shift 2 ;;
            *)             err "unknown flag: $1"; exit 2 ;;
        esac
    done

    if [[ -n "$only_phase" ]]; then
        run_phase "$only_phase"
        return
    fi

    log "factory bring-up starting"
    run_phase secrets || warn "secrets phase had issues — continuing"
    run_phase substrate
    if [[ "$skip_images" != true ]]; then
        run_phase images || warn "images phase had issues — continuing"
    fi
    run_phase factory
    run_phase production-line:traditional-cloud
    run_phase verify
    ok "factory bring-up complete"
}

cmd_down() {
    local keep_data=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --keep-data) keep_data=true; shift ;;
            *)           err "unknown flag: $1"; exit 2 ;;
        esac
    done

    warn "tear-down: removes Knative services + Argo WorkflowTemplates + CDs"
    if [[ "$keep_data" == true ]]; then
        info "(keeping persistent volumes + claims)"
    fi
    echo -n "  proceed? [y/N] " >&2
    read -r ans
    [[ "$ans" =~ ^[Yy]$ ]] || { info "cancelled"; return 0; }

    # Reverse-order delete
    log "removing per-line services + manifests"
    kubectl delete -f "$REPO_ROOT/production-lines/traditional-cloud/adapters/compose-mcp/knative-service.yaml" \
        --ignore-not-found=true || true
    kubectl delete -f "$REPO_ROOT/production-lines/traditional-cloud/adapters/catalog/" \
        --recursive --ignore-not-found=true || true
    kubectl delete -f "$REPO_ROOT/production-lines/traditional-cloud/adapters/execute/" \
        --recursive --ignore-not-found=true || true

    log "removing factory adapter services"
    for f in factory/adapters/*/knative-service.yaml; do
        kubectl delete -f "$REPO_ROOT/$f" --ignore-not-found=true || true
    done

    if [[ "$keep_data" != true ]]; then
        warn "removing substrate (CRDs, providers) — destructive"
        # Skipped by default; user must explicitly request full substrate teardown.
        info "(substrate teardown intentionally skipped — too destructive for default flow)"
        info "to fully tear down substrate, run: kubectl delete -f factory/substrate/ --recursive"
    fi

    ok "tear-down complete"
}

cmd_status() {
    bash "$SCRIPT_DIR/bootstrap/verify.sh"
}

cmd_images() {
    local mode="${1:-build-and-push}"
    bash "$SCRIPT_DIR/bootstrap/images.sh" "$mode"
}

cmd_phase() {
    local phase="${1:?usage: bootstrap.sh phase <phase> [flags...]}"
    shift
    run_phase "$phase" "$@"
}

run_phase() {
    local phase=$1
    case "$phase" in
        install-controllers)
            bash "$SCRIPT_DIR/bootstrap/install-controllers.sh"
            ;;
        uninstall-controllers)
            bash "$SCRIPT_DIR/bootstrap/uninstall-controllers.sh" "${@:2}"
            ;;
        secrets)
            bash "$SCRIPT_DIR/bootstrap/secrets.sh"
            ;;
        substrate)
            bash "$SCRIPT_DIR/bootstrap/substrate.sh"
            ;;
        images)
            bash "$SCRIPT_DIR/bootstrap/images.sh" build-and-push
            ;;
        factory)
            bash "$SCRIPT_DIR/bootstrap/factory.sh"
            ;;
        production-line:*)
            local line_id="${phase#production-line:}"
            bash "$SCRIPT_DIR/bootstrap/production-line.sh" "$line_id"
            ;;
        verify)
            bash "$SCRIPT_DIR/bootstrap/verify.sh"
            ;;
        *)
            err "unknown phase: $phase"
            err "known phases: install-controllers, uninstall-controllers, secrets, substrate, images, factory, production-line:<id>, verify"
            exit 2
            ;;
    esac
}

usage() {
    sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
}

case "${1:-}" in
    up)     shift; cmd_up "$@" ;;
    down)   shift; cmd_down "$@" ;;
    status) shift; cmd_status ;;
    images) shift; cmd_images "$@" ;;
    phase)  shift; cmd_phase "$@" ;;
    -h|--help|help|"") usage ;;
    *)      err "unknown command: $1"; usage; exit 2 ;;
esac
