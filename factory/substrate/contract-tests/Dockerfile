# HARD-4 (#171): contract-test-runner image.
# Built/pushed by .github/workflows/contract-test-runner-ci.yml to
#   healthidpuaeacr.azurecr.io/contract-test-runner:<sha>
#
# IMPORTANT: build for the cluster's arch (AMD64) — Mac M-series defaults to
# arm64 and the cluster will fail to pull. CI runs on ubuntu (amd64) already;
# for a local build pass --platform linux/amd64.
FROM python:3.11-slim

# aiokafka (Kafka produce/consume), websockets (ws roundtrip), httpx (health +
# graphql). Pinned for reproducibility; no app secrets ever baked in — all creds
# are read from the mounted <comp>-conn secret at runtime.
RUN pip install --no-cache-dir \
        aiokafka==0.10.0 \
        websockets==12.0 \
        httpx==0.27.2

WORKDIR /app
COPY runner.py /app/runner.py

# Non-root (Knative/PSS friendly; the Job also sets runAsNonRoot).
RUN useradd -u 1000 -m runner
USER 1000

ENTRYPOINT ["python", "-u", "/app/runner.py"]
