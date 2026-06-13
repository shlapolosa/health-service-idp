# dev-agent — the developer agent that fills the logic slot (DEV-AGENT W2-W4)

Ephemeral K8s Job that runs when ALL components of an OAM app are Ready and a
`REQUIREMENTS.md` exists: clones the app monorepo, implements the logic slots
(`microservices/<svc>/src/handlers.py` `to_message`/`transform`, or the rasa
variant files) via headless **opencode (GPT-5.4 via APIM)**, pushes, then
iterates against the HARD-4 contract-test verdicts until green (bounded by
`MAX_ITERATIONS`).

Plan: `factory/docs/plans/dev-agent-factory.md` (W2 image, W3 trigger, W4 loop).
Trigger + runtime manifests: `factory/substrate/dev-agent/`.

## Engine swap: claude-code → opencode / GPT-5.4-via-APIM

The coding engine was swapped from `@anthropic-ai/claude-code` to
[opencode](https://opencode.ai) running GPT-5.4 through the Azure APIM gateway
(no Anthropic key, no shim). opencode's `apim-gpt` provider
(`@ai-sdk/openai-compatible`) is baked into `/app/opencode.json`; `apiKey` +
`Ocp-Apim-Subscription-Key` come from `{env:APIM_SUBSCRIPTION_KEY}` at runtime
(no secret in any layer). `OPENCODE_DISABLE_CLAUDE_CODE=1` stops opencode
auto-reading `~/.claude`.

- Invocation: `opencode run "<prompt>" --dir "$SRC_DIR" -m apim-gpt/gpt-5.4 --dangerously-skip-permissions --format json`
  (`--dangerously-skip-permissions` is the acceptEdits-equivalent; egress is
  sandboxed by NetworkPolicy). The prompt is **positional** (in opencode `-p`
  means `--password`, NOT prompt).
- baseURL folds the APIM `api-version` query param in; gpt-5.4 needs
  `max_completion_tokens`, which the openai-compatible AI-SDK emits, plus an
  explicit `limit.output`.
- **Rollback** = `git revert` the single engine-swap commit (restores
  claude-code Dockerfile, `claude -p` invocation, `ANTHROPIC_API_KEY` secret,
  and api.anthropic.com egress).

## Layout

| Path | What |
|---|---|
| `Dockerfile` | node22-slim + git + python3 + pinned kubectl + pinned `opencode-ai`, non-root uid 1000 |
| `opencode.json` | baked `apim-gpt` provider (openai-compatible) → GPT-5.4 via APIM; auth via `{env:APIM_SUBSCRIPTION_KEY}` |
| `scripts/entrypoint.sh` | gate -> clone -> locate spec -> opencode implement -> commit/push -> verify-loop, iterate |
| `scripts/verify-loop.sh` | W4: wait new ksvc revisions -> read `ct-<revision>` Job verdict JSON -> pass/fail (engine-agnostic) |
| `prompts/implement.md` | prompt template (REQUIREMENTS + verdict-feedback slot + edit-surface rules) |
| `tests/dry-run.sh` | PATH-shim harness (git/kubectl/opencode stubbed), runs on macOS, no network |

## Env contract (set by the sensor Job / `dev-agent-secrets`)

| Var | Source | Default | Purpose |
|---|---|---|---|
| `APP_NAME` | sensor param (`app.oam.dev/name` label) | required | app == monorepo name |
| `SOURCE_REPO` | optional | `https://github.com/shlapolosa/<APP_NAME>.git` | monorepo |
| `GITOPS_REPO` | optional | `…/<APP_NAME>-gitops.git` | spec fallback location 2 |
| `CENTRAL_GITOPS_REPO` | optional | `…/health-service-idp-gitops.git` | spec fallback location 3 (ledger) |
| `GITHUB_TOKEN` | **secret** `dev-agent-secrets` | required | HTTPS x-access-token clone/push |
| `APIM_SUBSCRIPTION_KEY` | **secret** `dev-agent-secrets` | required | `Ocp-Apim-Subscription-Key` for GPT-5.4 via APIM |
| `OPENCODE_MODEL` | optional | `apim-gpt/gpt-5.4` | provider/model passed to `opencode run -m` |
| `MAX_ITERATIONS` | sensor Job env | `3` | implement->verify attempts |
| `NAMESPACE` | sensor Job env | `default` | where the app ksvcs live |
| `SPEC_HASH` | sensor param (annotation) | `""` | informational; entrypoint recomputes |
| `VERIFY_TIMEOUT` / `POLL_INTERVAL` | optional | `900` / `10` | verify-loop budget |

REQUIREMENTS.md lookup order: **source-repo root** → **`<app>-gitops` root** →
**ledger `health-service-idp-gitops/oam/applications/<app>-REQUIREMENTS.md`**.

## Build (operator)

```bash
az acr build --registry healthidpuaeacr \
  --image dev-agent:v0.2.0 \
  factory/production-lines/traditional-cloud/adapters/dev-agent/
```

`v0.2.0` = the opencode/GPT-5.4 engine (v0.1.0 was claude-code). Then point
`factory/substrate/dev-agent/all-ready-sensor.yaml` at the new tag (pinned tag,
never `:latest` — HARD-3). Verify the opencode npm pin exists first:
`npm view opencode-ai versions` (pinned: **opencode-ai@1.17.4**, amd64).

## Secrets (NEVER in git)

`dev-agent-secrets` in `dev-agent-system`, sourced from Key Vault
`kv-socrates-6706` via ESO (skeleton: `factory/substrate/dev-agent/externalsecret.yaml`):

| Secret key | Key Vault secret | Notes |
|---|---|---|
| `GITHUB_TOKEN` | `dev-agent-github-token` | FactoryBot installation token / PAT, repo scope on `<app>` + `<app>-gitops` |
| `APIM_SUBSCRIPTION_KEY` | `dev-agent-apim-subscription-key` | long-lived APIM gateway subscription key (preferred over the 1h SP JWT for unattended use); sent as `Ocp-Apim-Subscription-Key` |

## NetworkPolicy intent (engine-swap, security-critical)

Egress ONLY: github.com, **`aigw-apim-dev-w4x7ibwk4e2is.azure-api.net` (APIM
gateway, 443)**, kube-apiserver, DNS. **api.anthropic.com is DROPPED** — the
engine no longer talks to Anthropic. Vanilla AKS NetworkPolicy cannot scope by
FQDN, so `networkpolicy.yaml` allows 443-anywhere + DNS and blocks everything
else; the file ships a commented `CiliumNetworkPolicy` companion that makes the
anthropic-DENY / apim-ALLOW an enforced L7 control once Cilium is adopted.
Ingress: none.

## Safety rails

- prompts forbid edits outside `microservices/`; entrypoint reverts violations
- prompts forbid secrets in files (public repos) + tell GPT-5.4 to persist edits to disk
- pre-push secret scan (AWS/GitHub/Anthropic key + private-key patterns) — repos are PUBLIC
- `.dev-agent/spec-hash` marker breaks the self-trigger loop (own push -> new
  ksvc generation -> new Ready event); only a changed REQUIREMENTS re-runs
- bounded: `MAX_ITERATIONS` (3), Job `activeDeadlineSeconds` 3600,
  `backoffLimit` 0; `--dangerously-skip-permissions` is safe ONLY because the
  NetworkPolicy egress sandbox + forbidden-path revert + secret scan contain it

## Smoke-test gate (run BEFORE any pilot app)

GPT-5.4 edit fidelity is unproven vs claude-code. Before labelling a pilot app,
run one containerised `opencode run` against a real `handlers.py` slot and
confirm the contract tests pass — see
`factory/docs/plans/dev-agent-factory.md` ("Engine-swap smoke-test gate").

## Test

```bash
bash factory/production-lines/traditional-cloud/adapters/dev-agent/tests/dry-run.sh
```
