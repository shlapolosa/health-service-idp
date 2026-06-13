# rasa-base — invariant rasa runtime image (RASA-CONTAINER #178)

The "invariant container + variant repo" split applied to the `rasa-chatbot`
component type (same pattern as `mscv-image` HARD-1 and `realtime-transport`
HARD-2):

| | lives in | changes when |
|---|---|---|
| **Invariant** — rasa-plus 3.7.10 runtime + full python dep set, server settings, endpoints/credentials plumbing, train-cache entrypoint | this image (`rasa-base:vX.Y.Z`) | platform decides (rare, versioned) |
| **Variant** — `domain.yml`, `config.yml`, `data/` (nlu/stories/rules), `actions/actions.py` | generated app monorepo (`microservices/<svc>/`) | developer / dev-agent edits (often) |

The generated repo's Dockerfiles shrink to a thin layer:

```dockerfile
FROM healthidpuaeacr.azurecr.io/rasa-base:v1.1.0
COPY --chown=1001:1001 . /app/bot/
RUN train-if-needed.sh          # bakes the model at build time (content-hash cache)
```

so CI no longer reinstalls ~2 GB of python deps per build, and `rasa train`
only runs when the bot content fingerprint actually changed.

## Entrypoint modes

| CMD | behaviour |
|---|---|
| `run` (default) | train-if-needed → `rasa run --enable-api --cors '*' --port 5005` |
| `actions` | `rasa run actions --actions actions --port 5055` (rasa-plus bundles rasa-sdk; ONE base serves both containers of the CD's dual-ksvc pattern) |
| `train` | train-if-needed only |
| anything else | exec'd verbatim (debugging) |

`endpoints.yml` / `credentials.yml`: a bot-shipped copy in `/app/bot/` wins;
otherwise the baked env-driven fallback in `/opt/rasa-base/config/` is used
(`action_endpoint` resolves `${RASA_ACTION_ENDPOINT}`, which the
`rasa-chatbot` ComponentDefinition already injects).

## OPS — build BEFORE anything references this image

Same rule as the mscv image: the tag must exist in ACR **before** any
CD/scaffold change referencing it syncs, or every new chatbot build/deploy
fails on pull.

```bash
az acr build \
  --registry healthidpuaeacr \
  --image rasa-base:v1.1.0 \
  --platform linux/amd64 \
  factory/production-lines/traditional-cloud/adapters/rasa-base-image/
```

Notes:
- **HARD-3**: never tag or reference `:latest`. Version bumps = new tag
  (`v1.1.0`, ...) + an explicit scaffold/CD update.
- `--platform linux/amd64` is mandatory (cluster is AMD64).
- The build resolves `rasa-plus` from Rasa's supplemental package index
  (`europe-west3-python.pkg.dev/rasa-releases/rasa-plus-py`) — the same
  source the legacy `chat-template-base` image used. No credentials are
  baked; any runtime license belongs in an `envFrom` secret on the component.
- There is no lock file (mirrors the legacy base build). If resolution drift
  ever bites, capture a `poetry.lock` from a known-good build and commit it
  here.

## Versioning

`v<major>.<minor>.<patch>` — bump minor for dependency refreshes, major for a
rasa upgrade. The consuming pin lives in
`factory/production-lines/traditional-cloud/adapters/mscv-image/scripts/lib/rasa.sh`
(`RASA_BASE_IMAGE_DEFAULT`) and is overridable per-Job via the
`RASA_BASE_IMAGE` env var.

## Test

The scaffold side is covered by
`factory/production-lines/traditional-cloud/adapters/mscv-image/tests/dry-run.sh`
(rasa scenarios: variant-only layout, thin `FROM rasa-base`, no-clobber).
The image itself is validated by building it and running the smoke in
`factory/docs/plans/rasa-container.md`.
