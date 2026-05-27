#!/bin/bash
# Delete one microservice/project provisioned via the Slack /microservice flow.
# Tears down in the CORRECT order — the OAM Application MUST go first, otherwise
# KubeVela regenerates the Crossplane claims (which regenerate the namespace,
# vCluster, and provisioning jobs). See docs/VCLUSTER-PROVISIONING-AUDIT.md.
#
#   ./scripts/delete-microservice.sh <name>           # dry-run (default)
#   RUN=true ./scripts/delete-microservice.sh <name>  # execute
#
# Run against the HOST cluster context (internal-developer-platform).

set -o pipefail
NAME="${1:?usage: delete-microservice.sh <name> (set RUN=true to execute)}"
RUN="${RUN:-false}"
run(){ if [ "$RUN" = "true" ]; then eval "$@"; else echo "  DRY-RUN> $*"; fi; }

echo "=== Deleting microservice '$NAME' (RUN=$RUN) ==="

# 1. OAM Application FIRST (the regeneration root) + strip finalizer
echo "[1/6] OAM Application (core.oam.dev)"
run "kubectl delete applications.core.oam.dev $NAME -n default --wait=false 2>/dev/null || true"
[ "$RUN" = "true" ] && sleep 5 && kubectl patch applications.core.oam.dev "$NAME" -n default --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true

# 2. Crossplane claims in default (application/appcontainer/vclusterenvironment)
echo "[2/6] Crossplane claims"
run "kubectl delete applicationclaim,appcontainerclaim,vclusterenvironmentclaim $NAME -n default --wait=false 2>/dev/null || true"

# 3. ArgoCD Applications for this service
echo "[3/6] ArgoCD Applications"
if [ "$RUN" = "true" ]; then
  for a in $(kubectl get applications.argoproj.io -n argocd -o name 2>/dev/null | grep -E "/${NAME}(-|$)"); do
    kubectl patch "$a" -n argocd --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true
    kubectl delete "$a" -n argocd --wait=false 2>/dev/null || true
  done
else
  echo "  DRY-RUN> delete argocd apps matching $NAME-*"
fi

# 4. vCluster registration (KubeVela cluster + vela-system credential secret)
echo "[4/6] vCluster registration (ClusterGateway)"
run "kubectl delete clustergateway $NAME 2>/dev/null || true"
run "kubectl delete secret $NAME -n vela-system 2>/dev/null || true"

# 5. GitHub Repository CRs for this service (Crossplane provider-github)
echo "[5/6] GitHub Repository CRs"
if [ "$RUN" = "true" ]; then
  kubectl get repository.repo.github.upbound.io -A --no-headers 2>/dev/null | grep -E "${NAME}" \
    | awk '{print "kubectl delete repository.repo.github.upbound.io "$2" -n "$1}' | bash 2>/dev/null || true
else
  echo "  DRY-RUN> delete github Repository CRs matching $NAME"
fi

# 6. Namespace (removes vCluster + Knative pods). Strip finalizers if it hangs Terminating.
echo "[6/6] Namespace"
run "kubectl delete namespace $NAME --wait=false 2>/dev/null || true"
if [ "$RUN" = "true" ]; then
  sleep 10
  if [ "$(kubectl get ns "$NAME" --no-headers 2>/dev/null | awk '{print $2}')" = "Terminating" ]; then
    echo "  namespace stuck Terminating - stripping finalizers from leftover resources..."
    for r in $(kubectl api-resources --verbs=list --namespaced -o name 2>/dev/null); do
      for it in $(kubectl get "$r" -n "$NAME" --no-headers --ignore-not-found 2>/dev/null | awk '{print $1}'); do
        kubectl patch "$r" "$it" -n "$NAME" --type=merge -p '{"metadata":{"finalizers":null}}' 2>/dev/null || true
      done
    done
  fi
fi

echo "=== Done (RUN=$RUN). Verify: kubectl get applications.core.oam.dev,applicationclaim -A | grep $NAME ; vela cluster list ==="
