"""
Domain Services - Business logic that doesn't belong to a single entity
Contains the core business rules and domain logic
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .models import (AppContainerRequest, Capability, CapabilitySet,
                     InvalidVClusterRequestError, MicroserviceRequest, ParsedCommand, 
                     ResourceSpec, SlackCommand, VClusterRequest, VClusterSize)


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
        VClusterSize.XLARGE: ResourceSpec("8000m", "16Gi", "100Gi", 10),
    }

    def create_vcluster_request(
        self, parsed_command: ParsedCommand, user: str, channel: str, original_text: str
    ) -> VClusterRequest:
        """Create a VCluster request from parsed command."""

        if parsed_command.action != "create":
            raise InvalidVClusterRequestError(
                f"Invalid action for VCluster creation: {parsed_command.action}"
            )

        # Generate name if not provided
        name = parsed_command.vcluster_name
        if not name:
            from datetime import datetime

            name = f"vcluster-{int(datetime.now().timestamp())}"

        # Get resource specifications
        resources = self.RESOURCE_PRESETS[parsed_command.size]

        # Build capability set
        capabilities = self._build_capability_set(
            parsed_command.enabled_capabilities, parsed_command.disabled_capabilities
        )

        return VClusterRequest(
            name=name,
            namespace=parsed_command.namespace,
            user=user,
            slack_channel=channel,
            capabilities=capabilities,
            resources=resources,
            repository=parsed_command.repository,
            original_text=original_text,
        )

    def _build_capability_set(
        self, enabled: List[Capability], disabled: List[Capability]
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
            "backup": False,
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
        if request.repository and not self._is_valid_repository_name(
            request.repository
        ):
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
        if not name.replace("-", "").isalnum():
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
        cpu_value = int(resources.cpu_limit.rstrip("m"))
        if cpu_value < 100 or cpu_value > 16000:
            raise ValueError("CPU limit must be between 100m and 16000m")

        # Memory validation
        if resources.memory_limit.endswith("Gi"):
            memory_value = int(resources.memory_limit.rstrip("Gi"))
            if memory_value < 1 or memory_value > 64:
                raise ValueError("Memory limit must be between 1Gi and 64Gi")

        # Storage validation
        if resources.storage_size.endswith("Gi"):
            storage_value = int(resources.storage_size.rstrip("Gi"))
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
            cap
            for cap, enabled in request.capabilities.to_dict().items()
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
                        "text": "🚀 VCluster Creation Started",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Name:*\n`{request.name}`"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Namespace:*\n`{request.namespace}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Capabilities:*\n{', '.join(enabled_caps)}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Resources:*\nCPU: {request.resources.cpu_limit}, Memory: {request.resources.memory_limit}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Status:* Provisioning started... You'll receive updates as the process progresses.",
                    },
                },
            ],
        }

    def build_error_response(self, error_message: str) -> Dict:
        """Build error response."""
        return {"response_type": "ephemeral", "text": f"❌ {error_message}"}

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
                        "text": "*Available Commands:*\n• `/vcluster create [name] [options]` - Create new VCluster\n• `/vcluster list` - List existing VClusters\n• `/vcluster delete [name]` - Delete VCluster\n• `/vcluster status [name]` - Check VCluster status\n\n*Example:*\n`/vcluster create my-cluster with observability and security in namespace dev`",
                    },
                }
            ],
        }

    def build_appcontainer_success_response(self, request: AppContainerRequest) -> Dict:
        """Build success response for AppContainer creation."""
        return {
            "response_type": "in_channel",
            "text": f"🚀 AppContainer `{request.name}` creation started",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 AppContainer Creation Started",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Name:*\n`{request.name}`"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Namespace:*\n`{request.namespace}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Description:*\n{request.description}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*GitHub Org:*\n{request.github_org}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Observability:*\n{'✅ Enabled' if request.enable_observability else '❌ Disabled'}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Security:*\n{'✅ Enabled' if request.enable_security else '❌ Disabled'}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Status:* AppContainer provisioning started... You'll receive updates as the process progresses.",
                    },
                },
            ],
        }

    def build_appcontainer_help_response(self) -> Dict:
        """Build help response for AppContainer commands."""
        return {
            "response_type": "ephemeral",
            "text": "🤖 AppContainer Management Commands",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `/appcontainer create [name] [options]` - Create new AppContainer\n• `/app-cont create [name] [options]` - Alias for AppContainer creation\n\n*Options:*\n• `description \"text\"` - Set container description\n• `github-org [org]` - Set GitHub organization\n• `namespace [ns]` - Set deployment namespace\n• `without security` - Disable security features\n• `without observability` - Disable observability\n\n*Example:*\n`/appcontainer create my-api description \"REST API service\" github-org mycompany namespace production`",
                    },
                }
            ],
        }

    def build_microservice_success_response(self, request: MicroserviceRequest) -> Dict:
        """Build success response for Microservice creation."""
        return {
            "response_type": "in_channel",
            "text": f"🚀 Microservice `{request.name}` creation started",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 Microservice Creation Started",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Name:*\n`{request.name}`"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Namespace:*\n`{request.namespace}`",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Language:*\n{request.language.value.title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Database:*\n{request.database.value.title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Cache:*\n{request.cache.value.title()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Realtime:*\n{request.realtime or 'None'}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*GitHub Org:*\n{request.github_org}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⏳ *Status:* Creating microservice with complete OAM development environment...\n\n*Will create:*\n• 📚 Repository: `{request.get_repository_name()}`\n• 🔄 GitOps Repository: `{request.get_repository_name()}-gitops`\n• 🔧 VCluster: `{request.get_vcluster_name()}`",
                    },
                },
            ],
        }

    def build_microservice_help_response(self) -> Dict:
        """Build help response for Microservice commands."""
        return {
            "response_type": "ephemeral",
            "text": "🤖 Microservice Management Commands",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n• `/microservice create [name] [options]` - Create new microservice with OAM environment\n• `/service create [name] [options]` - Alias for microservice creation\n\n*Language Options:*\n• `python` or `fastapi` - Python with FastAPI framework\n• `java` or `springboot` - Java with Spring Boot framework\n\n*Database Options:*\n• `with database` or `with postgresql` - PostgreSQL database\n• `without database` - No database (default)\n\n*Cache Options:*\n• `with cache` or `with redis` - Redis cache\n• `without cache` - No cache (default)\n\n*🆕 Realtime Integration:*\n• `realtime [platform-name]` - Integrate with existing realtime platform\n• `platform [platform-name]` - Connect to streaming platform\n• `streaming [platform-name]` - Link to data streaming infrastructure\n• `iot [platform-name]` - Connect to IoT/MQTT platform\n\n*VCluster Options:*\n• `vcluster [name]` - Use existing vCluster\n• `in namespace [name]` - Set deployment namespace\n\n*Examples:*\n• `/microservice create order-service`\n• `/microservice create user-service python with database`\n• `/microservice create payment-service java with redis vcluster finance-cluster`\n• `/microservice create analytics-api realtime health-streaming` 🆕\n• `/microservice create iot-processor python platform sensor-data` 🆕\n• `/microservice create stream-api streaming financial-data with database` 🆕",
                    },
                }
            ],
        }


class OAMWebhookService:
    """Domain service for OAM webhook processing.
    
    This service handles the business logic for processing OAM Applications
    and determining which microservices need to be created.
    """
    
    def __init__(self):
        """Initialize with pattern orchestrator."""
        from .strategies.orchestrator import PatternOrchestrator
        self.orchestrator = None  # Will be set with argo_client
    
    def process_oam_webhook(
        self, 
        request: "OAMWebhookRequest",
        argo_client: Any
    ) -> "OAMWebhookResponse":
        """Process an OAM webhook request using pattern-based orchestration.
        
        This implements the pattern-based approach (3→2→1) - we process
        infrastructure first, then compositional services, then foundational services.
        
        Args:
            request: The OAM webhook request
            argo_client: Infrastructure client for triggering workflows
            
        Returns:
            OAMWebhookResponse with processing results
        """
        from .models import OAMWebhookResponse
        from .strategies.orchestrator import PatternOrchestrator
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Check if we should process this request
        if not request.should_process():
            return OAMWebhookResponse(
                uid=request.uid,
                allowed=True,
                message="Request does not require processing"
            )
        
        # Initialize orchestrator with argo client
        orchestrator = PatternOrchestrator(argo_client)
        
        # Build OAM application dictionary for orchestrator
        oam_app_dict = {
            "metadata": {
                "name": request.oam_application.name,
                "namespace": request.oam_application.namespace,
                "labels": request.oam_application.labels,
                "annotations": request.oam_application.annotations
            },
            "spec": {
                "components": [
                    {
                        "name": comp.name,
                        "type": comp.type,
                        "properties": comp.properties,
                        "traits": comp.traits
                    }
                    for comp in request.oam_application.components
                ]
            }
        }
        
        # Get GitHub owner from labels or use default
        github_owner = request.oam_application.labels.get("github-owner", "shlapolosa")
        
        # Process the application with pattern-based ordering
        logger.info(f"Processing OAM Application {request.oam_application.name} with pattern orchestrator")
        results = orchestrator.handle_oam_application(
            oam_application=oam_app_dict,
            namespace=request.oam_application.namespace,
            vcluster=request.oam_application.get_target_vcluster(),
            github_owner=github_owner
        )
        
        # Get processing summary
        summary = orchestrator.get_processing_summary(results)
        
        # Build response
        triggered_workflows = []
        for workflow in summary.get("workflows_triggered", []):
            triggered_workflows.append(f"{workflow['workflow']}: {workflow['run']}")
        
        # Log any errors
        for error in summary.get("errors", []):
            logger.warning(f"Component processing error: {error}")
        
        message = (
            f"Processed {summary['total']} components "
            f"(Pattern 3: {summary['by_pattern']['pattern_3']['successful']}, "
            f"Pattern 2: {summary['by_pattern']['pattern_2']['successful']}, "
            f"Pattern 1: {summary['by_pattern']['pattern_1']['successful']})"
        )
        
        if summary['failed'] > 0:
            message += f" - {summary['failed']} failed"
        
        return OAMWebhookResponse(
            uid=request.uid,
            allowed=True,
            message=message,
            triggered_workflows=triggered_workflows
        )
