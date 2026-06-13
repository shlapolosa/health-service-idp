#!/usr/bin/env bash
# RASA-CONTAINER (#178): regression test for the train-cache fingerprint.
#
# Proves bot_content_hash() is invariant to the exact things that differ
# between CI BUILD (RUN train-if-needed.sh, uid 1001) and POD BOOT (entrypoint,
# possibly a different uid / mounted dir / post-train rasa artifacts):
#   1. file mtime
#   2. file ownership/uid (best-effort; skipped if not root)
#   3. the absolute bot directory path
#   4. rasa-generated junk dropped into the bot dir (.rasa/, *.tar.gz, dotfiles,
#      non-yaml files under data/)
# and SENSITIVE to a real content change (the cache MUST miss when data changes).
#
# Run: bash tests/hash-stable.sh   (no cluster, no docker, no rasa needed)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../scripts/bot-hash.sh
. "$HERE/../scripts/bot-hash.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

make_bot() {
  local d="$1"
  mkdir -p "$d/data"
  printf 'version: "3.1"\nintents: [greet, goodbye]\n' > "$d/domain.yml"
  printf 'recipe: default.v1\npipeline: [{name: WhitespaceTokenizer}]\n' > "$d/config.yml"
  printf 'version: "3.1"\nnlu:\n- intent: greet\n  examples: |\n    - hi\n    - hello\n' > "$d/data/nlu.yml"
  printf 'version: "3.1"\nrules: []\n' > "$d/data/rules.yml"
}

fail() { echo "FAIL: $1" >&2; exit 1; }

# --- build context ---------------------------------------------------------
make_bot "$TMP/build"
H_BUILD="$(bot_content_hash "$TMP/build")"
[ -n "$H_BUILD" ] || fail "empty hash"
echo "build hash: $H_BUILD"

# --- boot context: different path + mtimes + rasa junk ---------------------
make_bot "$TMP/boot"
touch -t 200001010000 "$TMP/boot/domain.yml" "$TMP/boot/config.yml" \
  "$TMP/boot/data/nlu.yml" "$TMP/boot/data/rules.yml"
# rasa-train side-effects that DID flip the old inline fingerprint:
mkdir -p "$TMP/boot/.rasa/cache"
echo "cache" > "$TMP/boot/.rasa/cache/cache.db"
echo "graph" > "$TMP/boot/data/.rasa_graph_index"     # dotfile under data/
echo "junk"  > "$TMP/boot/data/train_index.json"      # non-yaml under data/
echo "model" > "$TMP/boot/model-deadbeef.tar.gz"      # baked model in bot dir
H_BOOT="$(bot_content_hash "$TMP/boot")"
echo "boot  hash: $H_BOOT"
[ "$H_BUILD" = "$H_BOOT" ] || fail "hash changed build->boot ($H_BUILD != $H_BOOT) — cache would MISS"
echo "PASS: hash stable across path/mtime/rasa-junk"

# --- ownership invariance (best-effort) ------------------------------------
if [ "$(id -u)" = "0" ]; then
  chown -R 1:1 "$TMP/boot" 2>/dev/null || true
  H_OWN="$(bot_content_hash "$TMP/boot")"
  [ "$H_BUILD" = "$H_OWN" ] || fail "hash changed after chown ($H_BUILD != $H_OWN)"
  echo "PASS: hash stable across ownership change"
else
  echo "SKIP: ownership test (not root)"
fi

# --- sensitivity: a real content change MUST change the hash ---------------
cp -r "$TMP/build" "$TMP/changed"
printf '    - good morning\n' >> "$TMP/changed/data/nlu.yml"
H_CHANGED="$(bot_content_hash "$TMP/changed")"
echo "changed hash: $H_CHANGED"
[ "$H_BUILD" != "$H_CHANGED" ] || fail "hash did NOT change after real content edit — cache would never retrain"
echo "PASS: hash sensitive to real content change"

echo "ALL TESTS PASSED"
