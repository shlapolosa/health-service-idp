# Build context MUST be repo root:
#   docker build -f factory/production-lines/traditional-cloud/adapters/compose-mcp/Dockerfile \
#     -t <acr>/capability-mcp-mfg-tc:<tag> .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates tar && rm -rf /var/lib/apt/lists/*

# kubectl + vela CLIs — required by catalog use cases that call out to them.
RUN curl -fsSL https://dl.k8s.io/release/v1.28.4/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl
RUN curl -fsSL https://github.com/kubevela/kubevela/releases/download/v1.10.8/vela-v1.10.8-linux-amd64.tar.gz \
      | tar xz -C /tmp \
    && mv /tmp/linux-amd64/vela /usr/local/bin/vela && chmod +x /usr/local/bin/vela

COPY factory/production-lines/traditional-cloud/adapters/compose-mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# This service's own source.
COPY factory/production-lines/traditional-cloud/adapters/compose-mcp/src/ /app/src/
COPY factory/production-lines/traditional-cloud/adapters/compose-mcp/main.py /app/main.py

# Shared use cases from capability-mcp-core (importable as `capability_mcp_core`).
COPY factory/shared-libs/capability-mcp-core/src/ /app/capability_mcp_core/

# Data trees the shared use cases need.
COPY factory/core/knowledge-base/ /capability-factory/
COPY factory/production-lines/traditional-cloud/adapters/catalog/ /repo/crossplane/oam/
COPY factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml /repo/crossplane/application-claim-composition.yaml

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /capability-factory /repo
USER 1000

ENV PYTHONPATH=/app PORT=8080 \
    CAPABILITY_FACTORY_DIR=/capability-factory \
    REPO_ROOT=/repo
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1
CMD ["python", "main.py"]
