# DEV-AGENT W2: the developer-agent image.
#
# Runs as an ephemeral K8s Job in `dev-agent-system` (spawned by
# factory/substrate/dev-agent/all-ready-sensor.yaml when every component of an
# OAM app is Ready and a REQUIREMENTS.md exists). The container IS the sandbox:
# NetworkPolicy restricts egress to github.com + api.anthropic.com + apiserver,
# which is what makes headless acceptEdits mode safe.
#
# Mirrors the HARD-1 mscv-image pattern: scripts baked in, entrypoint is the
# contract, image is versioned (NEVER :latest — HARD-3).
#
# NO SECRETS in this file or any layer. GITHUB_TOKEN / ANTHROPIC_API_KEY are
# injected at runtime from the dev-agent-secrets Secret (Key Vault via ESO).
FROM node:22-bookworm-slim

# git (clone/push), python3 (JSON parsing + prompt rendering — no jq needed),
# ca-certificates (HTTPS git + Anthropic API). gh CLI intentionally absent:
# auth is plain HTTPS x-access-token git, nothing else needs the API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# kubectl, pinned (verify-loop reads ksvc revisions + ct-* Job verdicts via the
# in-cluster SA). Bump deliberately alongside cluster upgrades.
ARG KUBECTL_VERSION=v1.31.4
ADD https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN chmod 0755 /usr/local/bin/kubectl

# Claude Code CLI, pinned. Verify the tag exists before building
# (`npm view @anthropic-ai/claude-code versions`) and bump deliberately.
ARG CLAUDE_CODE_VERSION=2.0.21
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

COPY scripts/ /agent/scripts/
COPY prompts/ /agent/prompts/
RUN chmod +x /agent/scripts/*.sh

# Non-root (uid 1000 = the node user). HOME must be writable for git config
# and the claude CLI state; entrypoint mkdir -p's it.
USER 1000:1000
ENV HOME=/tmp/dev-agent-home

# Env contract (see scripts/entrypoint.sh header): APP_NAME, SOURCE_REPO,
# GITOPS_REPO, GITHUB_TOKEN, ANTHROPIC_API_KEY, MAX_ITERATIONS (default 3).
ENTRYPOINT ["/agent/scripts/entrypoint.sh"]
