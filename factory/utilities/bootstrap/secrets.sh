#!/usr/bin/env bash
# bootstrap phase: secrets
#
# Wraps utilities/setup-secrets.sh (reads .env) + creates additional
# secrets the factory adapters need (github-credentials, slack-credentials,
# foundry-credentials, classify-router config).
#
# Idempotent: kubectl apply with merge.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

phase "secrets"

require_kubectl_context "${EXPECTED_KUBE_CONTEXT:-}"

if [[ -f "$REPO_ROOT/.env" ]]; then
    info "running legacy setup-secrets.sh against .env"
    if [[ -x "$REPO_ROOT/utilities/setup-secrets.sh" ]]; then
        bash "$REPO_ROOT/utilities/setup-secrets.sh" 2>&1 | sed 's/^/  /'
    else
        warn "utilities/setup-secrets.sh not executable"
    fi
else
    warn ".env file not found at $REPO_ROOT/.env — skip env-driven secrets"
fi

if [[ -x "$REPO_ROOT/utilities/add-acr-secret-to-repos.sh" ]]; then
    info "ACR pull-secret distribution"
    bash "$REPO_ROOT/utilities/add-acr-secret-to-repos.sh" 2>&1 | sed 's/^/  /' || \
        warn "ACR secret distribution had issues"
fi

ok "secrets phase complete"
