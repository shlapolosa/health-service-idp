# RASA-CONTAINER (#178): the INVARIANT rasa base image.
#
# Pattern: invariant container + variant repo (same split as mscv-image HARD-1
# and realtime-transport HARD-2). Everything a rasa bot needs that the
# developer never edits is baked HERE, once:
#   - the pinned rasa runtime (rasa-plus 3.7.10, exactly what chat-template
#     pins today — non-breaking) + the full proven python dependency set
#   - server settings (ports, CORS, telemetry off)
#   - endpoints.yml / credentials.yml plumbing (env-driven, see config/)
#   - the train-cache entrypoint (rasa train ONLY when the bot content hash
#     has no trained model yet — see scripts/train-if-needed.sh)
#
# The VARIANT bot (domain.yml, config.yml, data/, actions/) is COPY'd to
# /app/bot/ by a 3-line Dockerfile in the generated app repo:
#
#   FROM healthidpuaeacr.azurecr.io/rasa-base:v1.0.0
#   COPY --chown=1001:1001 . /app/bot/
#   RUN train-if-needed.sh        # bakes the model at CI build time
#
# HARD-3 image-pin discipline: this image is ONLY ever referenced by an
# explicit version tag (rasa-base:v1.0.0). NEVER :latest.
#
# Base mirrors the proven chat-template docker/Dockerfile build
# (python:3.10-slim + build toolchain + poetry, virtualenvs disabled).
FROM python:3.10-slim

# System build toolchain (DIET/TED native deps: blis, cchardet, uvloop) + poetry.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libc6-dev \
        python3-dev \
        curl \
    && curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && poetry config virtualenvs.create false \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Same setuptools pin as the chat-template base build.
RUN pip install --no-cache-dir --upgrade setuptools==65.5.1 virtualenv

# Invariant python dependency set (mirrors chat-template pyproject.toml,
# incl. the rasa-plus supplemental package source). Installed ONCE here so
# generated-repo CI never runs a dependency install again.
WORKDIR /opt/rasa-base
COPY pyproject.toml ./
RUN poetry install --no-root --no-interaction --no-ansi \
    # extras the legacy rasa-actions Dockerfile layered per-build — bake them too
    && pip install --no-cache-dir "certifi>=2023.11.17" "httpx>=0.24.0" \
    && rm -rf /root/.cache

# Invariant server config (fallbacks; a bot may ship its own endpoints.yml /
# credentials.yml in /app/bot/ to override — see docker-entrypoint.sh).
COPY config/endpoints.yml config/credentials.yml /opt/rasa-base/config/

# Entrypoint + content-hash train cache.
COPY scripts/docker-entrypoint.sh scripts/train-if-needed.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh /usr/local/bin/train-if-needed.sh \
    && mkdir -p /app/bot /app/models \
    && chown -R 1001:1001 /app

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    PYTHONUNBUFFERED=1 \
    RASA_TELEMETRY_ENABLED=false \
    RASA_BOT_DIR=/app/bot \
    RASA_MODELS_DIR=/app/models

USER 1001
WORKDIR /app/bot

# 5005 = rasa server (CD: rasa-chatbot ksvc), 5055 = actions server (CMD ["actions"]).
EXPOSE 5005 5055

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["run"]
