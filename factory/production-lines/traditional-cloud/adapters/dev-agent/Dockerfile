# DEV-AGENT W2: the developer-agent image.
#
# Runs as an ephemeral K8s Job in `dev-agent-system` (spawned by
# factory/substrate/dev-agent/all-ready-sensor.yaml when every component of an
# OAM app is Ready and a REQUIREMENTS.md exists). The container IS the sandbox:
# NetworkPolicy restricts egress to github.com + the APIM gateway + apiserver,
# which is what makes headless --dangerously-skip-permissions mode safe.
#
# ENGINE: opencode (sst/opencode) driving GPT-5.4 via the Azure APIM gateway
# (openai-compatible). NO Anthropic key, no shim. The coding engine was swapped
# from claude-code -> opencode/GPT-5.4 (see README "Engine swap" + the
# dev-agent-factory.md notes). Rollback = revert the engine-swap commit.
#
# Mirrors the HARD-1 mscv-image pattern: scripts baked in, entrypoint is the
# contract, image is versioned (NEVER :latest — HARD-3).
#
# NO SECRETS in this file or any layer. GITHUB_TOKEN / APIM_SUBSCRIPTION_KEY are
# injected at runtime from the dev-agent-secrets Secret (Key Vault via ESO).
FROM node:22-bookworm-slim

# git (clone/push), python3 (JSON parsing + prompt rendering — no jq needed),
# ca-certificates (HTTPS git + APIM API). gh CLI intentionally absent:
# auth is plain HTTPS x-access-token git, nothing else needs the API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# kubectl, pinned (verify-loop reads ksvc revisions + ct-* Job verdicts via the
# in-cluster SA). Bump deliberately alongside cluster upgrades.
ARG KUBECTL_VERSION=v1.31.4
ADD https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN chmod 0755 /usr/local/bin/kubectl

# opencode CLI, pinned (amd64 — the cluster is AMD64; never :latest, HARD-3).
# Verify the tag exists before building (`npm view opencode-ai versions`) and
# bump deliberately. The `opencode-ai` npm package ships the platform binary.
ARG OPENCODE_VERSION=1.17.4
RUN npm install -g opencode-ai@${OPENCODE_VERSION}

# Default opencode config: the `apim-gpt` provider (openai-compatible) pointed at
# the Azure APIM gateway's openai deployment path. baseURL folds in the
# api-version query param; auth + model selection are env-driven so NO SECRET is
# baked. gpt-5.4 needs max_completion_tokens (emitted by the openai-compatible
# AI-SDK) + an explicit output limit. Overridable at runtime via OPENCODE_CONFIG.
COPY opencode.json /app/opencode.json

COPY scripts/ /agent/scripts/
COPY prompts/ /agent/prompts/
RUN chmod +x /agent/scripts/*.sh

# Non-root (uid 1000 = the node user). HOME must be writable for git config
# and opencode state; entrypoint mkdir -p's it.
USER 1000:1000
ENV HOME=/tmp/dev-agent-home

# Engine config:
#   OPENCODE_CONFIG            - the baked provider config (apim-gpt -> GPT-5.4)
#   OPENCODE_DISABLE_CLAUDE_CODE=1 - never auto-read ~/.claude (no claude-code path)
ENV OPENCODE_CONFIG=/app/opencode.json \
    OPENCODE_DISABLE_CLAUDE_CODE=1

# Env contract (see scripts/entrypoint.sh header): APP_NAME, SOURCE_REPO,
# GITOPS_REPO, GITHUB_TOKEN, APIM_SUBSCRIPTION_KEY, MAX_ITERATIONS (default 3).
ENTRYPOINT ["/agent/scripts/entrypoint.sh"]
