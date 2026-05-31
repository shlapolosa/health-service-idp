# Build context = repo root.
#   docker build -f factory/adapters/mcp-web-gateway/Dockerfile -t healthidpuaeacr.azurecr.io/capability-web-mcp:<tag> .
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY factory/adapters/mcp-web-gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY factory/adapters/mcp-web-gateway/src/ /app/src/
COPY factory/adapters/mcp-web-gateway/main.py /app/main.py

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER 1000

ENV PYTHONPATH=/app PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz').status==200 else 1)" || exit 1
CMD ["python", "main.py"]
