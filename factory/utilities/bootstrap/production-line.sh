#!/usr/bin/env bash
# bootstrap phase: production-line:<id>
#
# Deploys a single production line's adapter set + catalog + composition + execute.
#
# Usage: production-line.sh <id>
# Today only `traditional-cloud` is supported.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

LINE_ID="${1:-traditional-cloud}"
LINE_DIR="$REPO_ROOT/production-lines/$LINE_ID"

if [[ ! -d "$LINE_DIR" ]]; then
    err "unknown production line: $LINE_ID (no directory at $LINE_DIR)"
    exit 1
fi

phase "production-line / $LINE_ID"

require_kubectl_context "${EXPECTED_KUBE_CONTEXT:-}"

# ───── 1. catalog — ComponentDefinitions, TraitDefinitions, PolicyDefinitions ─────
info "[$LINE_ID] catalog (OAM definitions)"
apply_dir "$LINE_DIR/adapters/catalog"
apply_dir_recursive "$LINE_DIR/adapters/catalog/webservice-modular"

# ───── 2. composition — Crossplane Composition that turns OAM into k8s resources ─────
info "[$LINE_ID] composition (Crossplane Composition)"
apply_dir "$LINE_DIR/adapters/composition"

# ───── 3. execute — Argo workflow templates ─────
info "[$LINE_ID] execute (Argo WorkflowTemplates)"
apply_dir "$LINE_DIR/adapters/execute"
apply_dir_recursive "$LINE_DIR/adapters/execute/workflow-templates"

# ───── 4. compose-mcp — per-line MCP gateway (Knative Service) ─────
info "[$LINE_ID] compose-mcp (per-line MCP)"
apply_file "$LINE_DIR/adapters/compose-mcp/knative-service.yaml"

# ───── 5. compose (architect-v1) — Foundry agent, registered via setup-architect-agent.sh ─────
info "[$LINE_ID] compose (architect-v1) — Foundry registration"
if command -v az >/dev/null 2>&1; then
    if [[ -x "$REPO_ROOT/utilities/setup-architect-agent.sh" ]]; then
        step "registering architect-v1 Foundry agent (idempotent)"
        bash "$REPO_ROOT/utilities/setup-architect-agent.sh" \
            --prompt-file "$LINE_DIR/adapters/compose/system-prompt.md" 2>&1 \
            | sed 's/^/    /' || warn "architect-v1 Foundry registration had issues — non-fatal"
    else
        warn "setup-architect-agent.sh not executable — skip"
    fi
else
    warn "az CLI not installed — skip Foundry agent registration"
fi

ok "[$LINE_ID] catalog + composition + execute applied"

info "waiting for compose-mcp Knative service to become Ready..."
case "$LINE_ID" in
    traditional-cloud) wait_for_ksvc default capability-mcp-mfg-tc 180 || warn "compose-mcp did not become Ready" ;;
    *)                 warn "no wait pattern defined for line $LINE_ID" ;;
esac

ok "production-line:$LINE_ID phase complete"
