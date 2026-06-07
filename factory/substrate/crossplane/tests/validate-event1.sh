#!/usr/bin/env bash
# EVENT-1 (#150) validation: composition-level ordering replaces the mscv poll.
#
# Verifies, WITHOUT a live cluster:
#   (a) both composition YAML files parse;
#   (b) the GitHub Contents-API poll loop is gone from the mscv script;
#   (c) the source-repo-setup ordering gate exists in the AppContainerClaim
#       composition and is wired to the verified observable field
#       (status.atProvider.manifest.status.succeeded via getComposedResource);
#   (d) go-template if/range/end tokens balance in the conditional-delivery step.
#
# Usage: bash factory/substrate/crossplane/tests/validate-event1.sh
set -euo pipefail

# Resolve repo root from this script's location (tests/ -> crossplane -> substrate -> factory -> root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

ACC="$ROOT/factory/substrate/crossplane/app-container-claim-composition.yaml"
APC="$ROOT/factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml"

fail() { echo "FAIL: $1"; exit 1; }
pass() { echo "PASS: $1"; }

[ -f "$ACC" ] || fail "missing $ACC"
[ -f "$APC" ] || fail "missing $APC"

# (a) YAML parse both files
python3 - "$ACC" "$APC" <<'PY' || fail "YAML parse failed"
import sys, yaml
for p in sys.argv[1:]:
    with open(p) as f:
        list(yaml.safe_load_all(f))
print("yaml-ok")
PY
pass "both composition files parse as YAML"

# (b) poll loop removed from mscv script. Match the LIVE shell statements (not
# comment references): the echo poll banner, the bounded seq loop, and the
# Contents-API URL the loop curled.
# The live poll banner was `echo "Waiting for CI workflow file in remote..."`.
# After removal the only remaining reference is the EVENT-1 explainer comment
# (a `#` line), so assert no ACTIVE echo statement targets it.
if grep -q 'echo \\"Waiting for CI workflow file in remote before pushing' "$APC"; then
  fail "mscv poll echo statement still present in $APC"
fi
# The poll curled the Contents API for the workflow file; that URL must be gone.
# (An unrelated `seq 1 60` poll for a vCluster secret in register-argocd is fine.)
if grep -q 'contents/.github/workflows/comprehensive-gitops.yml' "$APC"; then
  fail "mscv Contents-API poll URL still present in $APC"
fi
pass "mscv poll loop removed from ApplicationClaim composition"

# mscv must still rebase before push (UNIFY-1 sibling-race handling kept)
grep -q 'git pull --rebase origin HEAD' "$APC" || fail "mscv lost its git pull --rebase"
pass "mscv retains git pull --rebase (UNIFY-1 push-retry intact)"

# (c) ordering gate present and wired to the observable field
grep -q 'getComposedResource . "source-repo-setup"' "$ACC" || fail "gate missing getComposedResource lookup"
grep -q '\$srsReady' "$ACC" || fail "gate missing \$srsReady flag"
grep -q 'dig "succeeded" 0 \$atp' "$ACC" || fail "gate not reading atProvider status.succeeded"
grep -q 'policy: SuccessfulCreate' "$ACC" || fail "source-repo-setup missing explicit readiness policy"
grep -q 'EVENT-1' "$ACC" || fail "EVENT-1 ordering-contract comment missing"
pass "ordering gate present and wired to status.atProvider.manifest.status.succeeded"

# (d) go-template if/range == end balance in the conditional-delivery step
python3 - "$ACC" <<'PY' || fail "go-template token imbalance"
import sys, re
t = open(sys.argv[1]).read()
region = t[t.index("step: conditional-delivery"):]
ifs    = len(re.findall(r'\{\{-?\s*if\b', region))
rng    = len(re.findall(r'\{\{-?\s*range\b', region))
ends   = len(re.findall(r'\{\{-?\s*end\s*\}\}', region))
assert ends == ifs + rng, f"imbalance: if={ifs} range={rng} end={ends}"
print(f"balanced if={ifs} range={rng} end={ends}")
PY
pass "go-template if/range/end balanced in conditional-delivery step"

echo "ALL CHECKS PASSED"
