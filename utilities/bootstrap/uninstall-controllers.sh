#!/usr/bin/env bash
# uninstall-controllers.sh
# Reciprocal of install-controllers.sh. DESTRUCTIVE.
# Tears down platform controllers in reverse install order so CRDs/webhooks
# aren't yanked out from under their own custom resources.
#
# Usage:
#   ./uninstall-controllers.sh                # interactive, deletes PVCs
#   ./uninstall-controllers.sh --yes          # no prompt
#   ./uninstall-controllers.sh --keep-data    # preserve PVCs
#   ./uninstall-controllers.sh --yes --keep-data

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "${SCRIPT_DIR}/helpers/common.sh"

# ───── Flags ─────
YES=false
KEEP_DATA=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes)        YES=true; shift ;;
        --keep-data)  KEEP_DATA=true; shift ;;
        -h|--help)
            sed -n '1,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) err "unknown flag: $1"; exit 2 ;;
    esac
done

phase "uninstall-controllers (DESTRUCTIVE)"

require_cmd kubectl
require_cmd helm
require_kubectl_context

warn "═══════════════════════════════════════════════════════════════════════"
warn "  ABOUT TO UNINSTALL THE FOLLOWING FROM THE CURRENT CLUSTER:"
warn "    - OAM ComponentDefinitions / TraitDefinitions / Policy / WorkflowStep"
warn "    - Crossplane ApplicationClaims, AppContainerClaims, Compositions, XRDs"
warn "    - Crossplane Providers + ProviderConfigs"
warn "    - External Secrets Operator (helm release + CRDs + ns)"
warn "    - KubeVela (helm release + CRDs + ns)"
warn "    - Crossplane (helm release + CRDs + ns)"
warn "    - Argo Events (helm release + ns)"
warn "    - Argo Workflows (helm release + CRDs + ns)"
warn "    - ArgoCD (helm release + CRDs + ns)"
warn "    - Knative Serving (net-istio, serving-core, serving-crds + ns)"
warn "  Istio is NOT removed by default."
warn "═══════════════════════════════════════════════════════════════════════"
if [[ "$KEEP_DATA" == "true" ]]; then
    info "(--keep-data) PersistentVolumeClaims will be preserved"
else
    warn "(no --keep-data) PersistentVolumeClaims in the above namespaces WILL be deleted"
fi

if [[ "$YES" != "true" ]]; then
    echo -n "  type 'yes' to proceed: " >&2
    read -r ans
    [[ "$ans" == "yes" ]] || { info "cancelled"; exit 0; }
fi

# ───── Generic helpers ─────

# Strip finalizers from every instance of a (possibly namespaced) CR kind so it
# can actually be deleted. Safe if the CRD is absent.
strip_finalizers() {
    local kind=$1
    kubectl get "$kind" -A --no-headers --ignore-not-found 2>/dev/null \
      | awk '{print $1" "$2}' \
      | while read -r ns name; do
            [[ -z "$name" ]] && continue
            if [[ "$ns" == "<none>" || -z "$ns" ]]; then
                kubectl patch "$kind" "$name" \
                    --type=merge -p '{"metadata":{"finalizers":[]}}' \
                    >/dev/null 2>&1 || true
            else
                kubectl patch "$kind" "$name" -n "$ns" \
                    --type=merge -p '{"metadata":{"finalizers":[]}}' \
                    >/dev/null 2>&1 || true
            fi
        done
}

# Delete every instance of a CR kind across all namespaces, finalizers first.
delete_all_of_kind() {
    local kind=$1
    kubectl get "$kind" -A --no-headers --ignore-not-found 2>/dev/null \
      | head -1 >/dev/null || return 0
    step "strip finalizers + delete: $kind"
    strip_finalizers "$kind"
    kubectl delete "$kind" --all -A --wait=false --ignore-not-found \
        >/dev/null 2>&1 || true
}

# helm uninstall that doesn't fail if the release is gone.
helm_uninstall_safe() {
    local release=$1 ns=$2
    if helm status "$release" -n "$ns" >/dev/null 2>&1; then
        step "helm uninstall $release -n $ns"
        helm uninstall "$release" -n "$ns" --wait=false --ignore-not-found 2>&1 \
            | sed 's/^/    /' || true
        ok "helm release $release removed"
    else
        info "skip (no helm release $release in $ns)"
    fi
}

# Delete CRDs by name list. Strips finalizers from all CRs first so deletion
# doesn't block on dangling instances.
delete_crds() {
    local crd
    for crd in "$@"; do
        if kubectl get crd "$crd" >/dev/null 2>&1; then
            strip_finalizers "$crd"
            step "kubectl delete crd $crd"
            kubectl delete crd "$crd" --wait=false --ignore-not-found \
                >/dev/null 2>&1 || true
        fi
    done
}

# Delete a namespace. If --keep-data, scrub PVCs out of the delete (preserve
# them via reclaim). Otherwise let the ns delete take the PVCs with it.
delete_namespace() {
    local ns=$1
    if ! kubectl get ns "$ns" >/dev/null 2>&1; then
        info "skip (ns $ns absent)"
        return 0
    fi
    if [[ "$KEEP_DATA" == "true" ]]; then
        # Protect PVs from being garbage-collected with the namespace.
        kubectl get pvc -n "$ns" --no-headers --ignore-not-found 2>/dev/null \
          | awk '{print $1" "$3}' \
          | while read -r pvc pv; do
                [[ -z "$pv" || "$pv" == "<none>" ]] && continue
                kubectl patch pv "$pv" \
                    -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}' \
                    >/dev/null 2>&1 || true
                info "  retained pv $pv (was bound to $ns/$pvc)"
            done
    fi
    step "kubectl delete ns $ns"
    # Strip finalizers off lingering CRs in the ns so it doesn't get stuck.
    kubectl api-resources --verbs=list --namespaced -o name 2>/dev/null \
      | xargs -I{} -n1 kubectl get {} -n "$ns" --ignore-not-found -o name 2>/dev/null \
      | while read -r obj; do
            [[ -z "$obj" ]] && continue
            kubectl patch "$obj" -n "$ns" \
                --type=merge -p '{"metadata":{"finalizers":[]}}' \
                >/dev/null 2>&1 || true
        done
    kubectl delete ns "$ns" --wait=false --ignore-not-found \
        >/dev/null 2>&1 || true
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 1 — OAM definitions (must die BEFORE KubeVela CRDs vanish)
# ────────────────────────────────────────────────────────────────────────────
cleanup_oam_definitions() {
    phase "OAM definitions cleanup"
    if ! kubectl get crd componentdefinitions.core.oam.dev >/dev/null 2>&1; then
        info "skip (OAM CRDs not installed)"
        return 0
    fi
    local kind
    for kind in \
        applications.core.oam.dev \
        componentdefinitions.core.oam.dev \
        traitdefinitions.core.oam.dev \
        policydefinitions.core.oam.dev \
        workflowstepdefinitions.core.oam.dev
    do
        delete_all_of_kind "$kind"
    done
    ok "OAM CRs deleted"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 2 — Crossplane claims + XRDs (so providers clean up cleanly)
# ────────────────────────────────────────────────────────────────────────────
cleanup_crossplane_claims_and_xrds() {
    phase "Crossplane claims + Compositions + XRDs"
    if ! kubectl get crd compositions.apiextensions.crossplane.io >/dev/null 2>&1; then
        info "skip (Crossplane CRDs not installed)"
        return 0
    fi

    # Claims first (delete the things users care about).
    local kind
    for kind in \
        applicationclaims.platform.example.org \
        appcontainerclaims.platform.example.org
    do
        delete_all_of_kind "$kind"
    done

    # Then any composite resources defined by user XRDs.
    local xrd_list
    xrd_list=$(kubectl get xrd -o jsonpath='{range .items[*]}{.spec.names.kind}{"\n"}{end}' 2>/dev/null || true)
    if [[ -n "$xrd_list" ]]; then
        while read -r xrd_kind; do
            [[ -z "$xrd_kind" ]] && continue
            delete_all_of_kind "$xrd_kind"
        done <<<"$xrd_list"
    fi

    # Compositions + XRDs themselves.
    step "delete Compositions"
    strip_finalizers compositions.apiextensions.crossplane.io
    kubectl delete compositions.apiextensions.crossplane.io --all \
        --wait=false --ignore-not-found >/dev/null 2>&1 || true

    step "delete CompositeResourceDefinitions"
    strip_finalizers xrd
    kubectl delete xrd --all --wait=false --ignore-not-found \
        >/dev/null 2>&1 || true

    ok "Crossplane claims + Compositions + XRDs deleted"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 3 — External Secrets Operator
# ────────────────────────────────────────────────────────────────────────────
uninstall_external_secrets() {
    phase "External Secrets Operator"
    # Drop CRs first so finalizers release.
    local kind
    for kind in \
        externalsecrets.external-secrets.io \
        secretstores.external-secrets.io \
        clustersecretstores.external-secrets.io \
        pushsecrets.external-secrets.io
    do
        delete_all_of_kind "$kind" 2>/dev/null || true
    done

    helm_uninstall_safe external-secrets external-secrets

    delete_crds \
        externalsecrets.external-secrets.io \
        secretstores.external-secrets.io \
        clustersecretstores.external-secrets.io \
        clusterexternalsecrets.external-secrets.io \
        pushsecrets.external-secrets.io \
        clusterpushsecrets.external-secrets.io \
        acraccesstokens.generators.external-secrets.io \
        ecrauthorizationtokens.generators.external-secrets.io \
        fakes.generators.external-secrets.io \
        gcraccesstokens.generators.external-secrets.io \
        githubaccesstokens.generators.external-secrets.io \
        passwords.generators.external-secrets.io \
        vaultdynamicsecrets.generators.external-secrets.io \
        webhooks.generators.external-secrets.io

    delete_namespace external-secrets
    ok "external-secrets removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 4 — KubeVela
# ────────────────────────────────────────────────────────────────────────────
uninstall_kubevela() {
    phase "KubeVela"
    helm_uninstall_safe kubevela vela-system

    delete_crds \
        applications.core.oam.dev \
        applicationrevisions.core.oam.dev \
        componentdefinitions.core.oam.dev \
        traitdefinitions.core.oam.dev \
        policydefinitions.core.oam.dev \
        workflowstepdefinitions.core.oam.dev \
        workflows.core.oam.dev \
        workflowruns.core.oam.dev \
        definitionrevisions.core.oam.dev \
        resourcetrackers.core.oam.dev \
        scopedefinitions.core.oam.dev \
        healthscopes.core.oam.dev \
        envbindings.core.oam.dev

    delete_namespace vela-system
    ok "kubevela removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 5 — Crossplane providers (before the core)
# ────────────────────────────────────────────────────────────────────────────
uninstall_crossplane_providers() {
    phase "Crossplane providers + ProviderConfigs"
    if ! kubectl get crd providers.pkg.crossplane.io >/dev/null 2>&1; then
        info "skip (crossplane pkg CRDs not installed)"
        return 0
    fi

    # ProviderConfigs are provider-specific; iterate any CRD named providerconfigs.*
    local pc_crd
    while read -r pc_crd; do
        [[ -z "$pc_crd" ]] && continue
        delete_all_of_kind "$pc_crd" 2>/dev/null || true
    done < <(kubectl get crd -o name 2>/dev/null | sed 's|^customresourcedefinition.apiextensions.k8s.io/||' | grep -E '^providerconfigs\.' || true)

    delete_all_of_kind providers.pkg.crossplane.io
    delete_all_of_kind configurations.pkg.crossplane.io
    delete_all_of_kind functions.pkg.crossplane.io
    ok "providers + configurations + functions deleted"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 6 — Crossplane core
# ────────────────────────────────────────────────────────────────────────────
uninstall_crossplane() {
    phase "Crossplane core"
    helm_uninstall_safe crossplane crossplane-system

    # Strip finalizers from any lingering Crossplane CRs across all CRDs in
    # the crossplane.io group, then delete the CRDs themselves.
    local crd
    while read -r crd; do
        [[ -z "$crd" ]] && continue
        strip_finalizers "$crd"
        kubectl delete crd "$crd" --wait=false --ignore-not-found \
            >/dev/null 2>&1 || true
    done < <(kubectl get crd -o name 2>/dev/null \
        | sed 's|^customresourcedefinition.apiextensions.k8s.io/||' \
        | grep -E '\.(crossplane\.io|pkg\.crossplane\.io|apiextensions\.crossplane\.io|platform\.example\.org)$' || true)

    delete_namespace crossplane-system
    ok "crossplane removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 7 — Argo Events
# ────────────────────────────────────────────────────────────────────────────
uninstall_argo_events() {
    phase "Argo Events"
    local kind
    for kind in \
        eventbus.argoproj.io \
        eventsources.argoproj.io \
        sensors.argoproj.io
    do
        delete_all_of_kind "$kind" 2>/dev/null || true
    done

    helm_uninstall_safe argo-events argo-events

    delete_crds \
        eventbus.argoproj.io \
        eventsources.argoproj.io \
        sensors.argoproj.io

    delete_namespace argo-events
    ok "argo-events removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 8 — Argo Workflows
# ────────────────────────────────────────────────────────────────────────────
uninstall_argo_workflows() {
    phase "Argo Workflows"
    local kind
    for kind in \
        workflows.argoproj.io \
        workflowtemplates.argoproj.io \
        clusterworkflowtemplates.argoproj.io \
        cronworkflows.argoproj.io \
        workfloweventbindings.argoproj.io \
        workflowartifactgctasks.argoproj.io \
        workflowtaskresults.argoproj.io \
        workflowtasksets.argoproj.io
    do
        delete_all_of_kind "$kind" 2>/dev/null || true
    done

    helm_uninstall_safe argo-workflows argo

    delete_crds \
        workflows.argoproj.io \
        workflowtemplates.argoproj.io \
        clusterworkflowtemplates.argoproj.io \
        cronworkflows.argoproj.io \
        workfloweventbindings.argoproj.io \
        workflowartifactgctasks.argoproj.io \
        workflowtaskresults.argoproj.io \
        workflowtasksets.argoproj.io

    delete_namespace argo
    ok "argo-workflows removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 9 — ArgoCD
# ────────────────────────────────────────────────────────────────────────────
uninstall_argocd() {
    phase "ArgoCD"
    local kind
    for kind in \
        applications.argoproj.io \
        applicationsets.argoproj.io \
        appprojects.argoproj.io
    do
        delete_all_of_kind "$kind" 2>/dev/null || true
    done

    helm_uninstall_safe argo-cd argocd

    delete_crds \
        applications.argoproj.io \
        applicationsets.argoproj.io \
        appprojects.argoproj.io

    delete_namespace argocd
    ok "argocd removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 10 — Knative Serving
# ────────────────────────────────────────────────────────────────────────────
uninstall_knative() {
    phase "Knative Serving"
    if ! kubectl get ns knative-serving >/dev/null 2>&1 \
        && ! kubectl get crd services.serving.knative.dev >/dev/null 2>&1; then
        info "skip (knative-serving absent)"
        return 0
    fi

    # Drop user-facing CRs first.
    local kind
    for kind in \
        services.serving.knative.dev \
        configurations.serving.knative.dev \
        revisions.serving.knative.dev \
        routes.serving.knative.dev
    do
        delete_all_of_kind "$kind" 2>/dev/null || true
    done

    # If installers left the original yaml URLs reachable, prefer reverse-order
    # `kubectl delete -f`; else fall back to namespace + CRD scrub.
    local KNATIVE_VERSION="${KNATIVE_VERSION:-v1.13.1}"
    local urls=(
        "https://github.com/knative-extensions/net-istio/releases/download/knative-${KNATIVE_VERSION}/net-istio.yaml"
        "https://github.com/knative/serving/releases/download/knative-${KNATIVE_VERSION}/serving-core.yaml"
        "https://github.com/knative/serving/releases/download/knative-${KNATIVE_VERSION}/serving-crds.yaml"
    )
    local u
    for u in "${urls[@]}"; do
        step "kubectl delete -f $u  (best-effort)"
        kubectl delete --wait=false --ignore-not-found -f "$u" \
            >/dev/null 2>&1 || true
    done

    # Belt-and-braces: nuke remaining knative CRDs + ns.
    local crd
    while read -r crd; do
        [[ -z "$crd" ]] && continue
        strip_finalizers "$crd"
        kubectl delete crd "$crd" --wait=false --ignore-not-found \
            >/dev/null 2>&1 || true
    done < <(kubectl get crd -o name 2>/dev/null \
        | sed 's|^customresourcedefinition.apiextensions.k8s.io/||' \
        | grep -E '\.knative\.dev$' || true)

    delete_namespace knative-serving
    delete_namespace knative-eventing 2>/dev/null || true
    ok "knative removed"
}

# ────────────────────────────────────────────────────────────────────────────
# Phase 11 — Istio (opt-in only; mutates cluster-wide)
# ────────────────────────────────────────────────────────────────────────────
maybe_uninstall_istio() {
    phase "Istio (opt-in)"
    if ! kubectl get ns istio-system >/dev/null 2>&1; then
        info "skip (istio-system absent)"
        return 0
    fi
    if ! command -v istioctl >/dev/null 2>&1; then
        info "skip (istioctl not on PATH); to remove manually:"
        info "  istioctl uninstall --purge -y && kubectl delete ns istio-system"
        return 0
    fi
    warn "Istio removal affects EVERY workload in the cluster."
    if [[ "$YES" == "true" ]]; then
        info "skip (running --yes; refusing to auto-purge Istio)"
        info "  run manually: istioctl uninstall --purge -y && kubectl delete ns istio-system"
        return 0
    fi
    echo -n "  type 'purge-istio' to remove istio: " >&2
    read -r ans
    if [[ "$ans" != "purge-istio" ]]; then
        info "skip (istio left in place)"
        return 0
    fi
    step "istioctl uninstall --purge -y"
    istioctl uninstall --purge -y 2>&1 | sed 's/^/    /' || true
    delete_namespace istio-system
    ok "istio removed"
}

# ───── Execute in reverse-install order ─────
cleanup_oam_definitions
cleanup_crossplane_claims_and_xrds
uninstall_external_secrets
uninstall_kubevela
uninstall_crossplane_providers
uninstall_crossplane
uninstall_argo_events
uninstall_argo_workflows
uninstall_argocd
uninstall_knative
maybe_uninstall_istio

# ───── Summary ─────
phase "post-uninstall state"
info "helm releases remaining:"
helm list -A 2>&1 | sed 's/^/  /' || true
echo "" >&2
info "non-system namespaces remaining:"
kubectl get ns 2>&1 \
    | grep -vE '^(NAME|kube-|default[[:space:]]|local-path-storage[[:space:]])' \
    | sed 's/^/  /' \
    || true
echo "" >&2
info "CRDs remaining (filtered):"
kubectl get crd 2>&1 \
    | grep -E '(oam\.dev|crossplane\.io|argoproj\.io|knative\.dev|external-secrets\.io)' \
    | sed 's/^/  /' \
    || info "  none from removed controllers"
echo "" >&2

ok "uninstall-controllers complete"
if [[ "$KEEP_DATA" == "true" ]]; then
    info "PVs that were Retained may need manual cleanup (kubectl get pv)"
fi
