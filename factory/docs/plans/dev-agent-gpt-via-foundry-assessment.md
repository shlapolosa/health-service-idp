# Dev-Agent on GPT (Azure AI Foundry + APIM) — Assessment

Status: ASSESSMENT ONLY (no dev-agent changes, no commits). Date 2026-06-13.
Question: can the dev-agent run on GPT via Foundry+APIM instead of an Anthropic key?

## TL;DR
- **Yes, with a shim.** GPT (`gpt-5.4`) is LIVE and reachable through APIM with the
  platform SP's JWT — proven 200. But the dev-agent engine is the **claude-code CLI**,
  which speaks ONLY the Anthropic Messages API; it cannot call Azure-OpenAI directly.
- **Cleanest path (Option A): deploy a LiteLLM proxy** in-cluster that exposes the
  Anthropic `/v1/messages` contract and translates to the APIM `openai` GPT backend.
  Point the dev-agent at it via `ANTHROPIC_BASE_URL` — claude-code itself is UNCHANGED.
- A second, even cheaper lead exists: APIM already has an **`anthropic` API** that speaks
  the native Anthropic contract (injects a real Anthropic key downstream). That keeps
  claude-code on real Claude but moves the secret off the dev-agent — it does NOT make
  the agent GPT-backed (downstream is Anthropic, not GPT).

## 1. GPT exposure map (LIVE-verified)
APIM `aigw-apim-dev-w4x7ibwk4e2is` (RG `rg-ai-gateway-dev-uae`, sub `ea9b2fed-…`).

| API (APIM) | path | backend | downstream auth injected by APIM |
|---|---|---|---|
| `openai` | `/openai` | `https://aifoundry-socrates.cognitiveservices.azure.com/openai` | `authentication-managed-identity` → cognitiveservices (MI) |
| `anthropic` | `/anthropic` | `https://pii-gateway…swedencentral.azurecontainerapps.io` | `x-api-key: {{anthropic-api-key}}` + `anthropic-version: 2023-06-01` |

Caller-facing auth (BOTH APIs, identical dual-auth `<choose>`):
- **JWT** `Authorization: Bearer` validated against tenant `df03bef9-…`, audience
  `api://fe225ae2-c6eb-4e4e-b4c2-79b45b2dce69` (the `ai-apim-mcp-api` SP), OR
- **subscription key** fallback (`context.Subscription`).
- Then `rate-limit-by-key` 100/60s per caller-oid.

GPT deployments on aifoundry-socrates (probed via APIM, 200/400 = exists):
- `gpt-5.4` → **HTTP 200**, `model=gpt-5.4-2026-03-05`, answered "PONG".
- `gpt-5.4-mini` → exists (200).
- `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `o4-mini`, `gpt-5` → 404 MISSING.
- NOTE: gpt-5.4 rejects `max_tokens`; requires `max_completion_tokens` (reasoning-model param).

### Which call paths returned 200
- **APIM `openai` + JWT(aud `api://fe225ae2`)** → 200 (the SP in .env can mint this token via
  client-credentials; it is already granted on that resource). **This is the working path.**
- APIM `openai` + raw cognitiveservices AAD token → 401 "Invalid JWT" (wrong audience).
- **Direct to aifoundry-socrates** (`/openai/deployments/.../chat/completions` and
  `/openai/v1/responses`) with the SP's cognitiveservices AAD token → **401 PermissionDenied**:
  the platform SP `87d9cf17-…` lacks the `Cognitive Services OpenAI User` data action on
  aifoundry-socrates. So direct-to-Foundry is NOT open to this SP; **go through APIM.**

SP (.env) role assignments: `API Management Service Contributor` on the APIM instance,
`Contributor` on `health-service-idp-uae-rg`, AcrPush/AcrPull. No Cognitive Services RBAC.

## 2. claude-code provider-support verdict
- claude-code (image pins `@anthropic-ai/claude-code@2.0.21`, runs `claude -p
  --permission-mode acceptEdits --max-turns N`) speaks the **Anthropic Messages API only**.
- It supports redirection ONLY to gateways exposing one of: Anthropic Messages `/v1/messages`,
  Bedrock InvokeModel, or Vertex rawPredict (official docs, `code.claude.com/docs/.../llm-gateway`).
- **It has NO OpenAI/Azure-OpenAI provider.** Therefore it CANNOT talk to the APIM `openai`
  GPT endpoint directly — a translation shim is mandatory.
- With a shim it is fully usable headless: `ANTHROPIC_BASE_URL=<shim>` (+ `ANTHROPIC_AUTH_TOKEN`),
  no code change.

## 3. Ranked recommendation

### Option A (RECOMMENDED) — LiteLLM Anthropic→Azure-GPT shim, claude-code unchanged
- Deploy LiteLLM proxy (Knative/Deployment) in `dev-agent-system`. Config: one model entry
  `model: azure/gpt-5.4` with `api_base` = APIM `…/openai`, `api_version=2024-10-21`, and the
  APIM JWT (or sub-key) as the key. LiteLLM exposes the unified Anthropic `/v1/messages` endpoint.
- Dev-agent env (replaces `ANTHROPIC_API_KEY`):
  - `ANTHROPIC_BASE_URL=http://litellm.dev-agent-system.svc:4000`
  - `ANTHROPIC_AUTH_TOKEN=<litellm master key>` (a local secret, NOT an Anthropic key)
  - optionally `ANTHROPIC_MODEL=<litellm alias mapping to gpt-5.4>`
- `dev-agent-secrets` then carries the LiteLLM master key + (in LiteLLM's own secret) the APIM
  credential — no Anthropic key anywhere.
- NetworkPolicy: today egress = github.com + api.anthropic.com + apiserver. **Must add** the
  in-cluster LiteLLM svc (and LiteLLM itself needs egress to the APIM gateway FQDN). Drop
  api.anthropic.com from the dev-agent's allow-list.
- Effort: low-moderate (1 Deployment + 1 ConfigMap + NetworkPolicy edit). Risk: moderate —
  Anthropic↔OpenAI tool-use/`acceptEdits` fidelity through LiteLLM must be smoke-tested
  (tool-call translation + the gpt-5.4 `max_completion_tokens` quirk LiteLLM normally handles).

### Option B — replace claude-code with an OpenAI-native headless coding CLI
- e.g. aider (`--yes`/`--message`), OpenAI Codex CLI, or Cline-headless, pointed at APIM `openai`
  (OpenAI-compatible base_url + the APIM JWT/sub-key as api_key, model `gpt-5.4`).
- Pro: no translation shim, native GPT. Con: rewrites the entire W2 entrypoint contract
  (prompt rendering, acceptEdits autonomy, forbidden-path guard, the W4 verify-loop assume
  `claude -p` semantics) — high effort, re-tests everything. Defer unless A's fidelity fails.

### Option C — status quo (keep Anthropic key)
- Lowest effort. If GPT-backing is not a hard requirement, OR use the **existing APIM
  `anthropic` API** so the dev-agent points `ANTHROPIC_BASE_URL` at
  `…/anthropic` with the APIM JWT — this removes the Anthropic key from `dev-agent-secrets`
  (APIM injects it) while keeping real Claude. Note: this is NOT GPT-backed.

## Concrete next step (Option A)
1. Create LiteLLM `config.yaml`: `model_list: [{model_name: claude-via-gpt, litellm_params:
   {model: azure/gpt-5.4, api_base: https://aigw-apim-dev-w4x7ibwk4e2is.azure-api.net/openai,
   api_version: 2024-10-21, api_key: <APIM-jwt-or-subkey>}}]`. Set `master_key`.
2. Deploy LiteLLM (image `ghcr.io/berriai/litellm:<pinned>`) in `dev-agent-system`; svc :4000.
3. Smoke test: `ANTHROPIC_BASE_URL=http://litellm:4000 ANTHROPIC_AUTH_TOKEN=<master>
   claude -p "edit a file"` — verify tool-use/acceptEdits round-trips.
4. Flip `dev-agent-secrets`/OAM: drop `ANTHROPIC_API_KEY`, add `ANTHROPIC_BASE_URL` +
   `ANTHROPIC_AUTH_TOKEN`; update NetworkPolicy egress.

## Blockers / caveats (with sources)
- gpt-5.4 reasoning-param: `max_tokens`→400, needs `max_completion_tokens` (live-observed). LiteLLM
  normally maps this; verify after deploy.
- APIM rate-limit 100 calls/60s per caller-oid (live policy). A multi-turn dev-agent run can burst —
  may need a dedicated APIM product/sub for the dev-agent to avoid sharing the bucket.
- JWT audience must be `api://fe225ae2-…`; the SP is already onboarded (memory "APIM factory JWT
  role"). LiteLLM must refresh the token (1h AAD lifetime) — easiest to use a long-lived APIM
  **subscription key** instead (sub-key branch of the dual-auth `<choose>` is live too).
- Direct-to-Foundry is closed to this SP (no Cognitive Services OpenAI User) — must traverse APIM.
- Tool-use fidelity Anthropic↔Azure-OpenAI through LiteLLM is the one real risk to A; smoke-test gate.

Sources: live az/python probes (this session); claude-code official docs
`code.claude.com/docs/en/llm-gateway` + `/third-party-integrations` (gateway API-format reqs,
ANTHROPIC_BASE_URL, Bedrock/Vertex env); dev-agent Dockerfile + scripts/entrypoint.sh +
substrate/dev-agent/externalsecret.yaml; memory "APIM factory JWT role", "APIM openai serviceUrl fix".
