#!/usr/bin/env bash
# RASA-CONTAINER (#178): shared, deterministic bot-content fingerprint.
#
# THE single source of truth for "what is this bot's training surface, by
# content". Sourced by BOTH train-if-needed.sh (build + boot) so the hash is
# computed IDENTICALLY in every context. If build and boot disagree on this
# number, the train-cache misses and the pod re-trains at boot (the #178 bug).
#
# Why a dedicated script:
#   The previous inline fingerprint hashed `domain.yml config.yml` + EVERY file
#   `find data -type f` returned. `rasa train` (run at CI build time via the
#   thin Dockerfile's `RUN train-if-needed.sh`) scatters artifacts into the bot
#   working dir — a `.rasa/` cache and, depending on the pipeline, stray
#   index/lock files. Any extra (or missing) file under data/ between build and
#   boot flips the fingerprint -> new model name -> "model not found" -> the
#   entrypoint retrains. Proven locally: one extra file under data/ changes the
#   hash.
#
# This function fixes that by hashing ONLY a stable, explicit allowlist:
#   - domain.yml
#   - config.yml
#   - data/**/*.yml and data/**/*.yaml   (the ONLY training inputs rasa reads)
# It hashes file CONTENT keyed by RELATIVE PATH (sorted, NUL-safe), so it is
# invariant to:
#   - mtime / ctime           (not part of the stream)
#   - file ownership / uid     (1001 at build vs whatever at boot)
#   - the absolute bot dir     (paths are relative to BOT_DIR)
#   - any rasa-generated junk  (dotfiles, .rasa/, *.tar.gz, non-yaml all excluded)
#
# Usage:
#   source bot-hash.sh
#   FP="$(bot_content_hash "$BOT_DIR")"

# Emit the 16-char content fingerprint for the bot rooted at $1 (default: cwd).
bot_content_hash() {
  local bot_dir="${1:-.}"
  (
    cd "$bot_dir" || return 1
    {
      # The two always-present top-level inputs. `--` guards odd names; the
      # leading `./` is stripped so the stream matches the data/ entries below.
      for f in domain.yml config.yml; do
        [ -f "$f" ] && sha256sum "./$f"
      done
      # Only real training data: *.yml / *.yaml under data/, content-keyed by
      # path, sorted for order-stability. Everything else under data/ (dotfiles,
      # caches, generated artifacts) is deliberately ignored.
      if [ -d data ]; then
        find data \( -name '*.yml' -o -name '*.yaml' \) -type f \
          -not -path '*/.*' -print0 2>/dev/null \
          | sort -z \
          | xargs -0 -r sha256sum
      fi
    } | sha256sum | cut -c1-16
  )
}
