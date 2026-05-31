#!/usr/bin/env bash
# Shared helpers for bootstrap phase scripts.
# Sourced — not executed directly. Provides logging, idempotency, k8s waits.

set -euo pipefail

# ───── Repo root discovery ─────
# NOTE: use HELPERS_DIR (not SCRIPT_DIR) so we don't overwrite the
# SCRIPT_DIR variable in the calling script.
HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HELPERS_DIR}/../../.." && pwd)"
export REPO_ROOT

# ───── Colours ─────
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; RESET=''
fi

# ───── Logging ─────
log()   { echo -e "${BLUE}[$(date +%H:%M:%S)]${RESET} $*" >&2; }
info()  { echo -e "${BLUE}[INFO]${RESET} $*" >&2; }
ok()    { echo -e "${GREEN}[OK]${RESET} $*" >&2; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*" >&2; }
err()   { echo -e "${RED}[ERR]${RESET} $*" >&2; }
phase() { echo -e "\n${BOLD}${BLUE}══ $* ══${RESET}\n" >&2; }
step()  { echo -e "  ${YELLOW}▸${RESET} $*" >&2; }

# ───── Pre-flight checks ─────
require_cmd() {
    local cmd=$1
    if ! command -v "$cmd" >/dev/null 2>&1; then
        err "required command not found: $cmd"
        return 1
    fi
}

require_kubectl_context() {
    local expected=${1:-}
    require_cmd kubectl
    local current
    current=$(kubectl config current-context 2>/dev/null) || {
        err "no current kubectl context"
        return 1
    }
    if [[ -n "$expected" && "$current" != "$expected" ]]; then
        warn "current context: $current (expected: $expected)"
        echo -n "  continue anyway? [y/N] " >&2
        read -r ans
        [[ "$ans" =~ ^[Yy]$ ]] || return 1
    fi
    info "using kubectl context: $current"
}

# ───── Idempotent apply ─────
apply_dir() {
    local dir=$1
    local extra_args=${2:-}
    [[ -d "$dir" ]] || { warn "skip (not found): $dir"; return 0; }
    local count
    count=$(find "$dir" -maxdepth 1 -name '*.yaml' -type f 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" -eq 0 ]]; then
        warn "no yaml files in: $dir"
        return 0
    fi
    step "kubectl apply -f $dir/  ($count files) $extra_args"
    # shellcheck disable=SC2086
    kubectl apply -f "$dir" $extra_args
}

apply_dir_recursive() {
    local dir=$1
    [[ -d "$dir" ]] || { warn "skip (not found): $dir"; return 0; }
    step "kubectl apply -R -f $dir/"
    kubectl apply -R -f "$dir"
}

apply_file() {
    local file=$1
    [[ -f "$file" ]] || { warn "skip (not found): $file"; return 0; }
    step "kubectl apply -f $file"
    kubectl apply -f "$file"
}

# ───── k8s waits ─────
wait_for_crd() {
    local crd=$1
    local timeout=${2:-60}
    step "wait for CRD $crd (timeout ${timeout}s)"
    local elapsed=0
    until kubectl get crd "$crd" >/dev/null 2>&1; do
        sleep 2
        elapsed=$((elapsed + 2))
        if [[ "$elapsed" -ge "$timeout" ]]; then
            err "timeout waiting for CRD $crd"
            return 1
        fi
    done
    ok "CRD $crd present"
}

wait_for_deployment() {
    local ns=$1 deploy=$2 timeout=${3:-180}
    step "wait for deployment $ns/$deploy (timeout ${timeout}s)"
    kubectl wait --for=condition=Available "deployment/$deploy" \
        -n "$ns" --timeout="${timeout}s" || {
        warn "deployment $ns/$deploy did not become available in ${timeout}s"
        return 1
    }
    ok "deployment $ns/$deploy ready"
}

wait_for_ksvc() {
    local ns=$1 ksvc=$2 timeout=${3:-180}
    step "wait for Knative service $ns/$ksvc (timeout ${timeout}s)"
    kubectl wait --for=condition=Ready "ksvc/$ksvc" \
        -n "$ns" --timeout="${timeout}s" || {
        warn "ksvc $ns/$ksvc did not become Ready in ${timeout}s"
        return 1
    }
    ok "ksvc $ns/$ksvc Ready"
}

# ───── ACR / docker helpers ─────
acr_login() {
    local registry=${1:-${ACR_REGISTRY:-healthidpuaeacr}}
    require_cmd az
    require_cmd docker
    step "az acr login --name $registry"
    az acr login --name "$registry"
}

docker_build_push() {
    local image=$1 dockerfile=$2 context=${3:-$REPO_ROOT}
    require_cmd docker
    step "build  $image  (-f $dockerfile)"
    docker build -f "$dockerfile" -t "$image" "$context"
    step "push   $image"
    docker push "$image"
    ok "pushed $image"
}
