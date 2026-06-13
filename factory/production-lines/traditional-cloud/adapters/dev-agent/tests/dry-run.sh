#!/usr/bin/env bash
# DEV-AGENT W2-W4: lightweight dry-run harness (mirrors mscv-image/tests/dry-run.sh).
#
# Exercises entrypoint.sh + verify-loop.sh with git/kubectl/opencode stubbed via
# PATH shims against tmpdir fixtures. No cluster, no network, no APIM key.
# macOS-safe: the agent scripts use python3 (not sed/jq) for all parsing.
#
# ENGINE: the coding engine is opencode (GPT-5.4 via APIM); the stub asserts the
# exact `opencode run` invocation the entrypoint must emit.
#
# Assertions:
#   1. REQUIREMENTS.md 3-location fallback ORDER: source root > gitops root >
#      central ledger (oam/applications/<app>-REQUIREMENTS.md)
#   2. opencode is invoked: prompt (positional) CONTAINS the REQUIREMENTS content,
#      and the flags carry --dir, -m apim-gpt/gpt-5.4, --dangerously-skip-permissions
#   3. commit+push happen ONLY when opencode actually changed files
#   4. verify-loop parses pass/fail verdicts; red verdict detail is fed into
#      the next iteration's prompt; bounded by MAX_ITERATIONS
#   5. all-Ready gate exits 0 quietly when a sibling component is unready
#   6. spec-hash marker short-circuits a re-run for an already-implemented spec
#   7. no REQUIREMENTS.md anywhere -> quiet exit 0, opencode never invoked
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "$HERE/../scripts" && pwd)"
ENTRYPOINT="$SCRIPTS_DIR/entrypoint.sh"

PASS=0; FAIL=0
ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

PYTHON_BIN_DIR="$(dirname "$(command -v python3)")"

# ---------------------------------------------------------------------------
# PATH shims: git / kubectl / opencode. Behaviour driven by env knobs:
#   GIT_PUSH_MODE=ok|reject   OPENCODE_MODE=edit|noop
#   KSVC_READY_MODE=all|one-unready   CT_SEQUENCE="fail pass" (verdict per push)
#   SOURCE_FIXTURE / GITOPS_FIXTURE / LEDGER_FIXTURE   DA_STATE (run state dir)
# ---------------------------------------------------------------------------
STUB_DIR="$ROOT/bin"
mkdir -p "$STUB_DIR"

cat > "$STUB_DIR/git" <<'STUBEOF'
#!/usr/bin/env bash
cmd="${1:-}"; shift || true
case "$cmd" in
  clone)
    pos=()
    for a in "$@"; do case "$a" in --*) ;; *) pos+=("$a");; esac; done
    url="${pos[0]:-}"; dest="${pos[1]:-.}"
    case "$url" in
      *health-service-idp-gitops.git) src="${LEDGER_FIXTURE:-}";;
      *-gitops.git)                   src="${GITOPS_FIXTURE:-}";;
      *)                              src="${SOURCE_FIXTURE:-}";;
    esac
    if [ -z "$src" ] || [ ! -d "$src" ]; then
      echo "stub git: no fixture for $url" >&2; exit 128
    fi
    mkdir -p "$dest"; cp -R "$src/." "$dest/"
    exit 0;;
  status)
    # --porcelain: the claude stub records its edits in .claude-changed
    if [ -f .claude-changed ]; then
      while IFS= read -r p; do echo " M $p"; done < .claude-changed
    fi
    exit 0;;
  commit)
    rm -f .claude-changed
    echo "commit $*" >> "$DA_STATE/git-commits.log"
    exit 0;;
  push)
    if [ "${GIT_PUSH_MODE:-ok}" = "reject" ]; then
      echo "stub: push rejected (non-fast-forward)" >&2; exit 1
    fi
    c="$(cat "$DA_STATE/push-count" 2>/dev/null || echo 0)"
    echo $((c+1)) > "$DA_STATE/push-count"
    echo "push" >> "$DA_STATE/git-pushes.log"
    exit 0;;
  config|add|fetch|pull|rebase|checkout|init|remote) exit 0;;
  *) exit 0;;
esac
STUBEOF
chmod +x "$STUB_DIR/git"

cat > "$STUB_DIR/kubectl" <<'STUBEOF'
#!/usr/bin/env bash
all="$*"
pushes="$(cat "$DA_STATE/push-count" 2>/dev/null || echo 0)"

# verdict for push N (1-based) from CT_SEQUENCE ("fail pass"); default pass
verdict_for() {
  local n="$1" w
  w="$(echo "${CT_SEQUENCE:-pass}" | awk -v i="$n" '{print $i}')"
  echo "${w:-pass}"
}

case "$all" in
  *"get ksvc -l "*)
    # the all-Ready gate list
    python3 - <<'PY'
import json, os
svcs = os.environ.get("FIXTURE_SERVICES", "demo-svc").split()
mode = os.environ.get("KSVC_READY_MODE", "all")
items = []
for i, s in enumerate(svcs):
    status = "False" if (mode == "one-unready" and i == len(svcs) - 1) else "True"
    items.append({"metadata": {"name": s},
                  "status": {"conditions": [{"type": "Ready", "status": status}]}})
print(json.dumps({"items": items}))
PY
    exit 0;;
  *"get ksvc "*latestCreatedRevisionName*)
    # token after "ksvc" is the service name; revision bumps with each push
    svc=""
    prev=""
    for a in "$@"; do
      if [ "$prev" = "ksvc" ]; then svc="$a"; break; fi
      prev="$a"
    done
    echo "${svc}-$((pushes+1))"
    exit 0;;
  *"get job "*)
    job=""
    for a in "$@"; do case "$a" in ct-*) job="$a";; esac; done
    n="${job##*-}"            # revision number == push number + 1
    v="$(verdict_for $((n-1)))"
    case "$all" in
      *succeeded*) [ "$v" = "pass" ] && echo "1" || echo "";;
      *failed*)    [ "$v" = "fail" ] && echo "1" || echo "";;
    esac
    exit 0;;
  *"logs"*)
    job=""
    for a in "$@"; do case "$a" in job/ct-*) job="${a#job/}";; esac; done
    n="${job##*-}"
    base="${job#ct-}"; svc="${base%-*}"
    v="$(verdict_for $((n-1)))"
    DA_SVC="$svc" DA_PASS="$v" DA_N="$((n-1))" python3 - <<'PY'
import json, os
print(json.dumps({"component": os.environ["DA_SVC"], "type": "realtime-service",
                  "check": "stub-contract", "pass": os.environ["DA_PASS"] == "pass",
                  "detail": "stub-detail-push-%s" % os.environ["DA_N"]}))
PY
    exit 0;;
  *) exit 0;;
esac
STUBEOF
chmod +x "$STUB_DIR/kubectl"

cat > "$STUB_DIR/opencode" <<'STUBEOF'
#!/usr/bin/env bash
# opencode run "<prompt>" --dir <dir> -m <provider/model> \
#               --dangerously-skip-permissions --format json
sub="${1:-}"; shift || true
if [ "$sub" != "run" ]; then exit 0; fi
prompt=""
flags=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) flags="$flags --dir $2"; shift 2;;
    -m|--model) flags="$flags -m $2"; shift 2;;
    --dangerously-skip-permissions|--format) flags="$flags $1"; shift;;
    --*) shift;;
    *) [ -z "$prompt" ] && prompt="$1"; shift;;
  esac
done
n="$(cat "$DA_STATE/opencode-count" 2>/dev/null || echo 0)"; n=$((n+1))
echo "$n" > "$DA_STATE/opencode-count"
printf '%s' "$prompt" > "$DA_STATE/opencode-prompt-$n.txt"
printf '%s' "$flags"  > "$DA_STATE/opencode-flags-$n.txt"
if [ "${OPENCODE_MODE:-edit}" = "edit" ]; then
  for f in microservices/*/src/handlers.py; do
    [ -f "$f" ] || continue
    echo "# implemented by stub run $n" >> "$f"
    echo "$f" >> .claude-changed
  done
fi
exit 0
STUBEOF
chmod +x "$STUB_DIR/opencode"

# ---------------------------------------------------------------------------
# Fixtures. make_fixtures <dir> with env flags:
#   SRC_REQ=1 (REQUIREMENTS.md at source root), GITOPS_REQ=1, LEDGER_REQ=1,
#   SRC_MARKER=<hash> (pre-existing .dev-agent/spec-hash in the source repo)
# ---------------------------------------------------------------------------
APP="dryapp"
make_fixtures() {
  local base="$1"
  rm -rf "$base"
  mkdir -p "$base/source/microservices/demo-svc/src" "$base/gitops" "$base/ledger/oam/applications"
  cat > "$base/source/microservices/demo-svc/src/handlers.py" <<'EOF'
def to_message(payload):
    raise NotImplementedError  # logic slot

def transform(message):
    raise NotImplementedError  # logic slot
EOF
  if [ "${SRC_REQ:-0}" = "1" ]; then
    printf '# Requirements\nMARKER-SOURCE-REQ: ingest heart-rate, emit anomalies\n' \
      > "$base/source/REQUIREMENTS.md"
  fi
  if [ "${GITOPS_REQ:-0}" = "1" ]; then
    printf '# Requirements\nMARKER-GITOPS-REQ: gitops copy\n' > "$base/gitops/REQUIREMENTS.md"
  fi
  if [ "${LEDGER_REQ:-0}" = "1" ]; then
    printf '# Requirements\nMARKER-LEDGER-REQ: ledger copy\n' \
      > "$base/ledger/oam/applications/${APP}-REQUIREMENTS.md"
  fi
  if [ -n "${SRC_MARKER:-}" ]; then
    mkdir -p "$base/source/.dev-agent"
    printf '%s\n' "$SRC_MARKER" > "$base/source/.dev-agent/spec-hash"
  fi
}

req_hash() { # hash exactly as the entrypoint computes it
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()[:12])' "$1"
}

# run_entrypoint <state-dir> <fixtures-dir> [extra VAR=val ...]
run_entrypoint() {
  local state="$1" fx="$2"; shift 2
  mkdir -p "$state" "$ROOT/home"
  env -i \
    PATH="$STUB_DIR:/usr/bin:/bin:/usr/sbin:/sbin:$PYTHON_BIN_DIR" \
    HOME="$ROOT/home" \
    DA_STATE="$state" \
    SOURCE_FIXTURE="$fx/source" GITOPS_FIXTURE="$fx/gitops" LEDGER_FIXTURE="$fx/ledger" \
    FIXTURE_SERVICES="demo-svc" \
    APP_NAME="$APP" GITHUB_TOKEN="x" APIM_SUBSCRIPTION_KEY="x" \
    WORK_DIR="$state/work" \
    POLL_INTERVAL="0" VERIFY_TIMEOUT="30" \
    GIT_PUSH_MODE="ok" OPENCODE_MODE="edit" KSVC_READY_MODE="all" CT_SEQUENCE="pass" \
    "$@" \
    bash "$ENTRYPOINT"
}

opencode_count() { cat "$1/opencode-count" 2>/dev/null || echo 0; }
push_count()     { cat "$1/push-count"     2>/dev/null || echo 0; }

echo "=== Scenario 1: happy path — source-root REQUIREMENTS, green first push ==="
S="$ROOT/s1"; SRC_REQ=1 GITOPS_REQ=1 LEDGER_REQ=1 make_fixtures "$ROOT/fx1"
if run_entrypoint "$S" "$ROOT/fx1" > "$S.log" 2>&1; then
  ok "exit 0 on green contract test"
else
  bad "entrypoint failed (rc=$?)"; tail -20 "$S.log"
fi
if grep -q "MARKER-SOURCE-REQ" "$S/opencode-prompt-1.txt" 2>/dev/null; then
  ok "opencode prompt contains REQUIREMENTS content"
else
  bad "prompt missing REQUIREMENTS content"
fi
if ! grep -q "MARKER-GITOPS-REQ" "$S/opencode-prompt-1.txt" 2>/dev/null; then
  ok "fallback order: source root wins over gitops/ledger copies"
else
  bad "wrong REQUIREMENTS source used (gitops content in prompt)"
fi
FLAGS="$(cat "$S/opencode-flags-1.txt" 2>/dev/null || echo "")"
if printf '%s' "$FLAGS" | grep -q -- "--dir" \
   && printf '%s' "$FLAGS" | grep -q -- "-m apim-gpt/gpt-5.4" \
   && printf '%s' "$FLAGS" | grep -q -- "--dangerously-skip-permissions"; then
  ok "opencode invoked with --dir + -m apim-gpt/gpt-5.4 + --dangerously-skip-permissions"
else
  bad "opencode flags wrong: [$FLAGS]"
fi
[ "$(push_count "$S")" = "1" ] && ok "exactly one push" || bad "push count $(push_count "$S") != 1"
if grep -q '"pass": true' "$S/work/verdicts-1.jsonl" 2>/dev/null; then
  ok "verify-loop recorded the pass verdict"
else
  bad "verdicts file missing/wrong"
fi

echo "=== Scenario 2: fallback to gitops-repo root ==="
S="$ROOT/s2"; SRC_REQ=0 GITOPS_REQ=1 LEDGER_REQ=1 make_fixtures "$ROOT/fx2"
run_entrypoint "$S" "$ROOT/fx2" > "$S.log" 2>&1 || { bad "s2 run failed"; tail -20 "$S.log"; }
if grep -q "MARKER-GITOPS-REQ" "$S/opencode-prompt-1.txt" 2>/dev/null \
   && ! grep -q "MARKER-LEDGER-REQ" "$S/opencode-prompt-1.txt" 2>/dev/null; then
  ok "fallback order: gitops root wins over ledger when source root absent"
else
  bad "gitops fallback wrong"
fi

echo "=== Scenario 3: fallback to central ledger ==="
S="$ROOT/s3"; SRC_REQ=0 GITOPS_REQ=0 LEDGER_REQ=1 make_fixtures "$ROOT/fx3"
run_entrypoint "$S" "$ROOT/fx3" > "$S.log" 2>&1 || { bad "s3 run failed"; tail -20 "$S.log"; }
if grep -q "MARKER-LEDGER-REQ" "$S/opencode-prompt-1.txt" 2>/dev/null; then
  ok "fallback order: central ledger used last"
else
  bad "ledger fallback wrong"
fi

echo "=== Scenario 4: opencode makes no changes -> no commit, no push, quiet exit 0 ==="
S="$ROOT/s4"; SRC_REQ=1 make_fixtures "$ROOT/fx4"
set +e
run_entrypoint "$S" "$ROOT/fx4" OPENCODE_MODE=noop > "$S.log" 2>&1
RC=$?
set -e
if [ "$RC" = "0" ] && [ "$(push_count "$S")" = "0" ] && [ ! -f "$S/git-commits.log" ] \
   && grep -q "no changes on first attempt" "$S.log"; then
  ok "no-change run: exit 0, zero commits, zero pushes"
else
  bad "no-change run wrong (rc=$RC pushes=$(push_count "$S"))"; tail -5 "$S.log"
fi

echo "=== Scenario 5: red verdict feeds back, second iteration goes green ==="
S="$ROOT/s5"; SRC_REQ=1 make_fixtures "$ROOT/fx5"
if run_entrypoint "$S" "$ROOT/fx5" CT_SEQUENCE="fail pass" MAX_ITERATIONS=3 > "$S.log" 2>&1; then
  ok "exit 0 after recovering on iteration 2"
else
  bad "fail->pass run did not recover (rc=$?)"; tail -20 "$S.log"
fi
[ "$(opencode_count "$S")" = "2" ] && ok "opencode invoked exactly twice" || bad "opencode count $(opencode_count "$S") != 2"
[ "$(push_count "$S")" = "2" ]   && ok "two pushes (one per iteration)"   || bad "push count $(push_count "$S") != 2"
if grep -q "stub-detail-push-1" "$S/opencode-prompt-2.txt" 2>/dev/null \
   && grep -q '"pass": false' "$S/opencode-prompt-2.txt" 2>/dev/null; then
  ok "iteration-2 prompt carries the failed verdict detail"
else
  bad "verdict feedback missing from iteration-2 prompt"
fi

echo "=== Scenario 6: bounded by MAX_ITERATIONS, then exit 1 (escalate) ==="
S="$ROOT/s6"; SRC_REQ=1 make_fixtures "$ROOT/fx6"
set +e
run_entrypoint "$S" "$ROOT/fx6" CT_SEQUENCE="fail fail fail fail" MAX_ITERATIONS=2 > "$S.log" 2>&1
RC=$?
set -e
if [ "$RC" != "0" ] && [ "$(opencode_count "$S")" = "2" ] && [ "$(push_count "$S")" = "2" ] \
   && grep -q "exhausted MAX_ITERATIONS=2" "$S.log"; then
  ok "all-red run bounded to MAX_ITERATIONS=2 then exit 1 (rc=$RC)"
else
  bad "iteration bound wrong (rc=$RC opencode=$(opencode_count "$S") pushes=$(push_count "$S"))"
  tail -10 "$S.log"
fi

echo "=== Scenario 7: all-Ready gate — sibling unready -> quiet exit 0 ==="
S="$ROOT/s7"; SRC_REQ=1 make_fixtures "$ROOT/fx7"
set +e
run_entrypoint "$S" "$ROOT/fx7" KSVC_READY_MODE=one-unready FIXTURE_SERVICES="demo-svc sibling-svc" > "$S.log" 2>&1
RC=$?
set -e
if [ "$RC" = "0" ] && [ "$(opencode_count "$S")" = "0" ] && grep -q "all-Ready gate" "$S.log" \
   && grep -q "exiting quietly" "$S.log"; then
  ok "gate exits 0 quietly when a sibling is unready; opencode never invoked"
else
  bad "all-Ready gate wrong (rc=$RC opencode=$(opencode_count "$S"))"; tail -5 "$S.log"
fi

echo "=== Scenario 8: spec-hash marker — already implemented -> quiet exit 0 ==="
S="$ROOT/s8"; SRC_REQ=1 make_fixtures "$ROOT/fx8"
HASH="$(req_hash "$ROOT/fx8/source/REQUIREMENTS.md")"
SRC_REQ=1 SRC_MARKER="$HASH" make_fixtures "$ROOT/fx8"
set +e
run_entrypoint "$S" "$ROOT/fx8" > "$S.log" 2>&1
RC=$?
set -e
if [ "$RC" = "0" ] && [ "$(opencode_count "$S")" = "0" ] && grep -q "already implemented" "$S.log"; then
  ok "spec-hash marker short-circuits a re-run (idempotency)"
else
  bad "spec-hash marker wrong (rc=$RC opencode=$(opencode_count "$S"))"; tail -5 "$S.log"
fi

echo "=== Scenario 9: no REQUIREMENTS anywhere -> quiet exit 0, no opencode ==="
S="$ROOT/s9"; SRC_REQ=0 GITOPS_REQ=0 LEDGER_REQ=0 make_fixtures "$ROOT/fx9"
set +e
run_entrypoint "$S" "$ROOT/fx9" > "$S.log" 2>&1
RC=$?
set -e
if [ "$RC" = "0" ] && [ "$(opencode_count "$S")" = "0" ] && grep -q "no REQUIREMENTS.md found" "$S.log"; then
  ok "missing spec everywhere: quiet no-op"
else
  bad "missing-spec behaviour wrong (rc=$RC)"; tail -5 "$S.log"
fi

echo
echo "=== RESULT: $PASS passed, $FAIL failed ==="
[ "$FAIL" = "0" ]
