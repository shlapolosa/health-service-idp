#!/usr/bin/env bash
# bootstrap phase: verify
#
# Runs health checks across substrate + factory + production-lines.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

phase "verify"

# ───── 1. Existing infrastructure health check ─────
if [[ -x "$REPO_ROOT/utilities/infrastructure-health-check-enhanced.sh" ]]; then
    info "running infrastructure-health-check-enhanced.sh"
    bash "$REPO_ROOT/utilities/infrastructure-health-check-enhanced.sh" 2>&1 \
        | sed 's/^/  /' || warn "health check reported issues"
elif [[ -x "$REPO_ROOT/utilities/infrastructure-health-check.sh" ]]; then
    info "running infrastructure-health-check.sh"
    bash "$REPO_ROOT/utilities/infrastructure-health-check.sh" 2>&1 \
        | sed 's/^/  /' || warn "health check reported issues"
fi

# ───── 2. MFG-TC parity audit ─────
if [[ -x "$REPO_ROOT/utilities/check-mfg-tc-parity.sh" ]]; then
    info "running MFG-TC parity audit"
    if bash "$REPO_ROOT/utilities/check-mfg-tc-parity.sh"; then
        ok "parity audit passed"
    else
        warn "parity audit reported drift (see output above)"
    fi
fi

# ───── 3. Knative service liveness ─────
info "checking Knative services"
for ksvc in slack-api-server capability-mcp-factory capability-factory-mcp capability-web-mcp capability-mcp-mfg-tc; do
    if kubectl get ksvc "$ksvc" -n default >/dev/null 2>&1; then
        ready=$(kubectl get ksvc "$ksvc" -n default -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)
        if [[ "$ready" == "True" ]]; then
            ok "ksvc/$ksvc Ready"
        else
            warn "ksvc/$ksvc not Ready (status=$ready)"
        fi
    else
        warn "ksvc/$ksvc not found"
    fi
done

# ───── 4. Composition / XRD presence ─────
info "checking Crossplane CompositeResourceDefinitions"
for xrd in applicationclaims.platform.example.org appcontainerclaims.platform.example.org; do
    if kubectl get xrd "$xrd" >/dev/null 2>&1; then
        ok "XRD $xrd present"
    else
        warn "XRD $xrd not found"
    fi
done

# ───── 5. WorkflowTemplate presence ─────
info "checking Argo WorkflowTemplates"
for wt in oam-driven-contract oam-apply oam-apply-wait appcontainer-standard-contract; do
    if kubectl get workflowtemplate "$wt" -n argo >/dev/null 2>&1; then
        ok "WorkflowTemplate $wt present"
    else
        warn "WorkflowTemplate $wt not found in argo namespace"
    fi
done

ok "verify phase complete"
