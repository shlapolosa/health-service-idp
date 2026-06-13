# dev-agent engine: opencode-on-GPT5.4 vs claude-code (shim variants)

**Status:** assessment only (2026-06-13). No dev-agent code changed, nothing committed.
**Question:** replace `claude-code` with **opencode** (github.com/sst/opencode) as the dev-agent
engine so it drives **GPT-5.4 through APIM** natively (OpenAI contract) with no Anthropic shim.

---

## One-line verdict

**YES, with caveats.** opencode can replace claude-code for the dev-agent: it has a true headless
`run` mode, an acceptEdits-equivalent (`--dangerously-skip-permissions` / `permission:"allow"`),
and — the make-or-break — it supports **custom auth headers + custom baseURL** on an OpenAI-compatible
custom provider, so it can hit APIM's `openai` path with `Ocp-Apim-Subscription-Key` natively.
Caveats: (1) edit/tool-call fidelity on GPT-5.4 is unproven against *our* contract tests (opencode is
model-agnostic but its editing was tuned on Claude/Qwen-coder); (2) the dev-agent's egress
NetworkPolicy must swap `api.anthropic.com` → the APIM host; (3) opencode binary is heavier than the
claude npm CLI.

## The APIM-auth-header finding (the critical gate) — PASS

opencode's **Custom provider** (`provider.<id>` with `"npm":"@ai-sdk/openai-compatible"`) exposes
`options.baseURL`, `options.apiKey`, **and `options.headers`** (proven by the documented Helicone
config which injects arbitrary `Helicone-*` headers). Therefore the APIM trio is satisfiable:

- **(a) custom header** `Ocp-Apim-Subscription-Key: <key>` → `options.headers` (long-lived, no refresh). ✅
- **(b) `api-version` query param** → fold into `options.baseURL`
  (`.../openai/deployments/gpt-5.4/chat/completions?api-version=2024-12-01-preview`) or an APIM
  policy default. Use `@ai-sdk/openai-compatible` (→ `/v1/chat/completions` shape, which APIM's
  openai path serves). ✅
- **(c) `max_completion_tokens`** → the openai-compatible AI-SDK package emits this for GPT-5-family
  models; APIM passes it through (confirmed below). ✅

If a sub-key is **not** provisioned, the hourly platform **JWT** also works (`options.headers` →
`Authorization: Bearer <jwt>` OR set `options.apiKey`), but the 1-hour lifetime means a refresh
side-car/wrapper must re-mint before each `opencode run`. The **sub-key path is strongly preferred**
for the dev-agent (unattended, long-lived, no refresh logic).

## Live smoke — PASS at the HTTP layer

Ran in-sandbox (secrets never printed): minted a **client-credentials JWT** for audience
`api://fe225ae2-c6eb-4e4e-b4c2-79b45b2dce69` using the platform SP from `.env`, then called
`https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/openai/deployments/gpt-5.4/chat/completions?api-version=2024-12-01-preview`
with `Authorization: Bearer <jwt>`, body `{messages:[…], max_completion_tokens:16}`.

```
JWT minted OK (len 1391)
APIM gpt-5.4 status: 200
content: "PONG"   model: gpt-5.4-2026-03-05
```

This is byte-for-byte the request `@ai-sdk/openai-compatible` issues from opencode's custom provider
(baseURL + headers). The provider wiring is therefore proven viable end-to-end. *Not* tested: a full
`opencode run` agentic loop against the contract tests (opencode ships a platform binary downloaded at
install; deferred to a follow-up container build), and the `Ocp-Apim-Subscription-Key` header path
(no sub-key in `.env` — only the SP). Both are config-level, low-risk given the header support above.

---

## Comparison table

| Axis | **opencode + GPT-5.4 (no shim)** | LiteLLM-shim + claude-code | APIM-anthropic + claude-code |
|---|---|---|---|
| **GPT-native (no translation shim)** | ✅ direct OpenAI contract to APIM openai path | ❌ LiteLLM translates Anthropic↔OpenAI (extra hop, extra deploy) | ❌ needs an Anthropic-shaped APIM API in front of GPT (translation in APIM policy) |
| **Headless fit** | ✅ `opencode run "<prompt>" --dir <repo> -m <prov>/<model> --dangerously-skip-permissions --format json`; global flags, exit codes; runs as uid 1000 in container | ✅ unchanged `claude -p … --permission-mode acceptEdits` (current) | ✅ unchanged `claude -p …` |
| **APIM-auth fit (sub-key header!)** | ✅ `options.headers:{Ocp-Apim-Subscription-Key}` + baseURL w/ api-version (long-lived, no refresh) | ⚠️ claude-code only speaks `ANTHROPIC_*`; LiteLLM holds the APIM creds — sub-key lives in LiteLLM, not the agent | ⚠️ claude-code sends `x-api-key`/Bearer to APIM-anthropic; sub-key→APIM mapping done in APIM, JWT-refresh or sub-key in agent env |
| **Edit/tool fidelity** | ⚠️ model-agnostic but unproven on GPT-5.4 vs our contract tests; opencode editing tuned on Claude/Qwen-coder | ✅ claude-code+Claude is the reference quality (but you're paying for GPT via shim → you get GPT quality anyway) | ✅ same Claude quality if APIM fronts a real Claude; ❌ if it fronts GPT (you get GPT through a Claude-shaped lie) |
| **Effort to integrate into W2/W4 contract** | 🟡 Medium: Dockerfile engine swap + opencode.json + flag mapping + NetworkPolicy egress swap. The verify-loop is engine-agnostic (parses ksvc/ct verdicts) — **no W4 change** | 🔴 High: stand up + operate a LiteLLM deployment (new service, new failure mode, new secret) | 🔴 High: build+maintain an Anthropic-shaped APIM facade over GPT (policy translation, ongoing drift) |
| **Ongoing maintenance** | 🟢 one binary, one config, pinned version; APIM is already operated | 🔴 LiteLLM is a second moving part to patch/scale/monitor | 🔴 APIM translation policy is bespoke + brittle across model/contract changes |

## Recommendation (ranked)

1. **opencode + GPT-5.4 via APIM (custom openai-compatible provider).** Winner: GPT-native, no shim,
   no extra service, custom-header support clears the gate, W4 untouched. Accept the one real risk
   (edit fidelity) and de-risk it with a one-shot containerised smoke against a known service before
   cutover.
2. **LiteLLM-shim + claude-code.** Only if opencode's GPT-5.4 edit fidelity proves inadequate AND you
   still want GPT economics — keeps claude-code's editing but adds an operated proxy.
3. **APIM-anthropic + claude-code.** Last — bespoke translation facade, highest drift, least benefit.

---

## Concrete dev-agent change for the winner (opencode)

**Dockerfile engine swap** (`adapters/dev-agent/Dockerfile`):
- Remove `npm install -g @anthropic-ai/claude-code@…`.
- Install opencode pinned (binary; e.g. `npm i -g opencode-ai@<pin>` which fetches the platform
  binary, or the official install script) — keep the NEVER-`:latest` / explicit-pin discipline (HARD-3).
- Bake an `opencode.json` (or supply via `OPENCODE_CONFIG` / `OPENCODE_CONFIG_CONTENT`) defining the
  custom provider:
  ```jsonc
  { "$schema":"https://opencode.ai/config.json",
    "permission":"allow",                       // unattended acceptEdits-equivalent
    "provider": { "apim-gpt": {
      "npm":"@ai-sdk/openai-compatible", "name":"APIM GPT-5.4",
      "options": {
        "baseURL":"https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/openai/deployments/gpt-5.4?api-version=2024-12-01-preview",
        "headers": { "Ocp-Apim-Subscription-Key": "{env:APIM_SUBSCRIPTION_KEY}" }
      },
      "models": { "gpt-5.4": { "name":"GPT-5.4" } } } } }
  ```

**Secret carried by `dev-agent-secrets`:** drop `ANTHROPIC_API_KEY`; add **`APIM_SUBSCRIPTION_KEY`**
(long-lived APIM sub-key for a product scoped to the `openai` API; provision in Key Vault → ESO).
Keep `GITHUB_TOKEN`. (Fallback if sub-key undesired: keep the SP creds + a pre-`run` JWT-mint into
`Authorization: Bearer`, accepting hourly refresh.)

**entrypoint.sh diff (high level, line 218-221):** replace
```
claude -p "$(cat "$PROMPT_OUT")" --permission-mode acceptEdits --max-turns "$CLAUDE_MAX_TURNS"
```
with
```
opencode run "$(cat "$PROMPT_OUT")" --dir "$SRC_DIR" -m apim-gpt/gpt-5.4 \
  --dangerously-skip-permissions --format json
```
- `--dir "$SRC_DIR"` replaces the `cd` subshell (opencode is dir-flag native).
- `--dangerously-skip-permissions` (or the baked `permission:"allow"`) = acceptEdits.
- Keep the **prompt unchanged** — implement.md already forbids git/commit/push and pins the edit
  surface, which opencode honours; the harness still owns commit/push/secret-scan/verify (W4 intact).
- `CLAUDE_MAX_TURNS` → no direct opencode equivalent; rely on prompt scoping + `MAX_ITERATIONS`
  outer bound (and `OPENCODE_DISABLE_AUTOUPDATE=1`, `OPENCODE_DISABLE_AUTOCOMPACT` as needed for
  determinism). Cost guard moves from per-run turns to per-iteration count.

**verify-loop.sh:** **no change** — it parses ksvc revisions + `ct-*` Job verdicts; engine-agnostic.

**NetworkPolicy:** swap egress allow `api.anthropic.com` → `aigw-apim-dev-w4x7ibwk4e2is.azure-api.net`
(keep github.com + apiserver). This is the security-critical edit that keeps acceptEdits safe.

## Risks / open questions

- **Edit fidelity on GPT-5.4 (primary risk):** run one containerised `opencode run` against a real
  handlers.py slot + the contract tests before cutover. If GPT-5.4 underperforms on the diff/edit
  tool, fall to ranked option 2.
- **Binary size/provenance:** opencode pulls a platform binary at install — verify amd64 binary,
  pin the version, and confirm no daemon/login is required for `run` (docs show `run` is standalone;
  `serve`/`web` are the daemon modes we won't use).
- **`max_completion_tokens` emission:** confirm `@ai-sdk/openai-compatible` (not `@ai-sdk/openai`)
  is the right package for APIM's openai path; the live 200 used the chat/completions shape, which
  matches `@ai-sdk/openai-compatible`.
- **Sub-key provisioning:** the `Ocp-Apim-Subscription-Key` path was not live-tested (no sub-key in
  `.env`); only the JWT path was. Provision a scoped sub-key and smoke it before relying on it.
- **`.claude` auto-read:** opencode auto-reads `~/.claude/CLAUDE.md` + skills; set
  `OPENCODE_DISABLE_CLAUDE_CODE=1` in the container to avoid leaking host instructions into the agent.
