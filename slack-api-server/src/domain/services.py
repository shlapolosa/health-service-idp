"""
Domain Services - Business logic that doesn't belong to a single entity
Contains the core business rules and domain logic
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from .models import (
    VClusterRequest, SlackCommand, ParsedCommand, VClusterSize, 
    Capability, CapabilitySet, ResourceSpec, InvalidVClusterRequestError
)


class CommandParserInterface(ABC):
    """Interface for parsing Slack commands into domain objects."""
    
    @abstractmethod
    def parse_command(self, command: SlackCommand) -> ParsedCommand:
        """Parse a Slack command into a structured format."""
        pass


class VClusterFactoryService:
    """Domain service for creating VCluster requests."""
    
    # Resource presets by size
    RESOURCE_PRESETS = {
        VClusterSize.SMALL: ResourceSpec("1000m", "2Gi", "10Gi", 1),
        VClusterSize.MEDIUM: ResourceSpec("2000m", "4Gi", "20Gi", 3),
        VClusterSize.LARGE: ResourceSpec("4000m", "8Gi", "50Gi", 5),
        VClusterSize.XLARGE: ResourceSpec("8000m", "16Gi", "100Gi", 10)
    }
    
    def create_vcluster_request(
        self, 
        parsed_command: ParsedCommand, 
        user: str, 
        channel: str,
        original_text: str
    ) -> VClusterRequest:
        """Create a VCluster request from parsed command."""
        
        if parsed_command.action != "create":
            raise InvalidVClusterRequestError(f"Invalid action for VCluster creation: {parsed_command.action}")
        
        # Generate name if not provided
        name = parsed_command.vcluster_name
        if not name:
            from datetime import datetime
            name = f"vcluster-{int(datetime.now().timestamp())}"
        
        # Get resource specifications
        resources = self.RESOURCE_PRESETS[parsed_command.size]
        
        # Build capability set
        capabilities = self._build_capability_set(
            parsed_command.enabled_capabilities,
            parsed_command.disabled_capabilities
        )
        
        return VClusterRequest(
            name=name,
            namespace=parsed_command.namespace,
            user=user,
            slack_channel=channel,
            capabilities=capabilities,
            resources=resources,
            repository=parsed_command.repository,
            original_text=original_text
        )
    
    def _build_capability_set(
        self, 
        enabled: List[Capability], 
        disabled: List[Capability]
    ) -> CapabilitySet:
        """Build capability set from enabled/disabled lists."""
        
        # Start with defaults (all true except backup)
        capabilities = {
            "observability": True,
            "security": True,
            "gitops": True,
            "logging": True,
            "networking": True,
            "autoscaling": True,
            "backup": False
        }
        
        # Apply explicit enables
        for capability in enabled:
            capabilities[capability.value] = True
        
        # Apply explicit disables
        for capability in disabled:
            capabilities[capability.value] = False
        
        return CapabilitySet(**capabilities)


class VClusterValidationService:
    """Domain service for validating VCluster requests."""
    
    def validate_request(self, request: VClusterRequest) -> Tuple[bool, List[str]]:
        """Validate a VCluster request and return validation result."""
        errors = []
        
        # Name validation
        if not self._is_valid_kubernetes_name(request.name):
            errors.append(f"Invalid VCluster name: {request.name}")
        
        # Namespace validation  
        if not self._is_valid_kubernetes_name(request.namespace):
            errors.append(f"Invalid namespace: {request.namespace}")
        
        # Repository validation
        if request.repository and not self._is_valid_repository_name(request.repository):
            errors.append(f"Invalid repository name: {request.repository}")
        
        # Resource validation
        try:
            self._validate_resources(request.resources)
        except ValueError as e:
            errors.append(str(e))
        
        return len(errors) == 0, errors
    
    def _is_valid_kubernetes_name(self, name: str) -> bool:
        """Check if name follows Kubernetes naming conventions."""
        if not name or len(name) > 63:
            return False
        if not name.replace('-', '').isalnum():
            return False
        if not name[0].isalnum() or not name[-1].isalnum():
            return False
        return True
    
    def _is_valid_repository_name(self, name: str) -> bool:
        """Check if repository name is valid."""
        if not name:
            return True  # Repository is optional
        return self._is_valid_kubernetes_name(name)
    
    def _validate_resources(self, resources: ResourceSpec) -> None:
        """Validate resource specifications."""
        # CPU validation
        cpu_value = int(resources.cpu_limit.rstrip('m'))
        if cpu_value < 100 or cpu_value > 16000:
            raise ValueError("CPU limit must be between 100m and 16000m")
        
        # Memory validation
        if resources.memory_limit.endswith('Gi'):
            memory_value = int(resources.memory_limit.rstrip('Gi'))
            if memory_value < 1 or memory_value > 64:
                raise ValueError("Memory limit must be between 1Gi and 64Gi")
        
        # Storage validation
        if resources.storage_size.endswith('Gi'):
            storage_value = int(resources.storage_size.rstrip('Gi'))
            if storage_value < 1 or storage_value > 1000:
                raise ValueError("Storage size must be between 1Gi and 1000Gi")
        
        # Node count validation
        if resources.node_count < 1 or resources.node_count > 20:
            raise ValueError("Node count must be between 1 and 20")


class SlackResponseBuilderService:
    """Domain service for building Slack responses."""
    
    def build_success_response(self, request: VClusterRequest) -> Dict:
        """Build success response for VCluster creation."""
        enabled_caps = [
            cap for cap, enabled in request.capabilities.to_dict().items() 
            if enabled == "true"
        ]
        
        return {
            "response_type": "in_channel",
            "text": f"🚀 VCluster `{request.name}` creation started",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 VCluster Creation Started"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Name:*\n`{request.name}`"
                        },
                        {
                            "type": "mrkdwn", 
                            "text": f"*Namespace:*\n`{request.namespace}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Capabilities:*\n{', '.join(enabled_caps)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Resources:*\nCPU: {request.resources.cpu_limit}, Memory: {request.resources.memory_limit}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Status:* Provisioning started... You'll receive updates as the process progresses."
                    }
                }
            ]
        }
    
    def build_error_response(self, error_message: str) -> Dict:
        """Build error response."""
        return {
            "response_type": "ephemeral",
            "text": f"❌ {error_message}"
        }
    
    def build_help_response(self) -> Dict:
        """Build help response."""
        return {
            "response_type": "ephemeral",
            "text": "🤖 VCluster Management Commands",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `/vcluster create [name] [options]` - Create new VCluster\n• `/vcluster list` - List existing VClusters\n• `/vcluster delete [name]` - Delete VCluster\n• `/vcluster status [name]` - Check VCluster status\n\n*Example:*\n`/vcluster create my-cluster with observability and security in namespace dev`"
                    }
                }
            ]
        }