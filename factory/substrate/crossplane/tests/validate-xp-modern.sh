#!/usr/bin/env bash
#
# XP-MODERN (#158/#155/#156) validation: the realtime + graphql Crossplane
# Compositions were rewritten from legacy spec.resources patch-and-transform to the
# platform-idiomatic Crossplane v2 function-go-templating pipeline.
#
# Verifies, WITHOUT a live cluster:
#   (a) both rewritten composition YAML files parse;
#   (b) both are mode: Pipeline with a function-go-templating step (the exact
#       Function name used by the reference application-claim-composition);
#   (c) every composed resource uses kubernetes.m.crossplane.io/v1alpha1 Object +
#       ClusterProviderConfig 'kubernetes-provider' (the v2-idiomatic namespaced API,
#       NOT the cluster-scoped kubernetes.crossplane.io API);
#   (d) gotemplating composition-resource-name annotations are unique within each file;
#   (e) go-template if/range/end tokens balance in each rendered template body;
#   (f) the realtime topic-provisioning Job ranges over $spec.topics and emits a
#       per-topic create_topic call (RT-1 deferred limitation lifted);
#   (g) the duplicate realtime XRD has been archived (only the canonical one remains).
#
# Usage: bash factory/substrate/crossplane/tests/validate-xp-modern.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

RT="$ROOT/factory/substrate/crossplane/realtime-platform-claim-composition.yaml"
GQL="$ROOT/factory/substrate/crossplane/graphql-platform-claim-composition.yaml"
RT_XRD="$ROOT/factory/substrate/crossplane/realtime-platform-claim-xrd.yaml"
DUP_XRD="$ROOT/factory/substrate/crossplane/realtime-xrds.yaml"
ARCHIVE="$ROOT/factory/production-lines/traditional-cloud/adapters/execute/_archive"

fail() { echo "FAIL: $1"; exit 1; }
pass() { echo "PASS: $1"; }

[ -f "$RT" ]  || fail "missing $RT"
[ -f "$GQL" ] || fail "missing $GQL"

# (a) YAML parse both files
python3 - "$RT" "$GQL" <<'PY' || fail "YAML parse failed"
import sys, yaml
for p in sys.argv[1:]:
    with open(p) as f:
        docs = list(yaml.safe_load_all(f))
    assert docs and docs[0].get("kind") == "Composition", f"{p} not a Composition"
print("yaml-ok")
PY
pass "both rewritten composition files parse as YAML"

# (b) pipeline mode + exact function names
python3 - "$RT" "$GQL" <<'PY' || fail "pipeline structure invalid"
import sys, yaml
for p in sys.argv[1:]:
    d = yaml.safe_load(open(p))
    assert d["spec"]["mode"] == "Pipeline", f"{p} not mode: Pipeline"
    steps = d["spec"]["pipeline"]
    fns = [s["functionRef"]["name"] for s in steps]
    assert "function-go-templating" in fns, f"{p} missing function-go-templating step"
    # 'resources:' (legacy P&T) must be gone from spec
    assert "resources" not in d["spec"], f"{p} still has legacy spec.resources"
print("pipeline-ok")
PY
pass "both are mode: Pipeline with a function-go-templating step; legacy spec.resources gone"

# (c) every Object uses .m.crossplane.io/v1alpha1 + ClusterProviderConfig kubernetes-provider
python3 - "$RT" "$GQL" <<'PY' || fail "Object API / providerConfig drift"
import sys, yaml
for p in sys.argv[1:]:
    d = yaml.safe_load(open(p))
    tmpl = d["spec"]["pipeline"][0]["input"]["inline"]["template"]
    # the inline template is a string of YAML docs; parse the rendered-ish objects by
    # stripping go-template lines for a structural check.
    import re
    txt = tmpl
    bad_api = re.findall(r'apiVersion:\s*kubernetes\.crossplane\.io/v1alpha\d', txt)
    assert not bad_api, f"{p} uses cluster-scoped kubernetes.crossplane.io API (forbidden): {bad_api[:1]}"
    n_obj = txt.count("kind: Object")
    n_m   = txt.count("apiVersion: kubernetes.m.crossplane.io/v1alpha1")
    n_cpc = txt.count("kind: ClusterProviderConfig")
    n_kp  = txt.count("name: kubernetes-provider")
    assert n_obj == n_m == n_cpc, f"{p} Object/.m-api/ClusterProviderConfig count mismatch: obj={n_obj} m={n_m} cpc={n_cpc}"
    assert n_kp >= n_obj, f"{p} not every Object references kubernetes-provider ({n_kp}/{n_obj})"
    print(f"{p.split('/')[-1]}: {n_obj} Objects, all .m/v1alpha1 + ClusterProviderConfig/kubernetes-provider")
PY
pass "every composed resource is kubernetes.m.crossplane.io/v1alpha1 Object + ClusterProviderConfig/kubernetes-provider"

# (d) composition-resource-name annotation uniqueness
python3 - "$RT" "$GQL" <<'PY' || fail "duplicate composition-resource-name"
import sys, yaml, re
for p in sys.argv[1:]:
    d = yaml.safe_load(open(p))
    tmpl = d["spec"]["pipeline"][0]["input"]["inline"]["template"]
    names = re.findall(r'composition-resource-name:\s*(\S+)', tmpl)
    assert len(names) == len(set(names)), f"{p} duplicate resource-name(s): {[n for n in names if names.count(n)>1]}"
    print(f"{p.split('/')[-1]}: {len(names)} unique composition-resource-name annotations")
PY
pass "composition-resource-name annotations are unique within each file"

# (e) go-template if/range/end balance in the rendered template body
python3 - "$RT" "$GQL" <<'PY' || fail "go-template token imbalance"
import sys, yaml, re
for p in sys.argv[1:]:
    d = yaml.safe_load(open(p))
    tmpl = d["spec"]["pipeline"][0]["input"]["inline"]["template"]
    ifs  = len(re.findall(r'\{\{-?\s*if\b', tmpl))
    rng  = len(re.findall(r'\{\{-?\s*range\b', tmpl))
    ends = len(re.findall(r'\{\{-?\s*end\s*\}\}', tmpl))
    assert ends == ifs + rng, f"{p} imbalance: if={ifs} range={rng} end={ends}"
    print(f"{p.split('/')[-1]}: balanced if={ifs} range={rng} end={ends}")
PY
pass "go-template if/range/end tokens balanced in both files"

# (f) RT-1 lift: per-topic range in the topic-provisioning Job
python3 - "$RT" <<'PY' || fail "topic-provisioning is not per-topic"
import sys, yaml, re
d = yaml.safe_load(open(sys.argv[1]))
tmpl = d["spec"]["pipeline"][0]["input"]["inline"]["template"]
assert "range $t := $spec.topics" in tmpl, "missing range over spec.topics"
assert re.search(r'create_topic "\{\{ \$t\.name \}\}" "\{\{ \$t\.partitions[^"]*\}\}" "\{\{ \$t\.retention[^"]*\}\}"', tmpl), \
    "per-topic create_topic with exact partitions/retention not found"
# backward-compatible fallback to the health-domain seed set
assert "seeding default health-domain set" in tmpl, "missing empty-topics fallback"
# the legacy single TOPIC_PARTITIONS/TOPIC_RETENTION env-driven loop must be gone
assert "TOPIC_PARTITIONS" not in tmpl and "grep '^TOPIC_'" not in tmpl, \
    "legacy cluster-wide TOPIC_* env loop still present"
print("per-topic provisioning OK; legacy cluster-wide TOPIC_* loop removed")
PY
pass "topic-provisioning Job ranges over spec.topics with exact per-topic partitions/retention (RT-1 lifted)"

# (g) duplicate realtime XRD archived; canonical remains
[ -f "$RT_XRD" ] || fail "canonical realtime XRD missing: $RT_XRD"
[ ! -f "$DUP_XRD" ] || fail "duplicate realtime-xrds.yaml still present at $DUP_XRD (should be archived)"
[ -f "$ARCHIVE/realtime-xrds.yaml" ] || fail "duplicate not found in archive: $ARCHIVE/realtime-xrds.yaml"
python3 - "$RT_XRD" <<'PY' || fail "canonical XRD missing spec.topics"
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
props = d["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]["properties"]
assert "topics" in props, "canonical XRD missing spec.topics (RT-1 field)"
print("canonical XRD has spec.topics:", list(props["topics"]["items"]["properties"].keys()))
PY
pass "duplicate realtime XRD archived; canonical RT-1-extended XRD retained"

echo "ALL CHECKS PASSED"
