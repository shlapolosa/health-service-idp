"""FastAPI application factories for the three realtime transport roles.

  * create_realtime_agent_app  — gateway: consume topic(s) -> /ws broadcast (RT-1).
  * create_realtime_ingest_app  — ingest: POST /ingest -> to_message -> produce.
  * create_realtime_processor_app — processor: consume -> transform -> produce.

All three share the resilient connection machinery in realtime_agent: Kafka init
is NON-FATAL, so a broker blip never takes down the HTTP edge or live ws clients.

Diverges from agent_common.realtime_fastapi: the AI-agent HTTP task endpoints
(AgentRequestModel/AgentTask/process_task wiring) are dropped — transport roles
expose only the role-specific surface plus /health.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Type, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect

from .realtime_agent import RealtimeAgent, GenericRealtimeAgent
from .config import RealtimeConfig, get_realtime_config
from .secret_loader import load_realtime_platform_secrets, configure_config_from_secrets
from .websocket_manager import WebSocketConnectionManager

logger = logging.getLogger(__name__)


def _identity_to_message(body: Any) -> Dict[str, Any]:
    """Default to_message: passthrough."""
    return body if isinstance(body, dict) else {"value": body}


def _identity_transform(msg: Any) -> Optional[Dict[str, Any]]:
    """Default transform: identity."""
    return msg if isinstance(msg, dict) else {"value": msg}


async def _build_and_init_agent(
    agent_class: Type[RealtimeAgent], service_name: str, description: str,
    config: Optional[RealtimeConfig],
) -> RealtimeAgent:
    """Build config (best-effort secret overlay) + agent, then init (non-fatal)."""
    if not config:
        config = get_realtime_config(service_name)

    # Best-effort platform secret overlay. The <realtime>-conn binding secret is
    # already mounted via envFrom; this loader is a supplement, never a hard dep.
    if config.realtime_platform:
        try:
            secrets = await load_realtime_platform_secrets(config.realtime_platform)
            config = configure_config_from_secrets(config, secrets)
        except Exception as e:
            logger.warning(
                f"Platform secret loader unavailable ({e}); continuing with "
                f"binding env (KAFKA_BOOTSTRAP_SERVERS/CONSUME_*/PRODUCE_*)"
            )

    agent = agent_class(
        service_type=service_name.split("-")[0],
        service_name=service_name,
        description=description,
        config=config,
    )
    await agent.initialize()  # non-fatal: see RealtimeAgent._initialize_realtime_connections
    return agent


# =====================================================================
# Gateway role (RT-1): consume -> /ws broadcast
# =====================================================================

def create_realtime_agent_app(
    agent_class: Type[RealtimeAgent] = GenericRealtimeAgent,
    service_name: str = "realtime-gateway",
    description: str = "",
    endpoints: Optional[List[Dict[str, str]]] = None,
    websocket_endpoints: Optional[List[Dict[str, str]]] = None,
    config: Optional[RealtimeConfig] = None,
    verify_token: Optional[Callable[[Optional[str]], bool]] = None,
) -> FastAPI:
    """Gateway: a websocket service that broadcasts consumed Kafka events to /ws."""
    agent: Optional[RealtimeAgent] = None
    websocket_manager = WebSocketConnectionManager()

    # RT-1 (#156): in-service JWT gate. APIM does not proxy /ws, so /ws is exposed
    # via Istio and JWT verified here. Default verifier: if JWT_ISSUER_URI is set
    # (from the bound <identity>-conn) require a non-empty bearer/?token=, else open.
    _jwt_issuer = os.getenv("JWT_ISSUER_URI") or os.getenv("AUTH0_ISSUER")

    def _default_verify_token(token: Optional[str]) -> bool:
        if not _jwt_issuer:
            return True
        return bool(token)

    _verify = verify_token or _default_verify_token

    # RT-1 (#167): ws routes must register at app-BUILD time; runtime config loads
    # later in lifespan. Decide from build-time signals: WEBSOCKET_ENABLED env (set
    # by the CD), an explicit websocket_endpoints list, or a pre-supplied config.
    _websocket_enabled = (
        os.getenv("WEBSOCKET_ENABLED", "false").lower() == "true"
        or bool(websocket_endpoints)
        or (config is not None and getattr(config, "websocket_enabled", False))
    )

    def _extract_ws_token(ws: WebSocket) -> Optional[str]:
        auth = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ws.query_params.get("token")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent
        logger.info(f"Starting realtime gateway {service_name}...")
        agent = await _build_and_init_agent(agent_class, service_name, description, config)
        if agent.config.websocket_enabled:
            asyncio.create_task(_websocket_cleanup_task(websocket_manager))
        yield
        logger.info(f"Shutting down realtime gateway {service_name}...")
        if agent:
            await agent.cleanup()

    app = FastAPI(
        title=f"{service_name} Realtime Gateway",
        description=(description or service_name) + " (realtime gateway)",
        version="1.0.0", lifespan=lifespan,
    )

    async def get_websocket_manager() -> WebSocketConnectionManager:
        return websocket_manager

    @app.get("/health")
    async def health_check():
        base = {"status": "healthy", "service": service_name}
        if agent:
            st = agent.get_realtime_status()
            base.update({
                "realtime_enabled": st.realtime_enabled,
                "websocket_enabled": st.websocket_enabled,
                "connections": len(st.connections),
                "message_count": st.message_count,
                "error_count": st.error_count,
            })
        return base

    @app.get("/")
    async def root():
        return {"service": service_name, "status": "running", "type": "realtime-gateway"}

    if _websocket_enabled:

        @app.websocket("/ws")
        async def websocket_endpoint(
            websocket: WebSocket,
            manager: WebSocketConnectionManager = Depends(get_websocket_manager),
        ):
            # RT-1 (#156): in-service JWT gate on the upgrade.
            if not _verify(_extract_ws_token(websocket)):
                await websocket.close(code=4401)
                return
            await manager.connect(websocket)
            # RT-1 (#167): bridge this connection into the agent's broadcast set,
            # else streamed telemetry never reaches /ws clients (LAG=0 but nothing
            # delivered). manager.connect() alone does NOT register it there.
            if agent:
                await agent.add_websocket_connection(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.handle_message(websocket, data)
            except WebSocketDisconnect:
                await manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.disconnect(websocket, reason=f"Error: {str(e)}")
            finally:
                if agent:
                    await agent.remove_websocket_connection(websocket)

        # Custom ws endpoints; skip the reserved /ws (it carries the JWT gate).
        _reserved = {"/ws"}
        for ws_config in (websocket_endpoints or []):
            path = ws_config["path"]
            if path in _reserved:
                continue
            handler_name = ws_config.get("handler", "default")
            auto_subscribe = ws_config.get("auto_subscribe", [])

            def create_ws_handler(subscribe_topics: List[str], name: str):
                async def ws_handler(
                    websocket: WebSocket,
                    manager: WebSocketConnectionManager = Depends(get_websocket_manager),
                ):
                    await manager.connect(websocket, metadata={"endpoint_type": name})
                    if agent:
                        await agent.add_websocket_connection(websocket)
                    for topic in subscribe_topics:
                        await manager.subscribe_to_topic(websocket, topic)
                    try:
                        while True:
                            data = await websocket.receive_text()
                            await manager.handle_message(websocket, data)
                    except WebSocketDisconnect:
                        await manager.disconnect(websocket)
                    except Exception as e:
                        await manager.disconnect(websocket, reason=f"Error: {str(e)}")
                    finally:
                        if agent:
                            await agent.remove_websocket_connection(websocket)
                return ws_handler

            app.add_api_websocket_route(path, create_ws_handler(auto_subscribe, handler_name))

    return app


# =====================================================================
# Ingest role: POST /ingest -> to_message -> produce
# =====================================================================

def create_realtime_ingest_app(
    service_name: str = "realtime-ingest",
    produce_topic: Optional[str] = None,
    to_message: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    description: str = "",
    config: Optional[RealtimeConfig] = None,
    agent_class: Type[RealtimeAgent] = GenericRealtimeAgent,
) -> FastAPI:
    """Ingest: HTTP edge that maps a POST body to an event and produces it.

    ``produce_topic`` defaults to the first PRODUCE_* binding env. ``to_message``
    defaults to identity passthrough. No websocket routes.
    """
    agent: Optional[RealtimeAgent] = None
    _to_message = to_message or _identity_to_message
    _resolved_topic = produce_topic  # may be None at build; resolved in lifespan

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent, _resolved_topic
        logger.info(f"Starting realtime ingest {service_name}...")
        agent = await _build_and_init_agent(agent_class, service_name, description, config)
        if not _resolved_topic:
            produce = agent.config.produce_topics
            _resolved_topic = produce[0] if produce else None
            if not _resolved_topic:
                logger.warning("Ingest has no produce_topic and no PRODUCE_* binding env")
        yield
        if agent:
            await agent.cleanup()

    app = FastAPI(
        title=f"{service_name} Realtime Ingest",
        description=(description or service_name) + " (realtime ingest)",
        version="1.0.0", lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check():
        base = {"status": "healthy", "service": service_name}
        if agent:
            st = agent.get_realtime_status()
            base.update({"realtime_enabled": st.realtime_enabled,
                         "message_count": st.message_count,
                         "error_count": st.error_count})
        return base

    @app.post("/ingest")
    async def ingest(body: Dict[str, Any]):
        if agent is None:
            raise HTTPException(status_code=503, detail="Ingest not initialized")
        if not _resolved_topic:
            raise HTTPException(status_code=503, detail="No produce topic configured")
        try:
            message = _to_message(body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"to_message failed: {e}")
        try:
            await agent.send_kafka_message(_resolved_topic, message)
        except Exception as e:
            # Producer not yet (re)connected — surface 503 so the caller retries;
            # the background reconnect will recover the producer.
            raise HTTPException(status_code=503, detail=f"produce failed: {e}")
        return {"status": "produced", "topic": _resolved_topic}

    return app


# =====================================================================
# Processor role: consume -> transform -> produce
# =====================================================================

def create_realtime_processor_app(
    service_name: str = "realtime-processor",
    consume_topics: Optional[List[str]] = None,
    produce_topic: Optional[str] = None,
    transform: Optional[Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = None,
    description: str = "",
    config: Optional[RealtimeConfig] = None,
    agent_class: Type[RealtimeAgent] = GenericRealtimeAgent,
) -> FastAPI:
    """Processor: consume topic(s), run transform, produce non-None results.

    ``consume_topics`` defaults to the config streaming_topics (CONSUME_* env).
    ``produce_topic`` defaults to the first PRODUCE_* binding env. ``transform``
    defaults to identity. /health only.
    """
    agent: Optional[RealtimeAgent] = None
    _transform = transform or _identity_transform
    _resolved_produce = produce_topic

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent, _resolved_produce
        logger.info(f"Starting realtime processor {service_name}...")

        cfg = config or get_realtime_config(service_name)
        # If consume_topics passed explicitly, override the config's resolved set
        # so the consumer subscribes to exactly what the role declared.
        if consume_topics:
            cfg.streaming_topics = list(consume_topics)

        agent = await _build_and_init_agent(agent_class, service_name, description, cfg)

        if not _resolved_produce:
            produce = agent.config.produce_topics
            _resolved_produce = produce[0] if produce else None

        async def _make_handler():
            async def handler(value):
                try:
                    result = _transform(value)
                except Exception as e:
                    logger.error(f"transform failed: {e}")
                    return
                if result is None:
                    return  # filtered out
                if not _resolved_produce:
                    logger.warning("processor produced a result but no produce topic configured")
                    return
                try:
                    await agent.send_kafka_message(_resolved_produce, result)
                except Exception as e:
                    logger.error(f"processor produce failed: {e}")
            return handler

        handler = await _make_handler()
        for topic in agent.config.streaming_topics:
            agent.register_message_handler(topic, handler)
        yield
        if agent:
            await agent.cleanup()

    app = FastAPI(
        title=f"{service_name} Realtime Processor",
        description=(description or service_name) + " (realtime processor)",
        version="1.0.0", lifespan=lifespan,
    )

    @app.get("/health")
    async def health_check():
        base = {"status": "healthy", "service": service_name}
        if agent:
            st = agent.get_realtime_status()
            base.update({"realtime_enabled": st.realtime_enabled,
                         "message_count": st.message_count,
                         "error_count": st.error_count})
        return base

    return app


async def _websocket_cleanup_task(manager: WebSocketConnectionManager):
    """Background task to clean up inactive WebSocket connections."""
    while True:
        try:
            await asyncio.sleep(300)
            await manager.cleanup_inactive_connections(timeout_seconds=600)
        except Exception as e:
            logger.error(f"Error in WebSocket cleanup task: {e}")
            await asyncio.sleep(60)
