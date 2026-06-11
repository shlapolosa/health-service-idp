"""Transport-only data models for the realtime-transport package.

This is the subset of agent_common.models that the realtime transport path
actually uses. The AI-agent identity models (AgentType, ImplementationType,
AgentRequest/Response, HealthData, etc.) are intentionally absent: this package
carries bytes between Kafka/MQTT/WebSocket, not agent semantics.
"""

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, date

from pydantic import BaseModel, Field


def ws_json_default(o: Any) -> Any:
    """json.dumps default= for WebSocket payloads.

    Real-time event payloads carry Enum (e.g. EventType) and datetime values
    (RealtimeEvent.timestamp) that the stdlib JSON encoder rejects, which made
    every streamed broadcast fail ('Object of type datetime/EventType is not
    JSON serializable') and silently dropped delivery to /ws clients (RT-1 #167).
    """
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    return str(o)


class EventType(Enum):
    """Types of real-time events."""
    AGENT_TASK_STARTED = "agent_task_started"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    AGENT_TASK_FAILED = "agent_task_failed"
    DATA_PROCESSED = "data_processed"
    ALERT_TRIGGERED = "alert_triggered"
    STATUS_UPDATE = "status_update"
    SYSTEM_EVENT = "system_event"
    CUSTOM_EVENT = "custom_event"


class ConnectionStatus(Enum):
    """Connection status for real-time backing services."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class RealtimeEvent:
    """Real-time event data structure."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CUSTOM_EVENT
    source_service: str = ""
    source_agent: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    stream_id: Optional[str] = None
    priority: int = 1  # 1=low, 2=medium, 3=high


class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    payload: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    response_to: Optional[str] = None


class RealtimeConnectionInfo(BaseModel):
    """Information about real-time backing-service connections."""
    service_name: str
    connection_type: str  # kafka, mqtt, websocket, redis
    status: ConnectionStatus
    endpoint: str
    connected_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class RealtimeServiceStatus(BaseModel):
    """Real-time status for a transport service.

    All identity fields are plain strings: this package has no AgentType /
    ImplementationType enums. ``service_name`` is the only identity the
    transport needs; ``service_type`` is a free-form descriptor.
    """
    service_type: str
    service_name: str
    realtime_enabled: bool
    websocket_enabled: bool
    connections: List[RealtimeConnectionInfo] = Field(default_factory=list)
    active_streams: List[str] = Field(default_factory=list)
    message_count: int = 0
    error_count: int = 0
    last_activity: Optional[datetime] = None
