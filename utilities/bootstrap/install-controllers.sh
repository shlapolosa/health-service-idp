#!/usr/bin/env bash
# install-controllers.sh — install/upgrade platform controllers via Helm.
# Idempotent: re-runnable against an already-installed cluster (uses
# `helm upgrade --install`). Replaces the broken legacy install-*.sh scripts
# (install-aks-platform.sh, install-platform.sh, install-knative.sh) which
# used `helm install` (errors on re-run), referenced 6 hardcoded paths
# broken by the recent refactor, and would have downgraded some live
# component versions.
#
# Version pins below MATCH the live UAE cluster — do not bump casually.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/helpers/common.sh"

# ───── Pinned versions ─────
KNATIVE_VERSION="v1.13.0"
ARGOCD_CHART_VERSION="7.6.12"
ARGO_WF_CHART_VERSION="0.41.14"
ARGO_EVENTS_CHART_VERSION="2.4.8"
CROSSPLANE_CHART_VERSION="1.17.2"          # MATCH live cluster
PROVIDER_KUBERNETES_VERSION="v0.14.1"
PROVIDER_HELM_VERSION="v0.20.4"
PROVIDER_GITHUB_VERSION="v0.18.0"          # upbound/provider-github
KUBEVELA_CHART_VERSION="1.10.3"            # MATCH live cluster
EXTERNAL_SECRETS_CHART_VERSION="0.19.2"

HELM_TIMEOUT="${HELM_TIMEOUT:-5m}"

phase "install-controllers"
require_kubectl_context "${EXPECTED_KUBE_CONTEXT:-}"
require_cmd helm
require_cmd kubectl

# ───── Helm wrappers ─────
helm_repo_add() {
    local name=$1 url=$2
    if ! helm repo list 2>/dev/null | awk '{print $1}' | grep -qx "$name"; then
        step "helm repo add $name $url"
        helm repo add "$name" "$url" >/dev/null
    fi
}

helm_install() {
    # helm_install <release> <chart> <version> <namespace> [extra args...]
    local release=$1 chart=$2 version=$3 ns=$4
    shift 4
    step "helm upgrade --install $release $chart --version $version -n $ns"
    if helm upgrade --install "$release" "$chart" \
            --version "$version" \
            -n "$ns" --create-namespace \
            --wait --timeout "$HELM_TIMEOUT" \
            "$@"; then
        ok "$release ($version) installed/upgraded in $ns"
        return 0
    else
        warn "helm upgrade --install $release failed — continuing"
        return 1
    fi
}

# ───── Istio ─────
install_istio() {
    phase "istio"
    if kubectl get ns istio-system >/dev/null 2>&1 \
       && kubectl -n istio-system get deploy istiod >/dev/null 2>&1 \
       && [[ "$(kubectl -n istio-system get deploy istiod -o jsonpath='{.status.readyReplicas}' 2>/dev/null)" -ge 1 ]]; then
        ok "istio already installed (istiod Ready) — skipping"
        info "to upgrade: bump istioctl manually and re-run"
        return 0
    fi
    if ! command -v istioctl >/dev/null 2>&1; then
        warn "istioctl not found — skipping istio install"
        info "install istioctl, then re-run this script"
        return 0
    fi
    step "istioctl install --set profile=default -y"
    istioctl install --set profile=default -y || {
        warn "istioctl install failed — continuing"
        return 0
    }
    ok "istio installed"
}

# ───── Knative Serving ─────
install_knative() {
    phase "knative-serving $KNATIVE_VERSION"
    local base="https://github.com/knative/serving/releases/download/knative-${KNATIVE_VERSION}"
    step "apply CRDs"
    kubectl apply -f "${base}/serving-crds.yaml" || warn "serving-crds apply failed"
    step "apply core"
    kubectl apply -f "${base}/serving-core.yaml" || warn "serving-core apply failed"
    step "apply net-istio"
    local net_base="https://github.com/knative-extensions/net-istio/releases/download/knative-${KNATIVE_VERSION}"
    kubectl apply -f "${net_base}/net-istio.yaml" || warn "net-istio apply failed"
    ok "knative-serving manifests applied"
}

# ───── ArgoCD ─────
install_argocd() {
    phase "argocd"
    # Detect non-Helm-managed ArgoCD (legacy kubectl-apply install). Helm
    # can't adopt resources without `app.kubernetes.io/managed-by: Helm`
    # labels — trying just errors. If detected, skip cleanly so a fresh
    # `kubectl delete ns argocd` followed by re-running this script will
    # do a clean Helm install.
    if kubectl get sa -n argocd argocd-application-controller >/dev/null 2>&1 \
       && ! kubectl get sa -n argocd argocd-application-controller \
              -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null \
              | grep -q "Helm"; then
        warn "ArgoCD is installed via kubectl-apply (not Helm) — skipping."
        warn "To migrate: delete ns argocd, then re-run install-controllers."
        return 0
    fi
    helm_repo_add argo https://argoproj.github.io/argo-helm
    helm repo update argo >/dev/null 2>&1 || true
    helm_install argocd argo/argo-cd "$ARGOCD_CHART_VERSION" argocd
}

# ───── Argo Workflows ─────
install_argo_workflows() {
    phase "argo-workflows"
    helm_repo_add argo https://argoproj.github.io/argo-helm
    helm_install argo-workflows argo/argo-workflows "$ARGO_WF_CHART_VERSION" argo
}

# ───── Argo Events ─────
install_argo_events() {
    phase "argo-events"
    helm_repo_add argo https://argoproj.github.io/argo-helm
    helm_install argo-events argo/argo-events "$ARGO_EVENTS_CHART_VERSION" argo-events
}

# ───── Crossplane ─────
install_crossplane() {
    phase "crossplane $CROSSPLANE_CHART_VERSION"
    helm_repo_add crossplane-stable https://charts.crossplane.io/stable
    helm repo update crossplane-stable >/dev/null 2>&1 || true
    helm_install crossplane crossplane-stable/crossplane "$CROSSPLANE_CHART_VERSION" crossplane-system
    wait_for_crd providers.pkg.crossplane.io 120 || true
}

# ───── Crossplane providers ─────
install_crossplane_providers() {
    phase "crossplane-providers"
    if ! kubectl get crd providers.pkg.crossplane.io >/dev/null 2>&1; then
        warn "providers CRD missing — skipping provider install"
        return 0
    fi
    local tmp
    tmp=$(mktemp)
    cat >"$tmp" <<EOF
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-kubernetes
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-kubernetes:${PROVIDER_KUBERNETES_VERSION}
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-helm
spec:
  package: xpkg.upbound.io/crossplane-contrib/provider-helm:${PROVIDER_HELM_VERSION}
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-github
spec:
  package: xpkg.upbound.io/upbound/provider-github:${PROVIDER_GITHUB_VERSION}
EOF
    step "apply Provider CRs (kubernetes, helm, github)"
    kubectl apply -f "$tmp" || warn "provider apply failed"
    rm -f "$tmp"
    info "providers will install asynchronously; run 'kubectl get providers' to check"
}

# ───── AKS konnectivity webhook workaround ─────
# On fresh AKS installs the managed kube-apiserver can't reach a newly-created
# webhook pod IP through the konnectivity tunnel for ~1-5 min, so any apply of
# Crossplane Compositions/XRDs fails with `code 504: 504 Gateway Timeout` from
# the validation webhook. We temporarily relax failurePolicy from Fail→Ignore,
# run the apply, then restore. Stored state is per-webhook-index so configs
# with any number of webhooks are handled.
#
# Usage:  with_relaxed_webhook kubectl apply -f some/dir/
# Safe to call multiple times; only touches webhooks currently set to Fail.
with_relaxed_webhook() {
    local vwc="crossplane"
    local restored=0
    # Build list of indices currently set to Fail (the ones we will flip).
    local indices_to_restore=()

    if ! kubectl get validatingwebhookconfiguration "$vwc" >/dev/null 2>&1; then
        info "validatingwebhookconfiguration/$vwc not found — running command as-is"
        "$@"
        return $?
    fi

    local webhook_count
    webhook_count=$(kubectl get validatingwebhookconfiguration "$vwc" \
        -o jsonpath='{.webhooks[*].name}' 2>/dev/null | wc -w | tr -d ' ')
    if [[ "$webhook_count" -eq 0 ]]; then
        info "$vwc has no webhooks — running command as-is"
        "$@"
        return $?
    fi

    local patches=()
    local i policy
    for ((i=0; i<webhook_count; i++)); do
        policy=$(kubectl get validatingwebhookconfiguration "$vwc" \
            -o jsonpath="{.webhooks[$i].failurePolicy}" 2>/dev/null || echo "")
        if [[ "$policy" == "Fail" ]]; then
            patches+=("{\"op\":\"replace\",\"path\":\"/webhooks/$i/failurePolicy\",\"value\":\"Ignore\"}")
            indices_to_restore+=("$i")
        fi
    done

    if [[ ${#patches[@]} -eq 0 ]]; then
        info "all $vwc webhooks already failurePolicy!=Fail — no relax needed"
        "$@"
        return $?
    fi

    info "AKS konnectivity workaround: relaxing $vwc failurePolicy Fail→Ignore on indices [${indices_to_restore[*]}] for this apply"
    local relax_patch="[$(IFS=,; echo "${patches[*]}")]"

    restore_webhook() {
        if [[ "$restored" -eq 1 ]]; then return 0; fi
        restored=1
        local restore_patches=()
        local idx
        for idx in "${indices_to_restore[@]}"; do
            restore_patches+=("{\"op\":\"replace\",\"path\":\"/webhooks/$idx/failurePolicy\",\"value\":\"Fail\"}")
        done
        local restore_patch="[$(IFS=,; echo "${restore_patches[*]}")]"
        kubectl patch validatingwebhookconfiguration "$vwc" --type=json \
            -p="$restore_patch" >/dev/null 2>&1 \
            && ok "restored $vwc failurePolicy → Fail on indices [${indices_to_restore[*]}]" \
            || warn "failed to restore $vwc failurePolicy — check manually"
    }
    trap 'restore_webhook' RETURN

    if ! kubectl patch validatingwebhookconfiguration "$vwc" --type=json \
            -p="$relax_patch" >/dev/null 2>&1; then
        warn "failed to patch $vwc to Ignore — running command anyway"
    fi

    local rc=0
    "$@" || rc=$?
    restore_webhook
    trap - RETURN
    return $rc
}

# ───── Post-install substrate (XRDs / Compositions) ─────
# Applies XRDs + Compositions AFTER providers are scheduled. Wrapped with
# with_relaxed_webhook so AKS konnectivity 504s don't block the apply.
apply_post_install_substrate() {
    phase "post-install substrate (XRDs / Compositions)"
    # Brief grace period for crossplane core + providers to become reachable
    # before we touch the validating webhook.
    local elapsed=0
    while ! kubectl -n crossplane-system get deploy crossplane >/dev/null 2>&1; do
        sleep 3; elapsed=$((elapsed+3))
        [[ "$elapsed" -ge 30 ]] && break
    done
    kubectl -n crossplane-system wait --for=condition=Available \
        deploy/crossplane --timeout=120s >/dev/null 2>&1 || \
        warn "crossplane deploy not yet Available — proceeding anyway"

    local applied=0 errored=0
    local targets=(
        "$REPO_ROOT/substrate/crossplane/"
        "$REPO_ROOT/production-lines/traditional-cloud/adapters/composition/"
    )
    local t
    for t in "${targets[@]}"; do
        if [[ ! -d "$t" ]]; then
            info "skip (not found): $t"
            continue
        fi
        step "apply $t"
        if with_relaxed_webhook kubectl apply -f "$t"; then
            applied=$((applied+1))
            ok "applied: $t"
        else
            errored=$((errored+1))
            warn "errored: $t"
        fi
    done
    info "post-install substrate: applied=$applied errored=$errored"
}

# ───── KubeVela ─────
install_kubevela() {
    phase "kubevela $KUBEVELA_CHART_VERSION"
    helm_repo_add kubevela https://kubevela.github.io/charts
    helm repo update kubevela >/dev/null 2>&1 || true
    helm_install kubevela kubevela/vela-core "$KUBEVELA_CHART_VERSION" vela-system
}

# ───── External Secrets ─────
install_external_secrets() {
    phase "external-secrets $EXTERNAL_SECRETS_CHART_VERSION"
    helm_repo_add external-secrets https://charts.external-secrets.io
    helm repo update external-secrets >/dev/null 2>&1 || true
    helm_install external-secrets external-secrets/external-secrets \
        "$EXTERNAL_SECRETS_CHART_VERSION" external-secrets
}

# ───── Post-install configs (substrate/knative overlays etc.) ─────
apply_post_install_configs() {
    phase "post-install configs"
    if [[ -d "$REPO_ROOT/substrate/knative" ]]; then
        apply_dir_recursive "$REPO_ROOT/substrate/knative"
    else
        info "no substrate/knative dir — skipping"
    fi
}

# ───── CRD readiness gate ─────
verify_crds() {
    phase "verify critical CRDs"
    wait_for_crd services.serving.knative.dev 180 || true
    wait_for_crd providers.pkg.crossplane.io 120 || true
    wait_for_crd workflowtemplates.argoproj.io 120 || true
    wait_for_crd componentdefinitions.core.oam.dev 180 || true
}

# ───── Summary ─────
summary() {
    phase "summary"
    echo "Releases:" >&2
    helm list -A 2>/dev/null | grep -E "argo-cd|argo-workflows|argo-events|crossplane|kubevela|external-secrets" || true
    echo >&2
    echo "Crossplane providers:" >&2
    kubectl get providers.pkg.crossplane.io 2>/dev/null || true
}

# ───── Main ─────
# `set -e` would abort on first warn. We want to see the full picture across
# all 8 components, so each install call is gated with `|| true`.
install_istio                || true
install_knative              || true
install_argocd               || true
install_argo_workflows       || true
install_argo_events          || true
install_crossplane           || true
install_crossplane_providers || true
apply_post_install_substrate || true
install_kubevela             || true
install_external_secrets     || true
apply_post_install_configs   || true
verify_crds                  || true
summary                      || true

ok "install-controllers complete"
