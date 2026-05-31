# Build context = repo root, so secrets / .env are NEVER on the COPY path.
#   docker build -f capability-factory-mcp/Dockerfile -t <acr>/capability-factory-mcp:<tag> .
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY capability-factory-mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY capability-factory-mcp/src/ /app/src/
COPY capability-factory-mcp/main.py /app/main.py

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER 1000

ENV PYTHONPATH=/app PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz').status==200 else 1)" || exit 1
CMD ["python", "main.py"]
