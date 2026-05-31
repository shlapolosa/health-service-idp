#!/usr/bin/env bash
# bootstrap phase: factory
#
# Deploys the cross-manufacturer (factory-level) adapters:
#   intake-slack         — Slack command intake
#   operator             — operator-v1 agent (currently signal catalog only, no service)
#   mcp-read-gateway     — factory MCP read tools (oam.dry_run, examples, kb, factory.route, lifecycle.state)
#   mcp-write-gateway    — factory MCP write tools (factory.propose PR opener)
#   mcp-web-gateway      — factory MCP discover tools (web.search, web.fetch)
#
# Each adapter is a Knative Service. Images must be built+pushed beforehand
# (run utilities/bootstrap/images.sh).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

phase "factory / cross-mfg adapters"

require_kubectl_context "${EXPECTED_KUBE_CONTEXT:-}"

# ───── 1. intake-slack (Slack command receiver) ─────
info "intake-slack adapter"
apply_file "$REPO_ROOT/factory/adapters/intake-slack/knative-service.yaml"
# Apply additional manifests if present (istio, rbac, etc.)
for f in "$REPO_ROOT"/factory/adapters/intake-slack/*.yaml; do
    [[ -f "$f" && "$(basename "$f")" != "knative-service.yaml" ]] && apply_file "$f"
done

# ───── 2. mcp-read-gateway (factory MCP) ─────
info "mcp-read-gateway adapter"
apply_file "$REPO_ROOT/factory/adapters/mcp-read-gateway/knative-service.yaml"
apply_file "$REPO_ROOT/factory/adapters/mcp-read-gateway/rbac.yaml" 2>/dev/null || true

# ───── 3. mcp-write-gateway (factory.propose PR opener) ─────
info "mcp-write-gateway adapter"
apply_file "$REPO_ROOT/factory/adapters/mcp-write-gateway/knative-service.yaml"

# ───── 4. mcp-web-gateway (discover surface) ─────
info "mcp-web-gateway adapter"
apply_file "$REPO_ROOT/factory/adapters/mcp-web-gateway/knative-service.yaml"

# ───── 5. operator-v1 (currently signal catalog + system prompt, no runtime service yet) ─────
info "operator-v1 — currently signal catalog only (no runtime service to apply)"

ok "factory phase complete"

info "waiting for Knative services to become Ready..."
for ksvc in slack-api-server capability-mcp-factory capability-factory-mcp capability-web-mcp; do
    wait_for_ksvc default "$ksvc" 180 || warn "$ksvc did not become Ready (continuing)"
done

ok "factory adapters live"
