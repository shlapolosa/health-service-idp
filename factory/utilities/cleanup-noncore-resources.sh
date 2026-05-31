#!/bin/bash
# Non-Core Resources Cleanup  (host/control cluster)
# Deletes everything NOT part of the core platform (created by provisioning,
# not by the install/config scripts), in the CORRECT dependency order.
#
# REGENERATION CHAIN (learned the hard way 2026-05-27): deleting ArgoCD apps,
# namespaces, claims, or vClusters alone does NOT work -- they get recreated.
# The true root is the KubeVela OAM Application; the chain is:
#   OAM Application (core.oam.dev, in `default`)
#     -> Crossplane claims (applicationclaim/appcontainerclaim/vclusterenvironmentclaim, in `default`)
#       -> X* composites (cluster-scoped) -> namespaces + setup Jobs + vCluster
#       -> ArgoCD Applications (per project, in `argocd`)
# So delete OAM apps FIRST, then claims, then the downstream leftovers.
#
# vClusters are KubeVela registrations (virtualclusters.cluster.core.oam.dev is
# read-only -> `kubectl delete` returns MethodNotAllowed). Remove them by deleting
# their backing secrets in vela-system (label cluster.core.oam.dev/cluster-credential-type).
#
# SAFETY: dry-run by default. Set RUN=true to execute.
#   Preview:  ./cleanup-noncore-resources.sh
#   Execute:  RUN=true ./cleanup-noncore-resources.sh
# Requires a STABLE API server (AKS Standard tier) -- on Free tier this 503-storms.

set -o pipefail
RUN="${RUN:-false}"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info(){ echo -e "${BLUE}[i]${NC} $1"; }
ok(){ echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
run(){ if [ "$RUN" = "true" ]; then eval "$@"; else echo "    DRY-RUN> $*"; fi; }

CORE_NS=(
  kube-system kube-public kube-node-lease default
  gatekeeper-system
  calico-system calico-apiserver tigera-operator   # Calico CNI - NEVER delete
  istio-system knative-serving knative-eventing
  argocd argo argo-events
  crossplane-system upbound-system
  external-secrets cert-manager
  vela-system kubevela
  monitoring observability prometheus grafana
)
is_core(){ local ns="$1"; for c in "${CORE_NS[@]}"; do [ "$ns" = "$c" ] && return 0; done; return 1; }
CORE_VCLUSTER_SECRET=( local )   # KubeVela host self-reference
is_core_vc(){ local v="$1"; for c in "${CORE_VCLUSTER_SECRET[@]}"; do [ "$v" = "$c" ] && return 0; done; return 1; }

echo "=== Non-Core Cleanup (RUN=$RUN) ==="

# Step 1: KubeVela OAM Applications in default = THE regeneration root.
info "Step 1: Delete KubeVela OAM Applications (core.oam.dev) in default + strip finalizers"
if [ "$RUN" = "true" ]; then
  kubectl delete applications.core.oam.dev -n default --all --wait=false 2>/dev/null || true
  sleep 15
  for app in $(kubectl get applications.core.oam.dev -n default -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    kubectl patch applications.core.oam.dev "$app" -n default --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true
  done
else
  echo "    DRY-RUN> delete $(kubectl get applications.core.oam.dev -n default --no-headers 2>/dev/null | wc -l | tr -d ' ') OAM applications"
fi
ok "OAM applications handled"

# Step 2: Crossplane claims in default (recreated by OAM apps; delete after step 1). Composites cascade.
info "Step 2: Delete Crossplane claims in default"
run "kubectl delete applicationclaim,appcontainerclaim,vclusterenvironmentclaim -n default --all --wait=false 2>/dev/null || true"
ok "Crossplane claims handled"

# Step 3: ArgoCD Applications (per-project; none are core). Strip finalizer to avoid prune storm.
info "Step 3: Delete all ArgoCD Applications"
if [ "$RUN" = "true" ]; then
  for app in $(kubectl get applications.argoproj.io -n argocd -o name 2>/dev/null); do
    kubectl patch "$app" -n argocd --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true
  done
  kubectl delete applications.argoproj.io -n argocd --all --wait=false 2>/dev/null || true
else
  echo "    DRY-RUN> delete $(kubectl get applications.argoproj.io -n argocd --no-headers 2>/dev/null | wc -l | tr -d ' ') ArgoCD apps"
fi
ok "ArgoCD Applications handled"

# Step 4: stale vCluster registrations (delete backing secrets in vela-system; keep 'local').
info "Step 4: Delete stale vCluster registration secrets in vela-system (keep: ${CORE_VCLUSTER_SECRET[*]})"
for s in $(kubectl get secrets -n vela-system -l cluster.core.oam.dev/cluster-credential-type -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  is_core_vc "$s" && continue
  run "kubectl delete secret $s -n vela-system 2>/dev/null || true"
done
for cg in $(kubectl get clustergateway -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  is_core_vc "$cg" && continue
  run "kubectl delete clustergateway $cg 2>/dev/null || true"
done
ok "vCluster registrations handled"

# Step 5: orphaned GitHub Repository CRs (Crossplane provider; poll dead repos).
info "Step 5: Delete GitHub Repository CRs"
run "kubectl delete repository.repo.github.upbound.io --all -A --wait=false 2>/dev/null || true"
ok "GitHub Repository CRs handled"

# Step 6: leftover Jobs + their orphaned (CrashLoopBackOff) pods in default.
info "Step 6: Delete leftover provisioning Jobs/pods in default"
run "kubectl delete jobs -n default --all --wait=false 2>/dev/null || true"
if [ "$RUN" = "true" ]; then
  for p in $(kubectl get pods -n default --no-headers 2>/dev/null | grep -E '\-(gitops|source|crd|secrets|knative|vcluster|register)\-' | awk '{print $1}'); do
    kubectl delete pod "$p" -n default --force --grace-period=0 2>/dev/null || true
  done
fi
ok "Jobs/pods handled"

# Step 7: delete non-core namespaces (Crossplane usually GCs them after step 1-2; this catches stragglers).
ALL_NS=()
while IFS= read -r line; do [ -n "$line" ] && ALL_NS+=("$line"); done < <(kubectl get ns --no-headers 2>/dev/null | awk '{print $1}')
info "Step 7: Delete non-core namespaces"
for ns in "${ALL_NS[@]:-}"; do
  [ -n "$ns" ] || continue
  is_core "$ns" && continue
  run "kubectl delete namespace $ns --wait=false 2>/dev/null || true"
done
ok "Namespaces handled"

# Step 8: unstick namespaces stuck Terminating on a leftover finalized resource (e.g. crossplane referred-by secrets).
if [ "$RUN" = "true" ]; then
  info "Step 8: Strip finalizers from resources blocking Terminating namespaces"
  for ns in $(kubectl get ns --no-headers 2>/dev/null | awk '$2=="Terminating"{print $1}'); do
    is_core "$ns" && continue
    for r in $(kubectl api-resources --verbs=list --namespaced -o name 2>/dev/null); do
      for it in $(kubectl get "$r" -n "$ns" --no-headers --ignore-not-found 2>/dev/null | awk '{print $1}'); do
        kubectl patch "$r" "$it" -n "$ns" --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true
      done
    done
  done
  ok "Finalizer cleanup done"
fi

echo
ok "Done (RUN=$RUN). Verify: kubectl get applications.core.oam.dev,applicationclaim -A ; kubectl get applications.argoproj.io -n argocd"
