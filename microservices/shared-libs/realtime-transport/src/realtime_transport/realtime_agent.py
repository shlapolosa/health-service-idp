"""Real-time transport engine.

Divergence from agent_common.realtime_agent (documented intentionally):
  * NO BaseMicroserviceAgent inheritance — the minimal lifecycle (initialize /
    cleanup) is inlined, so this package has zero dependency on agent_common.
  * NO BaseProcessor / abstract _create_processor / _get_supported_task_types —
    a transport relays bytes, it has no agent task-processing. GenericRealtimeAgent
    is the concrete default (no abstract base to subclass).
  * Agent identity is a plain string (service_type / service_name) end-to-end —
    no AgentType / ImplementationType enums.
  * Kafka init is NON-FATAL (RT-SVC-RESILIENCE): a broker blip must not take down
    the HTTP ingest edge or live ws connections. On failure we log + schedule a
    background reconnect with exponential backoff.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime

from .config import RealtimeConfig
from .models import (
    ws_json_default,
    RealtimeEvent, EventType, ConnectionStatus, RealtimeConnectionInfo,
    RealtimeServiceStatus, WebSocketMessage,
)

logger = logging.getLogger(__name__)

# Background Kafka reconnect backoff (seconds): capped exponential.
_RECONNECT_BACKOFF = [1, 2, 5, 10, 30, 60]


class RealtimeAgent:
    """Real-time transport engine: Kafka/MQTT consume+produce and WebSocket fan-out.

    Concrete and instantiable (no abstract methods). ``GenericRealtimeAgent`` is
    a thin alias retained for naming compatibility with scaffolded entrypoints.
    """

    def __init__(self, agent_type: str = None, agent_name: str = None,
                 description: str = "", config: RealtimeConfig = None,
                 *, service_type: str = None, service_name: str = None):
        # Accept either the RT-1 entrypoint naming (agent_type/agent_name — how
        # create_realtime_agent_app instantiates the class) or the transport
        # naming (service_type/service_name). Identity is a plain string either
        # way; service_name is the only identity the transport needs.
        resolved_type = service_type or agent_type or "realtime"
        resolved_name = service_name or agent_name or resolved_type
        self.agent_id = str(uuid.uuid4())
        self.service_type = resolved_type
        # ``agent_type`` retained as an alias for entrypoints/health that read it.
        self.agent_type = resolved_type
        self.name = resolved_name
        self.description = description
        self.config = config

        # Backing-service clients
        self.kafka_producer = None
        self.kafka_consumer = None
        self.mqtt_client = None
        self.redis_client = None

        # WebSocket connections the engine broadcasts consumed events to
        self.websocket_connections: Set = set()

        # Connection status tracking
        self.connections: Dict[str, RealtimeConnectionInfo] = {}

        # Handlers
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.message_handlers: Dict[str, Callable] = {}  # topic -> handler

        # Statistics
        self.message_count = 0
        self.error_count = 0
        self.last_activity = None

        self._kafka_reconnecting = False

        logger.info(f"RealtimeAgent {self.name} initialized (type={self.service_type})")

    # --- lifecycle -----------------------------------------------------------

    async def initialize(self):
        """Initialize backing-service connections (non-fatal)."""
        if self.config.realtime_platform or self.config.kafka_bootstrap_servers:
            await self._initialize_realtime_connections()
            logger.info(f"RealtimeAgent {self.name} connection init attempted")

    async def cleanup(self):
        await self._cleanup_realtime_connections()
        logger.info(f"RealtimeAgent {self.name} cleanup completed")

    # --- connection init (resilient) -----------------------------------------

    async def _initialize_realtime_connections(self):
        """Initialize connections. NON-FATAL: failures log + schedule a
        background reconnect; startup proceeds so HTTP/ws stay available."""
        if self.config.kafka_bootstrap_servers:
            try:
                await self._initialize_kafka()
            except Exception as e:
                logger.warning(
                    f"Kafka init failed ({e}); serving without Kafka, "
                    f"background reconnect scheduled"
                )
                self.connections["kafka"] = RealtimeConnectionInfo(
                    service_name="kafka", connection_type="kafka",
                    status=ConnectionStatus.ERROR,
                    endpoint=self.config.kafka_bootstrap_servers or "unknown",
                    error_message=str(e),
                )
                self.error_count += 1
                self._schedule_kafka_reconnect()

        if self.config.mqtt_host:
            try:
                await self._initialize_mqtt()
            except Exception as e:
                logger.warning(f"MQTT init failed ({e}); serving without MQTT")
                self.error_count += 1

        if self.config.redis_host:
            try:
                await self._initialize_redis()
            except Exception as e:
                logger.warning(f"Redis init failed ({e}); serving without Redis")
                self.error_count += 1

    async def _initialize_kafka(self):
        from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

        self.kafka_producer = AIOKafkaProducer(
            bootstrap_servers=self.config.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=ws_json_default).encode('utf-8'),
        )
        await self.kafka_producer.start()

        if self.config.streaming_topics:
            self.kafka_consumer = AIOKafkaConsumer(
                *self.config.streaming_topics,
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                group_id=self.config.streaming_consumer_group or f"{self.name}-group",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            )
            await self.kafka_consumer.start()
            asyncio.create_task(self._kafka_consumer_loop())

        self.connections["kafka"] = RealtimeConnectionInfo(
            service_name="kafka", connection_type="kafka",
            status=ConnectionStatus.CONNECTED,
            endpoint=self.config.kafka_bootstrap_servers,
            connected_at=datetime.now(),
        )
        logger.info(f"Kafka connections initialized for {self.name}")

    def _schedule_kafka_reconnect(self):
        if self._kafka_reconnecting:
            return
        self._kafka_reconnecting = True
        asyncio.create_task(self._kafka_reconnect_loop())

    async def _kafka_reconnect_loop(self):
        """Background reconnect with capped exponential backoff."""
        attempt = 0
        while True:
            delay = _RECONNECT_BACKOFF[min(attempt, len(_RECONNECT_BACKOFF) - 1)]
            await asyncio.sleep(delay)
            attempt += 1
            try:
                await self._initialize_kafka()
                logger.info(f"Kafka reconnected for {self.name} after {attempt} attempt(s)")
                self._kafka_reconnecting = False
                return
            except Exception as e:
                logger.warning(f"Kafka reconnect attempt {attempt} failed ({e})")

    async def _initialize_mqtt(self):
        import asyncio_mqtt
        self.mqtt_client = asyncio_mqtt.Client(
            hostname=self.config.mqtt_host, port=self.config.mqtt_port,
            username=self.config.mqtt_user, password=self.config.mqtt_password,
        )
        await self.mqtt_client.__aenter__()
        if self.config.mqtt_topics:
            for topic in self.config.mqtt_topics:
                await self.mqtt_client.subscribe(topic)
            asyncio.create_task(self._mqtt_listener_loop())
        self.connections["mqtt"] = RealtimeConnectionInfo(
            service_name="mqtt", connection_type="mqtt",
            status=ConnectionStatus.CONNECTED,
            endpoint=f"{self.config.mqtt_host}:{self.config.mqtt_port}",
            connected_at=datetime.now(),
        )

    async def _initialize_redis(self):
        import aioredis
        self.redis_client = await aioredis.from_url(
            f"redis://{self.config.redis_host}:{self.config.redis_port}"
        )
        await self.redis_client.ping()
        self.connections["redis"] = RealtimeConnectionInfo(
            service_name="redis", connection_type="redis",
            status=ConnectionStatus.CONNECTED,
            endpoint=f"{self.config.redis_host}:{self.config.redis_port}",
            connected_at=datetime.now(),
        )

    async def _cleanup_realtime_connections(self):
        try:
            if self.kafka_producer:
                await self.kafka_producer.stop()
            if self.kafka_consumer:
                await self.kafka_consumer.stop()
            if self.mqtt_client:
                await self.mqtt_client.__aexit__(None, None, None)
            if self.redis_client:
                await self.redis_client.close()
            for websocket in self.websocket_connections.copy():
                try:
                    await websocket.close()
                except Exception:
                    pass
            self.websocket_connections.clear()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    # --- consume loops -------------------------------------------------------

    async def _kafka_consumer_loop(self):
        try:
            async for message in self.kafka_consumer:
                try:
                    await self._handle_kafka_message(message)
                    self.message_count += 1
                    self.last_activity = datetime.now()
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    self.error_count += 1
        except Exception as e:
            logger.error(f"Kafka consumer loop error: {e}")
            self.error_count += 1

    async def _mqtt_listener_loop(self):
        try:
            async for message in self.mqtt_client.messages:
                try:
                    await self._handle_mqtt_message(message)
                    self.message_count += 1
                    self.last_activity = datetime.now()
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")
                    self.error_count += 1
        except Exception as e:
            logger.error(f"MQTT listener loop error: {e}")
            self.error_count += 1

    async def _handle_kafka_message(self, message):
        topic = message.topic
        if topic in self.message_handlers:
            await self.message_handlers[topic](message.value)
        else:
            event = RealtimeEvent(
                event_type=EventType.DATA_PROCESSED,
                source_service=self.name, source_agent=self.service_type,
                data={"topic": topic, "message": message.value,
                      "offset": message.offset, "partition": message.partition},
            )
            await self._emit_event(event)

    async def _handle_mqtt_message(self, message):
        topic = message.topic.value
        payload = message.payload.decode('utf-8')
        if topic in self.message_handlers:
            await self.message_handlers[topic](payload)
        else:
            event = RealtimeEvent(
                event_type=EventType.DATA_PROCESSED,
                source_service=self.name, source_agent=self.service_type,
                data={"topic": topic, "payload": payload},
            )
            await self._emit_event(event)

    async def _emit_event(self, event: RealtimeEvent):
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
        if self.websocket_connections:
            message = WebSocketMessage(
                message_type="event", payload=event.__dict__,
                correlation_id=event.correlation_id,
            )
            await self._broadcast_websocket(message)

    async def _broadcast_websocket(self, message: WebSocketMessage):
        if not self.websocket_connections:
            return
        message_data = message.dict()
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message_data, default=ws_json_default))
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)
        self.websocket_connections -= disconnected

    # --- public API ----------------------------------------------------------

    def register_event_handler(self, event_type: EventType, handler: Callable):
        self.event_handlers.setdefault(event_type, []).append(handler)

    def register_message_handler(self, topic: str, handler: Callable):
        self.message_handlers[topic] = handler

    async def send_kafka_message(self, topic: str, message: Any, key: Optional[str] = None):
        if not self.kafka_producer:
            raise RuntimeError("Kafka producer not initialized")
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        await self.kafka_producer.send_and_wait(topic, message, key=key_bytes)
        logger.debug(f"Sent Kafka message to {topic}")

    async def send_mqtt_message(self, topic: str, payload: Any, qos: int = 1):
        if not self.mqtt_client:
            raise RuntimeError("MQTT client not initialized")
        if isinstance(payload, dict):
            payload = json.dumps(payload, default=ws_json_default)
        await self.mqtt_client.publish(topic, payload, qos=qos)

    async def add_websocket_connection(self, websocket):
        self.websocket_connections.add(websocket)

    async def remove_websocket_connection(self, websocket):
        self.websocket_connections.discard(websocket)

    def get_realtime_status(self) -> RealtimeServiceStatus:
        return RealtimeServiceStatus(
            service_type=str(self.service_type),
            service_name=self.name,
            realtime_enabled=bool(self.config.realtime_platform or self.config.kafka_bootstrap_servers),
            websocket_enabled=self.config.websocket_enabled,
            connections=list(self.connections.values()),
            active_streams=self.config.streaming_topics,
            message_count=self.message_count,
            error_count=self.error_count,
            last_activity=self.last_activity,
        )

    def _get_supported_task_types(self) -> List[str]:
        """Retained for parity with scaffolded entrypoints / health probes."""
        return ["stream", "passthrough"]


# Naming-compatibility alias: the scaffold + RT-1 entrypoints reference
# GenericRealtimeAgent. In this package RealtimeAgent is already concrete, so
# the "generic" agent is simply the base.
class GenericRealtimeAgent(RealtimeAgent):
    """Concrete passthrough realtime agent (transport-only, no domain logic)."""
    pass
