"""Slim configuration for realtime-transport services.

Diverges from agent_common.config: there is NO AGENT_TYPE / IMPLEMENTATION_TYPE
requirement. A transport service (ingest / processor / gateway) is identified by
its ``service_name`` alone. All connection settings come from the binding env the
realtime-service CD injects (KAFKA_BOOTSTRAP_SERVERS, CONSUME_<t>/PRODUCE_<t>,
REALTIME_PLATFORM_NAME, etc.).
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class RealtimeConfig:
    """Configuration for a realtime transport service."""
    service_name: str
    log_level: str = "INFO"
    port: int = 8080
    host: str = "0.0.0.0"

    # Real-time platform
    realtime_platform: Optional[str] = None
    websocket_enabled: bool = False

    # Kafka / streaming
    kafka_bootstrap_servers: Optional[str] = None
    kafka_schema_registry_url: Optional[str] = None
    streaming_topics: List[str] = field(default_factory=list)
    streaming_consumer_group: Optional[str] = None
    produce_topics: List[str] = field(default_factory=list)

    # MQTT
    mqtt_host: Optional[str] = None
    mqtt_port: int = 1883
    mqtt_user: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_topics: List[str] = field(default_factory=list)

    # Redis
    redis_host: Optional[str] = None
    redis_port: int = 6379

    # Database / analytics / stream-processing (carried for secret-loader parity)
    db_host: Optional[str] = None
    db_port: int = 5432
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    metabase_url: Optional[str] = None
    metabase_user: Optional[str] = None
    metabase_password: Optional[str] = None
    lenses_url: Optional[str] = None
    lenses_user: Optional[str] = None
    lenses_password: Optional[str] = None

    custom_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def _resolve_streaming_topics() -> List[str]:
    """Topics the consumer subscribes to.

    Prefer an explicit STREAMING_TOPICS (comma-separated). Otherwise fall back
    to the per-topic CONSUME_<topic> env vars injected by the realtime-service
    CD (RT-1 binding convention), e.g. CONSUME_sensor_agg=sensor_agg. Without
    this the consumer subscribed to nothing and no data ever reached /ws.
    """
    explicit = os.getenv("STREAMING_TOPICS", "")
    if explicit:
        return [t for t in explicit.split(",") if t]
    return sorted(
        v for k, v in os.environ.items() if k.startswith("CONSUME_") and v
    )


def _resolve_produce_topics() -> List[str]:
    """Topics this service produces to.

    From the per-topic PRODUCE_<topic> env vars the realtime-service CD injects
    (e.g. PRODUCE_sensor_raw=sensor_raw). Ingest/processor default their
    produce_topic to the first of these when not explicitly passed.
    """
    return sorted(
        v for k, v in os.environ.items() if k.startswith("PRODUCE_") and v
    )


def get_realtime_config(service_name: Optional[str] = None) -> RealtimeConfig:
    """Build a RealtimeConfig from the binding environment.

    Unlike agent_common.get_agent_config, this requires no agent identity. The
    service_name falls back to SERVICE_NAME env if not supplied.
    """
    name = service_name or os.getenv("SERVICE_NAME", "realtime-service")

    return RealtimeConfig(
        service_name=name,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        port=int(os.getenv("PORT", "8080")),
        host=os.getenv("HOST", "0.0.0.0"),

        # The realtime-service CD injects REALTIME_PLATFORM_NAME (binding
        # convention); honor it so Kafka consumer/producer actually initialize.
        realtime_platform=os.getenv("REALTIME_PLATFORM") or os.getenv("REALTIME_PLATFORM_NAME"),
        websocket_enabled=os.getenv("WEBSOCKET_ENABLED", "false").lower() == "true",

        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        kafka_schema_registry_url=os.getenv("KAFKA_SCHEMA_REGISTRY_URL"),
        streaming_topics=_resolve_streaming_topics(),
        streaming_consumer_group=os.getenv("STREAMING_CONSUMER_GROUP"),
        produce_topics=_resolve_produce_topics(),

        mqtt_host=os.getenv("MQTT_HOST"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_user=os.getenv("MQTT_USER"),
        mqtt_password=os.getenv("MQTT_PASSWORD"),
        mqtt_topics=os.getenv("MQTT_TOPICS", "").split(",") if os.getenv("MQTT_TOPICS") else [],

        redis_host=os.getenv("REDIS_HOST"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),

        db_host=os.getenv("DB_HOST"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        metabase_url=os.getenv("METABASE_URL"),
        metabase_user=os.getenv("METABASE_USER"),
        metabase_password=os.getenv("METABASE_PASSWORD"),
        lenses_url=os.getenv("LENSES_URL"),
        lenses_user=os.getenv("LENSES_USER"),
        lenses_password=os.getenv("LENSES_PASSWORD"),
    )
