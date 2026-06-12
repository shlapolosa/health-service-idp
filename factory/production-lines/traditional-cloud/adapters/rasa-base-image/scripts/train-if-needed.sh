#!/usr/bin/env bash
# RASA-CONTAINER (#178): content-hash train cache.
#
# Trains ONLY when no model exists for the current bot-data fingerprint.
# Fingerprint = sha256 over the contents of domain.yml + config.yml + data/**
# (the exact VARIANT surface). Same content => same model name => no retrain.
#
# Called from two places:
#   1. the generated repo's thin Dockerfile (RUN train-if-needed.sh) — bakes
#      the model into the variant image layer at CI build time, so cold starts
#      never train;
#   2. docker-entrypoint.sh "run" mode — safety net: if the image was built
#      without the RUN step (or the bot was mounted at runtime), the first
#      boot trains once and subsequent boots of the same content skip.
set -euo pipefail

BOT_DIR="${RASA_BOT_DIR:-/app/bot}"
MODELS_DIR="${RASA_MODELS_DIR:-/app/models}"

cd "$BOT_DIR"

if [ ! -f domain.yml ] || [ ! -f config.yml ]; then
  echo "train-if-needed: ERROR - no bot found in $BOT_DIR (need domain.yml + config.yml + data/)." >&2
  echo "train-if-needed: the variant layer must COPY the bot files to /app/bot/ (see rasa-base-image README)." >&2
  exit 1
fi

# Deterministic content fingerprint of the variant training surface.
FP="$( (sha256sum domain.yml config.yml; find data -type f -print0 2>/dev/null | sort -z | xargs -0 -r sha256sum) | sha256sum | cut -c1-16)"
MODEL="$MODELS_DIR/model-$FP.tar.gz"

mkdir -p "$MODELS_DIR"

if [ -f "$MODEL" ]; then
  echo "train-if-needed: model for fingerprint $FP already present — skipping rasa train"
else
  echo "train-if-needed: no model for fingerprint $FP — training (this is the slow path, runs once per content change)"
  python -m rasa train --num-threads 1 --quiet --fixed-model-name "model-$FP" --out "$MODELS_DIR"
fi

# Record the active model for docker-entrypoint.sh.
echo "$MODEL" > "$MODELS_DIR/.current-model"
echo "train-if-needed: active model -> $MODEL"
