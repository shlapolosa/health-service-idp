"""realtime-transport: role-aware realtime transport machinery.

Standalone extraction of the RT-1 realtime transport from agent_common, WITHOUT
the AI-agent identity baggage. Provides three role factories — ingest, processor,
gateway — that own bytes-in/bytes-out; the developer owns what the bytes mean.
"""

from .config import RealtimeConfig, get_realtime_config
from .models import (
    ws_json_default, RealtimeEvent, EventType, ConnectionStatus,
    RealtimeConnectionInfo, WebSocketMessage, RealtimeServiceStatus,
)
from .realtime_agent import RealtimeAgent, GenericRealtimeAgent
from .realtime_fastapi import (
    create_realtime_agent_app,
    create_realtime_ingest_app,
    create_realtime_processor_app,
)
from .websocket_manager import WebSocketConnectionManager

__version__ = "0.1.1"

__all__ = [
    "RealtimeConfig", "get_realtime_config",
    "ws_json_default", "RealtimeEvent", "EventType", "ConnectionStatus",
    "RealtimeConnectionInfo", "WebSocketMessage", "RealtimeServiceStatus",
    "RealtimeAgent", "GenericRealtimeAgent",
    "create_realtime_agent_app", "create_realtime_ingest_app",
    "create_realtime_processor_app", "WebSocketConnectionManager",
]
