#!/usr/bin/env bash
# HARD-1 (#168): python/fastapi scaffold incl. RT-1 realtime flavor
# (agent_common vendoring + pyproject dep injection) — heredoc lines 40-111 verbatim.
mscv_scaffold_python_fastapi() {
  # Copy onion architecture template
  cp -r $TEMPLATE_DIR/* microservices/$SERVICE_NAME/
  cd microservices/$SERVICE_NAME
  
  # Customize template for the specific service
  sed -i "s/template-service/$SERVICE_NAME/g" pyproject.toml README.md
  sed -i "s/Template Service/$SERVICE_NAME Service/g" README.md
  
  # Update any hardcoded references
  find . -name "*.py" -exec sed -i "s/template_service/$SERVICE_NAME/g" {} \;
  find . -name "*.md" -exec sed -i "s/template-service/$SERVICE_NAME/g" {} \;
  
  # RT-1 (#156): realtime flavor — overwrite src/main.py with a websocket variant
  # wired to agent_common.realtime_fastapi (create_realtime_agent_app) and add
  # aiokafka+websockets deps. Smallest delta that yields a bootable ws service
  # consuming/producing the declared topics from the <realtime>-conn env.
  if [ "${SERVICE_FLAVOR:-webservice}" = "realtime" ]; then
    echo "📡 Applying realtime flavor (websocket + aiokafka) to $SERVICE_NAME"
    mkdir -p src
    cat > src/main.py << 'RTMAIN'
"""RT-1 realtime-service entrypoint (generated). Websocket + Kafka over
agent_common.realtime_fastapi. Topics discovered from CONSUME_*/PRODUCE_*/TOPIC_*
env injected by the realtime-service CD + <realtime>-conn secret."""
import os
from agent_common.realtime_fastapi import create_realtime_agent_app
from agent_common.realtime_agent import GenericRealtimeAgent

SERVICE_NAME = os.getenv("WEBSERVICE_NAME", os.getenv("REALTIME_PLATFORM_NAME", "realtime-service"))

app = create_realtime_agent_app(
    agent_class=GenericRealtimeAgent,
    service_name=SERVICE_NAME,
    description="RT-1 realtime websocket+kafka service",
    endpoints=[],
    websocket_endpoints=[{"path": "/ws", "description": "realtime stream"}],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
RTMAIN
    # RT-1 (#167) DURABLE FIX: the realtime main.py imports the agent_common
    # package, but the onion scaffold image never contained it (-> ModuleNotFound
    # -> pod never Ready). Mechanism A (vendor): copy the agent_common package
    # SOURCE (single source of truth = health-service-idp) into src/agent_common/
    # so PYTHONPATH=/app/src (set by the onion Dockerfile) resolves the import,
    # and the Dockerfile's `COPY src/ src/` bundles it at build time. No wheel
    # (the committed 0.1.0 wheel is stale: missing realtime_*.py), no index.
    echo "📦 Vendoring agent_common package source into src/agent_common"
    AC_SRC="/tmp/agent-common-src-$SERVICE_NAME"
    rm -rf $AC_SRC
    git clone --depth 1 https://$GITHUB_TOKEN@github.com/$GITHUB_USER/health-service-idp.git $AC_SRC
    if [ -d "$AC_SRC/microservices/shared-libs/agent-common/src/agent_common" ]; then
      rm -rf src/agent_common
      cp -r $AC_SRC/microservices/shared-libs/agent-common/src/agent_common src/agent_common
      find src/agent_common -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
      echo "✅ vendored agent_common ($(ls src/agent_common/*.py | wc -l) modules)"
    else
      echo "❌ agent_common source not found in health-service-idp clone"; exit 1
    fi
    rm -rf $AC_SRC
    # Add agent_common's runtime deps to the fastapi scaffold pyproject so
    # `poetry install --only=main` brings them into the image (idempotent).
    # Mirrors agent-common/pyproject.toml: aiokafka, websockets, aioredis,
    # httpx (+ asyncio-mqtt) on top of the onion base (fastapi/pydantic present).
    if [ -f pyproject.toml ]; then
      grep -q '^aiokafka' pyproject.toml || sed -i '/\[tool.poetry.dependencies\]/a aiokafka = "^0.10.0"\nwebsockets = "^12.0"\naioredis = "^2.0.0"\nhttpx = "^0.25.0"\n"asyncio-mqtt" = "^0.16.0"' pyproject.toml
    fi
    echo "✅ realtime flavor applied"
  fi

  echo "✅ Successfully created onion architecture microservice from template"
}
