# RASA-CONTAINER (#178) — invariant container + variant repo for rasa-chatbot

Apply the platform's invariant/variant split (mscv-image HARD-1, realtime-transport
HARD-2, handlers.py logic slot RT-2) to the `rasa-chatbot` component type:
instantiation is fast (prebaked image), and only the developer/dev-agent edit
surface lives in the generated app monorepo.

## What was wrong

The legacy path copied the whole `shlapolosa/chat-template` into every generated
service: a full `pyproject.toml` (rasa-plus + ~20 deps), a base Dockerfile that
reinstalls everything, and CI Dockerfiles that run `rasa train` **every build**.
Worse, the template's Dockerfiles default to
`socrates12345/chat-template-base:latest` — an unversioned Docker Hub image
(HARD-3 violation) outside platform control.

## Invariant / variant split

| Concern | Class | Lives in | Changes when |
|---|---|---|---|
| rasa runtime (`rasa-plus = 3.7.10`, kept exactly — non-breaking) + full python dep set | invariant | `rasa-base:v1.0.0` image | platform bump (new tag) |
| server settings (ports 5005/5055, CORS, telemetry off) | invariant | rasa-base entrypoint | platform bump |
| `endpoints.yml` / `credentials.yml` plumbing (env-driven `${RASA_ACTION_ENDPOINT}`; bot-shipped copy overrides) | invariant | rasa-base `/opt/rasa-base/config/` | platform bump |
| Dockerfile mechanics + train-cache entrypoint | invariant | rasa-base scripts | platform bump |
| `domain.yml` (identity, intents, responses) | **variant** | app repo `microservices/<svc>/` | dev-agent edits |
| `config.yml` (NLU pipeline / policies) | **variant** | app repo | dev-agent edits |
| `data/` (nlu / stories / rules) | **variant** | app repo | dev-agent edits |
| `actions/actions.py` (custom-action logic slot — the rasa `handlers.py`) | **variant** | app repo | dev-agent edits |
| thin Dockerfiles (`FROM rasa-base:v1.0.0` + `COPY . /app/bot/`) | variant shim | app repo `docker/rasa{,-actions}/Dockerfile` | base-tag bumps only |

The scaffold ships a minimal **working** bot (greet/goodbye/bot_challenge + a
passthrough `action_health_check`) so the service boots, trains, and answers
before any real logic lands — mirroring the `src/handlers.py`
passthrough-defaults idea. All variant files are **create-if-absent**, and
`domain.yml` is now a no-clobber guard artifact in mscv `entrypoint.sh`
(closes the #175 recreation-storm hole for rasa services, which previously had
NO guard artifact at all).

## Train-cache decision

`rasa train` is gated on a content fingerprint: sha256 over the contents of
`domain.yml` + `config.yml` + `data/**` → model `model-<fp>.tar.gz`.

- **Build time** (`RUN train-if-needed.sh` in the thin Dockerfile): bakes the
  model into the variant layer, so Knative cold starts never train.
- **Boot time** (entrypoint `run` mode re-invokes it): safety net for images
  built without the RUN step or bots mounted at runtime; same content ⇒ skip.

Rejected alternatives: ONBUILD triggers in the base (opaque, hard to debug);
runtime-only training (slow scale-from-zero); model in a PVC (stateful, fights
Knative). Docker layer caching alone was rejected because CI runners don't
retain cache; the fingerprint makes the skip *content*-deterministic instead of
cache-deterministic.

## CI-path compatibility (deliberate deviation)

The thin Dockerfiles are written to the **same paths the generated-repo CI
already watches** (`docker/rasa/Dockerfile`, `docker/rasa-actions/Dockerfile`)
instead of a single root Dockerfile — the existing build matrix keeps working
unchanged; builds just become a COPY + (cached) train. Both files are thin
layers over the SAME base; the actions image only flips the entrypoint mode
(`CMD ["actions"]` — rasa-plus bundles rasa-sdk, so one base serves the CD's
dual-ksvc pattern).

## Rollout order (operator runbook)

1. **Build the base image FIRST** (same rule as the mscv image — the tag must
   exist before any scaffold referencing it merges/syncs):
   ```bash
   az acr build \
     --registry healthidpuaeacr \
     --image rasa-base:v1.0.0 \
     --platform linux/amd64 \
     factory/production-lines/traditional-cloud/adapters/rasa-base-image/
   ```
   Smoke (optional but recommended): scaffold a throwaway bot locally, build the
   thin image against it, `docker run -p 5005:5005 <img>` and
   `curl localhost:5005/webhooks/rest/webhook -d '{"sender":"t","message":"hi"}'`.
2. **Merge the mscv changes** (`scripts/lib/rasa.sh`, `entrypoint.sh` guard,
   `tests/dry-run.sh`) and rebuild/push the mscv image per its own README
   (new mscv tag, then bump the composition's image pin — HARD-3 discipline).
3. **CD**: no functional change shipped (comment block only); `rasaImage` /
   `actionsImage` remain required pinned strings from the app spec.
4. After the first new-style chatbot is proven end-to-end, delete
   `mscv_scaffold_rasa_legacy` (+ its `RASA_SCAFFOLD_MODE=legacy` knob).

Existing rasa apps are untouched: their repos already contain the legacy
full-fat files, the new guard (`domain.yml`) makes re-runs no-ops, and their CI
keeps building the old Dockerfiles.

## What the dev-agent edits later

Exactly the variant table rows: `domain.yml`, `data/*.yml`, `config.yml`,
`actions/actions.py`. It never touches Dockerfiles, deps, ports, or endpoints
wiring. Re-scaffolds can never clobber its work (create-if-absent +
entrypoint guard, proven by dry-run scenarios 6–7).

## Risks / open questions

- **rasa-plus licensing/index**: the base build pulls `rasa-plus==3.7.10` from
  Rasa's supplemental index, same as the legacy `chat-template-base` build. If
  that index now requires auth (or a runtime `RASA_PRO_LICENSE`), the operator
  `az acr build` will surface it; fallback is OSS `rasa==3.6.x` (the scaffolded
  bot uses no pro features) — that would be a v2.0.0 base, decided then.
- **No lock file**: dependency resolution drift between base builds (legacy had
  the same exposure). Mitigation noted in the base README: commit a
  `poetry.lock` from the first known-good build.
- **Generated-repo CI build context**: thin Dockerfiles assume context = the
  service directory (true for the current chat build matrix). If a generated
  repo's workflow uses repo-root context, the COPY would over-include —
  harmless but worth confirming on the first live run.
- The dry-run harness validates the scaffold, not the image; the base image is
  only proven by step 1's ACR build + smoke.
