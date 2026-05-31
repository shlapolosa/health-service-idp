# Build context MUST be repo root. The image bakes in:
#   - this service's own source (factory/adapters/mcp-read-gateway/)
#   - the shared capability-mcp-core library (factory/shared-libs/capability-mcp-core/)
#   - the factory knowledge-base data (factory/core/knowledge-base/)
#   - the catalog + composition YAML from factory/production-lines/traditional-cloud/
# Build from repo root:
#   docker build -f factory/adapters/mcp-read-gateway/Dockerfile \
#     -t <acr>/capability-mcp-factory:<tag> .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates tar && rm -rf /var/lib/apt/lists/*

# kubectl + vela CLIs — needed by the shared use cases that this image
# imports from capability-mcp-core (oam.dry_run, crossplane.dry_run,
# catalog tools when factory-level needs to delegate).
RUN curl -fsSL https://dl.k8s.io/release/v1.28.4/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl
RUN curl -fsSL https://github.com/kubevela/kubevela/releases/download/v1.10.8/vela-v1.10.8-linux-amd64.tar.gz \
      | tar xz -C /tmp \
    && mv /tmp/linux-amd64/vela /usr/local/bin/vela && chmod +x /usr/local/bin/vela

COPY factory/adapters/mcp-read-gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Bake in this service's own source.
COPY factory/adapters/mcp-read-gateway/src/ /app/src/
COPY factory/adapters/mcp-read-gateway/main.py /app/main.py

# Bake in the shared use cases from capability-mcp-core as an importable
# package. We rename the path to `capability_mcp_core` (underscores)
# to match the import in src/mcp_server.py. The src tree already ships
# its own __init__.py files, so no `touch` is needed.
COPY factory/shared-libs/capability-mcp-core/src/ /app/capability_mcp_core/

# Bake in the data trees the shared use cases need.
COPY factory/core/knowledge-base/ /capability-factory/
COPY factory/production-lines/traditional-cloud/adapters/catalog/ /repo/crossplane/oam/
COPY factory/production-lines/traditional-cloud/adapters/composition/application-claim-composition.yaml /repo/crossplane/application-claim-composition.yaml

# Bake the sibling cafe-spec manifests so factory.list_manufacturers
# returns real data. The build-helpers/stage-cafe-spec.sh script copies
# ../cafe-spec/manufacturers/<id>/manifest.yaml into the local
# cafe-spec-staging/ dir (Docker build context can't reach outside the repo).
# Run that script BEFORE `docker build`. CI must do the same.
COPY factory/adapters/mcp-read-gateway/cafe-spec-staging/ /cafe-spec/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /capability-factory /repo /cafe-spec
USER appuser

ENV PYTHONPATH=/app PORT=8080 \
    CAPABILITY_FACTORY_DIR=/capability-factory \
    REPO_ROOT=/repo \
    CAFE_SPEC_ROOT=/cafe-spec
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1
CMD ["python", "main.py"]
