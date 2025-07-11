"""
Domain Models - Core business entities and value objects
Contains the fundamental business logic without external dependencies
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class VClusterSize(Enum):
    """VCluster size enumeration."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class Capability(Enum):
    """VCluster capability enumeration."""
    OBSERVABILITY = "observability"
    SECURITY = "security"
    GITOPS = "gitops"
    LOGGING = "logging"
    NETWORKING = "networking"
    AUTOSCALING = "autoscaling"
    BACKUP = "backup"


@dataclass(frozen=True)
class ResourceSpec:
    """Value object for VCluster resource specifications."""
    cpu_limit: str
    memory_limit: str
    storage_size: str
    node_count: int
    
    def __post_init__(self):
        """Validate resource specifications."""
        if not self.cpu_limit.endswith('m'):
            raise ValueError("CPU limit must end with 'm' (millicores)")
        if not (self.memory_limit.endswith('Gi') or self.memory_limit.endswith('Mi')):
            raise ValueError("Memory limit must end with 'Gi' or 'Mi'")
        if not (self.storage_size.endswith('Gi') or self.storage_size.endswith('Ti')):
            raise ValueError("Storage size must end with 'Gi' or 'Ti'")
        if self.node_count < 1:
            raise ValueError("Node count must be at least 1")


@dataclass(frozen=True)
class CapabilitySet:
    """Value object for VCluster capabilities."""
    observability: bool = True
    security: bool = True
    gitops: bool = True
    logging: bool = True
    networking: bool = True
    autoscaling: bool = True
    backup: bool = False
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format expected by GitHub API."""
        return {
            "observability": str(self.observability).lower(),
            "security": str(self.security).lower(),
            "gitops": str(self.gitops).lower(),
            "logging": str(self.logging).lower(),
            "networking": str(self.networking).lower(),
            "autoscaling": str(self.autoscaling).lower(),
            "backup": str(self.backup).lower()
        }


@dataclass
class VClusterRequest:
    """Domain entity representing a VCluster creation request."""
    name: str
    namespace: str
    user: str
    slack_channel: str
    capabilities: CapabilitySet
    resources: ResourceSpec
    repository: Optional[str] = None
    original_text: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now())
        
        # Validate name and namespace (Kubernetes naming conventions)
        self._validate_kubernetes_name(self.name, "name")
        self._validate_kubernetes_name(self.namespace, "namespace")
    
    def _validate_kubernetes_name(self, value: str, field: str) -> None:
        """Validate Kubernetes naming conventions."""
        if not value:
            raise ValueError(f"{field} cannot be empty")
        if len(value) > 63:
            raise ValueError(f"{field} cannot exceed 63 characters")
        if not value.replace('-', '').isalnum():
            raise ValueError(f"{field} must contain only alphanumeric characters and hyphens")
        if not value[0].isalnum() or not value[-1].isalnum():
            raise ValueError(f"{field} must start and end with alphanumeric characters")
    
    def to_github_payload(self) -> Dict:
        """Convert to GitHub repository dispatch payload."""
        return {
            "event_type": "slack_create_vcluster",
            "client_payload": {
                "vcluster_name": self.name,
                "namespace": self.namespace,
                "repository": self.repository or "",
                "user": self.user,
                "slack_channel": self.slack_channel,
                "slack_user_id": self.user,
                "capabilities": self.capabilities.to_dict(),
                "resources": {
                    "cpu_limit": self.resources.cpu_limit,
                    "memory_limit": self.resources.memory_limit,
                    "storage_size": self.resources.storage_size,
                    "node_count": str(self.resources.node_count)
                },
                "original_request": self.original_text or "",
                "created_at": self.created_at.isoformat()
            }
        }


@dataclass
class SlackCommand:
    """Domain entity representing a Slack slash command."""
    command: str
    text: str
    user_id: str
    user_name: str
    channel_id: str
    channel_name: str
    team_id: str
    team_domain: str
    timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now())


@dataclass
class ParsedCommand:
    """Value object representing a parsed command result."""
    action: str  # create, list, delete, status, help
    vcluster_name: Optional[str] = None
    namespace: str = "default"
    repository: Optional[str] = None
    size: VClusterSize = VClusterSize.MEDIUM
    enabled_capabilities: List[Capability] = None
    disabled_capabilities: List[Capability] = None
    parsing_method: str = "regex"
    
    def __post_init__(self):
        """Initialize default values."""
        if self.enabled_capabilities is None:
            object.__setattr__(self, 'enabled_capabilities', [])
        if self.disabled_capabilities is None:
            object.__setattr__(self, 'disabled_capabilities', [])


# Domain exceptions
class DomainError(Exception):
    """Base domain exception."""
    pass


class InvalidVClusterRequestError(DomainError):
    """Raised when VCluster request is invalid."""
    pass


class InvalidSlackCommandError(DomainError):
    """Raised when Slack command is invalid."""
    pass


class ParsingError(DomainError):
    """Raised when command parsing fails."""
    pass