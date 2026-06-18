#!/usr/bin/env bash
# DEV-AGENT W2 entrypoint: clone monorepo -> read REQUIREMENTS.md -> implement
# logic slots via headless opencode (GPT-5.4 via APIM) -> push -> W4 verify-loop
# against the HARD-4 contract tests -> iterate (bounded) until green.
#
# ENGINE: opencode run, provider `apim-gpt` -> model gpt-5.4 (Azure APIM gateway,
# openai-compatible). NO Anthropic key. Engine was swapped claude-code ->
# opencode; rollback = revert the engine-swap commit.
#
# Env contract (the sensor Job sets these; secrets via envFrom dev-agent-secrets):
#   APP_NAME              - OAM app name == source monorepo name     (required)
#   GITHUB_USER           - GitHub org/user (default shlapolosa)
#   SOURCE_REPO           - default https://github.com/$GITHUB_USER/$APP_NAME.git
#   GITOPS_REPO           - default https://github.com/$GITHUB_USER/$APP_NAME-gitops.git
#   CENTRAL_GITOPS_REPO   - default https://github.com/$GITHUB_USER/health-service-idp-gitops.git
#   GITHUB_TOKEN          - PAT / App installation token (SECRET, required)
#   APIM_SUBSCRIPTION_KEY - APIM gateway subscription key, header
#                           Ocp-Apim-Subscription-Key (SECRET, required unless
#                           DRY-stubbed). Consumed by opencode.json {env:...}.
#   OPENCODE_MODEL        - provider/model (default apim-gpt/gpt-5.4)
#   MAX_ITERATIONS        - implement->push->verify attempts (default 3)
#   NAMESPACE             - where the app's ksvcs live (default default)
#   SPEC_HASH             - optional, stamped by the sensor from the OAM annotation
#   VERIFY_TIMEOUT/POLL_INTERVAL - passed to verify-loop.sh
#
# EXIT SEMANTICS (the W3 "all-Ready gate" lives HERE, not in the sensor —
# Argo Events can't join across resources):
#   exit 0 quietly when: a sibling component is not Ready yet (a later Ready
#     event re-fires us), no REQUIREMENTS.md anywhere, spec-hash already
#     implemented, no logic slots, or opencode produced no changes on attempt 1.
#   exit 1 (escalate) when: iterations exhausted red, push permanently rejected,
#     or a secret pattern is detected in the diff.
set -euo pipefail

APP_NAME="${APP_NAME:?APP_NAME required}"
GITHUB_USER="${GITHUB_USER:-shlapolosa}"
SOURCE_REPO="${SOURCE_REPO:-https://github.com/${GITHUB_USER}/${APP_NAME}.git}"
GITOPS_REPO="${GITOPS_REPO:-https://github.com/${GITHUB_USER}/${APP_NAME}-gitops.git}"
CENTRAL_GITOPS_REPO="${CENTRAL_GITOPS_REPO:-https://github.com/${GITHUB_USER}/health-service-idp-gitops.git}"
GITHUB_TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN required}"
MAX_ITERATIONS="${MAX_ITERATIONS:-3}"
NAMESPACE="${NAMESPACE:-default}"
OPENCODE_MODEL="${OPENCODE_MODEL:-apim-gpt/gpt-5.4}"
MAX_PUSH_ATTEMPTS="${MAX_PUSH_ATTEMPTS:-5}"
WORK_DIR="${WORK_DIR:-/tmp/dev-agent}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$SCRIPT_DIR/../prompts/implement.md}"
TDD_TEMPLATE="${TDD_TEMPLATE:-$SCRIPT_DIR/../prompts/implement-tdd.md}"
SKILLS_SRC="${SKILLS_SRC:-/agent/skills}"          # baked opencode TDD skills (W4)
VERIFY_LOOP="${VERIFY_LOOP:-$SCRIPT_DIR/verify-loop.sh}"

mkdir -p "$WORK_DIR" "${HOME:-/tmp/dev-agent-home}"
SRC_DIR="$WORK_DIR/src"

# Inject the token into clone/push URLs only (never written to any file).
auth_url() { printf '%s' "$1" | python3 -c '
import sys, os
print(sys.stdin.read().replace("https://github.com/",
      "https://x-access-token:%s@github.com/" % os.environ["GITHUB_TOKEN"]))'; }

# ---------------------------------------------------------------------------
# W3 all-Ready gate: every sibling component of the app must be Ready.
# A single ksvc Ready event fired us; if siblings lag, exit 0 — THEIR Ready
# event creates the (same-named, rejected-or-new) Job and we run then.
# ---------------------------------------------------------------------------
GATE="$(kubectl -n "$NAMESPACE" get ksvc -l "app.oam.dev/name=$APP_NAME" -o json | python3 -c '
import json, sys
d = json.load(sys.stdin)
items = d.get("items", [])
if not items:
    print("NONE"); raise SystemExit
for it in items:
    conds = it.get("status", {}).get("conditions", [])
    ready = next((c for c in conds if c.get("type") == "Ready"), None)
    if not ready or ready.get("status") != "True":
        print("UNREADY " + it["metadata"]["name"]); raise SystemExit
print("READY")')"
if [ "$GATE" != "READY" ]; then
  echo "all-Ready gate: app=$APP_NAME not fully Ready ($GATE) — exiting quietly (a later Ready event re-fires)"
  exit 0
fi
echo "all-Ready gate: all components of $APP_NAME Ready"

# ---------------------------------------------------------------------------
# Clone the source monorepo.
# ---------------------------------------------------------------------------
rm -rf "$SRC_DIR"
git clone "$(auth_url "$SOURCE_REPO")" "$SRC_DIR"
cd "$SRC_DIR"
git config user.name  "dev-agent[bot]"
git config user.email "dev-agent@platform.local"

# ---------------------------------------------------------------------------
# Locate REQUIREMENTS.md — 3-location fallback, in order:
#   1. source monorepo root (target state once the SPEC-1 fix lands)
#   2. <app>-gitops root (where spec UPDATES land today)
#   3. central ledger health-service-idp-gitops/oam/applications/<app>-REQUIREMENTS.md
#      (where day-0 specs land today)
# ---------------------------------------------------------------------------
REQ_FILE=""
REQ_LOC=""
if [ -f "$SRC_DIR/REQUIREMENTS.md" ]; then
  REQ_FILE="$SRC_DIR/REQUIREMENTS.md"; REQ_LOC="source-repo root"
else
  rm -rf "$WORK_DIR/gitops"
  if git clone "$(auth_url "$GITOPS_REPO")" "$WORK_DIR/gitops" 2>/dev/null \
     && [ -f "$WORK_DIR/gitops/REQUIREMENTS.md" ]; then
    REQ_FILE="$WORK_DIR/gitops/REQUIREMENTS.md"; REQ_LOC="gitops-repo root"
  else
    rm -rf "$WORK_DIR/ledger"
    if git clone "$(auth_url "$CENTRAL_GITOPS_REPO")" "$WORK_DIR/ledger" 2>/dev/null \
       && [ -f "$WORK_DIR/ledger/oam/applications/${APP_NAME}-REQUIREMENTS.md" ]; then
      REQ_FILE="$WORK_DIR/ledger/oam/applications/${APP_NAME}-REQUIREMENTS.md"; REQ_LOC="central ledger"
    fi
  fi
fi
if [ -z "$REQ_FILE" ]; then
  echo "no REQUIREMENTS.md found for $APP_NAME (source root, gitops root, ledger) — exiting quietly"
  exit 0
fi
echo "REQUIREMENTS.md located at: $REQ_LOC ($REQ_FILE)"

# Spec-hash idempotency marker (second guard behind the Job-name idempotency):
# the agent's OWN push creates a new ksvc generation -> new Ready event -> new
# Job name -> without this marker we would loop on ourselves forever.
REQ_HASH="$(python3 -c '
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest()[:12])' "$REQ_FILE")"
if [ -f "$SRC_DIR/.dev-agent/spec-hash" ] \
   && [ "$(cat "$SRC_DIR/.dev-agent/spec-hash")" = "$REQ_HASH" ]; then
  echo "spec-hash $REQ_HASH already implemented (marker .dev-agent/spec-hash) — exiting quietly"
  exit 0
fi
echo "spec-hash to implement: $REQ_HASH"

# ---------------------------------------------------------------------------
# Discover service dirs with a logic slot:
#   realtime/webservice: microservices/<svc>/src/handlers.py (to_message/transform)
#   rasa:                microservices/<svc>/domain.yml (+ data/, config.yml, actions/)
# ---------------------------------------------------------------------------
SERVICES=()
for d in "$SRC_DIR"/microservices/*/; do
  [ -d "$d" ] || continue
  svc="$(basename "$d")"
  if [ -f "$d/src/handlers.py" ] || [ -f "$d/domain.yml" ]; then
    SERVICES+=("$svc")
  fi
done
if [ "${#SERVICES[@]}" -eq 0 ]; then
  echo "no service with a logic slot found under microservices/ — exiting quietly"
  exit 0
fi
echo "services with logic slots: ${SERVICES[*]}"

# ---------------------------------------------------------------------------
# W4: classify each service by whether REQUIREMENTS.md carries a structured
# ```acceptance block for it. Services WITH a block take the skill-driven TDD
# path (red→green from criteria + the local coverage gate); services WITHOUT
# fall back to the legacy free-form implement path (v0.2.0 behaviour).
# A MALFORMED block is a hard fail (contract: never silent-fallback).
# ---------------------------------------------------------------------------
ACCEPTANCE_SERVICES=()
for svc in "${SERVICES[@]}"; do
  if out="$(python3 "$SCRIPT_DIR/parse_acceptance.py" "$REQ_FILE" --service "$svc" 2>"$WORK_DIR/parse-err.txt")"; then
    if printf '%s' "$out" | grep -q '"absent"'; then
      echo "  $svc: no acceptance block — legacy path"
    else
      ACCEPTANCE_SERVICES+=("$svc")
      echo "  $svc: acceptance block present — skill-driven TDD path"
    fi
  else
    rc=$?
    if [ "$rc" -eq 3 ]; then
      echo "MALFORMED acceptance block in REQUIREMENTS.md — aborting (no silent fallback):" >&2
      cat "$WORK_DIR/parse-err.txt" >&2
      exit 1
    fi
    echo "  $svc: parse_acceptance non-fatal rc=$rc — legacy path"
  fi
done

is_acceptance() { # svc -> 0 if it has an acceptance block
  local s="$1" x
  for x in "${ACCEPTANCE_SERVICES[@]:-}"; do [ "$x" = "$s" ] && return 0; done
  return 1
}

edit_surface_for() {
  local svc="$1"
  if [ -f "$SRC_DIR/microservices/$svc/src/handlers.py" ]; then
    echo "- microservices/$svc/src/handlers.py (the to_message/transform logic slots)
- microservices/$svc/tests/ (unit tests for the handlers)"
  else
    echo "- microservices/$svc/domain.yml
- microservices/$svc/data/ (nlu.yml, stories.yml, rules.yml)
- microservices/$svc/config.yml
- microservices/$svc/actions/actions.py"
  fi
}

render_prompt() { # svc iteration feedback_file out_file
  DA_TPL="$PROMPT_TEMPLATE" DA_REQ_FILE="$REQ_FILE" DA_FEEDBACK_FILE="$3" \
  DA_APP="$APP_NAME" DA_SVC="$1" DA_ITER="$2" DA_MAX="$MAX_ITERATIONS" \
  DA_SURFACE="$(edit_surface_for "$1")" DA_OUT="$4" python3 - <<'PYEOF'
import os
tpl = open(os.environ["DA_TPL"]).read()
out = (tpl
       .replace("__APP_NAME__", os.environ["DA_APP"])
       .replace("__SERVICE_NAME__", os.environ["DA_SVC"])
       .replace("__ITERATION__", os.environ["DA_ITER"])
       .replace("__MAX_ITERATIONS__", os.environ["DA_MAX"])
       .replace("__EDIT_SURFACE__", os.environ["DA_SURFACE"])
       .replace("__REQUIREMENTS__", open(os.environ["DA_REQ_FILE"]).read())
       .replace("__FEEDBACK__", open(os.environ["DA_FEEDBACK_FILE"]).read()))
open(os.environ["DA_OUT"], "w").write(out)
PYEOF
}

# W4: TDD prompt renderer (skill-driven path). The skill reads the criteria itself
# via parse_acceptance.py, so we pass the requirements PATH, not the full body.
render_tdd_prompt() { # svc iteration feedback_file out_file
  DA_TPL="$TDD_TEMPLATE" DA_FEEDBACK_FILE="$3" DA_APP="$APP_NAME" DA_SVC="$1" \
  DA_ITER="$2" DA_MAX="$MAX_ITERATIONS" DA_REQ_FILE="$REQ_FILE" DA_OUT="$4" python3 - <<'PYEOF'
import os
tpl = open(os.environ["DA_TPL"]).read()
out = (tpl
       .replace("__APP_NAME__", os.environ["DA_APP"])
       .replace("__SERVICE_NAME__", os.environ["DA_SVC"])
       .replace("__ITERATION__", os.environ["DA_ITER"])
       .replace("__MAX_ITERATIONS__", os.environ["DA_MAX"])
       .replace("__REQ_FILE__", os.environ["DA_REQ_FILE"])
       .replace("__FEEDBACK__", open(os.environ["DA_FEEDBACK_FILE"]).read()))
open(os.environ["DA_OUT"], "w").write(out)
PYEOF
}

# W4: stage the baked opencode TDD skills into the cloned repo's project-local
# `.opencode/skill/` — the documented highest-priority discovery path for both
# native opencode skills and the opencode-skills plugin. Removed again before we
# compute the diff so the skills are NEVER committed/pushed.
HAD_OPENCODE_DIR=false; [ -d "$SRC_DIR/.opencode" ] && HAD_OPENCODE_DIR=true
stage_skills() {
  [ -d "$SKILLS_SRC" ] || { echo "WARN: no skills dir at $SKILLS_SRC — skill discovery may fail" >&2; return 0; }
  mkdir -p "$SRC_DIR/.opencode/skill"
  cp -R "$SKILLS_SRC"/. "$SRC_DIR/.opencode/skill/"
}
unstage_skills() {
  if $HAD_OPENCODE_DIR; then rm -rf "$SRC_DIR/.opencode/skill"; else rm -rf "$SRC_DIR/.opencode"; fi
}

run_opencode() { # prompt_file svc
  ( cd "$SRC_DIR" && \
    opencode run "$(cat "$1")" \
      --dir "$SRC_DIR" \
      -m "$OPENCODE_MODEL" \
      --dangerously-skip-permissions \
      --format json ) || echo "opencode run for $2 exited non-zero (continuing; git state decides)"
}

# W4 local gate (the requirement-specific gate that runs IN the Job, before push —
# the post-deploy HARD-4 contract test is the second, independent gate). For an
# acceptance-block service: run its pytest, assert every kind:test criterion has a
# passing test (check_acceptance == COVERED), then emit the deterministic
# TRACEABILITY.md + .dev-agent/traceability.json. Returns 0 COVERED / 1 not.
local_gate() { # svc reqfile report_out
  local svc="$1" reqfile="$2" report="$3"
  local junit="$WORK_DIR/$svc-junit.xml"
  rm -f "$junit"
  # Run pytest FROM the service dir with both it and its src/ on PYTHONPATH, so the
  # scaffold's `src/handlers.py` resolves whether the test imports `src.handlers` or
  # `handlers` (running from the monorepo root would break both). junit is absolute.
  # PYTHONDONTWRITEBYTECODE + no:cacheprovider keep caches out of the commit.
  local sdir="$SRC_DIR/microservices/$svc"
  ( cd "$sdir" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$sdir:$sdir/src:${PYTHONPATH:-}" \
      python3 -m pytest tests/ --junitxml="$junit" -p no:cacheprovider -q ) || true
  local ca_args=( "$reqfile" --service "$svc" )
  [ -f "$junit" ] && ca_args+=( --junit "$junit" )
  if ! python3 "$SCRIPT_DIR/check_acceptance.py" "${ca_args[@]}" > "$report" 2>&1; then
    return 1
  fi
  # COVERED → deterministic traceability (platform-written, in-surface → committed).
  local changed_csv
  changed_csv="$(cd "$SRC_DIR" && git status --porcelain | awk '{print $2}' \
                  | grep "^microservices/$svc/" | paste -sd, - || true)"
  python3 "$SCRIPT_DIR/emit_traceability.py" "$reqfile" --service "$svc" \
    --junit "$junit" --changed "$changed_csv" \
    --md "$SRC_DIR/microservices/$svc/TRACEABILITY.md" \
    --json "$SRC_DIR/microservices/$svc/.dev-agent/traceability.json" >/dev/null 2>&1 || true
  return 0
}

# Pre-push secret scan (repos are PUBLIC — never push a credential).
secret_scan() { # file...
  local hit=0 f
  for f in "$@"; do
    [ -f "$f" ] || continue
    if grep -nE 'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' "$f"; then
      echo "SECRET PATTERN detected in $f — refusing to push" >&2
      hit=1
    fi
  done
  return $hit
}

push_with_retry() { # mscv rebase-retry pattern (#162)
  local attempt
  for (( attempt=1; attempt<=MAX_PUSH_ATTEMPTS; attempt++ )); do
    if git push origin HEAD 2>&1; then
      echo "push ok (attempt $attempt)"
      return 0
    fi
    echo "push rejected (attempt $attempt) — rebasing and retrying"
    git pull --rebase origin HEAD || true
  done
  echo "failed to push after $MAX_PUSH_ATTEMPTS attempts" >&2
  return 1
}

# ---------------------------------------------------------------------------
# W4 outer loop: implement -> commit/push -> contract-test verdicts -> feedback.
# ---------------------------------------------------------------------------
FEEDBACK_FILE="$WORK_DIR/feedback.txt"
printf '(none — first attempt)\n' > "$FEEDBACK_FILE"

for (( n=1; n<=MAX_ITERATIONS; n++ )); do
  echo "=== iteration $n/$MAX_ITERATIONS ==="
  # Stage the TDD skills only when at least one service uses the skill-driven path.
  [ "${#ACCEPTANCE_SERVICES[@]:-0}" -gt 0 ] && stage_skills
  for svc in "${SERVICES[@]}"; do
    PROMPT_OUT="$WORK_DIR/prompt-$n-$svc.txt"
    # opencode run: prompt is POSITIONAL (NOT -p; -p is --password in opencode).
    # --dir scopes the working tree; -m selects provider/model;
    # --dangerously-skip-permissions == acceptEdits-equivalent (egress is sandboxed
    # by NetworkPolicy); --format json keeps stdout machine-parseable. git state
    # (below) is the source of truth for "did it change files", not the exit code.
    if is_acceptance "$svc"; then
      render_tdd_prompt "$svc" "$n" "$FEEDBACK_FILE" "$PROMPT_OUT"
      echo "--- opencode TDD via tdd-acceptance skill: $svc (iteration $n, model $OPENCODE_MODEL) ---"
    else
      render_prompt "$svc" "$n" "$FEEDBACK_FILE" "$PROMPT_OUT"
      echo "--- opencode implement (legacy): $svc (iteration $n, model $OPENCODE_MODEL) ---"
    fi
    run_opencode "$PROMPT_OUT" "$svc"
  done
  # Remove the staged skills BEFORE diffing so they are never committed/pushed.
  [ "${#ACCEPTANCE_SERVICES[@]:-0}" -gt 0 ] && unstage_skills

  CHANGED="$(cd "$SRC_DIR" && git status --porcelain)"
  if [ -z "$CHANGED" ]; then
    if [ "$n" -eq 1 ]; then
      echo "opencode produced no changes on first attempt — nothing to implement; exiting quietly"
      exit 0
    fi
    echo "opencode produced no changes while contract tests are red — escalating" >&2
    exit 1
  fi

  # Forbidden-path guard (defense in depth behind the prompt): revert anything
  # outside microservices/ that claude touched.
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    echo "forbidden path touched: $path — reverting" >&2
    ( cd "$SRC_DIR" && git checkout -- "$path" 2>/dev/null || rm -rf "${SRC_DIR:?}/$path" )
  done < <(printf '%s\n' "$CHANGED" | awk '{print $2}' | grep -v '^microservices/' | grep -v '^\.dev-agent/' || true)

  CHANGED_FILES=()
  while IFS= read -r p; do [ -n "$p" ] && CHANGED_FILES+=("$SRC_DIR/$p"); done \
    < <(printf '%s\n' "$CHANGED" | awk '{print $2}' | grep '^microservices/' || true)
  if [ "${#CHANGED_FILES[@]}" -eq 0 ]; then
    echo "no in-surface changes after forbidden-path revert — exiting quietly"
    exit 0
  fi
  secret_scan "${CHANGED_FILES[@]}" || exit 1

  # -------------------------------------------------------------------------
  # W4 local acceptance gate: every CHANGED acceptance-block service must be
  # COVERED (its kind:test criteria all pass) BEFORE we push. On any miss we
  # feed the coverage report back and re-prompt — without pushing a red spec.
  # -------------------------------------------------------------------------
  if [ "${#ACCEPTANCE_SERVICES[@]:-0}" -gt 0 ]; then
    GATE_FAIL=0; : > "$WORK_DIR/local-feedback.txt"
    for svc in "${ACCEPTANCE_SERVICES[@]}"; do
      printf '%s\n' "$CHANGED" | awk '{print $2}' | grep -q "^microservices/$svc/" || continue
      echo "--- local acceptance gate: $svc ---"
      if local_gate "$svc" "$REQ_FILE" "$WORK_DIR/gate-$svc.txt"; then
        cat "$WORK_DIR/gate-$svc.txt"
        echo "  $svc: COVERED (+TRACEABILITY.md)"
      else
        GATE_FAIL=1
        { echo "### service $svc — acceptance coverage NOT met:"; cat "$WORK_DIR/gate-$svc.txt"; echo; } \
          >> "$WORK_DIR/local-feedback.txt"
      fi
    done
    if [ "$GATE_FAIL" -eq 1 ]; then
      cp "$WORK_DIR/local-feedback.txt" "$FEEDBACK_FILE"
      echo "local acceptance gate RED (iteration $n) — re-prompting without push"
      if [ "$n" -eq "$MAX_ITERATIONS" ]; then
        echo "exhausted MAX_ITERATIONS with uncovered acceptance criteria — escalating" >&2
        exit 1
      fi
      continue
    fi
    echo "local acceptance gate: all changed acceptance-block services COVERED"
  fi

  CHANGED_SERVICES="$(printf '%s\n' "$CHANGED" | awk '{print $2}' | grep '^microservices/' | cut -d/ -f2 | sort -u | tr '\n' ' ')"
  echo "changed services: $CHANGED_SERVICES"

  # Baseline revisions BEFORE the push so verify-loop can wait for the new ones.
  BASELINE_FILE="$WORK_DIR/baseline-$n.txt"
  : > "$BASELINE_FILE"
  for svc in $CHANGED_SERVICES; do
    rev="$(kubectl -n "$NAMESPACE" get ksvc "$svc" -o "jsonpath={.status.latestCreatedRevisionName}" 2>/dev/null || echo "")"
    echo "$svc $rev" >> "$BASELINE_FILE"
  done

  ( cd "$SRC_DIR" \
    && mkdir -p .dev-agent && printf '%s\n' "$REQ_HASH" > .dev-agent/spec-hash \
    && git add -A \
    && git commit -m "feat(dev-agent): implement logic per REQUIREMENTS.md [iteration $n]" )
  ( cd "$SRC_DIR" && push_with_retry ) || exit 1

  # W4: wait for the HARD-4 contract-test verdicts of the NEW revisions.
  VERDICTS_OUT="$WORK_DIR/verdicts-$n.jsonl"
  if NAMESPACE="$NAMESPACE" BASELINE_FILE="$BASELINE_FILE" \
     CHANGED_SERVICES="$CHANGED_SERVICES" VERDICTS_OUT="$VERDICTS_OUT" \
     VERIFY_TIMEOUT="${VERIFY_TIMEOUT:-900}" POLL_INTERVAL="${POLL_INTERVAL:-10}" \
     bash "$VERIFY_LOOP"; then
    echo "=== all contract tests GREEN for $APP_NAME (iteration $n) ==="
    exit 0
  fi
  echo "contract tests red (iteration $n) — feeding verdicts back"
  {
    echo "The previous attempt FAILED its post-deploy contract tests. Verdicts:"
    grep -E '"pass": *false' "$VERDICTS_OUT" || cat "$VERDICTS_OUT"
  } > "$FEEDBACK_FILE"
done

echo "exhausted MAX_ITERATIONS=$MAX_ITERATIONS with red contract tests — escalating (Slack notify handled by platform)" >&2
exit 1
