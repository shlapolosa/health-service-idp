#!/usr/bin/env bash
# RASA-CONTAINER (#178): content-hash train cache.
#
# Trains ONLY when no model exists for the current bot-content fingerprint.
# Fingerprint = bot_content_hash() over domain.yml + config.yml + data/**/*.y{a,}ml
# (see bot-hash.sh — the ONE place the fingerprint is defined, sourced here so
# build and boot agree byte-for-byte). Same content => same model name => no
# retrain.
#
# Called from two places:
#   1. the generated repo's thin Dockerfile (RUN train-if-needed.sh) — bakes
#      the model into the variant image layer at CI build time, so cold starts
#      never train;
#   2. docker-entrypoint.sh "run" mode — safety net: if the image was built
#      without the RUN step (or the bot was mounted at runtime), the first
#      boot trains once and subsequent boots of the same content skip.
#
# Cache contract (build writes, boot reads):
#   $MODELS_DIR/model-<FP>.tar.gz   the trained model archive
#   $MODELS_DIR/.bot-hash           the FP that produced the active model
#   $MODELS_DIR/.current-model      path of the active model (for the entrypoint)
# Boot skips training iff BOTH the model file exists AND the freshly recomputed
# FP equals the baked .bot-hash. This decouples the skip decision from any
# files `rasa train` may scatter into the bot dir between build and boot.
set -euo pipefail

BOT_DIR="${RASA_BOT_DIR:-/app/bot}"
MODELS_DIR="${RASA_MODELS_DIR:-/app/models}"

# The single, shared fingerprint definition (identical at build and boot).
# shellcheck source=bot-hash.sh
. "$(dirname "$0")/bot-hash.sh"

cd "$BOT_DIR"

if [ ! -f domain.yml ] || [ ! -f config.yml ]; then
  echo "train-if-needed: ERROR - no bot found in $BOT_DIR (need domain.yml + config.yml + data/)." >&2
  echo "train-if-needed: the variant layer must COPY the bot files to /app/bot/ (see rasa-base-image README)." >&2
  exit 1
fi

mkdir -p "$MODELS_DIR"

# Deterministic content fingerprint of the variant training surface.
FP="$(bot_content_hash "$BOT_DIR")"
MODEL="$MODELS_DIR/model-$FP.tar.gz"
HASH_FILE="$MODELS_DIR/.bot-hash"

# Skip iff the baked model exists AND its sidecar hash matches the current FP.
BAKED_HASH=""
[ -f "$HASH_FILE" ] && BAKED_HASH="$(cat "$HASH_FILE")"

if [ -f "$MODEL" ] && [ "$BAKED_HASH" = "$FP" ]; then
  echo "train-if-needed: model for fingerprint $FP already present (sidecar matches) — skipping rasa train"
else
  if [ -f "$MODEL" ]; then
    echo "train-if-needed: model file present but sidecar hash '$BAKED_HASH' != current '$FP' — retraining"
  else
    echo "train-if-needed: no model for fingerprint $FP — training (slow path, runs once per content change)"
  fi
  python -m rasa train --num-threads 1 --quiet --fixed-model-name "model-$FP" --out "$MODELS_DIR"
  # Bake the sidecar alongside the model so the next boot can skip deterministically.
  printf '%s' "$FP" > "$HASH_FILE"
fi

# Record the active model for docker-entrypoint.sh.
echo "$MODEL" > "$MODELS_DIR/.current-model"
echo "train-if-needed: active model -> $MODEL"
