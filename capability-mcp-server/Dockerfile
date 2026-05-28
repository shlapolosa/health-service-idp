# Build context MUST be the repo root (the image bundles the capability-factory/ data tree):
#   docker build -f capability-mcp-server/Dockerfile -t <acr>/capability-mcp-server:<tag> .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates tar && rm -rf /var/lib/apt/lists/*

# kubectl + vela CLIs — vela renders ComponentDefinition schemas live (catalog.describe) and runs
# `vela dry-run` (catalog.validate / app.submit pre-check). Pin vela to the cluster's version (1.10.8).
RUN curl -fsSL https://dl.k8s.io/release/v1.28.4/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl
RUN curl -fsSL https://github.com/kubevela/kubevela/releases/download/v1.10.8/vela-v1.10.8-linux-amd64.tar.gz \
      | tar xz -C /tmp \
    && mv /tmp/linux-amd64/vela /usr/local/bin/vela && chmod +x /usr/local/bin/vela

COPY capability-mcp-server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY capability-mcp-server/src/ /app/src/
COPY capability-mcp-server/main.py /app/main.py
COPY capability-factory/ /capability-factory/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /capability-factory
USER appuser

ENV PYTHONPATH=/app PORT=8080 CAPABILITY_FACTORY_DIR=/capability-factory
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1
CMD ["python", "main.py"]
