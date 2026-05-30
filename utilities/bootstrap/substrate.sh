#!/usr/bin/env bash
# bootstrap phase: substrate
#
# Provisions the cluster-level platform that hosts the factory:
#   Crossplane (XRDs, Compositions, providers, RBAC)
#   Argo Workflows + Argo Events
#   ArgoCD
#   Knative Serving
#
# Assumes an existing Kubernetes cluster (AKS). For from-scratch cluster
# creation, run utilities/install-aks-platform.sh first (legacy script,
# kept for reference; it still works against the new substrate/ layout).
#
# Idempotent — re-runnable.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
. "${SCRIPT_DIR}/helpers/common.sh"

phase "substrate / platform"

require_kubectl_context "${EXPECTED_KUBE_CONTEXT:-}"

# ───── 1. Crossplane (XRDs, Compositions, RBAC, providers) ─────
info "Crossplane providers + RBAC + cluster gateway"
apply_dir       "$REPO_ROOT/substrate/crossplane/rbac"           "--recursive"
apply_dir       "$REPO_ROOT/substrate/crossplane/cluster-gateway" "--recursive"

info "Crossplane XRDs + Compositions (substrate-level)"
apply_dir       "$REPO_ROOT/substrate/crossplane"
apply_dir       "$REPO_ROOT/substrate/crossplane/compositions"
apply_dir_recursive "$REPO_ROOT/substrate/crossplane/templates"

info "real-time platform manifests (PostgreSQL, MQTT, Kafka, Lenses, Metabase)"
apply_dir_recursive "$REPO_ROOT/substrate/crossplane/realtime-platform"

info "GraphQL substrate"
apply_dir_recursive "$REPO_ROOT/substrate/crossplane/graphql"

# ───── 2. Argo Workflows server config + RBAC ─────
info "Argo Workflows server config + RBAC"
apply_dir "$REPO_ROOT/substrate/argo"

# ───── 3. Argo Events (OAM webhook + watcher) ─────
info "Argo Events sensors + OAM webhook"
apply_dir "$REPO_ROOT/substrate/argo-events"

# ───── 4. ArgoCD ─────
info "ArgoCD vcluster app templates"
apply_dir "$REPO_ROOT/substrate/argocd"

# ───── 5. Knative Serving ─────
info "Knative Serving install + autoscaler config"
apply_dir "$REPO_ROOT/substrate/knative"

ok "substrate phase complete"
