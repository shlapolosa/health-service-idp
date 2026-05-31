#!/usr/bin/env bash
# scripts/test-architect-agent.sh — drive the architect-v1 agent via Foundry's Threads API.
#
# Sends a CapabilityRequest as a chat message, polls until the agent finishes (or asks for
# consent — in which case we surface the assistant turn and exit). For end-to-end tests including
# the consent step, drive interactively in the portal; this script covers the deterministic part.
#
# Usage:
#   bash scripts/test-architect-agent.sh \
#     --foundry-endpoint https://aifoundry-socrates.openai.azure.com \
#     --agent-id agent_abc... \
#     --message "We need durable lightweight messaging."

set -euo pipefail

ENDPOINT=""
AGENT_ID=""
MESSAGE="We need a durable, low-latency, lightweight messaging capability."
API_VERSION="2024-10-21-preview"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --foundry-endpoint) ENDPOINT="$2"; shift 2 ;;
    --agent-id)         AGENT_ID="$2"; shift 2 ;;
    --message)          MESSAGE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

for v in ENDPOINT AGENT_ID; do
  if [ -z "${!v}" ]; then echo "missing --${v,,}" >&2; exit 1; fi
done

TOKEN=$(az account get-access-token --resource "https://cognitiveservices.azure.com" \
  --query accessToken -o tsv)
H="Authorization: Bearer $TOKEN"

echo "==> Create thread"
THREAD=$(curl -sS -X POST "$ENDPOINT/openai/threads?api-version=$API_VERSION" -H "$H" -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "  thread=$THREAD"

echo "==> Add user message"
curl -sS -X POST "$ENDPOINT/openai/threads/$THREAD/messages?api-version=$API_VERSION" \
  -H "$H" -H 'Content-Type: application/json' \
  -d "$(python3 -c "import json,sys; print(json.dumps({'role':'user','content':'$MESSAGE'}))")" >/dev/null

echo "==> Start run"
RUN=$(curl -sS -X POST "$ENDPOINT/openai/threads/$THREAD/runs?api-version=$API_VERSION" \
  -H "$H" -H 'Content-Type: application/json' \
  -d "$(python3 -c "import json; print(json.dumps({'assistant_id':'$AGENT_ID'}))")" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "  run=$RUN"

echo "==> Poll for completion / consent gate"
for i in $(seq 1 60); do
  STATUS=$(curl -sS "$ENDPOINT/openai/threads/$THREAD/runs/$RUN?api-version=$API_VERSION" -H "$H" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status",""))')
  echo "  [${i}s] status=$STATUS"
  case "$STATUS" in
    completed)
      echo "==> Final assistant turn:"
      curl -sS "$ENDPOINT/openai/threads/$THREAD/messages?api-version=$API_VERSION&order=desc&limit=1" -H "$H" \
        | python3 -c 'import sys,json
m=json.load(sys.stdin)["data"][0]
for c in m["content"]:
    if c["type"]=="text": print(c["text"]["value"])'
      exit 0 ;;
    requires_action)
      echo "==> Agent requested approval (this is the consent gate):"
      curl -sS "$ENDPOINT/openai/threads/$THREAD/runs/$RUN?api-version=$API_VERSION" -H "$H" \
        | python3 -m json.tool | grep -A 20 required_action || true
      echo
      echo "==> To approve: POST submit_tool_outputs to ${ENDPOINT}/openai/threads/${THREAD}/runs/${RUN}/submit_tool_outputs"
      exit 0 ;;
    failed|cancelled|expired)
      echo "==> Run terminated: $STATUS"
      curl -sS "$ENDPOINT/openai/threads/$THREAD/runs/$RUN?api-version=$API_VERSION" -H "$H" | python3 -m json.tool | tail -20
      exit 1 ;;
  esac
  sleep 1
done
echo "==> timeout"
exit 2
