#!/usr/bin/env bash
# HARD-1 (#168): python/fastapi scaffold incl. realtime flavor.
# RT-2 (#176): realtime flavor is ROLE-BRANCHED (gateway|ingest|processor) and
# consumes the versioned realtime-transport WHEEL instead of git-clone vendoring
# agent_common source (HARD-2 #169 — no drift, provenance via release tag).
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

  if [ "${SERVICE_FLAVOR:-webservice}" = "realtime" ]; then
    ROLE="${SERVICE_ROLE:-gateway}"
    case "$ROLE" in gateway|ingest|processor) ;; *) ROLE="gateway" ;; esac
    echo "📡 Applying realtime flavor (role=$ROLE) to $SERVICE_NAME"
    mkdir -p src

    # --- the developer logic slot (dev-agent edit surface) -------------------
    # Created ONLY if absent: re-scaffolds must never clobber implemented logic
    # (#175 no-clobber also guards the whole dir; this is belt-and-braces).
    if [ ! -f src/handlers.py ]; then
      cat > src/handlers.py << 'RTHANDLERS'
"""Developer logic slot (RT-2). The platform owns transport (Kafka, /ws, HTTP);
this module owns what the bytes MEAN. Implement per REQUIREMENTS.md; the
post-deploy contract test is the acceptance gate.

- to_message(body)  : ingest    — map an HTTP POST body to the produced event.
- transform(message): processor — map a consumed event to the produced event
                                  (return None to drop).
Defaults are passthrough/identity so the service boots before logic lands.
"""
from typing import Any, Dict, Optional


def to_message(body: Dict[str, Any]) -> Dict[str, Any]:
    return body


def transform(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return message
RTHANDLERS
      echo "✅ src/handlers.py logic slot created"
    else
      echo "src/handlers.py exists - preserved (no-clobber)"
    fi

    # --- role-branched entrypoint --------------------------------------------
    case "$ROLE" in
      gateway)
        cat > src/main.py << 'RTMAIN'
"""Realtime GATEWAY (generated, RT-2). Consumes the declared topics and streams
to websocket clients on /ws. Transport via realtime-transport; topics/bindings
from CONSUME_*/PRODUCE_* + <realtime>-conn env (realtime-service CD)."""
import os
from realtime_transport import create_realtime_agent_app, GenericRealtimeAgent

SERVICE_NAME = os.getenv("WEBSERVICE_NAME", os.getenv("REALTIME_PLATFORM_NAME", "realtime-service"))

app = create_realtime_agent_app(
    agent_class=GenericRealtimeAgent,
    service_name=SERVICE_NAME,
    description="Realtime websocket gateway (consume -> /ws)",
    endpoints=[],
    websocket_endpoints=[{"path": "/ws", "description": "realtime stream"}],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
RTMAIN
        ;;
      ingest)
        cat > src/main.py << 'RTMAIN'
"""Realtime INGEST (generated, RT-2). POST /ingest -> handlers.to_message ->
produce to the declared PRODUCE_* topic. Transport via realtime-transport."""
import os
from realtime_transport import create_realtime_ingest_app
from src.handlers import to_message

SERVICE_NAME = os.getenv("WEBSERVICE_NAME", os.getenv("REALTIME_PLATFORM_NAME", "realtime-ingest"))

app = create_realtime_ingest_app(
    service_name=SERVICE_NAME,
    to_message=to_message,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
RTMAIN
        ;;
      processor)
        cat > src/main.py << 'RTMAIN'
"""Realtime PROCESSOR (generated, RT-2). Consume declared CONSUME_* topics ->
handlers.transform -> produce to the declared PRODUCE_* topic. Transport via
realtime-transport."""
import os
from realtime_transport import create_realtime_processor_app
from src.handlers import transform

SERVICE_NAME = os.getenv("WEBSERVICE_NAME", os.getenv("REALTIME_PLATFORM_NAME", "realtime-processor"))

app = create_realtime_processor_app(
    service_name=SERVICE_NAME,
    transform=transform,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
RTMAIN
        ;;
    esac

    # --- dependency: the versioned realtime-transport wheel ------------------
    # HARD-2 (#169): pinned release-asset URL replaces git-clone vendoring of
    # agent_common source. The wheel declares fastapi/pydantic/aiokafka/websockets
    # so poetry resolves transport deps transitively. Idempotent.
    if [ -f pyproject.toml ]; then
      grep -q '^realtime-transport' pyproject.toml || sed -i '/\[tool.poetry.dependencies\]/a realtime-transport = {url = "https://github.com/shlapolosa/health-service-idp/releases/download/realtime-transport-v0.1.0/realtime_transport-0.1.0-py3-none-any.whl"}' pyproject.toml
      # Align template pins with the wheel's requirements (caught live on rtdemo2:
      # wheel needs fastapi >=0.115.14,<0.116.0 but the onion template pins
      # ^0.104.0 -> poetry solver hard-fails the docker build). pydantic ^2.0.0
      # already satisfies the wheel's >=2.11.7,<3. Idempotent.
      sed -i 's/^fastapi = .*$/fastapi = "^0.115.14"/g' pyproject.toml
    fi
    echo "✅ realtime flavor applied (role=$ROLE, realtime-transport wheel)"
  fi

  echo "✅ Successfully created onion architecture microservice from template"
}
