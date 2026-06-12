#!/usr/bin/env bash
# RASA-CONTAINER (#178): invariant entrypoint for rasa-base.
#
# Contract:
#   - expects the VARIANT bot (domain.yml, config.yml, data/, actions/) at
#     /app/bot/ (RASA_BOT_DIR), copied there by the generated repo's thin
#     Dockerfile (or mounted for local dev);
#   - "run"     (default) -> train-if-needed (content-hash cache) + rasa run
#   - "actions"           -> rasa run actions (the <name>-actions container;
#                            rasa-plus bundles rasa-sdk, one image serves both)
#   - "train"             -> train-if-needed only (CI / debugging)
#   - anything else       -> exec'd verbatim (debug shell etc.)
#
# Ports match the rasa-chatbot ComponentDefinition: 5005 (server), 5055 (actions).
set -euo pipefail

BOT_DIR="${RASA_BOT_DIR:-/app/bot}"
MODELS_DIR="${RASA_MODELS_DIR:-/app/models}"
cd "$BOT_DIR"

# The CD injects RASA_ACTION_ENDPOINT (-> http://<name>-actions.<ns>.svc...:5055/webhook).
# Default to localhost so the baked endpoints.yml interpolates in local runs too.
export RASA_ACTION_ENDPOINT="${RASA_ACTION_ENDPOINT:-http://localhost:5055/webhook}"

# Bot-shipped config wins; otherwise fall back to the invariant baked config.
ENDPOINTS="$BOT_DIR/endpoints.yml"
[ -f "$ENDPOINTS" ] || ENDPOINTS="/opt/rasa-base/config/endpoints.yml"
CREDENTIALS="$BOT_DIR/credentials.yml"
[ -f "$CREDENTIALS" ] || CREDENTIALS="/opt/rasa-base/config/credentials.yml"

MODE="${1:-run}"
case "$MODE" in
  actions)
    exec python -m rasa run actions --actions actions --port "${ACTIONS_PORT:-5055}"
    ;;
  train)
    exec train-if-needed.sh
    ;;
  run)
    train-if-needed.sh
    MODEL="$(cat "$MODELS_DIR/.current-model")"
    exec python -m rasa run \
      --enable-api \
      --cors '*' \
      --port "${RASA_PORT:-5005}" \
      --model "$MODEL" \
      --endpoints "$ENDPOINTS" \
      --credentials "$CREDENTIALS"
    ;;
  *)
    exec "$@"
    ;;
esac
