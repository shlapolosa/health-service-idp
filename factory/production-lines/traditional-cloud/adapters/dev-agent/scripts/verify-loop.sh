#!/usr/bin/env bash
# DEV-AGENT W4 verify-loop: after the agent pushes, CI builds -> new ksvc
# revision -> the HARD-4 contract-test sensor fires Job ct-<revision> which
# prints ONE JSON verdict line: {"component","type","check","pass","detail"}
# (factory/substrate/contract-tests/runner.py). This script waits for the NEW
# revision of each changed service, collects its verdict, and exits 0 only
# when every component passes.
#
# Env contract:
#   NAMESPACE        - ksvc/Job namespace (default default)
#   BASELINE_FILE    - lines "<svc> <latestCreatedRevisionName-before-push>"
#   CHANGED_SERVICES - space-separated svc names whose code changed
#   VERDICTS_OUT     - file to append one verdict JSON line per service
#   VERIFY_TIMEOUT   - overall budget in seconds (default 900)
#   POLL_INTERVAL    - seconds between polls (default 10)
#
# Exit: 0 all pass:true; 1 any pass:false / timeout (synthetic fail verdict
# is appended so the caller always has detail to feed back).
set -euo pipefail

NAMESPACE="${NAMESPACE:-default}"
BASELINE_FILE="${BASELINE_FILE:?BASELINE_FILE required}"
CHANGED_SERVICES="${CHANGED_SERVICES:?CHANGED_SERVICES required}"
VERDICTS_OUT="${VERDICTS_OUT:?VERDICTS_OUT required}"
VERIFY_TIMEOUT="${VERIFY_TIMEOUT:-900}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"

: > "$VERDICTS_OUT"
DEADLINE=$(( $(date +%s) + VERIFY_TIMEOUT ))
ALL_PASS=1

synthetic_fail() { # svc detail
  python3 -c '
import json, sys
print(json.dumps({"component": sys.argv[1], "type": "", "check": "verify-loop",
                  "pass": False, "detail": sys.argv[2]}))' "$1" "$2" >> "$VERDICTS_OUT"
  ALL_PASS=0
}

for svc in $CHANGED_SERVICES; do
  base="$(grep "^$svc " "$BASELINE_FILE" | awk '{print $2}' || echo "")"

  # 1. Wait for the NEW revision (CI build + rollout).
  newrev=""
  while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    cur="$(kubectl -n "$NAMESPACE" get ksvc "$svc" -o "jsonpath={.status.latestCreatedRevisionName}" 2>/dev/null || echo "")"
    if [ -n "$cur" ] && [ "$cur" != "$base" ]; then newrev="$cur"; break; fi
    sleep "$POLL_INTERVAL"
  done
  if [ -z "$newrev" ]; then
    echo "verify-loop: timeout waiting for new revision of $svc (baseline=$base)"
    synthetic_fail "$svc" "timeout waiting for new revision after push (baseline=$base) — CI may have failed"
    continue
  fi
  echo "verify-loop: $svc new revision $newrev"

  # 2. Wait for its contract-test Job (ct-<revision>, fired by the HARD-4
  #    sensor on Ready) to COMPLETE (either .status.succeeded or .status.failed).
  job="ct-$newrev"
  done_flag=""
  while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    s="$(kubectl -n "$NAMESPACE" get job "$job" -o "jsonpath={.status.succeeded}" 2>/dev/null || echo "")"
    f="$(kubectl -n "$NAMESPACE" get job "$job" -o "jsonpath={.status.failed}" 2>/dev/null || echo "")"
    if [ -n "$s" ] || [ -n "$f" ]; then done_flag="yes"; break; fi
    sleep "$POLL_INTERVAL"
  done
  if [ -z "$done_flag" ]; then
    echo "verify-loop: timeout waiting for contract-test job $job"
    synthetic_fail "$svc" "timeout waiting for contract-test job $job (revision $newrev)"
    continue
  fi

  # 3. Read the one-line JSON verdict from the Job logs (last parseable line).
  verdict="$(kubectl -n "$NAMESPACE" logs "job/$job" --tail=50 2>/dev/null | python3 -c '
import json, sys
verdict = None
for line in sys.stdin:
    line = line.strip()
    if not line.startswith("{"):
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    if "pass" in d:
        verdict = d
print(json.dumps(verdict) if verdict else "")')"
  if [ -z "$verdict" ] || [ "$verdict" = "null" ]; then
    synthetic_fail "$svc" "contract-test job $job completed but no verdict JSON found in logs"
    continue
  fi
  printf '%s\n' "$verdict" >> "$VERDICTS_OUT"
  if printf '%s' "$verdict" | python3 -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("pass") else 1)'; then
    echo "verify-loop: $svc PASS ($job)"
  else
    echo "verify-loop: $svc FAIL ($job)"
    ALL_PASS=0
  fi
done

[ "$ALL_PASS" = "1" ]
