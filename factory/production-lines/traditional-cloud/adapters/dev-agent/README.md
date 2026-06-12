# dev-agent — the developer agent that fills the logic slot (DEV-AGENT W2-W4)

Ephemeral K8s Job that runs when ALL components of an OAM app are Ready and a
`REQUIREMENTS.md` exists: clones the app monorepo, implements the logic slots
(`microservices/<svc>/src/handlers.py` `to_message`/`transform`, or the rasa
variant files) via headless Claude Code, pushes, then iterates against the
HARD-4 contract-test verdicts until green (bounded by `MAX_ITERATIONS`).

Plan: `factory/docs/plans/dev-agent-factory.md` (W2 image, W3 trigger, W4 loop).
Trigger + runtime manifests: `factory/substrate/dev-agent/`.

## Layout

| Path | What |
|---|---|
| `Dockerfile` | node22-slim + git + python3 + pinned kubectl + pinned `@anthropic-ai/claude-code`, non-root uid 1000 |
| `scripts/entrypoint.sh` | gate -> clone -> locate spec -> claude implement -> commit/push -> verify-loop, iterate |
| `scripts/verify-loop.sh` | W4: wait new ksvc revisions -> read `ct-<revision>` Job verdict JSON -> pass/fail |
| `prompts/implement.md` | prompt template (REQUIREMENTS + verdict-feedback slot + edit-surface rules) |
| `tests/dry-run.sh` | PATH-shim harness (git/kubectl/claude stubbed), runs on macOS, no network |

## Env contract (set by the sensor Job / `dev-agent-secrets`)

| Var | Source | Default | Purpose |
|---|---|---|---|
| `APP_NAME` | sensor param (`app.oam.dev/name` label) | required | app == monorepo name |
| `SOURCE_REPO` | optional | `https://github.com/shlapolosa/<APP_NAME>.git` | monorepo |
| `GITOPS_REPO` | optional | `…/<APP_NAME>-gitops.git` | spec fallback location 2 |
| `CENTRAL_GITOPS_REPO` | optional | `…/health-service-idp-gitops.git` | spec fallback location 3 (ledger) |
| `GITHUB_TOKEN` | **secret** `dev-agent-secrets` | required | HTTPS x-access-token clone/push |
| `ANTHROPIC_API_KEY` | **secret** `dev-agent-secrets` | required | Claude Code |
| `MAX_ITERATIONS` | sensor Job env | `3` | implement->verify attempts |
| `NAMESPACE` | sensor Job env | `default` | where the app ksvcs live |
| `SPEC_HASH` | sensor param (annotation) | `""` | informational; entrypoint recomputes |
| `CLAUDE_MAX_TURNS` | optional | `50` | per-run cost guard |
| `VERIFY_TIMEOUT` / `POLL_INTERVAL` | optional | `900` / `10` | verify-loop budget |

REQUIREMENTS.md lookup order: **source-repo root** → **`<app>-gitops` root** →
**ledger `health-service-idp-gitops/oam/applications/<app>-REQUIREMENTS.md`**.

## Build (operator)

```bash
az acr build --registry healthidpuaeacr \
  --image dev-agent:v0.1.0 \
  factory/production-lines/traditional-cloud/adapters/dev-agent/
```

Then point `factory/substrate/dev-agent/all-ready-sensor.yaml` at the new tag
(pinned tag, never `:latest` — HARD-3). Verify the claude-code npm pin exists
first: `npm view @anthropic-ai/claude-code versions`.

## Secrets (NEVER in git)

`dev-agent-secrets` in `dev-agent-system`, sourced from Key Vault
`kv-socrates-6706` via ESO (skeleton: `factory/substrate/dev-agent/externalsecret.yaml`):

| Secret key | Key Vault secret | Notes |
|---|---|---|
| `GITHUB_TOKEN` | `dev-agent-github-token` | FactoryBot installation token / PAT, repo scope on `<app>` + `<app>-gitops` |
| `ANTHROPIC_API_KEY` | `dev-agent-anthropic-key` | Claude Code |

## NetworkPolicy intent

Egress ONLY: github.com, api.anthropic.com, kube-apiserver, DNS. Vanilla AKS
NetworkPolicy cannot scope by FQDN, so `networkpolicy.yaml` allows 443-anywhere
+ DNS and blocks everything else; tighten to the two hostnames when Cilium
(`toFQDNs`) or Calico DNS policy is adopted. Ingress: none.

## Safety rails

- prompts forbid edits outside `microservices/`; entrypoint reverts violations
- pre-push secret scan (AWS/GitHub/Anthropic key + private-key patterns) — repos are PUBLIC
- `.dev-agent/spec-hash` marker breaks the self-trigger loop (own push -> new
  ksvc generation -> new Ready event); only a changed REQUIREMENTS re-runs
- bounded: `MAX_ITERATIONS` (3), `CLAUDE_MAX_TURNS` (50), Job
  `activeDeadlineSeconds` 3600, `backoffLimit` 0

## Test

```bash
bash factory/production-lines/traditional-cloud/adapters/dev-agent/tests/dry-run.sh
```
